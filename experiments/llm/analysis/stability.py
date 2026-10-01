"""Single-pass accuracy and run-to-run stability on the nine sealed scenarios (corrected contract, 9 runs per model
and scenario):

- accuracy: per model, mean over scenarios of the per-cell mean (slot F1, relation F1, pooled weak-3 F1, S), with a
  95% bootstrap interval that resamples scenarios and runs within scenarios (5000 resamples, seed 20260930);
- stability: within-cell standard deviation of each metric, and inter-run agreement: slot and normalized-relation F1
  of one run against another run of the same cell (all 36 pairs), aligned by the scorer's matcher (con.align_to).
usage: python experiments/llm/analysis/stability.py   -> analysis/results/stability.json
"""
import itertools, json, os, random, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import consensus as con  # noqa: E402
S = con.S


def pair_agreement(m1, m2):
    mp = con.align_to(m1, m2)  # m2 id -> m1 id
    n1 = sum(len(v) for v in S.slots_by_type(m1).values()); n2 = sum(len(v) for v in S.slots_by_type(m2).values())
    tp = len(set(mp.values()))
    sf = 2 * tp / (n1 + n2) if n1 + n2 else 0
    k1 = set(con.keyset(m1)); k2 = set(con.keyset(m2, mp))
    n2r = len(con.keyset(m2))
    rf = 2 * len(k1 & k2) / (len(k1) + n2r) if len(k1) + n2r else 0
    return sf, rf


def main():
    files = C.run_files("corrected", inputs=C.SEALED)
    C.score(files)
    out = {}
    for m in C.MODELS:
        cells = {}
        for n in C.SEALED:
            fs = [f for f in files if C.model_of(f) == m and C.input_of(f) == n]
            xs = [C.metrics(f[:-5] + ".score.json") for f in fs]
            models = [con.load(f)[1] for f in fs]
            pairs = [pair_agreement(a, b) for a, b in itertools.combinations(models, 2)]
            cells[n] = {"x": xs, "agree_slot": st.mean(p[0] for p in pairs), "agree_rel": st.mean(p[1] for p in pairs), "n": len(xs)}
        rng = random.Random(20260930)
        res = {}
        for q in ("slot", "rel", "weak", "S"):
            point = st.mean(st.mean(x[q] for x in c["x"]) for c in cells.values())
            boots = []
            for _ in range(5000):
                cs = [cells[k] for k in rng.choices(list(cells), k=len(cells))]
                boots.append(st.mean(st.mean(rng.choice(c["x"])[q] for _ in c["x"]) for c in cs))
            boots.sort()
            res[q] = {"mean": point, "ci": (boots[124], boots[4874]), "within_cell_sd": st.mean(st.pstdev([x[q] for x in c["x"]]) for c in cells.values()),
                      "cell_range": (min(st.mean(x[q] for x in c["x"]) for c in cells.values()), max(st.mean(x[q] for x in c["x"]) for c in cells.values()))}
        res["agree_slot"] = st.mean(c["agree_slot"] for c in cells.values())
        res["agree_rel"] = st.mean(c["agree_rel"] for c in cells.values())
        res["n_runs"] = sum(c["n"] for c in cells.values())
        res["per_cell"] = {n: {q: st.mean(x[q] for x in c["x"]) for q in ("slot", "rel", "weak", "S")} for n, c in cells.items()}
        out[m] = res
        print(m, f"n={res['n_runs']}")
        for q in ("slot", "rel", "weak", "S"):
            r = res[q]
            print(f"  {q:5s} mean {r['mean']:.3f} [{r['ci'][0]:.3f}, {r['ci'][1]:.3f}]  within-cell SD {r['within_cell_sd']:.3f}  cells {r['cell_range'][0]:.3f}-{r['cell_range'][1]:.3f}")
        print(f"  inter-run agreement: slot F1 {res['agree_slot']:.3f}, relation F1 {res['agree_rel']:.3f}")
    os.makedirs(os.path.join(C.HERE, "results"), exist_ok=True)
    json.dump(out, open(os.path.join(C.HERE, "results", "stability.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
