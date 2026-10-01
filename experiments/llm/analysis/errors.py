"""Error taxonomy of single-pass extraction on the nine sealed scenarios (sealed2-A, sealed3-A, sealed4-A), scorer v3.1.

Every gold slot the scorer leaves unmatched (FN) and every predicted slot it leaves unmatched (FP) gets one category,
checked in this order:
  (flows, transitions, controls: "endpoint" if an endpoint slot is not aligned, else "edge" - wrong or missing edge)
  type      - a leftover slot of another type on the other side shares most content words (containment >= 0.6)
  near      - a leftover slot of the same type on the other side shares at least a third of its content words
  granular  - an already matched slot of the same type on the other side shares at least half of its content words:
              one side split or merged what the other kept whole
  supported - FP only: no counterpart, but most content words of the label occur in its source paragraph (extra slot
              stated in the text)
  missing / unsupported - otherwise
Relations: FN/FP whose endpoint slots are not both aligned are "endpoint" errors (they follow from a slot error); the
others are "relation" errors, split into "type" (same endpoints, other relation type), "reversed", and "other".
usage: python experiments/llm/analysis/errors.py [--sample N]   -> results/errors.json, results/errors_sample.json
"""
import glob, json, os, random, re, sys
from collections import Counter, defaultdict
import numpy as np  # noqa: F401
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scoring"))  # t2a-ess: experiments/llm/scoring
import score as S  # noqa: E402
import common as C  # noqa: E402

MAN = json.load(open(os.path.join(C.LLM, "scoring", "inputs", "manifest.json"), encoding="utf-8"))
RESULTS = os.path.join(HERE, "results")
NEAR = 0.80


def words(t):
    return [w for w in re.findall(r"[0-9A-Za-z가-힣]+", t or "") if len(w) >= 2]


def overlap(a, b):
    A, B = words(a), words(b)
    if not A or not B:
        return 0.0
    hit = sum(1 for w in A if any(w == v or (len(w) > 2 and len(v) > 2 and (w[:-1] == v[:-1] or w in v or v in w)) for v in B))
    return hit / min(len(A), len(B))


def supported(label, para):
    ws = words(label)
    if not ws:
        return False
    hit = sum(1 for w in ws if w in para or (len(w) > 2 and w[:-1] in para))
    return hit / len(ws) >= 0.6


def analyse(run_path, gold):
    pred = S.load_json_text(json.load(open(run_path, encoding="utf-8"))["result_text"])
    pred = pred.get("text2activity_extraction_model", pred)
    G, P = S.slots_by_type(gold), S.slots_by_type(pred)
    grel, prel = gold.get("slot_relations", []) or [], pred.get("slot_relations", []) or []
    mapping = {}
    for c in S.ORDER:
        matched, _ = S.align(G[c], P[c], c, grel, prel, mapping)
        for i, j, _s in matched:
            mapping[P[c][j][S.ID_FIELD[c]]] = G[c][i][S.ID_FIELD[c]]
    gm = set(mapping.values())
    paras = {u["source_unit_id"]: u.get("text", "") for u in gold.get("source_units", [])}
    gl = [(c, g) for c in S.SCORED for g in G[c] if g[S.ID_FIELD[c]] not in gm]
    pl = [(c, p) for c in S.SCORED for p in P[c] if p[S.ID_FIELD[c]] not in mapping]
    gmat = [(c, g) for c in S.SCORED for g in G[c] if g[S.ID_FIELD[c]] in gm]
    pmat = [(c, p) for c in S.SCORED for p in P[c] if p[S.ID_FIELD[c]] in mapping]
    out = []
    STRUCT = {"flows": ("flow_source", "flow_target"), "transitions": ("from_situation", "to_situation"), "controls": ("controls_flow",)}

    def ends(model_rels, sid, rts):
        return [r.get("target_slot_id") for r in model_rels if r.get("source_slot_id") == sid and r.get("relation_type") in rts]

    def cat(side, k, c, x):
        if c in STRUCT:
            e = ends(grel if side == "FN" else prel, x[S.ID_FIELD[c]], STRUCT[c])
            aligned = bool(e) and all((t in gm) if side == "FN" else (t in mapping) for t in e)
            return ("edge" if aligned else "endpoint"), ""
        other = pl if side == "FN" else gl
        mat = pmat if side == "FN" else gmat
        best = max(((overlap(S.disp(x), S.disp(o)), oc, S.disp(o)) for oc, o in other if oc != c and oc not in STRUCT), default=(0, "", ""))
        if best[0] >= 0.6:
            return "type", f"{best[1]}:{best[2]}"
        best = max(((overlap(S.disp(x), S.disp(o)), S.disp(o)) for oc, o in other if oc == c), default=(0, ""))
        if best[0] >= 0.34:
            return "near", best[1]
        best = max(((overlap(S.disp(x), S.disp(o)), S.disp(o)) for oc, o in mat if oc == c), default=(0, ""))
        if best[0] >= 0.5:
            return "granular", best[1]
        if side == "FP":
            units = S.units_of(x)
            para = " ".join(paras.get(str(u), "") for u in units) or " ".join(paras.values())
            return ("supported" if supported(S.disp(x), para) else "unsupported"), ""
        return "missing", ""
    for k, (c, g) in enumerate(gl):
        cc, why = cat("FN", k, c, g)
        out.append({"kind": "slot", "side": "FN", "type": c, "cat": cc, "label": S.disp(g), "counterpart": why,
                    "para": " ".join(paras.get(str(u), "") for u in S.units_of(g))[:300]})
    for k, (c, p) in enumerate(pl):
        cc, why = cat("FP", k, c, p)
        out.append({"kind": "slot", "side": "FP", "type": c, "cat": cc, "label": S.disp(p), "counterpart": why,
                    "para": " ".join(paras.get(str(u), "") for u in S.units_of(p))[:300]})
    gids = {x[S.ID_FIELD[c]] for c in S.SCORED for x in G[c]}
    gkeys = {S.rel_key(r, True) for r in grel if r.get("source_slot_id") in gids and r.get("target_slot_id") in gids
             and S.rel_key(r, False)[1] not in S.EXCLUDED_RELS}
    pkeys = set()
    for r in prel:
        s_, t_, o_ = S.rel_key(r, True)
        if t_ in S.EXCLUDED_RELS:
            continue
        pkeys.add((mapping.get(s_, "?" + str(s_)), t_, mapping.get(o_, "?" + str(o_))))
    gpairs = defaultdict(set); ppairs = defaultdict(set)
    for s_, t_, o_ in gkeys:
        gpairs[(s_, o_)].add(t_)
    for s_, t_, o_ in pkeys:
        ppairs[(s_, o_)].add(t_)
    gname = {x[S.ID_FIELD[c]]: S.disp(x) for c in S.SCORED for x in G[c]}
    for side, A, B, pairs_other in (("FN", gkeys, pkeys, ppairs), ("FP", pkeys, gkeys, gpairs)):
        for s_, t_, o_ in A - B:
            if side == "FN":
                ok_ends = s_ in gm and o_ in gm
            else:
                ok_ends = not str(s_).startswith("?") and not str(o_).startswith("?")
            if not ok_ends:
                cc = "endpoint"
            elif pairs_other.get((s_, o_)):
                cc = "type"
            elif t_ in pairs_other.get((o_, s_), set()):
                cc = "reversed"
            else:
                cc = "other"
            out.append({"kind": "rel", "side": side, "type": t_, "cat": cc,
                        "label": f"{gname.get(s_, s_)} -[{t_}]-> {gname.get(o_, o_)}",
                        "counterpart": ",".join(sorted(pairs_other.get((s_, o_), set()) | {"rev:" + x for x in pairs_other.get((o_, s_), set())}))})
    return out


def main():
    rows = []
    os.makedirs(RESULTS, exist_ok=True)
    for m in C.MODELS:
        for n in C.SEALED:
            gold = json.load(open(os.path.join(C.ROOT, MAN[n]["gold"]), encoding="utf-8-sig"))["text2activity_extraction_model"]
            for f in C.run_files("corrected", model=m, inputs=[n]):
                for e in analyse(f, gold):
                    rows.append({"model": m, "input": n, "run": os.path.basename(f)[:-5], **e})
    json.dump(rows, open(os.path.join(RESULTS, "errors.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    nrun = len({(r["model"], r["run"]) for r in rows})
    for kind in ("slot", "rel"):
        for side in ("FN", "FP"):
            R = [r for r in rows if r["kind"] == kind and r["side"] == side]
            c = Counter(r["cat"] for r in R)
            print(f"{kind:4s} {side}: {len(R) / nrun:5.1f} per run  " + "  ".join(f"{k} {v / len(R):.0%}" for k, v in c.most_common()))
            if kind == "slot":
                t = Counter((r["type"], r["cat"]) for r in R)
                print("     top type/cat:", [(f"{a}/{b}", round(v / nrun, 2)) for (a, b), v in t.most_common(8)])
            else:
                t = Counter(r["type"] for r in R if r["cat"] != "endpoint")
                print("     non-endpoint by relation type:", [(a, round(v / nrun, 2)) for a, v in t.most_common(8)])
    k = int(sys.argv[sys.argv.index("--sample") + 1]) if "--sample" in sys.argv else 0
    if k:
        rng = random.Random(20260930)
        sample = []
        for kind in ("slot", "rel"):
            for side in ("FN", "FP"):
                R = [r for r in rows if r["kind"] == kind and r["side"] == side]
                sample += rng.sample(R, min(k, len(R)))
        json.dump(sample, open(os.path.join(RESULTS, "errors_sample.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
