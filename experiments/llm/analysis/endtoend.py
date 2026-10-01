"""End-to-end validity of the single-pass extractions on the sealed scenarios (corrected contract).

Each result goes through the same structural layers as the gold fixtures, with this repository's code: JSON parse,
traceability report (struct_prepare.py), EFFBD converter + contract validator + language-server round trip
(struct_check.mjs). Runs are copied to runs/_e2e/<model>/ so that the run folders stay untouched.
With --converter <root> (for example experiments/llm/ablation/no-name-disambiguation, the same code without the
converter's name disambiguation) the converter/validator/LSP layer uses that code instead; results then go to <run>.struct-<tag>.json.
usage: python experiments/llm/analysis/endtoend.py [--check] [--converter <root> --tag <tag>]   (SELAB_LSP_BIN)
   -> analysis/results/endtoend_rows.json and a summary
"""
import json, os, shutil, statistics as st, subprocess, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

OUT = os.path.join(C.RUNS, "_e2e")


def main():
    conv = sys.argv[sys.argv.index("--converter") + 1] if "--converter" in sys.argv else C.ROOT
    tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else ""
    sfx = f".struct-{tag}.json" if tag else ".struct.json"
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1", T2A_ROOT=os.path.abspath(conv), T2A_STRUCT_SUFFIX=sfx)
    copied = []
    for f in C.run_files("corrected", inputs=C.SEALED):
        d = os.path.join(OUT, C.model_of(f))
        os.makedirs(d, exist_ok=True)
        t = os.path.join(d, os.path.basename(f))
        if not os.path.exists(t):
            shutil.copy(f, t)
        copied.append(t)
    todo = [t for t in copied if not os.path.exists(t[:-5] + ".trace.json")]
    for i in range(0, len(todo), 40):
        subprocess.run([sys.executable, os.path.join(C.HERE, "struct_prepare.py"), C.ROOT] + todo[i:i + 40], check=True, env=env, stdout=subprocess.DEVNULL)
    preds = [t[:-5] + ".pred.json" for t in copied if os.path.exists(t[:-5] + ".pred.json")]
    need = [p for p in preds if "--check" in sys.argv or not os.path.exists(p.replace(".pred.json", sfx))]
    for i in range(0, len(need), 40):
        subprocess.run(["node", os.path.join(C.HERE, "struct_check.mjs")] + need[i:i + 40], check=True, env=env, stdout=subprocess.DEVNULL)
    rows = []
    for t in copied:
        base = t[:-5]
        meta = json.load(open(t, encoding="utf-8"))["meta"]
        tr = json.load(open(base + ".trace.json", encoding="utf-8"))
        sc = json.load(open(base + sfx, encoding="utf-8")) if os.path.exists(base + sfx) else {"ok": False}
        rows.append({"model": meta["model_requested"], "input": meta["input"], "parse": tr.get("ok", False), "trace_defects": tr.get("total_defects"),
                     "trace": tr.get("defects", {}), "convert": sc.get("ok", False), "lsp_ok": sc.get("lsp_ok"), "lsp_errors": sc.get("lsp_errors"),
                     "v_errors": (sc.get("validator") or {}).get("errors"), "v_warnings": (sc.get("validator") or {}).get("warnings"),
                     "codes": (sc.get("validator") or {}).get("codes", {}), "nested": sc.get("nested"), "lsp_problems": sc.get("lsp_problems")})
    os.makedirs(os.path.join(C.HERE, "results"), exist_ok=True)
    json.dump(rows, open(os.path.join(C.HERE, "results", f"endtoend_rows{('-' + tag) if tag else ''}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for m in C.MODELS + ["all"]:
        R = [r for r in rows if m in ("all", r["model"])]
        k = lambda f: sum(1 for r in R if f(r))  # noqa: E731
        print(f"{m:18s} n={len(R)} parse {k(lambda r: r['parse'])}  convert {k(lambda r: r['convert'])}  lsp0err {k(lambda r: r['lsp_errors'] == 0)}  "
              f"validator0err {k(lambda r: r['v_errors'] == 0)}  all-gates {k(lambda r: r['convert'] and r['lsp_errors'] == 0 and r['v_errors'] == 0)}")
        if R:
            print("   validator E/W mean %.2f/%.2f  trace defects mean %.2f" % (st.mean(r["v_errors"] or 0 for r in R), st.mean(r["v_warnings"] or 0 for r in R),
                                                                           st.mean(r["trace_defects"] or 0 for r in R)))
            c = Counter()
            for r in R:
                if r["v_errors"]:
                    c.update(r["codes"])
            print("   codes in results with validator errors:", dict(c.most_common(6)))
            t = Counter()
            for r in R:
                t.update({k2: v for k2, v in r["trace"].items() if v})
            print("   trace defects per result:", {k2: round(v / len(R), 2) for k2, v in t.most_common(6)})
            print("   lsp problems:", dict(Counter(str(x)[:90] for r in R for x in (r["lsp_problems"] or [])).most_common(4)))


if __name__ == "__main__":
    main()
