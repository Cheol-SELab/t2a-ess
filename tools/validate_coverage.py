#!/usr/bin/env python3
"""Validate semantic benchmark coverage across easy, medium, and hard inputs.

usage: python tools/validate_coverage.py   (data/gold/coverage_requirements.json against data/gold/<k>/)"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parents[1] / "data" / "gold"  # t2a-ess layout: data/gold/<k>/<k>.gold.json
DIFFICULTIES = ("easy", "medium", "hard")
COLLECTIONS = (
    "scenarios",
    "episodes",
    "situations",
    "state_values",
    "observations",
    "events",
    "transitions",
    "performers",
    "actions",
    "items",
    "flows",
    "controls",
    "constraints",
    "goals",
    "reasons",
    "domain_extension_rules",
    "semantic_bindings",
)


def relation_key(relation: dict) -> tuple[str, str, str]:
    relation_type = relation["relation_type"]
    if relation_type == "custom":
        relation_type += ":" + relation.get("custom_relation_type", "")
    return (
        relation["source_slot_id"],
        relation_type,
        relation["target_slot_id"],
    )


def narrative_paragraphs(text: str) -> list[str]:
    paragraphs = []
    current = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith(">"):
            continue
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(stripped)
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs


def validate_domain(domain: str, requirements: dict) -> list[str]:
    errors: list[str] = []
    model_path = BASE / domain / f"{domain}.gold.json"
    model = json.loads(model_path.read_text(encoding="utf-8"))[
        "text2activity_extraction_model"
    ]

    source_ids = {unit["source_unit_id"] for unit in model.get("source_units", [])}
    source_document_ids = {
        document.get("document_id")
        for document in model.get("source_documents", [])
        if document.get("document_id")
    }
    unit_document_ids = {
        unit.get("document")
        for unit in model.get("source_units", [])
        if unit.get("document")
    }
    if not source_document_ids:
        errors.append(f"{domain}: source_documents is missing or empty")
    if not unit_document_ids.issubset(source_document_ids):
        errors.append(
            f"{domain}: unregistered source document ids "
            f"{sorted(unit_document_ids - source_document_ids)}"
        )

    all_slot_ids = set()
    for collection in COLLECTIONS:
        for slot in model.get(collection, []):
            slot_id = next(
                (
                    value
                    for key, value in slot.items()
                    if key.endswith("_id")
                ),
                "<unknown>",
            )
            all_slot_ids.add(slot_id)
            source_id = slot.get("source_ref", {}).get("source_unit_id")
            if source_id not in source_ids:
                errors.append(
                    f"{domain}: dangling slot source {slot_id} -> {source_id}"
                )
    for forbidden_slot_id in requirements.get("forbidden_slot_ids", []):
        if forbidden_slot_id in all_slot_ids:
            errors.append(f"{domain}: forbidden slot id remains {forbidden_slot_id}")
    for unit in model.get("source_units", []):
        if not unit.get("planned_content"):
            errors.append(f"{domain}: empty planned_content: {unit['source_unit_id']}")
        if not isinstance(unit.get("order_index"), int):
            errors.append(f"{domain}: missing order_index: {unit['source_unit_id']}")
        if unit.get("text"):
            errors.append(f"{domain}: canonical source text must be empty: {unit['source_unit_id']}")

    realizations = {
        entry["difficulty"]: entry
        for entry in model.get("benchmark_realizations", [])
    }
    for difficulty in DIFFICULTIES:
        realization = realizations.get(difficulty)
        if realization is None:
            errors.append(f"{domain}/{difficulty}: missing benchmark realization")
            continue
        mapped = {
            mapping["source_unit_id"]
            for mapping in realization.get("source_unit_map", [])
        }
        if mapped != source_ids:
            missing = sorted(source_ids - mapped)
            extra = sorted(mapped - source_ids)
            errors.append(
                f"{domain}/{difficulty}: realization mismatch "
                f"missing={missing}, extra={extra}"
            )

        text_path = BASE / domain / realization["document"]
        if not text_path.exists():
            errors.append(f"{domain}/{difficulty}: missing input {text_path.name}")
            continue
        text = text_path.read_text(encoding="utf-8")
        paragraph_count = len(narrative_paragraphs(text))
        for mapping in realization.get("source_unit_map", []):
            indexes = mapping.get("paragraph_index", [])
            if not indexes or any(
                not isinstance(index, int) or index < 1 or index > paragraph_count
                for index in indexes
            ):
                errors.append(
                    f"{domain}/{difficulty}: invalid paragraph mapping "
                    f"{mapping['source_unit_id']} -> {indexes}, "
                    f"paragraph_count={paragraph_count}"
                )
        for label, pattern in requirements["required_text_patterns"].items():
            if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) is None:
                errors.append(f"{domain}/{difficulty}: missing {label} /{pattern}/")

    relations = {relation_key(relation) for relation in model["slot_relations"]}
    for expected in requirements.get("required_relations", []):
        key = tuple(expected)
        if key not in relations:
            errors.append(f"{domain}: missing relation {key}")
    for forbidden in requirements.get("forbidden_relations", []):
        key = tuple(forbidden)
        if key in relations:
            errors.append(f"{domain}: forbidden relation remains {key}")
    return errors


def main() -> int:
    requirements = json.loads(
        (BASE / "coverage_requirements.json").read_text(encoding="utf-8")
    )
    errors = []
    for domain, domain_requirements in requirements.items():
        errors.extend(validate_domain(domain, domain_requirements))

    if errors:
        print("Ground-truth coverage validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        f"Ground-truth coverage validation passed: "
        f"{len(requirements)} domains x {len(DIFFICULTIES)} difficulties."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
