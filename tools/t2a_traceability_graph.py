#!/usr/bin/env python3
"""
Build and analyze a traceability graph from Text2Activity T2A-ESS JSON files.

The graph has two edge families:
- source_trace: SourceUnit -> extracted slot, derived from each slot's source_ref.
- slot_relation: slot -> slot, derived from text2activity_extraction_model.slot_relations.

The script uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


SLOT_COLLECTIONS: List[Tuple[str, str, str]] = [
    ("scenarios", "scenario_id", "Scenario"),
    ("episodes", "episode_id", "Episode"),
    ("situations", "situation_id", "Situation"),
    ("state_values", "state_value_id", "StateValue"),
    ("observations", "observation_id", "Observation"),
    ("events", "event_id", "Event"),
    ("transitions", "transition_id", "Transition"),
    ("performers", "performer_id", "Performer"),
    ("actions", "action_id", "Action"),
    ("items", "item_id", "Item"),
    ("flows", "flow_id", "Flow"),
    ("controls", "control_id", "Control"),
    ("constraints", "constraint_id", "Constraint"),
    ("goals", "goal_id", "Goal"),
    ("reasons", "reason_id", "Reason"),
    ("domain_extension_rules", "domain_extension_rule_id", "DomainExtensionRule"),
    ("semantic_bindings", "semantic_binding_id", "SemanticBinding"),
]

COLLECTION_BY_TYPE = {slot_type: collection for collection, _, slot_type in SLOT_COLLECTIONS}
ID_FIELD_BY_COLLECTION = {collection: id_field for collection, id_field, _ in SLOT_COLLECTIONS}
PERFORMER_RELATION_TYPES = {
    "performed_by",
    "performs",
    "has_performer",
    "assigned_to",
    "allocated_to",
}


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    return data.get("text2activity_extraction_model", data)


def relation_type(rel: Dict[str, Any]) -> str:
    raw = str(rel.get("relation_type", "") or "")
    if raw == "custom" and rel.get("custom_relation_type"):
        return str(rel["custom_relation_type"])
    return raw or "unspecified"


def compact(value: Any, limit: int = 90) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).replace("\r", " ").replace("\n", " ").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


def best_label(record: Dict[str, Any]) -> str:
    for key in ("label", "title", "name", "text", "description", "value", "object_text"):
        if key in record and record[key] not in (None, ""):
            return compact(record[key], 120)
    return ""


def collect_key_values(obj: Any, key_name: str) -> List[str]:
    found: List[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == key_name and isinstance(value, str):
                found.append(value)
            else:
                found.extend(collect_key_values(value, key_name))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(collect_key_values(item, key_name))
    return found


def unique_in_order(values: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def node_collection_counts(nodes: Dict[str, Dict[str, Any]]) -> collections.Counter:
    counts: collections.Counter = collections.Counter()
    for node in nodes.values():
        if node["type"] != "SourceUnit":
            counts[node["type"]] += 1
    return counts


def build_graph(path: Path) -> Dict[str, Any]:
    model = load_json(path)
    nodes: Dict[str, Dict[str, Any]] = {}
    semantic_node_ids: Set[str] = set()
    source_unit_ids: Set[str] = set()
    duplicate_ids: List[str] = []
    missing_ids: List[str] = []

    for source in model.get("source_units", []) or []:
        source_id = source.get("source_unit_id")
        if not source_id:
            missing_ids.append("source_units:<missing source_unit_id>")
            continue
        source_unit_ids.add(source_id)
        if source_id in nodes:
            duplicate_ids.append(source_id)
        nodes[source_id] = {
            "id": source_id,
            "type": "SourceUnit",
            "collection": "source_units",
            "label": compact(source.get("text", ""), 140),
            "source_refs": [],
            "confidence": None,
            "record": source,
            "is_semantic_slot": False,
        }

    for collection, id_field, slot_type in SLOT_COLLECTIONS:
        for record in model.get(collection, []) or []:
            slot_id = record.get(id_field)
            if not slot_id:
                missing_ids.append(f"{collection}:<missing {id_field}>")
                continue
            if slot_id in nodes:
                duplicate_ids.append(slot_id)
            refs = unique_in_order(collect_key_values(record, "source_unit_id"))
            nodes[slot_id] = {
                "id": slot_id,
                "type": slot_type,
                "collection": collection,
                "label": best_label(record),
                "source_refs": refs,
                "confidence": record.get("confidence"),
                "record": record,
                "is_semantic_slot": True,
            }
            semantic_node_ids.add(slot_id)

    edges: List[Dict[str, Any]] = []
    edge_id_seq = 1

    for slot_id in sorted(semantic_node_ids):
        for source_id in nodes[slot_id]["source_refs"]:
            edges.append(
                {
                    "id": f"TRACE_{edge_id_seq:05d}",
                    "kind": "source_trace",
                    "source": source_id,
                    "target": slot_id,
                    "relation_type": "source_ref",
                    "confidence": nodes[slot_id].get("confidence"),
                    "record": {},
                }
            )
            edge_id_seq += 1

    relation_edges: List[Dict[str, Any]] = []
    for rel in model.get("slot_relations", []) or []:
        edge = {
            "id": rel.get("relation_id") or f"REL_{edge_id_seq:05d}",
            "kind": "slot_relation",
            "source": rel.get("source_slot_id"),
            "target": rel.get("target_slot_id"),
            "relation_type": relation_type(rel),
            "confidence": rel.get("confidence"),
            "record": rel,
        }
        edges.append(edge)
        relation_edges.append(edge)
        edge_id_seq += 1

    outgoing: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    incoming: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    for edge in edges:
        outgoing[edge.get("source")].append(edge)
        incoming[edge.get("target")].append(edge)

    return {
        "path": path,
        "model": model,
        "nodes": nodes,
        "semantic_node_ids": semantic_node_ids,
        "source_unit_ids": source_unit_ids,
        "edges": edges,
        "relation_edges": relation_edges,
        "outgoing": outgoing,
        "incoming": incoming,
        "duplicate_ids": duplicate_ids,
        "missing_ids": missing_ids,
    }


def semantic_degree(graph: Dict[str, Any], slot_id: str) -> int:
    count = 0
    for edge in graph["outgoing"].get(slot_id, []):
        if edge["kind"] == "slot_relation":
            count += 1
    for edge in graph["incoming"].get(slot_id, []):
        if edge["kind"] == "slot_relation":
            count += 1
    return count


def relation_endpoint_issues(graph: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    semantic_ids = graph["semantic_node_ids"]
    nodes = graph["nodes"]
    for edge in graph["relation_edges"]:
        source = edge.get("source")
        target = edge.get("target")
        if source not in nodes:
            issues.append(f"{edge['id']}: missing source {source}")
        elif source not in semantic_ids:
            issues.append(f"{edge['id']}: source is not a semantic slot {source}")
        if target not in nodes:
            issues.append(f"{edge['id']}: missing target {target}")
        elif target not in semantic_ids:
            issues.append(f"{edge['id']}: target is not a semantic slot {target}")
    return issues


def source_ref_issues(graph: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    defined = graph["source_unit_ids"]
    for slot_id in graph["semantic_node_ids"]:
        for source_id in graph["nodes"][slot_id]["source_refs"]:
            if source_id not in defined:
                issues.append(f"{slot_id}: missing source_unit {source_id}")
    return issues


def source_units_without_slots(graph: Dict[str, Any]) -> List[str]:
    result: List[str] = []
    for source_id in sorted(graph["source_unit_ids"]):
        trace_edges = [
            edge
            for edge in graph["outgoing"].get(source_id, [])
            if edge["kind"] == "source_trace"
        ]
        if not trace_edges:
            result.append(source_id)
    return result


def slots_without_source_ref(graph: Dict[str, Any]) -> List[str]:
    result: List[str] = []
    for slot_id in sorted(graph["semantic_node_ids"]):
        if not graph["nodes"][slot_id]["source_refs"]:
            result.append(slot_id)
    return result


def isolated_slots(graph: Dict[str, Any]) -> List[str]:
    result: List[str] = []
    for slot_id in sorted(graph["semantic_node_ids"]):
        if semantic_degree(graph, slot_id) == 0:
            result.append(slot_id)
    return result


def actions_without_performer_relation(graph: Dict[str, Any]) -> List[str]:
    result: List[str] = []
    nodes = graph["nodes"]
    for slot_id in sorted(graph["semantic_node_ids"]):
        node = nodes[slot_id]
        if node["type"] != "Action":
            continue
        actor_text = node["record"].get("primary_actor_text")
        if not actor_text:
            continue
        linked = False
        for edge in graph["outgoing"].get(slot_id, []) + graph["incoming"].get(slot_id, []):
            if edge["kind"] != "slot_relation":
                continue
            other_id = edge["target"] if edge["source"] == slot_id else edge["source"]
            other = nodes.get(other_id)
            if not other:
                continue
            if other["type"] == "Performer" and edge["relation_type"] in PERFORMER_RELATION_TYPES:
                linked = True
                break
            if other["type"] == "Performer" and edge["relation_type"] == "custom":
                linked = True
                break
        if not linked:
            result.append(slot_id)
    return result


def transition_completeness(graph: Dict[str, Any]) -> Dict[str, List[str]]:
    missing = {
        "missing_from_situation": [],
        "missing_to_situation": [],
        "missing_trigger": [],
    }
    for slot_id in sorted(graph["semantic_node_ids"]):
        node = graph["nodes"][slot_id]
        if node["type"] != "Transition":
            continue
        out_types = {
            edge["relation_type"]
            for edge in graph["outgoing"].get(slot_id, [])
            if edge["kind"] == "slot_relation"
        }
        in_types = {
            edge["relation_type"]
            for edge in graph["incoming"].get(slot_id, [])
            if edge["kind"] == "slot_relation"
        }
        if "from_situation" not in out_types:
            missing["missing_from_situation"].append(slot_id)
        if "to_situation" not in out_types:
            missing["missing_to_situation"].append(slot_id)
        if "triggers" not in in_types:
            missing["missing_trigger"].append(slot_id)
    return missing


def flow_completeness(graph: Dict[str, Any]) -> Dict[str, List[str]]:
    missing = {
        "missing_flow_source": [],
        "missing_flow_target": [],
    }
    for slot_id in sorted(graph["semantic_node_ids"]):
        node = graph["nodes"][slot_id]
        if node["type"] != "Flow":
            continue
        incident_types = {
            edge["relation_type"]
            for edge in graph["outgoing"].get(slot_id, []) + graph["incoming"].get(slot_id, [])
            if edge["kind"] == "slot_relation"
        }
        if "flow_source" not in incident_types:
            missing["missing_flow_source"].append(slot_id)
        if "flow_target" not in incident_types:
            missing["missing_flow_target"].append(slot_id)
    return missing


def relation_counts(graph: Dict[str, Any]) -> collections.Counter:
    counts: collections.Counter = collections.Counter()
    for edge in graph["relation_edges"]:
        counts[edge["relation_type"]] += 1
    return counts


def validation_summary(graph: Dict[str, Any]) -> Dict[str, Any]:
    trans = transition_completeness(graph)
    flows = flow_completeness(graph)
    return {
        "duplicate_ids": graph["duplicate_ids"],
        "missing_ids": graph["missing_ids"],
        "relation_endpoint_issues": relation_endpoint_issues(graph),
        "source_ref_issues": source_ref_issues(graph),
        "source_units_without_slots": source_units_without_slots(graph),
        "slots_without_source_ref": slots_without_source_ref(graph),
        "isolated_slots": isolated_slots(graph),
        "actions_without_performer_relation": actions_without_performer_relation(graph),
        "transition_missing_from": trans["missing_from_situation"],
        "transition_missing_to": trans["missing_to_situation"],
        "transition_missing_trigger": trans["missing_trigger"],
        "flow_missing_source": flows["missing_flow_source"],
        "flow_missing_target": flows["missing_flow_target"],
    }


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> List[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return lines


def list_preview(values: Sequence[str], max_items: int) -> str:
    if not values:
        return "-"
    head = list(values[:max_items])
    suffix = "" if len(values) <= max_items else f" ... (+{len(values) - max_items})"
    return ", ".join(head) + suffix


def neighborhood(
    graph: Dict[str, Any],
    start_id: str,
    depth: int,
    include_source_trace: bool = True,
) -> List[Tuple[int, str, Dict[str, Any], str]]:
    visited = {start_id}
    queue: collections.deque = collections.deque([(start_id, 0)])
    rows: List[Tuple[int, str, Dict[str, Any], str]] = []
    while queue:
        node_id, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        incident: List[Tuple[str, Dict[str, Any], str]] = []
        for edge in graph["outgoing"].get(node_id, []):
            if edge["kind"] == "source_trace" and not include_source_trace:
                continue
            incident.append(("out", edge, edge["target"]))
        for edge in graph["incoming"].get(node_id, []):
            if edge["kind"] == "source_trace" and not include_source_trace:
                continue
            incident.append(("in", edge, edge["source"]))
        for direction, edge, other_id in incident:
            rows.append((current_depth + 1, direction, edge, other_id))
            if other_id not in visited:
                visited.add(other_id)
                queue.append((other_id, current_depth + 1))
    return rows


def shortest_path(graph: Dict[str, Any], start_id: str, end_id: str) -> Optional[List[Tuple[str, Optional[Dict[str, Any]]]]]:
    queue: collections.deque = collections.deque([start_id])
    parent: Dict[str, Tuple[Optional[str], Optional[Dict[str, Any]]]] = {start_id: (None, None)}
    while queue:
        node_id = queue.popleft()
        if node_id == end_id:
            break
        for edge in graph["outgoing"].get(node_id, []):
            nxt = edge["target"]
            if nxt not in parent:
                parent[nxt] = (node_id, edge)
                queue.append(nxt)
        for edge in graph["incoming"].get(node_id, []):
            nxt = edge["source"]
            if nxt not in parent:
                reverse_edge = dict(edge)
                reverse_edge["relation_type"] = f"reverse:{edge['relation_type']}"
                parent[nxt] = (node_id, reverse_edge)
                queue.append(nxt)
    if end_id not in parent:
        return None
    result: List[Tuple[str, Optional[Dict[str, Any]]]] = []
    node_id: Optional[str] = end_id
    while node_id is not None:
        prev, edge = parent[node_id]
        result.append((node_id, edge))
        node_id = prev
    result.reverse()
    return result


def dot_escape(text: Any) -> str:
    value = str(text)
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")


def mermaid_escape(text: Any, limit: Optional[int] = None) -> str:
    value = compact(text, limit or 10_000)
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    value = value.replace('"', "'").replace("[", "(").replace("]", ")")
    value = value.replace("{", "(").replace("}", ")").replace("|", "/")
    return value


def mermaid_edge_label(text: Any) -> str:
    value = mermaid_escape(text, 60)
    value = value.replace("-", "_").replace(":", "_")
    return value or "rel"


def node_color(node_type: str) -> str:
    colors = {
        "SourceUnit": "#F6F8FA",
        "Scenario": "#DDEBFF",
        "Episode": "#E7F0FF",
        "Action": "#E8F5E9",
        "Performer": "#FFF4D6",
        "Event": "#FFE3E3",
        "Transition": "#FFD6D6",
        "Situation": "#EFE6FF",
        "StateValue": "#F5ECFF",
        "Flow": "#E0F7FA",
        "Control": "#E0F2F1",
        "Constraint": "#FCE4EC",
        "Goal": "#E8EAF6",
        "Reason": "#FFF8E1",
    }
    return colors.get(node_type, "#FFFFFF")


def write_dot(graph: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "digraph T2A_Traceability {",
        '  graph [rankdir=LR, splines=true, overlap=false];',
        '  node [shape=box, style="rounded,filled", fontname="Malgun Gothic", fontsize=10];',
        '  edge [fontname="Malgun Gothic", fontsize=9];',
    ]
    for node_id, node in sorted(graph["nodes"].items()):
        label_parts = [node["type"], node_id]
        if node["label"]:
            label_parts.append(compact(node["label"], 70))
        label = "\\n".join(dot_escape(part) for part in label_parts)
        lines.append(
            f'  "{dot_escape(node_id)}" [label="{label}", fillcolor="{node_color(node["type"])}"];'
        )
    for edge in graph["edges"]:
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            continue
        style = "dashed" if edge["kind"] == "source_trace" else "solid"
        color = "#8A8A8A" if edge["kind"] == "source_trace" else "#333333"
        label = dot_escape(edge["relation_type"])
        lines.append(
            f'  "{dot_escape(source)}" -> "{dot_escape(target)}" '
            f'[label="{label}", style="{style}", color="{color}"];'
        )
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def mermaid_graph(
    graph: Dict[str, Any],
    include_source_trace: bool,
    max_edges: int,
    direction: str,
    label_length: int,
) -> Tuple[List[str], int, int]:
    candidate_edges = [
        edge
        for edge in graph["edges"]
        if include_source_trace or edge["kind"] == "slot_relation"
    ]
    valid_edges = [
        edge
        for edge in candidate_edges
        if edge.get("source") in graph["nodes"] and edge.get("target") in graph["nodes"]
    ]
    selected_edges = valid_edges[:max_edges]
    omitted_edges = max(0, len(valid_edges) - len(selected_edges))

    included_node_ids: Set[str] = set()
    for edge in selected_edges:
        included_node_ids.add(edge["source"])
        included_node_ids.add(edge["target"])

    node_aliases = {
        node_id: f"N{index:04d}"
        for index, node_id in enumerate(sorted(included_node_ids), start=1)
    }

    lines = [f"flowchart {direction}"]
    for node_id in sorted(included_node_ids):
        node = graph["nodes"][node_id]
        label_parts = [node["type"], node_id]
        if node["label"]:
            label_parts.append(node["label"])
        label = "<br/>".join(mermaid_escape(part, label_length) for part in label_parts)
        lines.append(f'  {node_aliases[node_id]}["{label}"]')

    for edge in selected_edges:
        source = node_aliases[edge["source"]]
        target = node_aliases[edge["target"]]
        label = mermaid_edge_label(edge["relation_type"])
        style = "-.->" if edge["kind"] == "source_trace" else "-->"
        lines.append(f"  {source} {style}|{label}| {target}")

    class_defs = [
        ("SourceUnit", "#F6F8FA", "#8A8A8A"),
        ("Scenario", "#DDEBFF", "#5A78B8"),
        ("Episode", "#E7F0FF", "#5A78B8"),
        ("Action", "#E8F5E9", "#4C8A4C"),
        ("Performer", "#FFF4D6", "#9A7A2F"),
        ("Event", "#FFE3E3", "#B45A5A"),
        ("Transition", "#FFD6D6", "#B45A5A"),
        ("Situation", "#EFE6FF", "#7B5AB8"),
        ("StateValue", "#F5ECFF", "#7B5AB8"),
        ("Flow", "#E0F7FA", "#438A91"),
        ("Control", "#E0F2F1", "#438A75"),
        ("Constraint", "#FCE4EC", "#A35272"),
        ("Goal", "#E8EAF6", "#5A62A8"),
        ("Reason", "#FFF8E1", "#9A7A2F"),
        ("Item", "#F1F8E9", "#6B8A3A"),
        ("DomainExtensionRule", "#ECEFF1", "#607D8B"),
        ("SemanticBinding", "#ECEFF1", "#607D8B"),
    ]
    for class_name, fill, stroke in class_defs:
        lines.append(f"  classDef {class_name} fill:{fill},stroke:{stroke},stroke-width:1px,color:#111;")

    class_groups: Dict[str, List[str]] = collections.defaultdict(list)
    for node_id in sorted(included_node_ids):
        node_type = graph["nodes"][node_id]["type"]
        class_groups[node_type].append(node_aliases[node_id])
    for node_type, aliases in sorted(class_groups.items()):
        if node_type in {name for name, _, _ in class_defs}:
            lines.append(f"  class {','.join(aliases)} {node_type};")

    return lines, len(selected_edges), omitted_edges


def write_report(
    graphs: Sequence[Dict[str, Any]],
    path: Path,
    max_items: int,
    trace_slots: Sequence[str],
    trace_sources: Sequence[str],
    trace_depth: int,
    path_queries: Sequence[Tuple[str, str]],
    include_mermaid: bool,
    mermaid_include_source_trace: bool,
    mermaid_max_edges: int,
    mermaid_direction: str,
    mermaid_label_length: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = [
        "# T2A-ESS Relationship Traceability Report",
        "",
        "This report is generated from T2A-ESS JSON files. It checks relationship endpoints, source traceability, graph connectivity, and selected semantic completeness indicators.",
        "",
    ]

    overview_rows = []
    for graph in graphs:
        counts = node_collection_counts(graph["nodes"])
        overview_rows.append(
            [
                graph["path"].name,
                len(graph["source_unit_ids"]),
                sum(counts.values()),
                len(graph["relation_edges"]),
                len(graph["edges"]),
            ]
        )
    lines.extend(markdown_table(["File", "Source Units", "Slots", "Slot Relations", "Graph Edges"], overview_rows))
    lines.append("")

    for graph in graphs:
        model = graph["model"]
        title = model.get("title") or graph["path"].stem
        validation = validation_summary(graph)
        counts = node_collection_counts(graph["nodes"])
        relation_count = relation_counts(graph)

        lines.extend([f"## {graph['path'].name}", "", f"- Model: {compact(title, 140)}"])
        lines.append("")

        slot_rows = [[slot_type, counts.get(slot_type, 0)] for _, _, slot_type in SLOT_COLLECTIONS]
        lines.extend(markdown_table(["Slot Type", "Count"], slot_rows))
        lines.append("")

        rel_rows = [[name, count] for name, count in relation_count.most_common()]
        lines.extend(markdown_table(["Relation Type", "Count"], rel_rows or [["-", 0]]))
        lines.append("")

        if include_mermaid:
            mermaid_lines, selected_edges, omitted_edges = mermaid_graph(
                graph,
                include_source_trace=mermaid_include_source_trace,
                max_edges=mermaid_max_edges,
                direction=mermaid_direction,
                label_length=mermaid_label_length,
            )
            lines.append("### Mermaid Relationship Graph")
            lines.append("")
            mode = "slot_relations + source_ref" if mermaid_include_source_trace else "slot_relations"
            lines.append(
                f"- Mode: `{mode}`. Rendered edges: `{selected_edges}`. Omitted edges: `{omitted_edges}`."
            )
            lines.append("")
            lines.append("```mermaid")
            lines.extend(mermaid_lines)
            lines.append("```")
            lines.append("")

        quality_rows = [
            ["Duplicate IDs", len(validation["duplicate_ids"]), list_preview(validation["duplicate_ids"], max_items)],
            ["Missing IDs", len(validation["missing_ids"]), list_preview(validation["missing_ids"], max_items)],
            [
                "Dangling Slot Relations",
                len(validation["relation_endpoint_issues"]),
                list_preview(validation["relation_endpoint_issues"], max_items),
            ],
            ["Dangling Source Refs", len(validation["source_ref_issues"]), list_preview(validation["source_ref_issues"], max_items)],
            [
                "Source Units Without Slots",
                len(validation["source_units_without_slots"]),
                list_preview(validation["source_units_without_slots"], max_items),
            ],
            [
                "Slots Without Source Ref",
                len(validation["slots_without_source_ref"]),
                list_preview(validation["slots_without_source_ref"], max_items),
            ],
            ["Isolated Slots", len(validation["isolated_slots"]), list_preview(validation["isolated_slots"], max_items)],
            [
                "Actions With Actor Text But No Performer Relation",
                len(validation["actions_without_performer_relation"]),
                list_preview(validation["actions_without_performer_relation"], max_items),
            ],
            [
                "Transitions Missing from_situation",
                len(validation["transition_missing_from"]),
                list_preview(validation["transition_missing_from"], max_items),
            ],
            [
                "Transitions Missing to_situation",
                len(validation["transition_missing_to"]),
                list_preview(validation["transition_missing_to"], max_items),
            ],
            [
                "Transitions Missing trigger",
                len(validation["transition_missing_trigger"]),
                list_preview(validation["transition_missing_trigger"], max_items),
            ],
            ["Flows Missing source", len(validation["flow_missing_source"]), list_preview(validation["flow_missing_source"], max_items)],
            ["Flows Missing target", len(validation["flow_missing_target"]), list_preview(validation["flow_missing_target"], max_items)],
        ]
        lines.extend(markdown_table(["Check", "Count", "Examples"], quality_rows))
        lines.append("")

        if graph["source_unit_ids"]:
            first_source = sorted(graph["source_unit_ids"])[0]
            lines.append(f"### Example Source Trace: `{first_source}`")
            rows = []
            for depth, direction, edge, other_id in neighborhood(graph, first_source, 1):
                other = graph["nodes"].get(other_id, {})
                rows.append([depth, direction, edge["relation_type"], other_id, other.get("type", "?"), compact(other.get("label", ""), 80)])
            lines.extend(markdown_table(["Depth", "Dir", "Relation", "Node", "Type", "Label"], rows[:max_items] or [["-", "-", "-", "-", "-", "-"]]))
            lines.append("")

        requested_starts = list(trace_sources) + list(trace_slots)
        for start_id in requested_starts:
            if start_id not in graph["nodes"]:
                continue
            lines.append(f"### Requested Trace: `{start_id}`")
            rows = []
            for depth, direction, edge, other_id in neighborhood(graph, start_id, trace_depth):
                other = graph["nodes"].get(other_id, {})
                rows.append([depth, direction, edge["relation_type"], other_id, other.get("type", "?"), compact(other.get("label", ""), 80)])
            lines.extend(markdown_table(["Depth", "Dir", "Relation", "Node", "Type", "Label"], rows[:max_items] or [["-", "-", "-", "-", "-", "-"]]))
            lines.append("")

        for start_id, end_id in path_queries:
            if start_id not in graph["nodes"] or end_id not in graph["nodes"]:
                continue
            lines.append(f"### Requested Path: `{start_id}` -> `{end_id}`")
            path_result = shortest_path(graph, start_id, end_id)
            if not path_result:
                lines.append("")
                lines.append("No path found.")
                lines.append("")
                continue
            path_text = []
            for index, (node_id, edge) in enumerate(path_result):
                if index == 0:
                    path_text.append(f"`{node_id}`")
                else:
                    rel = edge["relation_type"] if edge else "?"
                    path_text.append(f"-[{rel}]-> `{node_id}`")
            lines.append("")
            lines.append(" ".join(path_text))
            lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def report_path_for_graph(report_dir: Path, graph: Dict[str, Any]) -> Path:
    return report_dir / f"{graph['path'].stem}_traceability_report.md"


def expand_inputs(patterns: Sequence[str], base_dir: Path) -> List[Path]:
    paths: List[Path] = []
    for pattern in patterns:
        pattern_path = Path(pattern)
        glob_pattern = str(pattern_path if pattern_path.is_absolute() else base_dir / pattern)
        matches = [Path(match) for match in glob.glob(glob_pattern)]
        if matches:
            paths.extend(matches)
        elif pattern_path.exists():
            paths.append(pattern_path)
    unique: Dict[Path, None] = {}
    for path in paths:
        if path.is_file():
            unique[path.resolve()] = None
    return sorted(unique.keys())


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Build T2A-ESS traceability graphs and relationship quality reports."
    )
    parser.add_argument(
        "--input",
        nargs="*",
        default=["*T2A-ESS*.json"],
        help="Input JSON file(s) or glob(s). Defaults to '*T2A-ESS*.json' in the script directory.",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Optional combined Markdown report output path. If omitted, one Markdown report is generated per JSON.",
    )
    parser.add_argument(
        "--report-dir",
        default=str(script_dir / "traceability_reports"),
        help="Directory for per-JSON Markdown reports.",
    )
    parser.add_argument(
        "--dot-dir",
        default=str(script_dir / "traceability_graphs"),
        help="Directory for Graphviz DOT files.",
    )
    parser.add_argument("--no-dot", action="store_true", help="Do not write DOT graph files.")
    parser.add_argument("--max-list", type=int, default=20, help="Maximum examples shown per report row.")
    parser.add_argument("--trace-slot", action="append", default=[], help="Slot ID to trace in the report.")
    parser.add_argument("--trace-source", action="append", default=[], help="Source unit ID to trace in the report.")
    parser.add_argument("--trace-depth", type=int, default=2, help="Trace BFS depth for requested traces.")
    parser.add_argument(
        "--path",
        nargs=2,
        action="append",
        default=[],
        metavar=("FROM_ID", "TO_ID"),
        help="Find an undirected shortest path between two graph nodes.",
    )
    parser.add_argument("--no-mermaid", action="store_true", help="Do not embed Mermaid diagrams in the Markdown report.")
    parser.add_argument(
        "--mermaid-include-source-trace",
        action="store_true",
        help="Include SourceUnit -> Slot source_ref edges in Mermaid diagrams. Defaults to slot_relations only.",
    )
    parser.add_argument(
        "--mermaid-max-edges",
        type=int,
        default=120,
        help="Maximum graph edges to render in each Mermaid diagram.",
    )
    parser.add_argument(
        "--mermaid-direction",
        choices=["LR", "TD", "RL", "BT"],
        default="LR",
        help="Mermaid flowchart direction.",
    )
    parser.add_argument(
        "--mermaid-label-length",
        type=int,
        default=55,
        help="Maximum label length per node label line in Mermaid diagrams.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with code 1 if duplicate IDs, dangling slot relations, or dangling source refs exist.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    script_dir = Path(__file__).resolve().parent
    input_paths = expand_inputs(args.input, script_dir)
    if not input_paths:
        print("No input JSON files found.", file=sys.stderr)
        return 2

    graphs = [build_graph(path) for path in input_paths]

    if not args.no_dot:
        dot_dir = Path(args.dot_dir)
        for graph in graphs:
            write_dot(graph, dot_dir / f"{graph['path'].stem}.dot")

    report_paths: List[Path] = []
    report_dir = Path(args.report_dir)
    for graph in graphs:
        report_path = report_path_for_graph(report_dir, graph)
        write_report(
            [graph],
            report_path,
            max_items=args.max_list,
            trace_slots=args.trace_slot,
            trace_sources=args.trace_source,
            trace_depth=args.trace_depth,
            path_queries=args.path,
            include_mermaid=not args.no_mermaid,
            mermaid_include_source_trace=args.mermaid_include_source_trace,
            mermaid_max_edges=args.mermaid_max_edges,
            mermaid_direction=args.mermaid_direction,
            mermaid_label_length=args.mermaid_label_length,
        )
        report_paths.append(report_path)

    combined_report_path: Optional[Path] = None
    if args.report:
        combined_report_path = Path(args.report)
        write_report(
            graphs,
            combined_report_path,
            max_items=args.max_list,
            trace_slots=args.trace_slot,
            trace_sources=args.trace_source,
            trace_depth=args.trace_depth,
            path_queries=args.path,
            include_mermaid=not args.no_mermaid,
            mermaid_include_source_trace=args.mermaid_include_source_trace,
            mermaid_max_edges=args.mermaid_max_edges,
            mermaid_direction=args.mermaid_direction,
            mermaid_label_length=args.mermaid_label_length,
        )

    print(f"Analyzed {len(graphs)} file(s).")
    print(f"Per-JSON reports: {report_dir}")
    for report_path in report_paths:
        print(f"  - {report_path}")
    if combined_report_path:
        print(f"Combined report: {combined_report_path}")
    if not args.no_dot:
        print(f"DOT graphs: {Path(args.dot_dir)}")

    if args.fail_on_error:
        hard_errors = []
        for graph in graphs:
            validation = validation_summary(graph)
            if validation["duplicate_ids"] or validation["relation_endpoint_issues"] or validation["source_ref_issues"]:
                hard_errors.append(graph["path"].name)
        if hard_errors:
            print("Hard validation errors in: " + ", ".join(hard_errors), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
