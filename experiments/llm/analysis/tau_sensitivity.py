"""Sensitivity of the sealed-scenario accuracy to the scorer's similarity threshold.

The embedding threshold (0.87; 0.93 for flow labels) was calibrated on a pilot and frozen. The runs
are rescored at 0.83, 0.85, 0.87 (frozen), 0.89, and 0.91 (T2A_TAU; flow labels keep max(tau, 0.93)) to show how
much the reported F1 depends on it. Score files: <run>.tau<value>.score.json.
usage: python experiments/llm/analysis/tau_sensitivity.py   -> analysis/results/tau_sensitivity.json
"""
import json, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

TAUS = ["0.83", "0.85", "0.87", "0.89", "0.91"]


def main():
    files = C.run_files("corrected", inputs=C.SEALED)
    res = {}
    for tau in TAUS:
        suffix = ".score.json" if tau == "0.87" else f".tau{tau}.score.json"
        C.score(files, suffix=suffix, env_extra={"T2A_TAU": tau, "T2A_SCORE_SUFFIX": suffix})
        res[tau] = {}
        for m in C.MODELS:
            cells = {}
            for f in files:
                if C.model_of(f) == m:
                    cells.setdefault(C.input_of(f), []).append(C.metrics(f[:-5] + suffix))
            res[tau][m] = {q: st.mean(st.mean(x[q] for x in v) for v in cells.values()) for q in ("slot", "rel", "weak", "S")}
        print(tau, {m[7:]: {q: round(v, 3) for q, v in r.items()} for m, r in res[tau].items()})
    os.makedirs(os.path.join(C.HERE, "results"), exist_ok=True)
    json.dump(res, open(os.path.join(C.HERE, "results", "tau_sensitivity.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
