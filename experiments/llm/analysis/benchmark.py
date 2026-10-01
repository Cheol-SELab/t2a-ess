"""Benchmark measurement (paper Table "LLM extraction against the gold fixtures on the easy benchmark texts").

Cells: repository prompt, model x scenario, means over 3 runs. Model rows weight the three scenarios equally:
repository prompt (3 runs per cell) and corrected contract (6 runs per cell). Also the facts quoted in the text:
runs without any control / flow slot, and gold-aligned flows among predicted flows.
usage: python experiments/llm/analysis/benchmark.py   -> analysis/results/benchmark.{json,md}
"""
import json, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

OUT = os.path.join(C.HERE, "results")
SC = {"MUMT_easy": "MUM-T", "NGHE_easy": "NGHE", "AV_easy": "AV"}
CONDS = {"repository": "Repository prompt", "bench-corr": "Corrected contract"}


def cells(cond):
    files = C.run_files(cond, inputs=C.BENCH)
    C.score(files)
    out = {}
    for f in files:
        k = (C.model_of(f), C.input_of(f))
        s = json.load(open(f[:-5] + ".score.json", encoding="utf-8"))
        pt = s["slots"]["per_type"]
        m = C.metrics(f[:-5] + ".score.json") | {"no_control": pt["controls"]["pred"] == 0, "no_flow": pt["flows"]["pred"] == 0,
                                                    "flows_pred": pt["flows"]["pred"], "flows_tp": pt["flows"]["tp"]}
        out.setdefault(k, []).append(m)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    res, md = {}, []
    for cond in CONDS:
        c = cells(cond)
        res[cond] = {}
        for m in C.MODELS:
            per = {}
            for n in C.BENCH:
                runs = c.get((m, n), [])
                if not runs:
                    continue
                # weak-3 pooled per run, then the mean over the runs of the cell
                p, r, f = (st.mean(x[k] for x in runs) for k in ("weak_p", "weak_r", "weak"))
                per[n] = {"n": len(runs), "weak_p": p, "weak_r": r, "weak_f1": f, "S": st.mean(x["S"] for x in runs), "slot": st.mean(x["slot"] for x in runs),
                          "rel": st.mean(x["rel"] for x in runs), "actions": st.mean(x["actions"] for x in runs), "gold_actions": runs[0]["gold_actions"],
                          "no_control": sum(x["no_control"] for x in runs), "no_flow": sum(x["no_flow"] for x in runs),
                          "flows_pred": [x["flows_pred"] for x in runs], "flows_tp": [x["flows_tp"] for x in runs]}
            model_row = {k: st.mean(per[n][k] for n in per) for k in ("weak_p", "weak_r", "weak_f1", "S", "slot", "rel")} if per else {}
            res[cond][m] = {"cells": per, "model": model_row}
    json.dump(res, open(os.path.join(OUT, "benchmark.json"), "w", encoding="utf-8"), indent=1)
    md.append("| Model | Scen. | Weak-3 P / R / F1 | Slot F1 | Rel. F1 | Actions / gold |\n|---|---|---|---|---|---|")
    for m in C.MODELS:
        for n in C.BENCH:
            x = res["repository"][m]["cells"].get(n)
            if x:
                md.append(f"| {m[7:]} | {SC[n]} | {x['weak_p']:.2f} / {x['weak_r']:.2f} / {x['weak_f1']:.2f} | {x['slot']:.2f} | {x['rel']:.2f} | {x['actions']:.1f} / {x['gold_actions']} |")
    for cond, title in CONDS.items():
        md.append(f"| *{title}* | | | | | |")
        for m in C.MODELS:
            x = res[cond][m]["model"]
            if x:
                md.append(f"| {m[7:]} | all | {x['weak_p']:.2f} / {x['weak_r']:.2f} / {x['weak_f1']:.2f} | {x['slot']:.2f} | {x['rel']:.2f} | |")
    md.append("")
    for cond in CONDS:
        for m in C.MODELS:
            cl = res[cond][m]["cells"]
            md.append(f"{cond} {m}: runs without control {sum(v['no_control'] for v in cl.values())}/{sum(v['n'] for v in cl.values())}, "
                      f"without flow {sum(v['no_flow'] for v in cl.values())}; NGHE flows predicted {cl.get('NGHE_easy', {}).get('flows_pred')} aligned {cl.get('NGHE_easy', {}).get('flows_tp')}")
    ds = [res["bench-corr"][m]["cells"][n]["S"] - res["repository"][m]["cells"][n]["S"] for m in C.MODELS for n in C.BENCH
          if n in res["bench-corr"][m]["cells"] and n in res["repository"][m]["cells"]]
    if ds:
        md.append(f"corrected - repository: mean dS {st.mean(ds):+.3f}, positive {sum(d > 0 for d in ds)}/{len(ds)}")
    open(os.path.join(OUT, "benchmark.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
