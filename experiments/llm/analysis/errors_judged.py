"""Manual judgment of the random error sample (results/errors_sample.json, 25 per group, seed 20260930) by one author,
on the English runs.

D = defensible: the prediction (or the gold's alternative) is stated or implied by the text and allowed by the schema
    rules; the difference is a modeling choice (slot type, granularity, state vocabulary, episode boundary, whether a
    message or device is an item, whether a measured value is an event or a state value).
E = error: stated content is omitted, or the prediction is not supported by the text or is wrong.
Judged by reading each error with its source paragraph (index = position in errors_sample.json).
usage: python experiments/llm/analysis/errors_judged.py   -> results/errors_judged.json and a summary with Wilson 95% intervals
"""
import json, math, os
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
J = {
    # slot FN (0-24)
    0: "E", 1: "D", 2: "D", 3: "E", 4: "E", 5: "E", 6: "D", 7: "E", 8: "E", 9: "E", 10: "E", 11: "D", 12: "D", 13: "E",
    14: "D", 15: "D", 16: "D", 17: "E", 18: "E", 19: "E", 20: "E", 21: "E", 22: "D", 23: "E", 24: "E",
    # slot FP (25-49)
    25: "D", 26: "D", 27: "D", 28: "D", 29: "D", 30: "D", 31: "D", 32: "D", 33: "D", 34: "D", 35: "E", 36: "E", 37: "D",
    38: "D", 39: "E", 40: "D", 41: "D", 42: "D", 43: "D", 44: "D", 45: "D", 46: "D", 47: "D", 48: "D", 49: "D",
    # relation FN (50-74)
    50: "E", 51: "D", 52: "D", 53: "D", 54: "D", 55: "E", 56: "E", 57: "E", 58: "D", 59: "D", 60: "D", 61: "E", 62: "E",
    63: "D", 64: "D", 65: "D", 66: "D", 67: "D", 68: "D", 69: "E", 70: "D", 71: "D", 72: "D", 73: "D", 74: "D",
    # relation FP (75-99)
    75: "D", 76: "D", 77: "D", 78: "D", 79: "D", 80: "D", 81: "D", 82: "D", 83: "D", 84: "D", 85: "D", 86: "D", 87: "D",
    88: "D", 89: "D", 90: "D", 91: "D", 92: "D", 93: "D", 94: "D", 95: "D", 96: "D", 97: "D", 98: "E", 99: "D",
}


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def main():
    S = json.load(open(os.path.join(RES, "errors_sample.json"), encoding="utf-8"))
    assert len(S) == 100 and set(J) == set(range(100))
    for i, e in enumerate(S):
        e["judgment"] = J[i]
    json.dump(S, open(os.path.join(RES, "errors_judged.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rows = json.load(open(os.path.join(RES, "errors.json"), encoding="utf-8"))
    nrun = len({(r["model"], r["run"]) for r in rows})
    out, tot_e, tot = {}, 0, 0
    for g, (kind, side) in enumerate((("slot", "FN"), ("slot", "FP"), ("rel", "FN"), ("rel", "FP"))):
        part = S[25 * g:25 * g + 25]
        k = sum(e["judgment"] == "E" for e in part)
        per_run = sum(1 for r in rows if r["kind"] == kind and r["side"] == side) / nrun
        lo, hi = wilson(k, 25)
        out[f"{kind}_{side}"] = {"per_run": per_run, "errors_in_sample": k, "ci": (lo, hi), "errors_per_run": per_run * k / 25,
                                 "cats": dict(Counter(f"{e['cat']}/{e['judgment']}" for e in part))}
        print(f"{kind:4s} {side}: {per_run:5.1f} per run; error {k}/25 = {k / 25:.0%} [{lo:.0%}, {hi:.0%}]  -> {per_run * k / 25:.1f} errors per run")
        tot_e += per_run * k / 25; tot += per_run
    out["all"] = {"unmatched_per_run": tot, "errors_per_run": tot_e, "error_share": tot_e / tot}
    json.dump(out, open(os.path.join(RES, "errors_summary.json"), "w", encoding="utf-8"), indent=1)
    print(f"all unmatched: {tot:.1f} per run, estimated errors {tot_e:.1f} ({tot_e / tot:.0%}), defensible {tot - tot_e:.1f}")


if __name__ == "__main__":
    main()
