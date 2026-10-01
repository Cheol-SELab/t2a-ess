"""Structural validation of the EFFBD derived from a T2A-ESS model.

The EFFBD SysML *dialect* is validated at runtime by the selab-effbd-editor's
IMM environment (the plain SysML v2 Pilot parser rejects it, and text2effbd's
compiler validates blueprints, not SysML text). This module instead checks the
EFFBD's *structure* in-repo — reference resolution, start→done reachability, and
item-flow completeness — so problems are caught before loading in the editor.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .model import ALL_SLOT_COLLECTIONS, T2AModel


@dataclass(frozen=True)
class Issue:
    severity: str  # "error" | "warning"
    code: str
    message: str


# ---------------------------------------------------------------------------
# Schema-level validation ("Slot Relation contract", docs/Text2Activity-Extraction-
# Slot-Schema.md §Slot Relation contract + pipeline step 14 validation).
# ---------------------------------------------------------------------------

# Registered custom_relation_type values; extend when a custom meaning is
# promoted into the contract.
REGISTERED_CUSTOM_TYPES: list[str] = []

_A, _E, _I, _P, _S, _SC = "actions", "episodes", "items", "performers", "situations", "scenarios"
_C, _F, _G, _R = "constraints", "flows", "goals", "reasons"
_OB, _EV, _T, _SV = "observations", "events", "transitions", "state_values"
_DR, _SB = "domain_extension_rules", "semantic_bindings"

# relation_type -> allowed (source_collection, target_collection) pairs.
RELATION_CONTRACT: dict[str, tuple[tuple[str, str], ...]] = {
    "has_episode": ((_SC, _E),),
    "contains_action": ((_E, _A),),
    "has_situation": ((_SC, _S), (_E, _S)),
    "entry_situation": ((_E, _S),),
    "exit_situation": ((_E, _S),),
    "has_part": ((_P, _P),),
    "performed_by": ((_A, _P),),
    "acts_on": ((_A, _I), (_A, _P)),
    "provided_to": ((_A, _P), (_A, _I)),
    "uses_item": ((_A, _I),),
    "produces_item": ((_A, _I),),
    "flow_source": ((_F, _A),),
    "flow_target": ((_F, _A),),
    "carries_item": ((_F, _I),),
    "controls_flow": (("controls", _F),),
    **{rt: tuple((s, t) for s in (_A, _T, _EV) for t in (_A, _T, _EV))
       for rt in ("temporal_before", "temporal_after", "temporal_during",
                  "temporal_while", "temporal_overlaps",
                  "temporal_starts_with", "temporal_ends_with")},
    "has_state_value": ((_S, _SV),),
    "from_situation": ((_T, _S),),
    "to_situation": ((_T, _S),),
    "observes": ((_OB, _EV), (_OB, _SV)),
    "triggers": ((_EV, _T), (_EV, _A)),
    "causes_event": ((_EV, _EV),),
    "originates_event": ((_P, _EV),),
    "causes": ((_A, _T),),
    "constrained_by": ((_A, _C), (_T, _C)),
    "has_goal": ((_SC, _G), (_A, _G), (_R, _G)),
    "has_reason": ((_A, _R), (_T, _R)),
    "has_evidence": ((_R, _OB),),
    "has_binding": ((_DR, _SB),),
    "binds_to": ((_SB, _A), (_SB, _P), (_SB, _I), (_SB, _EV), (_SB, _SV), (_SB, _S), (_SB, _T)),
    # "custom": any -> any (requires custom_relation_type; handled inline).
}


def validate_schema(model: T2AModel) -> list[Issue]:
    """Validate the T2A-ESS slot graph against the Slot Relation contract."""
    issues: list[Issue] = []
    def err(code: str, msg: str) -> None:
        issues.append(Issue("error", code, msg))

    def warn(code: str, msg: str) -> None:
        issues.append(Issue("warning", code, msg))

    # duplicate slot ids across collections
    owner: dict[str, str] = {}
    for collection in ALL_SLOT_COLLECTIONS:
        for slot in model.collection(collection):
            sid = model.slot_id(slot)
            if not sid:
                continue
            if sid in owner and owner[sid] != collection:
                err("DUPLICATE_SLOT_ID", f"{sid}: id in both {owner[sid]} and {collection}")
            else:
                owner.setdefault(sid, collection)

    by_id = model.by_id
    touched: set[str] = set()

    def _rid(rel: dict) -> str:
        return str(rel.get("relation_id") or rel.get("id") or "?")

    for rel in model.relations:
        rid = _rid(rel)
        rt = rel.get("relation_type")
        src, tgt = rel.get("source_slot_id"), rel.get("target_slot_id")
        touched.update(x for x in (src, tgt) if x)

        dangling = [x for x in (src, tgt) if x and x not in by_id]
        if dangling:
            err("DANGLING_RELATION_ENDPOINT",
                f"{rid}: endpoint not found: {', '.join(dangling)}")
            continue

        if rt == "custom":
            crt = rel.get("custom_relation_type")
            if not crt or not str(crt).strip():
                err("CUSTOM_TYPE_MISSING", f"{rid}: custom relation without custom_relation_type")
            elif crt not in REGISTERED_CUSTOM_TYPES:
                warn("CUSTOM_TYPE_NOT_REGISTERED",
                     f"{rid}: unregistered custom_relation_type: {crt}")
            continue

        if rt not in RELATION_CONTRACT:
            err("UNKNOWN_RELATION_TYPE", f"{rid}: unknown relation_type: {rt}")
            continue

        src_type, tgt_type = by_id[src][0], by_id[tgt][0]
        allowed = RELATION_CONTRACT[rt]
        if (src_type, tgt_type) not in allowed:
            allowed_s = ", ".join(f"{s}→{t}" for s, t in allowed)
            err("RELATION_ENDPOINT_TYPE",
                f"{rid}: {rt} {src_type}→{tgt_type} not allowed (allowed: {allowed_s})")

    # state-axis completeness
    for tr in model.collection("transitions"):
        tid = model.slot_id(tr)
        if len(model.out_relations(tid, "from_situation")) != 1 or \
           len(model.out_relations(tid, "to_situation")) != 1:
            err("TRANSITION_ENDPOINTS",
                f"{tid}: transition needs exactly 1 from_situation and 1 to_situation "
                f"(from={len(model.out_relations(tid, 'from_situation'))}, "
                f"to={len(model.out_relations(tid, 'to_situation'))})")
    for st in model.collection("situations"):
        sid = model.slot_id(st)
        if not model.out_relations(sid, "has_state_value"):
            warn("SITUATION_NO_STATE_VALUE", f"{sid}: situation has no has_state_value")
    for ob in model.collection("observations"):
        oid = model.slot_id(ob)
        if not model.out_relations(oid, "observes"):
            warn("OBSERVATION_NO_OBSERVES", f"{oid}: observation has no observes")
    for ev in model.collection("events"):
        eid = model.slot_id(ev)
        if eid not in touched:
            warn("ISOLATED_EVENT", f"{eid}: event appears in no relation")

    # episode coverage of actions
    for action in model.collection("actions"):
        aid = model.slot_id(action)
        parents = set(model.sources(aid, "contains_action"))
        if not parents:
            warn("ACTION_NO_EPISODE", f"{aid}: action not target of any contains_action")
        elif len(parents) > 1:
            warn("ACTION_MULTI_EPISODE",
                 f"{aid}: action target of contains_action from {len(parents)} episodes")

    # auxiliary *_text fields must be backed by the canonical relation they mirror
    def _nonempty(value) -> bool:
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, list):
            return any(str(v).strip() for v in value)
        return bool(value)

    for episode in model.collection("episodes"):
        eid = model.slot_id(episode)
        for field_name, rt in (("entry_situation_text", "entry_situation"),
                               ("exit_situation_text", "exit_situation")):
            if _nonempty(episode.get(field_name)) and not model.out_relations(eid, rt):
                warn("AUX_TEXT_WITHOUT_RELATION", f"{eid}: {field_name} set but no {rt} relation")
    for action in model.collection("actions"):
        aid = model.slot_id(action)
        context = action.get("context") or {}
        if _nonempty(context.get("causes_transition_text")) and not model.out_relations(aid, "causes"):
            warn("AUX_TEXT_WITHOUT_RELATION",
                 f"{aid}: context.causes_transition_text set but no causes relation")
        why = action.get("why") or {}
        if _nonempty(why.get("reason_texts")) and not model.out_relations(aid, "has_reason"):
            warn("AUX_TEXT_WITHOUT_RELATION",
                 f"{aid}: why.reason_texts set but no has_reason relation")
    for reason in model.collection("reasons"):
        rid2 = model.slot_id(reason)
        evidence = reason.get("evidence") or {}
        if _nonempty(evidence.get("observation_texts")) and not model.out_relations(rid2, "has_evidence"):
            warn("AUX_TEXT_WITHOUT_RELATION",
                 f"{rid2}: evidence.observation_texts set but no has_evidence relation")

    return issues


def _edges(model: T2AModel) -> list[tuple[str, str]]:
    action_ids = {model.slot_id(a) for a in model.collection("actions")}
    edges: list[tuple[str, str]] = []
    seen = set()

    def add(a, b):
        if a in action_ids and b in action_ids and a != b and (a, b) not in seen:
            seen.add((a, b))
            edges.append((a, b))

    for flow in model.collection("flows"):
        fid = model.slot_id(flow)
        for a in model.targets(fid, "flow_source"):
            for b in model.targets(fid, "flow_target"):
                add(a, b)
    for rel in model.relations:
        if rel.get("relation_type") == "temporal_before":
            add(rel["source_slot_id"], rel["target_slot_id"])
    return edges


def validate_effbd(model: T2AModel) -> list[Issue]:
    issues: list[Issue] = []
    action_ids = [model.slot_id(a) for a in model.collection("actions")]
    action_set = set(action_ids)
    edges = _edges(model)

    # 1) reachability: start -> (no-incoming) ... -> (no-outgoing) -> done.
    #    Every action must be reachable from start (else it sits in an isolated cycle).
    out_adj: dict[str, list[str]] = {a: [] for a in action_ids}
    has_in = set()
    has_out = set()
    for a, b in edges:
        out_adj[a].append(b)
        has_in.add(b)
        has_out.add(a)
    starts = [a for a in action_ids if a not in has_in]
    reached = set()
    queue = deque(starts)
    reached.update(starts)
    while queue:
        node = queue.popleft()
        for nxt in out_adj.get(node, []):
            if nxt not in reached:
                reached.add(nxt)
                queue.append(nxt)
    for a in action_ids:
        if a not in reached:
            issues.append(Issue("error", "UNREACHABLE_ACTION",
                                 f"action not reachable from start (isolated cycle?): {a}"))

    # 2) item-flow completeness: every item should have a producer and a consumer.
    producers: dict[str, list[str]] = {}
    consumers: dict[str, list[str]] = {}
    for a in action_ids:
        for i in model.targets(a, "produces_item"):
            producers.setdefault(i, []).append(a)
        for rt in ("uses_item", "provided_to"):
            for i in model.targets(a, rt):
                consumers.setdefault(i, []).append(a)
    for flow in model.collection("flows"):
        if "object" in str(flow.get("flow_kind", "")):
            fid = model.slot_id(flow)
            for i in model.targets(fid, "carries_item"):
                for a in model.targets(fid, "flow_source"):
                    producers.setdefault(i, []).append(a)
                for b in model.targets(fid, "flow_target"):
                    consumers.setdefault(i, []).append(b)
    for item in model.collection("items"):
        iid = model.slot_id(item)
        has_p = iid in producers
        has_c = iid in consumers
        if has_p and not has_c:
            issues.append(Issue("warning", "ITEM_NO_CONSUMER", f"item produced but never consumed: {iid}"))
        elif has_c and not has_p:
            issues.append(Issue("warning", "ITEM_NO_PRODUCER", f"item consumed but never produced: {iid}"))

    # 3) allocation coverage: every action should be allocated to a performer.
    for a in action_ids:
        if not model.targets(a, "performed_by"):
            issues.append(Issue("warning", "ACTION_NO_PERFORMER", f"action has no performer (allocation): {a}"))

    # 4) dangling flow endpoints (references to non-actions).
    for a, b in edges:
        for end in (a, b):
            if end not in action_set:
                issues.append(Issue("error", "DANGLING_FLOW_ENDPOINT", f"flow endpoint is not an action: {end}"))

    return issues


def summarize(issues: list[Issue]) -> dict:
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    return {"ok": not errors, "errors": len(errors), "warnings": len(warnings)}
