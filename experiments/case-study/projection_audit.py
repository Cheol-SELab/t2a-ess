"""Audit what the EFFBD projection keeps and drops, per control and per flow (English case-study models)."""
import json, re, sys
sys.stdout.reconfigure(encoding="utf-8")
OUT = sys.argv[1]
report = {}
for key in ("mumt", "nghe"):
    m = json.load(open(f"{OUT}/{key}-gold-en.json", encoding="utf-8"))["text2activity_extraction_model"]
    sysml = open(f"{OUT}/{key}-en.sysml", encoding="utf-8").read()
    graph = json.load(open(f"{OUT}/{key}-en.graph.json", encoding="utf-8"))
    rel = m["slot_relations"]
    tg = lambda s, t: [r["target_slot_id"] for r in rel if r["source_slot_id"] == s and r["relation_type"] == t]
    ep_of = {}
    for ep in m["episodes"]:
        for r in rel:
            if r["source_slot_id"] == ep["episode_id"] and r["relation_type"] in ("custom", "has_action", "contains", "contains_action"):
                ep_of.setdefault(r["target_slot_id"], ep["episode_id"])
    flows = {f["flow_id"]: f for f in m["flows"]}
    rows_c = []
    for c in m["controls"]:
        for fid in tg(c["control_id"], "controls_flow"):
            src, dst = tg(fid, "flow_source"), tg(fid, "flow_target")
            cross = bool(src and dst and ep_of.get(src[0]) != ep_of.get(dst[0]))
            texts = c.get("guard_texts", [])
            shown = [t for t in texts if f"if '{t}' == true" in sysml]
            rows_c.append({"control": c["control_id"], "type": c.get("control_type"), "flow": fid,
                           "src_ep": ep_of.get(src[0]) if src else None, "dst_ep": ep_of.get(dst[0]) if dst else None,
                           "cross_episode": cross, "guard_texts": len(texts), "guard_texts_emitted": len(shown)})
    rows_f = []
    for fid, f in flows.items():
        src, dst = tg(fid, "flow_source"), tg(fid, "flow_target")
        rows_f.append({"flow": fid, "kind": f.get("flow_kind"), "cross_episode": bool(src and dst and ep_of.get(src[0]) != ep_of.get(dst[0])),
                       "carries_item": bool(tg(fid, "carries_item"))})
    # per-episode ordering: intra-episode flows vs actions
    per_ep = []
    for ep in m["episodes"]:
        acts = [a for a, e in ep_of.items() if e == ep["episode_id"]]
        intra = [r for r in rows_f if not r["cross_episode"] and tg(r["flow"], "flow_source") and tg(r["flow"], "flow_source")[0] in acts]
        owner = [n["id"] for n in graph["nodes"] if n["kind"] == "ActionUsage" and n["id"].endswith("::" + ep["label"])]
        forks = [n for n in graph["nodes"] if n["kind"] == "ForkNode" and owner and n["id"].startswith(owner[0] + "::")]
        joins = [n for n in graph["nodes"] if n["kind"] == "JoinNode" and owner and n["id"].startswith(owner[0] + "::")]
        per_ep.append({"episode": ep["label"], "actions": len(acts), "intra_episode_flows": len(intra), "forks": len(forks), "joins": len(joins)})
    # joins fed by guarded successions
    guarded_join = [e for e in graph["edges"] if e["kind"] == "succession" and e.get("data", {}).get("guardCondition")
                    and "New End Concurrency" in e["target"]]
    report[key] = {"controls": rows_c, "flows": rows_f, "episodes": per_ep, "guarded_edges_into_join": len(guarded_join)}
json.dump(report, open(f"{OUT}/projection-audit.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
for k, v in report.items():
    print("==", k, "guarded edges into join:", v["guarded_edges_into_join"])
    for r in v["controls"]:
        print("  C", r)
    for r in v["flows"]:
        print("  F", r)
    for r in v["episodes"]:
        print("  E", r)
