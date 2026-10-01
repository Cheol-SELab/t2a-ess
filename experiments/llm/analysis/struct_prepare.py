"""Extract predicted JSON from run files and compute traceability-report defects (Table 4 categories).

usage: python struct_prepare.py <repository-root> <run.json> [...]
  writes <run>.pred.json (wrapped as text2activity_extraction_model) and <run>.trace.json
"""
import json, os, sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scoring"))
import score as S  # noqa: E402

head = sys.argv[1]
sys.path.insert(0, os.path.join(head, "tools"))  # t2a-ess: tools/t2a_traceability_graph.py
import t2a_traceability_graph as T  # noqa: E402

for run_path in sys.argv[2:]:
    run = json.load(open(run_path, encoding="utf-8"))
    base = run_path[:-5]
    try:
        pred = S.load_json_text(run["result_text"] or "")
    except Exception as e:  # noqa: BLE001
        json.dump({"ok": False, "error": str(e)[:300]}, open(base + ".trace.json", "w", encoding="utf-8"))
        continue
    pred = pred.get("text2activity_extraction_model", pred)
    wrapped = {"text2activity_extraction_model": pred}
    json.dump(wrapped, open(base + ".pred.json", "w", encoding="utf-8"), ensure_ascii=False)
    g = T.build_graph(Path(base + ".pred.json"))
    v = T.validation_summary(g)
    counts = {k: (len(x) if isinstance(x, list) else x) for k, x in v.items() if isinstance(x, list)}
    json.dump({"ok": True, "defects": counts, "total_defects": sum(counts.values())}, open(base + ".trace.json", "w", encoding="utf-8"), indent=1)
    print(os.path.basename(base), sum(counts.values()), {k: c for k, c in counts.items() if c})
