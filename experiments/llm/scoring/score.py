"""Score LLM T2A-ESS extractions against the gold fixtures (scorer version 3.1).

Alignment (per slot type): score(g, p) = 0.8 * sim(label) + 0.2 * sim(auxiliary fields). Two matchers:
  embedding (primary): cosine of intfloat/multilingual-e5-large mean-pooled embeddings ("query: " prefix),
                       threshold TAU_EMB (calibrated on the pilot; sensitivity reported);
  lexical (baseline):  Dice coefficient of character bigrams after NFKC/lowercase/punctuation removal, TAU_LEX.
Structural evidence overrides label similarity where the schema fixes a slot by its endpoints: after the
endpoint slots are aligned, a transition pair whose mapped from/to situations coincide, a flow pair whose
mapped flow_source/flow_target actions coincide, and a control pair governing the same mapped flow score 1.0.
Pairs are assigned by the Hungarian algorithm per type and kept when score >= threshold. Source units are
deliberately NOT used for alignment, so that source_ref accuracy can be measured independently afterwards.

Scored slot types: scenarios, episodes, performers, actions, items, flows, controls, situations, state_values,
events, transitions, constraints, goals, reasons, observations. Domain extension rules and semantic bindings
(schema-internal extension slots, not requested by the prompt) are excluded, together with their relations.

Relations: a predicted relation is a true positive when both endpoints are aligned and the mapped triple is in
the gold set. "strict" compares relation types as written (custom relations by custom_relation_type);
"normalized" first maps legacy/synonym names to the schema catalog (produces->produces_item, uses->uses_item,
triggered_by->triggers with direction reversed, precedes->temporal_before, has_action/contains->contains_action);
"untyped" ignores type and direction.

Scorer v2 (2026-09-26, after the P1 diagnosis):
  * a slot without `label` (all MUM-T and most NGHE gold state values carry only subject/variable/value) is
    compared through its display text "subject variable value unit" instead of an empty label;
  * a granularity-tolerant view is reported next to the one-to-one alignment: gold coverage (share of gold slots
    with at least one predicted slot above threshold) and predicted support (share of predicted slots with at
    least one gold slot above threshold), so that an action split into two finer actions is not counted wrong.
The one-to-one alignment stays the primary metric and is otherwise unchanged.

usage: python score.py <repository-root> <run.json> [...]      -> writes <run>.score.json next to each run

t2a-ess copy of scorer v3.1 (paper evidence, pipelines/dep/scoring/score.py): only the coverage-file lookup
changed (manifest fields `coverage`, `coverage_key`); alignment, thresholds, and normalization are unchanged.
"""
import itertools, json, os, re, sys, unicodedata
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import linear_sum_assignment

HERE = os.path.dirname(os.path.abspath(__file__))
TAU_LEX = 0.5
TAU_EMB = 0.87
TAU_FLOW_LABEL = 0.93
MATCHER = os.environ.get("T2A_MATCHER", "embedding")
TAU = float(os.environ.get("T2A_TAU", TAU_EMB if MATCHER == "embedding" else TAU_LEX))
# endpoint slots must be aligned before the slots they anchor
ORDER = ["scenarios", "episodes", "performers", "items", "situations", "state_values", "events", "actions",
         "constraints", "goals", "reasons", "observations", "transitions", "flows", "controls"]
STRUCTURAL = {"transitions": ("from_situation", "to_situation"), "flows": ("flow_source", "flow_target"),
              "controls": ("controls_flow",)}
SCORED = ["scenarios", "episodes", "performers", "actions", "items", "flows", "controls", "situations",
          "state_values", "events", "transitions", "constraints", "goals", "reasons", "observations"]
ID_FIELD = {c: c[:-1] + "_id" for c in SCORED}
ID_FIELD.update({"state_values": "state_value_id", "scenarios": "scenario_id", "episodes": "episode_id"})
AUX = {
    "actions": ["primary_actor_text", "object_text"],
    "transitions": ["from_situation_text", "to_situation_text", "trigger_text"],
    "state_values": ["variable", "value"],
    "observations": ["observer_text", "observed_text"],
    "controls": ["guard_texts"],
    "constraints": ["expression_text"],
}
EXCLUDED_RELS = {"binds_to", "custom/has_binding", "has_binding"}
SYNONYMS = {"produces": "produces_item", "uses": "uses_item", "precedes": "temporal_before",
            "has_action": "contains_action", "contains": "contains_action", "action_target": "acts_on"}
CONTRACT = {"has_episode", "contains_action", "has_situation", "entry_situation", "exit_situation", "has_part",
            "performed_by", "acts_on", "provided_to", "uses_item", "produces_item", "flow_source", "flow_target",
            "carries_item", "controls_flow", "temporal_before", "temporal_after", "temporal_during", "temporal_while",
            "temporal_overlaps", "temporal_starts_with", "temporal_ends_with", "has_state_value", "from_situation",
            "to_situation", "observes", "triggers", "causes_event", "originates_event", "causes", "constrained_by",
            "has_goal", "has_reason", "has_evidence", "has_binding", "binds_to"}
REVERSED = {"triggered_by": "triggers"}
SKIP_TEXT_KEYS = {"text", "surface_text", "source_text", "source_ref", "source_refs", "evidence", "interpretation_uncertainty"}


def norm(s):
    s = unicodedata.normalize("NFKC", str(s)).lower()
    return re.sub(r"[\s\W_]+", "", s)


def bigrams(s):
    s = norm(s)
    return Counter(s[i:i + 2] for i in range(len(s) - 1)) if len(s) > 1 else Counter([s]) if s else Counter()


class Embedder:
    """multilingual-e5-large mean-pooled embeddings, cached on disk by text."""
    def __init__(self):
        self.cache_path = os.path.join(HERE, "cache", "e5_large_embeddings.json")
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        self.cache = json.load(open(self.cache_path, encoding="utf-8")) if os.path.exists(self.cache_path) else {}
        self.model = None
        self.dirty = False
        import atexit
        atexit.register(self.save)  # write the cache once per process (I/O only; scores are unaffected)

    def save(self):
        if self.dirty:
            json.dump(self.cache, open(self.cache_path, "w", encoding="utf-8"))
            self.dirty = False

    def _load(self):
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-large")
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = AutoModel.from_pretrained("intfloat/multilingual-e5-large").to(dev).eval()
        self.dev = dev

    def vectors(self, texts):
        missing = [t for t in dict.fromkeys(texts) if t not in self.cache]
        if missing:
            if self.model is None:
                self._load()
            F = self.torch.nn.functional
            for k in range(0, len(missing), 64):
                chunk = missing[k:k + 64]
                b = self.tok(["query: " + t for t in chunk], padding=True, truncation=True, max_length=128, return_tensors="pt").to(self.dev)
                with self.torch.no_grad():
                    o = self.model(**b).last_hidden_state
                m = b["attention_mask"].unsqueeze(-1)
                v = F.normalize((o * m).sum(1) / m.sum(1), dim=-1).cpu().numpy()
                for t, vec in zip(chunk, v):
                    self.cache[t] = [round(float(x), 6) for x in vec]
            self.dirty = True
        return np.array([self.cache[t] for t in texts])


EMB = Embedder() if MATCHER == "embedding" else None


def sim_matrix(xs, ys):
    """Pairwise similarity of two string lists under the active matcher; empty strings score 0."""
    if not xs or not ys:
        return np.zeros((len(xs), len(ys)))
    if EMB is None:
        return np.array([[dice(x, y) for y in ys] for x in xs])
    xe = [x if x.strip() else " " for x in xs]
    ye = [y if y.strip() else " " for y in ys]
    M = EMB.vectors(xe) @ EMB.vectors(ye).T
    for i, x in enumerate(xs):
        if not x.strip():
            M[i, :] = 0
    for j, y in enumerate(ys):
        if not y.strip():
            M[:, j] = 0
    return M


def dice(a, b):
    A, B = bigrams(a), bigrams(b)
    if not A or not B:
        return 0.0
    return 2 * sum((A & B).values()) / (sum(A.values()) + sum(B.values()))


def flat(v):
    if isinstance(v, dict):
        return " ".join(flat(x) for k, x in v.items() if k not in ("value_type", "normalized"))
    if isinstance(v, list):
        return " ".join(flat(x) for x in v)
    return "" if v is None else str(v)


def units_of(slot, para_map=None):
    refs = []
    for key in ("source_ref", "source_refs"):
        v = slot.get(key)
        for r in (v if isinstance(v, list) else [v] if v else []):
            refs.append(r.get("source_unit_id") if isinstance(r, dict) else r)
    out = set()
    for r in refs:
        if r is None:
            continue
        if para_map is None:
            out.add(r)
        else:
            out.update(para_map.get(str(r), []))
    return out


def load_json_text(text):
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1].rsplit("```", 1)[0]
    s = s[s.find("{"):s.rfind("}") + 1]
    return json.loads(s)


def rel_key(r, normalize):
    t = r.get("relation_type", "")
    if t == "custom":
        t = "custom/" + str(r.get("custom_relation_type", ""))
    s, o = r.get("source_slot_id"), r.get("target_slot_id")
    if normalize:
        if t in REVERSED:
            t, s, o = REVERSED[t], o, s
        if t.startswith("custom/") and (t[7:] in CONTRACT or t[7:] in SYNONYMS):
            t = t[7:]
        t = SYNONYMS.get(t, t)
    return s, t, o


def slots_by_type(model):
    out = {}
    for c in SCORED:
        items = []
        for x in model.get(c, []) or []:
            if isinstance(x, dict) and x.get(ID_FIELD[c]):
                items.append(x)
        out[c] = items
    return out


def disp(slot):
    """Label, or for label-less slots (e.g. gold state values) the text "subject variable value unit"."""
    lab = slot.get("label")
    if lab:
        return str(lab)
    return " ".join(flat(slot.get(k)) for k in ("subject_text", "variable", "value", "unit") if slot.get(k) not in (None, "")).strip()


def type_tau(ctype):
    # flow labels are formulaic ("B after A"), so a flow matched on its label alone needs a stricter threshold;
    # a structural (endpoint) match scores 1.0 and always passes (calibrated on the AV-easy pilot, then frozen)
    return max(TAU, TAU_FLOW_LABEL) if ctype == "flows" and MATCHER == "embedding" else TAU


def endpoints(model_rels, slot_id, rtypes, mapping=None):
    out = []
    for rt in rtypes:
        tg = sorted(str(r.get("target_slot_id")) for r in model_rels
                    if r.get("source_slot_id") == slot_id and r.get("relation_type") == rt)
        out.append(tuple(sorted(mapping.get(t, "?" + t) for t in tg)) if mapping is not None else tuple(tg))
    return tuple(out)


def align(gold_slots, pred_slots, ctype, gold_rels=(), pred_rels=(), mapping=None):
    if not gold_slots or not pred_slots:
        return [], np.zeros((len(gold_slots), len(pred_slots)))
    idf = ID_FIELD[ctype]
    lab = sim_matrix([disp(g) for g in gold_slots], [disp(p) for p in pred_slots])
    aux = AUX.get(ctype, [])
    if aux:
        ga = [" ".join(flat(g.get(k)) for k in aux).strip() for g in gold_slots]
        pa = [" ".join(flat(p.get(k)) for k in aux).strip() for p in pred_slots]
        A = sim_matrix(ga, pa)
        has = np.outer([bool(x) for x in ga], [bool(y) for y in pa])
        S = np.where(has, 0.8 * lab + 0.2 * A, lab)
    else:
        S = lab
    if ctype in STRUCTURAL and mapping is not None:
        rts = STRUCTURAL[ctype]
        ge = [endpoints(gold_rels, g[idf], rts) for g in gold_slots]
        pe = [endpoints(pred_rels, p[idf], rts, mapping) for p in pred_slots]
        for i, e in enumerate(ge):
            if not all(e):
                continue
            for j, f in enumerate(pe):
                if e == f:
                    S[i, j] = 1.0
    rows, cols = linear_sum_assignment(-S)
    tau = type_tau(ctype)
    return [(i, j, S[i, j]) for i, j in zip(rows, cols) if S[i, j] >= tau], S


def prf(tp, npred, ngold):
    p = tp / npred if npred else 0.0
    r = tp / ngold if ngold else 0.0
    return {"tp": tp, "pred": npred, "gold": ngold, "precision": round(p, 4), "recall": round(r, 4),
            "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0}


def score_run(head, run_path):
    run = json.load(open(run_path, encoding="utf-8"))
    # t2a-ess: T2A_MANIFEST selects another gold manifest (e.g. the schema-granularity gold); default unchanged
    manifest = json.load(open(os.environ.get("T2A_MANIFEST") or os.path.join(HERE, "inputs", "manifest.json"), encoding="utf-8"))
    info = manifest[run["meta"]["input"]]
    gold = json.load(open(os.path.join(head, info["gold"]), encoding="utf-8-sig"))["text2activity_extraction_model"]
    result = {"meta": run["meta"], "tau": TAU}
    try:
        pred = load_json_text(run["result_text"] or "")
        pred = pred.get("text2activity_extraction_model", pred)
        result["parse_ok"] = True
    except Exception as e:  # noqa: BLE001
        result.update(parse_ok=False, parse_error=str(e)[:300])
        return result

    G, P = slots_by_type(gold), slots_by_type(pred)
    mapping, per_type, pairs = {}, {}, []
    tp_all = np_all = ng_all = 0
    gold_rels_all = gold.get("slot_relations", []) or []
    pred_rels_all = pred.get("slot_relations", []) or []
    tolerant, cov_all, sup_all = {}, 0, 0
    for c in ORDER:
        matched, M = align(G[c], P[c], c, gold_rels_all, pred_rels_all, mapping)
        tau_c = type_tau(c)
        cov = int((M.max(axis=1) >= tau_c).sum()) if M.size else 0
        sup = int((M.max(axis=0) >= tau_c).sum()) if M.size else 0
        cr = cov / len(G[c]) if G[c] else 0.0
        sp = sup / len(P[c]) if P[c] else 0.0
        tolerant[c] = {"gold_coverage": round(cr, 4), "pred_support": round(sp, 4),
                       "f1": round(2 * cr * sp / (cr + sp), 4) if cr + sp else 0.0, "gold": len(G[c]), "pred": len(P[c])}
        cov_all += cov; sup_all += sup
        for i, j, s in matched:
            gid, pid = G[c][i][ID_FIELD[c]], P[c][j][ID_FIELD[c]]
            mapping[pid] = gid
            pairs.append({"type": c, "gold": gid, "gold_label": disp(G[c][i]), "pred": pid,
                          "pred_label": disp(P[c][j]), "score": round(float(s), 3)})
        per_type[c] = prf(len(matched), len(P[c]), len(G[c]))
        tp_all += len(matched); np_all += len(P[c]); ng_all += len(G[c])
    per_type = {c: per_type[c] for c in SCORED}
    result["matcher"] = MATCHER
    result["scorer_version"] = "3.1"
    crm = cov_all / ng_all if ng_all else 0.0
    spm = sup_all / np_all if np_all else 0.0
    result["slots_tolerant"] = {"micro": {"gold_coverage": round(crm, 4), "pred_support": round(spm, 4),
                                          "f1": round(2 * crm * spm / (crm + spm), 4) if crm + spm else 0.0},
                                "per_type": {c: tolerant[c] for c in SCORED}}
    result["slots"] = {"micro": prf(tp_all, np_all, ng_all), "per_type": per_type,
                       "macro_f1": round(float(np.mean([v["f1"] for v in per_type.values() if v["gold"]])), 4)}
    result["alignment_pairs"] = pairs

    # cross-type confusion among slots left unmatched
    gold_left = [(c, g) for c in SCORED for g in G[c] if g[ID_FIELD[c]] not in mapping.values()]
    pred_left = [(c, p) for c in SCORED for p in P[c] if p[ID_FIELD[c]] not in mapping]
    confusion = Counter()
    if gold_left and pred_left:
        S = sim_matrix([disp(g) for _, g in gold_left], [disp(p) for _, p in pred_left])
        for i, j in zip(*linear_sum_assignment(-S)):
            if S[i, j] >= TAU and gold_left[i][0] != pred_left[j][0]:
                confusion[f"{gold_left[i][0]}->{pred_left[j][0]}"] += 1
    result["type_confusion"] = dict(confusion)

    # source_ref accuracy on aligned pairs
    para_map = info["paragraph_to_units"]
    gold_by_id = {g[ID_FIELD[c]]: g for c in SCORED for g in G[c]}
    pred_by_id = {p[ID_FIELD[c]]: p for c in SCORED for p in P[c]}
    hit = tot = 0
    for pid, gid in mapping.items():
        gu, pu = units_of(gold_by_id[gid]), units_of(pred_by_id[pid], para_map)
        if gu:
            tot += 1
            hit += bool(gu & pu)
    result["source_ref_accuracy"] = {"correct": hit, "aligned_with_gold_ref": tot, "accuracy": round(hit / tot, 4) if tot else None}

    # relations
    gold_ids = set(gold_by_id)
    gold_rels = [r for r in gold.get("slot_relations", []) if r.get("source_slot_id") in gold_ids
                 and r.get("target_slot_id") in gold_ids and rel_key(r, False)[1] not in EXCLUDED_RELS]
    pred_rels = pred.get("slot_relations", []) or []
    rel = {}
    unscored = {x.get(k) for c, k in (("semantic_bindings", "semantic_binding_id"), ("domain_extension_rules", "domain_extension_rule_id"))
                for x in (pred.get(c) or []) if isinstance(x, dict)} - {None}
    pred_rels_scored = [r for r in pred_rels if r.get("source_slot_id") not in unscored and r.get("target_slot_id") not in unscored
                        and rel_key(r, False)[1] not in EXCLUDED_RELS and rel_key(r, True)[1] not in EXCLUDED_RELS]
    for mode, normalize in (("strict", False), ("normalized", True)):
        gset = {rel_key(r, normalize) for r in gold_rels}
        pset = set()
        for r in pred_rels_scored:
            s, t, o = rel_key(r, normalize)
            pset.add((mapping.get(s, "?" + str(s)), t, mapping.get(o, "?" + str(o))))
        tp = gset & pset
        by_type = {}
        for t in sorted({k[1] for k in gset}):
            gt = {k for k in gset if k[1] == t}
            by_type[t] = {"gold": len(gt), "recalled": len(gt & tp)}
        rel[mode] = {**prf(len(tp), len(pset), len(gset)), "recall_by_type": by_type}
    gu = {frozenset((r["source_slot_id"], r["target_slot_id"])) for r in gold_rels}
    pu = {frozenset((mapping.get(r.get("source_slot_id"), "?"), mapping.get(r.get("target_slot_id"), "??"))) for r in pred_rels_scored}
    rel["untyped"] = prf(len(gu & pu), len(pu), len(gu))
    result["relations"] = rel

    # coverage requirements: atomic facts over slot content (source text copies excluded) and required/forbidden relations
    # t2a-ess: the manifest names the coverage file and its key (English data layout); no file -> no requirements
    cov_path = os.path.join(head, info["coverage"]) if info.get("coverage") else None
    cov = json.load(open(cov_path, encoding="utf-8")) if cov_path and os.path.exists(cov_path) else {}
    dom = info.get("coverage_key", "")
    req = cov.get(dom, {})

    def slot_text(v):
        if isinstance(v, dict):
            return " ".join(slot_text(x) for k, x in v.items() if k not in SKIP_TEXT_KEYS)
        if isinstance(v, list):
            return " ".join(slot_text(x) for x in v)
        return str(v) if isinstance(v, (str, int, float)) else ""
    content = " ".join(slot_text(P[c]) for c in SCORED)
    facts = {name: bool(re.search(pat, content)) for name, pat in req.get("required_text_patterns", {}).items()}
    result["atomic_facts"] = {"found": sum(facts.values()), "total": len(facts), "missing": [k for k, v in facts.items() if not v]}
    mapped_pred = {rel_key({**r, "source_slot_id": mapping.get(r.get("source_slot_id")), "target_slot_id": mapping.get(r.get("target_slot_id"))}, True)
                   for r in pred_rels}

    def spec_key(spec):
        s, t, o = spec
        return rel_key({"relation_type": "custom", "custom_relation_type": t.split(":", 1)[1], "source_slot_id": s,
                        "target_slot_id": o} if t.startswith("custom:") else {"relation_type": t, "source_slot_id": s,
                        "target_slot_id": o}, True)
    rq = [spec_key(x) for x in req.get("required_relations", [])]
    fb = [spec_key(x) for x in req.get("forbidden_relations", [])]
    result["required_relations"] = {"hit": sum(k in mapped_pred for k in rq), "total": len(rq)}
    result["forbidden_relations"] = {"violated": sum(k in mapped_pred for k in fb), "total": len(fb)}

    # structural: episode coverage (nested vs flat), allocation coverage, dangling predicted relations
    pids = set(pred_by_id)
    actions = {p["action_id"] for p in P["actions"]}
    contained = {r["target_slot_id"] for r in pred_rels if rel_key(r, True)[1] == "contains_action"}
    allocated = {r["source_slot_id"] for r in pred_rels if r.get("relation_type") == "performed_by"}
    result["structure"] = {
        "actions": len(actions), "actions_in_episode": len(actions & contained), "actions_allocated": len(actions & allocated),
        "nested_mode": bool(actions) and actions <= contained,
        "dangling_relations": sum(1 for r in pred_rels if r.get("source_slot_id") not in pids or r.get("target_slot_id") not in pids),
        "relations": len(pred_rels),
    }
    return result


def main():
    head, runs = sys.argv[1], sys.argv[2:]
    for path in runs:
        res = score_run(head, path)
        out = path[:-5] + os.environ.get("T2A_SCORE_SUFFIX", ".score.json")
        json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if not res.get("parse_ok"):
            print(os.path.basename(path), "PARSE FAIL", res.get("parse_error"))
            continue
        s, r = res["slots"]["micro"], res["relations"]
        print(os.path.basename(path), f"slots P/R/F1 {s['precision']:.2f}/{s['recall']:.2f}/{s['f1']:.2f}",
              f"rel(norm) {r['normalized']['precision']:.2f}/{r['normalized']['recall']:.2f}/{r['normalized']['f1']:.2f}",
              f"rel(untyped) F1 {r['untyped']['f1']:.2f}", f"facts {res['atomic_facts']['found']}/{res['atomic_facts']['total']}",
              f"srcref {res['source_ref_accuracy']['accuracy']}", res["structure"])


if __name__ == "__main__":
    main()
