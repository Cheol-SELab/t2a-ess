"""CON: dependency-ordered consensus integrator over K independent extractions of the same input.

Slots are aligned run-to-pivot type by type in the dependency order of the slot schema (endpoint slots before the slots
and relations they anchor; flows/controls last, matched on their already-aligned endpoints), then slots and relations
are kept by majority vote. No LLM call; inputs are ordinary extraction records.
usage: python consensus.py --out <version> --src <A version> --inputs ... --groups 1,2,3 [4,5,6 ...] [--slot-min 2] [--rel-min 2]
"""
import argparse, copy, datetime, json, os, sys
from collections import Counter, defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scoring"))  # t2a-ess: experiments/llm/scoring
import score as S  # noqa: E402

RUNS = os.path.join(os.path.dirname(HERE), "runs")


def load(p):
    rec = json.load(open(p, encoding="utf-8"))
    m = S.load_json_text(rec["result_text"])
    return rec, m.get("text2activity_extraction_model", m)


def align_to(pivot, other):
    """mapping other-id -> pivot-id, aligned in dependency order exactly like the scorer aligns a run to gold."""
    G, P = S.slots_by_type(pivot), S.slots_by_type(other)
    gr, pr = pivot.get("slot_relations", []) or [], other.get("slot_relations", []) or []
    mapping = {}
    for c in S.ORDER:
        matched, _ = S.align(G[c], P[c], c, gr, pr, mapping)
        for i, j, _s in matched:
            mapping[P[c][j][S.ID_FIELD[c]]] = G[c][i][S.ID_FIELD[c]]
    return mapping


def keyset(model, mapping=None):
    out = {}
    for r in model.get("slot_relations", []) or []:
        s, t, o = S.rel_key(r, True)
        if mapping is not None:
            if s not in mapping or o not in mapping:
                continue
            s, o = mapping[s], mapping[o]
        out.setdefault((s, t, o), r)
    return out


def consensus(models, slot_min, rel_min):
    k = len(models)
    # pivot: the run that agrees most with the others (sum of aligned slots)
    maps = {(i, j): align_to(models[i], models[j]) for i in range(k) for j in range(k) if i != j}
    piv = max(range(k), key=lambda i: sum(len(maps[(i, j)]) for j in range(k) if j != i))
    pm = copy.deepcopy(models[piv])
    others = [j for j in range(k) if j != piv]
    support = Counter()
    for j in others:
        for pid in set(maps[(piv, j)].values()):
            support[pid] += 1
    keep = set()
    for c in S.SCORED:
        idf = S.ID_FIELD[c]
        kept = [x for x in pm.get(c, []) or [] if isinstance(x, dict) and 1 + support[x.get(idf)] >= slot_min]
        if c in pm:
            pm[c] = kept
        keep |= {x.get(idf) for x in kept}
    ids_all = {x.get(S.ID_FIELD[c]) for c in S.SCORED for x in (models[piv].get(c) or []) if isinstance(x, dict)}
    votes = Counter(keyset(models[piv]).keys())
    for j in others:
        votes.update(keyset(models[j], maps[(piv, j)]).keys())
    base = keyset(models[piv])
    rels = []
    for key, n in votes.items():
        s, t, o = key
        if n < rel_min:
            continue
        if (s in ids_all and s not in keep) or (o in ids_all and o not in keep):
            continue
        if key in base:
            rels.append(base[key])
        elif s in keep and o in keep:  # majority relation the pivot missed
            r = {"relation_type": t, "source_slot_id": s, "target_slot_id": o}
            if t.startswith("custom/"):
                r = {"relation_type": "custom", "custom_relation_type": t[7:], "source_slot_id": s, "target_slot_id": o}
            rels.append(r)
    # non-slot relation endpoints (source units etc.) of pivot relations with one vote-able key are kept as in pivot
    pm["slot_relations"] = rels
    return pm, piv


def consensus_union(models, slot_min, rel_min):
    """Incremental clustering: runs are aligned one by one to a growing union model (pivot first), in dependency order;
    a slot no earlier run has becomes a new cluster, so a slot the pivot missed can still win the vote."""
    k = len(models)
    maps = {(i, j): align_to(models[i], models[j]) for i in range(k) for j in range(k) if i != j}
    piv = max(range(k), key=lambda i: sum(len(maps[(i, j)]) for j in range(k) if j != i))
    order = [piv] + [j for j in range(k) if j != piv]
    aug = copy.deepcopy(models[piv])
    support = Counter({x.get(S.ID_FIELD[c]): 1 for c in S.SCORED for x in (aug.get(c) or []) if isinstance(x, dict)})
    votes = Counter(keyset(aug).keys())
    origin = dict(keyset(aug))
    for j in order[1:]:
        mp = align_to(aug, models[j])
        for pid in set(mp.values()):
            support[pid] += 1
        for c in S.SCORED:
            idf = S.ID_FIELD[c]
            for x in models[j].get(c) or []:
                if isinstance(x, dict) and x.get(idf) and x.get(idf) not in mp:
                    nid = f"u{j}_{x[idf]}"
                    mp[x[idf]] = nid
                    aug.setdefault(c, []).append({**copy.deepcopy(x), idf: nid})
                    support[nid] = 1
        ks = keyset(models[j], mp)
        votes.update(ks.keys())
        for key, r in ks.items():
            if key not in origin:
                s_, t_, o_ = key
                origin[key] = {**copy.deepcopy(r), "source_slot_id": s_, "target_slot_id": o_} if r.get("relation_type") not in S.REVERSED else                     {"relation_type": t_, "source_slot_id": s_, "target_slot_id": o_}
                aug.setdefault("slot_relations", []).append(origin[key])
    keep = set()
    for c in S.SCORED:
        idf = S.ID_FIELD[c]
        if c in aug:
            aug[c] = [x for x in aug[c] if isinstance(x, dict) and support[x.get(idf)] >= slot_min]
            keep |= {x.get(idf) for x in aug[c]}
    ids_all = set(support)
    rels = []
    for key, n in votes.items():
        s_, t_, o_ = key
        if n < rel_min or (s_ in ids_all and s_ not in keep) or (o_ in ids_all and o_ not in keep):
            continue
        r = origin[key]
        if r.get("relation_type") in S.REVERSED:
            r = {"relation_type": t_, "source_slot_id": s_, "target_slot_id": o_}
        rels.append(r)
    aug["slot_relations"] = rels
    return aug, piv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--src", nargs="+", required=True, help="one A version per input, or one for all")
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--models", nargs="+", default=["claude-sonnet-5", "claude-opus-5-5"])
    ap.add_argument("--groups", nargs="+", default=["1,2,3"])
    ap.add_argument("--slot-min", type=int, default=2)
    ap.add_argument("--rel-min", type=int, default=2)
    ap.add_argument("--cond", default="A")
    ap.add_argument("--union", action="store_true")
    args = ap.parse_args()
    src = args.src if len(args.src) == len(args.inputs) else args.src * len(args.inputs)
    for m in args.models:
        od = os.path.join(RUNS, args.out, "DEP", m)
        os.makedirs(od, exist_ok=True)
        for name, sv in zip(args.inputs, src):
            for gi, g in enumerate(args.groups, 1):
                # member: "r" | "version:cond:r" | "version:cond:r:model" (SRC = this input's --src version)
                spec = [(x.split(":") + [m])[:4] if ":" in x else (sv, args.cond, x, m) for x in g.split(",")]
                spec = [(sv if v == "SRC" else v, c, r, mm) for v, c, r, mm in spec]
                reps = [f"{v}:{c}:{r}:{mm[7:]}" if (v, c, mm) != (sv, args.cond, m) else int(r) for v, c, r, mm in spec]
                paths = [os.path.join(RUNS, v, c, mm, f"{name}_r{r}.json") for v, c, r, mm in spec]
                recs = [load(p) for p in paths]
                if not all(r[0]["meta"].get("ok") for r in recs):
                    print("skip (parent not ok)", m, name, g); continue
                cm, piv = (consensus_union if args.union else consensus)([r[1] for r in recs], args.slot_min, args.rel_min)
                meta = dict(recs[0][0]["meta"])
                meta.update(condition="DEP", prompt_set="con", version=args.out, repeat=gi, parents=[os.path.relpath(p, RUNS) for p in paths],
                            pivot=reps[piv], union=args.union, slot_min=args.slot_min, rel_min=args.rel_min, llm_calls=sum(r[0]["meta"].get("llm_calls", 1) or 1 for r in recs),
                            total_cost_usd=round(sum(r[0]["meta"].get("total_cost_usd") or 0 for r in recs), 4),
                            runner_sha256=S.__dict__.get("sha", None) or "", ok=True, started_utc=datetime.datetime.utcnow().isoformat(timespec="seconds"))
                json.dump({"meta": meta, "result_text": json.dumps(cm, ensure_ascii=False)},
                          open(os.path.join(od, f"{name}_r{gi}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                print(m, name, g, "pivot", reps[piv], "rels", len(cm["slot_relations"]))
    if S.EMB is not None and getattr(S.EMB, "dirty", False) and hasattr(S.EMB, "save"):
        S.EMB.save()


if __name__ == "__main__":
    main()
