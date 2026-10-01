"""Structural evaluation of the seven reported outputs.

1. Traceability reports and DOT graphs (tools/t2a_traceability_graph.py), written next to each output
   (traceability_reports/, traceability_graphs/).
2. Graph counts and defect counts (same tool, API), and the language-server / validator layers (lsp_all.mjs).
usage: python experiments/structural/run_structural.py   (SELAB_LSP_BIN must point to sysml-lsp)
   -> experiments/structural/results/{structural.json, lsp.json, lsp.log, summary.txt}
"""
import json, os, subprocess, sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import t2a_traceability_graph as T  # noqa: E402

FILES = ["gold/mumt/mumt.gold.json", "gold/nghe/nghe.gold.json", "gold/av/av.gold.json",
         "diagnostic/mumt/mumt.nongold.json", "diagnostic/mumt/mumt.exhaustive.json",
         "diagnostic/nghe/nghe.nongold.json", "diagnostic/nghe/nghe.exhaustive.json"]
RES = os.path.join(HERE, "results")


def graph_counts():
    out = {}
    for f in FILES:
        p = Path(os.path.join(ROOT, "data", f))
        g = T.build_graph(p)
        v = T.validation_summary(g)
        m = json.load(open(p, encoding="utf-8-sig"))["text2activity_extraction_model"]
        slots = sum(len(m.get(c, []) or []) for c, _, _ in T.SLOT_COLLECTIONS)
        out[f] = {"source_units": len(m.get("source_units", []) or []), "slots": slots, "slot_relations": len(m.get("slot_relations", []) or []),
                  "graph": {k: (len(x) if isinstance(x, (list, dict, set)) else x) for k, x in g.items() if k in ("nodes", "edges")},
                  "defects": {k: (len(x) if isinstance(x, list) else x) for k, x in v.items() if isinstance(x, list)}}
    return out


def main():
    os.makedirs(RES, exist_ok=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for f in FILES:
        d = os.path.dirname(os.path.join(ROOT, "data", f))
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "t2a_traceability_graph.py"), "--input", os.path.join(ROOT, "data", f),
                        "--report-dir", os.path.join(d, "traceability_reports"), "--dot-dir", os.path.join(d, "traceability_graphs")],
                       check=True, env=env, stdout=subprocess.DEVNULL)
    counts = graph_counts()
    json.dump(counts, open(os.path.join(RES, "structural.json"), "w", encoding="utf-8"), indent=1)
    r = subprocess.run(["node", os.path.join(HERE, "lsp_all.mjs"), os.path.join(ROOT, "data"), os.path.join(RES, "lsp.json")],
                       env=env, capture_output=True, text=True, encoding="utf-8")
    open(os.path.join(RES, "lsp.log"), "w", encoding="utf-8").write(r.stdout + r.stderr)
    lsp = json.load(open(os.path.join(RES, "lsp.json"), encoding="utf-8"))
    lines, ok_all = [], True
    for f in FILES:
        c, a = counts[f], next(x for x in lsp if x["file"] == f)
        ok_all &= bool(a["lspOk"])
        lines.append(f"{f:40s} slots {c['slots']}  relations {c['slot_relations']}  "
                     f"units {c['source_units']}  edges {c['graph'].get('edges')}  defects {sum(c['defects'].values())}  "
                     f"lsp {'ok' if a['lspOk'] else 'FAIL'} err {a['stats']['diagnostics'].get('error', 0)}  validator {a['validator']['errors']}E/{a['validator']['warnings']}W  "
                     f"schema {a['schema']['errors']}E/{a['schema']['warnings']}W")
    g = [counts[f] for f in FILES[:3]]
    lines.append(f"gold totals: units {sum(x['source_units'] for x in g)}, slots {sum(x['slots'] for x in g)}, relations {sum(x['slot_relations'] for x in g)}, "
                 f"edges {sum(x['graph'].get('edges', 0) for x in g)}")
    lines.append(f"all seven: slots {sum(counts[f]['slots'] for f in FILES)}, relations {sum(counts[f]['slot_relations'] for f in FILES)}")
    open(os.path.join(RES, "summary.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
