"""Load and index a T2A-ESS extraction model + its slot_relations graph."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Slot collections we map to SysML (order = declaration preference).
SLOT_COLLECTIONS = (
    "scenarios",
    "episodes",
    "performers",
    "actions",
    "items",
    "flows",
    "controls",
    "situations",
    "transitions",
    "constraints",
    "goals",
)

# All 17 T2A-ESS slot collections (SLOT_COLLECTIONS plus the non-EFFBD ones);
# `by_id` indexes all of them so schema validation can resolve every endpoint.
ALL_SLOT_COLLECTIONS = SLOT_COLLECTIONS + (
    "state_values",
    "events",
    "observations",
    "reasons",
    "domain_extension_rules",
    "semantic_bindings",
)

_ID_FIELDS = (
    "scenario_id",
    "episode_id",
    "performer_id",
    "action_id",
    "item_id",
    "flow_id",
    "control_id",
    "situation_id",
    "state_value_id",
    "observation_id",
    "event_id",
    "transition_id",
    "constraint_id",
    "goal_id",
    "reason_id",
    "domain_extension_rule_id",
    "semantic_binding_id",
)


def _slot_id(slot: dict) -> str | None:
    for field_name in _ID_FIELDS:
        if field_name in slot:
            return str(slot[field_name])
    return None


@dataclass
class T2AModel:
    """Indexed view over the inner ``text2activity_extraction_model`` object."""

    raw: dict
    model: dict
    by_id: dict[str, tuple[str, dict]] = field(default_factory=dict)  # id -> (collection, slot)
    relations: list[dict] = field(default_factory=list)
    _by_source: dict[str, list[dict]] = field(default_factory=dict)
    _by_target: dict[str, list[dict]] = field(default_factory=dict)

    # --- collection accessors -------------------------------------------------
    def collection(self, name: str) -> list[dict]:
        value = self.model.get(name)
        return value if isinstance(value, list) else []

    @property
    def title(self) -> str:
        return str(self.model.get("title") or self.model.get("model_id") or "Text2ActivityModel")

    @property
    def model_id(self) -> str:
        return str(self.model.get("model_id") or "T2A_MODEL")

    def slot_id(self, slot: dict) -> str | None:
        return _slot_id(slot)

    # --- relation queries -----------------------------------------------------
    def out_relations(self, source_id: str, relation_type: str | None = None) -> list[dict]:
        rels = self._by_source.get(source_id, [])
        if relation_type is None:
            return rels
        return [r for r in rels if r.get("relation_type") == relation_type]

    def in_relations(self, target_id: str, relation_type: str | None = None) -> list[dict]:
        rels = self._by_target.get(target_id, [])
        if relation_type is None:
            return rels
        return [r for r in rels if r.get("relation_type") == relation_type]

    def targets(self, source_id: str, relation_type: str) -> list[str]:
        return [r["target_slot_id"] for r in self.out_relations(source_id, relation_type)]

    def sources(self, target_id: str, relation_type: str) -> list[str]:
        return [r["source_slot_id"] for r in self.in_relations(target_id, relation_type)]


def load_model_from_dict(raw: dict) -> T2AModel:
    inner = raw.get("text2activity_extraction_model", raw)

    model = T2AModel(raw=raw, model=inner)
    for collection in ALL_SLOT_COLLECTIONS:
        for slot in model.collection(collection):
            slot_id = _slot_id(slot)
            if slot_id:
                model.by_id.setdefault(slot_id, (collection, slot))

    for relation in inner.get("slot_relations", []) or []:
        source = relation.get("source_slot_id")
        target = relation.get("target_slot_id")
        if not source or not target:
            continue
        model.relations.append(relation)
        model._by_source.setdefault(source, []).append(relation)
        model._by_target.setdefault(target, []).append(relation)
    return model


def load_model(path: str | Path) -> T2AModel:
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return load_model_from_dict(raw)
