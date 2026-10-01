"""Majority vote over six extractions (three per model) on the last three sealed scenarios (TUNNEL, COLD, SHIP),
as in the paper's consensus sentence (design fixed before those scenarios were written).

Groups: repeats (1,2,3), (4,5,6), (7,8,9) of the corrected-contract runs, Sonnet 5 and Opus 5.5 together, merged by
con.consensus_union with 4 of 6 votes for slots and relations. Each of the six model-scenario cells compares the
three consensus records with the nine single runs of that model; statistic = mean over cells of the difference in
S; one-sided p from a permutation of the labels within each cell.
usage: python experiments/llm/analysis/consensus_mix.py [--perm 20000]  -> analysis/results/consensus_mix.json
"""
import datetime, json, os, random, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import consensus as con  # noqa: E402

NAMES = ["TUNNEL_sealed", "COLD_sealed", "SHIP_sealed"]
GROUPS = [(1, 2, 3), (4, 5, 6), (7, 8, 9)]
OUT = os.path.join(C.RUNS, "con-mix")


def build():
    for n in NAMES:
        for gi, reps in enumerate(GROUPS, 1):
            paths = [os.path.join(C.RUNS, "corrected", m, f"{n}_r{r}.json") for m in C.MODELS for r in reps]
            recs = [con.load(p) for p in paths]
            if not all(r[0]["meta"].get("ok") for r in recs):
                raise SystemExit(f"not ok: {n} {reps}")
            cm, piv = con.consensus_union([r[1] for r in recs], 4, 4)
            meta = {"input": n, "repeat": gi, "condition": "con-mix", "parents": [os.path.relpath(p, C.RUNS).replace(os.sep, "/") for p in paths],
                    "pivot": os.path.relpath(paths[piv], C.RUNS).replace(os.sep, "/"), "slot_min": 4, "rel_min": 4, "ok": True,
                    "total_cost_usd": round(sum(r[0]["meta"].get("total_cost_usd") or 0 for r in recs), 4),
                    "created_utc": datetime.datetime.utcnow().isoformat(timespec="seconds")}
            for m in C.MODELS:  # the same record is compared with each model's single runs
                os.makedirs(os.path.join(OUT, m), exist_ok=True)
                json.dump({"meta": meta, "result_text": json.dumps(cm, ensure_ascii=False)},
                          open(os.path.join(OUT, m, f"{n}_r{gi}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    perm = int(sys.argv[sys.argv.index("--perm") + 1]) if "--perm" in sys.argv else 20000
    build()
    A = C.run_files("corrected", inputs=NAMES)
    B = C.run_files("con-mix", inputs=NAMES, ok_only=True)
    C.score(A + B)
    cells, rows = [], []
    for m in C.MODELS:
        for n in NAMES:
            a = [C.metrics(f[:-5] + ".score.json") for f in A if C.model_of(f) == m and C.input_of(f) == n]
            b = [C.metrics(f[:-5] + ".score.json") for f in B if C.model_of(f) == m and C.input_of(f) == n]
            cells.append(([x["S"] for x in a], [x["S"] for x in b]))
            rows.append({"model": m, "input": n, "A_S": st.mean(x["S"] for x in a), "CON_S": st.mean(x["S"] for x in b),
                         "dS": st.mean(x["S"] for x in b) - st.mean(x["S"] for x in a), "n_A": len(a), "n_CON": len(b),
                         **{f"A_{k}": st.mean(x[k] for x in a) for k in ("weak", "rel", "slot")}, **{f"CON_{k}": st.mean(x[k] for x in b) for k in ("weak", "rel", "slot")}})
    obs = st.mean(r["dS"] for r in rows)
    rng, hit = random.Random(20260930), 0
    for _ in range(perm):
        t = []
        for a, b in cells:
            pool = a + b
            rng.shuffle(pool)
            t.append(st.mean(pool[len(a):]) - st.mean(pool[:len(a)]))
        hit += st.mean(t) >= obs - 1e-12
    cost_a = st.mean(json.load(open(f, encoding="utf-8"))["meta"]["total_cost_usd"] for f in A)
    cost_b = st.mean(json.load(open(f, encoding="utf-8"))["meta"]["total_cost_usd"] for f in B if C.model_of(f) == C.MODELS[0])
    res = {"cells": rows, "mean_dS": obs, "positive": sum(r["dS"] > 0 for r in rows), "p_one_sided": (hit + 1) / (perm + 1), "perm": perm,
           "cost_single": cost_a, "cost_consensus": cost_b}
    os.makedirs(os.path.join(C.HERE, "results"), exist_ok=True)
    json.dump(res, open(os.path.join(C.HERE, "results", "consensus_mix.json"), "w", encoding="utf-8"), indent=1)
    for r in rows:
        print(f"{r['input']:16s} {r['model'][7:]:9s} A {r['A_S']:.3f}  CON {r['CON_S']:.3f}  dS {r['dS']:+.3f}")
    print(f"mean dS {obs:+.4f}, positive {res['positive']}/6, p {res['p_one_sided']:.5f}; cost per result ${cost_a:.2f} vs ${cost_b:.2f}")


if __name__ == "__main__":
    main()
