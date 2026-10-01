"""Sensitivity of the benchmark to the gold's action granularity: rescoring against the schema-granularity gold.

The derived gold (data/gold-sg/, with the labels of data/gold/) applies the schema's own rules for
atomic actions to the easy texts. The benchmark runs are rescored against it without new calls (score files
<run>.sg.score.json). Reported: per model and condition weak-3 / slot / relation F1, predicted actions per gold
action, and the gain of the corrected contract over the repository prompt (mean dS over the six cells).
usage: python experiments/llm/analysis/goldsg.py   -> analysis/results/goldsg.json
"""
import json, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

MAN = os.path.join(C.LLM, "scoring", "inputs", "manifest.json")
MAN_SG = os.path.join(C.LLM, "scoring", "inputs", "manifest_gold_sg.json")


def main():
    man = json.load(open(MAN, encoding="utf-8"))
    sg = {}
    for n in C.BENCH:
        k = man[n]["domain"].lower()
        sg[n] = dict(man[n], gold=f"data/gold-sg/{k}/{k}.gold-sg.json", coverage="data/gold-sg/coverage_requirements.json")
    json.dump(sg, open(MAN_SG, "w", encoding="utf-8"), indent=2)
    res = {}
    for cond in ("repository", "bench-corr"):
        files = C.run_files(cond, inputs=C.BENCH)
        C.score(files, manifest=MAN_SG, suffix=".sg.score.json")
        C.score(files)
        res[cond] = {}
        for m in C.MODELS:
            per = {}
            for n in C.BENCH:
                fs = [f for f in files if C.model_of(f) == m and C.input_of(f) == n]
                orig = [C.metrics(f[:-5] + ".score.json") for f in fs]
                der = [C.metrics(f[:-5] + ".sg.score.json") for f in fs]
                per[n] = {"orig": {q: st.mean(x[q] for x in orig) for q in ("S", "weak", "slot", "rel")},
                          "sg": {q: st.mean(x[q] for x in der) for q in ("S", "weak", "slot", "rel")},
                          "actions": st.mean(x["actions"] for x in der), "sg_gold_actions": der[0]["gold_actions"], "orig_gold_actions": orig[0]["gold_actions"]}
            res[cond][m] = {"cells": per, "orig": {q: st.mean(per[n]["orig"][q] for n in per) for q in ("weak", "slot", "rel")},
                            "sg": {q: st.mean(per[n]["sg"][q] for n in per) for q in ("weak", "slot", "rel")},
                            "action_ratio_sg": {n: per[n]["actions"] / per[n]["sg_gold_actions"] for n in per},
                            "action_ratio_orig": {n: per[n]["actions"] / per[n]["orig_gold_actions"] for n in per}}
    for gold in ("orig", "sg"):
        ds = [res["bench-corr"][m]["cells"][n][gold]["S"] - res["repository"][m]["cells"][n][gold]["S"] for m in C.MODELS for n in C.BENCH]
        res[f"gain_{gold}"] = {"mean_dS": st.mean(ds), "positive": sum(d > 0 for d in ds), "n": len(ds)}
    os.makedirs(os.path.join(C.HERE, "results"), exist_ok=True)
    json.dump(res, open(os.path.join(C.HERE, "results", "goldsg.json"), "w", encoding="utf-8"), indent=1)
    for cond in ("repository", "bench-corr"):
        for m in C.MODELS:
            r = res[cond][m]
            print(f"{cond:11s} {m[7:]:9s} orig weak/slot/rel {r['orig']['weak']:.2f}/{r['orig']['slot']:.2f}/{r['orig']['rel']:.2f}  "
                  f"SG {r['sg']['weak']:.2f}/{r['sg']['slot']:.2f}/{r['sg']['rel']:.2f}  actions/gold SG {', '.join(f'{v:.2f}' for v in r['action_ratio_sg'].values())}")
    print("corrected - repository:", {g: res[f"gain_{g}"] for g in ("orig", "sg")})


if __name__ == "__main__":
    main()
