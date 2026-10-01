"""Tests for the T2A-ESS -> EFFBD SysML converter (text2activity/src/t2a_sysml).

Targets the selab-effbd-editor EFFBD dialect. Note: this dialect is validated by
the EFFBD editor's IMM-aware environment, not the plain SysML v2 Pilot parser
(the editor's own example files also fail the plain Pilot parser), so these tests
assert EFFBD structure rather than plain-Pilot acceptance.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # text2activity/
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from t2a_sysml import convert_file, load_model  # noqa: E402

GOLD = ROOT / "data" / "gold"
MUMT = GOLD / "mumt" / "mumt.gold.json"
GOLD_JSONS = [
    MUMT,
    GOLD / "nghe" / "nghe.gold.json",
    GOLD / "av" / "av.gold.json",
]


def _balanced(text: str) -> bool:
    depth = 0
    for ch in text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


class EffbdConverterTests(unittest.TestCase):
    def test_mumt_effbd_structure(self) -> None:
        if not MUMT.is_file():
            self.skipTest("MUM-T gold fixture not present")
        sysml = convert_file(MUMT)  # default: imm_tags=True

        # EFFBD editor dialect: IMM import + edge/Performer defs
        self.assertIn("private import IMMBaseSchema::*;", sysml)
        self.assertIn("item def ItemInputEdge;", sysml)
        self.assertIn("part def Performer;", sysml)
        # performers as tagged Performer parts (by quoted label)
        self.assertIn("#Performer", sysml)
        self.assertIn("part 'TDSS' : Performer;", sysml)
        # root function + child functions by label
        self.assertIn("#Function", sysml)
        self.assertIn("action 'MUM-T-based attack maneuver and electronic warfare response' {", sysml)
        # item edges (produces/uses)
        self.assertIn("out item 'Summary track data' : ItemOutputEdge;", sysml)
        self.assertIn("in item 'Drone video stream' : ItemInputEdge;", sysml)
        # performed_by -> allocate
        self.assertIn("allocate 'SA resynchronization' to 'TDSS';", sysml)
        # episode nesting: episodes are nested #Function actions with their own body
        self.assertIn("action 'Preparation and normal communication maneuver' {", sysml)
        self.assertIn(
            "succession first 'TDSS self-diagnosis and normal communication confirmation' then 'Sequential reconnaissance drone launch and surveillance deployment';",
            sysml,
        )
        # scenario-level episode sequencing (start -> ep1 -> ... -> done)
        self.assertIn("succession first start then 'Preparation and normal communication maneuver';", sysml)
        self.assertIn("then done;", sysml)
        # cross-episode object flow: the *target* action must declare the in-port too,
        # otherwise the editor/LSP cannot resolve the flow's target path.
        self.assertRegex(sysml, r"action 'SA resynchronization' \{[^}]*in item 'Summary track data' : ItemInputEdge;")
        # cross-episode object flow uses a 3-level dotted path (episode.action.item)
        self.assertIn(
            "flow from 'Electronic warfare jamming and communication degradation response'.'Drone switch to Edge AI analysis mode'.'Summary track data' "
            "to 'Communication recovery and attack resumption'.'SA resynchronization'.'Summary track data';",
            sysml,
        )
        self.assertTrue(_balanced(sysml))

    def test_all_gold_convert_and_are_well_formed(self) -> None:
        for path in GOLD_JSONS:
            with self.subTest(fixture=path.name):
                if not path.is_file():
                    self.skipTest(f"missing {path.name}")
                model = load_model(path)
                sysml = convert_file(path)
                self.assertTrue(_balanced(sysml), "unbalanced braces")
                # every performer appears as a Performer part
                for performer in model.collection("performers"):
                    label = str(performer.get("label", ""))
                    if label:
                        self.assertIn(f"part '{label}'", sysml)
                # start/done framing present when there are actions
                if model.collection("actions"):
                    self.assertIn("succession first start then", sysml)
                    self.assertIn("then done;", sysml)

    def test_plain_form_drops_imm_tags(self) -> None:
        if not MUMT.is_file():
            self.skipTest("MUM-T gold fixture not present")
        plain = convert_file(MUMT, imm_tags=False)
        self.assertNotIn("IMMBaseSchema", plain)
        self.assertNotIn("#Performer", plain)
        self.assertNotIn("#Function", plain)
        # still the EFFBD structure (Performer parts, actions, successions)
        self.assertIn("part 'TDSS' : Performer;", plain)
        self.assertIn("succession first start then", plain)
        self.assertTrue(_balanced(plain))

    def test_controls_become_guarded_successions(self) -> None:
        if not MUMT.is_file():
            self.skipTest("MUM-T gold fixture not present")
        sysml = convert_file(MUMT)
        # intra-episode control guard_texts -> boolean attribute + guarded succession.
        # (inter-episode controls are subsumed by episode sequencing — see README.)
        self.assertIn("attribute 'While the communication blackout state persists' : ScalarValues::Boolean;", sysml)
        self.assertIn("// control: loop", sysml)
        self.assertIn("// control: guarded_sequence", sysml)
        self.assertIn("if 'While the communication blackout state persists' == true then", sysml)

    def test_episode_nesting(self) -> None:
        if not MUMT.is_file():
            self.skipTest("MUM-T gold fixture not present")
        model = load_model(MUMT)
        sysml = convert_file(MUMT)
        # every episode becomes a nested function; fork/join sits at episode level
        for episode in model.collection("episodes"):
            self.assertIn(f"action '{episode['label']}' {{", sysml)
        self.assertIn("fork 'New Start Concurrency_1';", sysml)

    def test_structural_validation_of_gold(self) -> None:
        from t2a_sysml import summarize, validate_effbd

        for path in GOLD_JSONS:
            with self.subTest(fixture=path.name):
                if not path.is_file():
                    self.skipTest(f"missing {path.name}")
                model = load_model(path)
                issues = validate_effbd(model)
                summary = summarize(issues)
                # structurally sound: reachable start->done, resolved references
                self.assertTrue(summary["ok"], f"{path.name}: {issues}")
                self.assertEqual(summary["errors"], 0)
                for issue in issues:
                    self.assertIn(issue.severity, ("warning", "error"))

    def test_guide_coffee_example(self) -> None:
        # keeps docs/T2A-to-EFFBD-Converter-Guide.md example in sync with the code
        from t2a_sysml import summarize, validate_effbd

        path = ROOT / "src" / "examples" / "coffee_order_T2A-ESS.json"
        if not path.is_file():
            self.skipTest("coffee example not present")
        model = load_model(path)
        sysml = convert_file(path)
        # nesting + concurrency + guard + cross-episode item flow
        self.assertIn("action 'Order taking' {", sysml)
        self.assertIn("fork 'New Start Concurrency_1';", sysml)
        self.assertIn("succession first 'Order entry' if 'Payment completed' == true then 'Payment';", sysml)
        self.assertIn(
            "flow from 'Order taking'.'Order entry'.'Order ticket' to 'Beverage preparation'.'Beverage making'.'Order ticket';",
            sysml,
        )
        summary = summarize(validate_effbd(model))
        self.assertEqual((summary["ok"], summary["errors"], summary["warnings"]), (True, 0, 0))

    def test_non_gold_llm_extraction_converts(self) -> None:
        path = ROOT / "data" / "diagnostic" / "mumt" / "mumt.nongold.json"
        if not path.is_file():
            self.skipTest("non-gold fixture not present")
        sysml = convert_file(path)
        self.assertIn("action '", sysml)
        self.assertTrue(_balanced(sysml))

    def test_fork_join_names_unique_across_file(self) -> None:
        # EFFBD editor keys nodes by quoted label globally; duplicate fork/join names in
        # sibling episodes render as "node is outside the parent region envelope".
        import re

        for path in GOLD_JSONS:
            with self.subTest(fixture=path.name):
                if not path.is_file():
                    self.skipTest(f"missing {path.name}")
                sysml = convert_file(path)
                names = re.findall(r"^\s*(?:fork|join) '([^']+)';", sysml, flags=re.M)
                self.assertEqual(len(names), len(set(names)), f"duplicate fork/join names: {names}")

    def test_legacy_name_field_falls_back_to_label(self) -> None:
        # Older extraction prompt emitted `name` instead of `label`; keep converting it.
        import json
        import tempfile

        from t2a_sysml import convert_model
        from t2a_sysml.model import load_model as _load

        raw = {
            "text2activity_extraction_model": {
                "model_id": "LEGACY", "title": "legacy",
                "scenarios": [{"scenario_id": "S", "name": "Legacy scenario"}],
                "performers": [{"performer_id": "P", "name": "Operator"}],
                "actions": [{"action_id": "A1", "name": "Observe"}, {"action_id": "A2", "name": "Report"}],
                "flows": [{"flow_id": "F", "flow_kind": "control_flow"}],
                "slot_relations": [
                    {"source_slot_id": "A1", "relation_type": "performed_by", "target_slot_id": "P"},
                    {"source_slot_id": "F", "relation_type": "flow_source", "target_slot_id": "A1"},
                    {"source_slot_id": "F", "relation_type": "flow_target", "target_slot_id": "A2"},
                ],
            }
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump(raw, fh, ensure_ascii=False)
        sysml = convert_model(_load(fh.name))
        self.assertIn("action 'Legacy scenario' {", sysml)
        self.assertIn("part 'Operator' : Performer;", sysml)
        self.assertIn("succession first 'Observe' then 'Report';", sysml)
        self.assertNotIn("Function_", sysml)


def _model(inner: dict):
    """Wrap a minimal inner-model dict into a T2AModel."""
    from t2a_sysml import load_model_from_dict

    return load_model_from_dict({"text2activity_extraction_model": inner})


def _rel(rid: str, src: str, rt: str, tgt: str, **extra) -> dict:
    rel = {"relation_id": rid, "source_slot_id": src, "relation_type": rt, "target_slot_id": tgt}
    rel.update(extra)
    return rel


class SchemaValidationTests(unittest.TestCase):
    """One test per validate_schema issue code (docs §Slot Relation contract)."""

    def _codes(self, inner: dict) -> list:
        from t2a_sysml import validate_schema

        return [(i.code, i.severity) for i in validate_schema(_model(inner))]

    def test_duplicate_slot_id(self) -> None:
        codes = self._codes({
            "scenarios": [{"scenario_id": "X"}],
            "episodes": [{"episode_id": "X"}],
        })
        self.assertIn(("DUPLICATE_SLOT_ID", "error"), codes)

    def test_dangling_relation_endpoint(self) -> None:
        codes = self._codes({
            "scenarios": [{"scenario_id": "S"}],
            "slot_relations": [_rel("R1", "S", "has_episode", "NOPE")],
        })
        self.assertIn(("DANGLING_RELATION_ENDPOINT", "error"), codes)

    def test_unknown_relation_type(self) -> None:
        codes = self._codes({
            "scenarios": [{"scenario_id": "S"}],
            "episodes": [{"episode_id": "E"}],
            "slot_relations": [_rel("R1", "S", "bogus_rel", "E")],
        })
        self.assertIn(("UNKNOWN_RELATION_TYPE", "error"), codes)

    def test_relation_endpoint_type(self) -> None:
        codes = self._codes({
            "scenarios": [{"scenario_id": "S"}],
            "episodes": [{"episode_id": "E"}],
            "slot_relations": [_rel("R1", "E", "has_episode", "S")],  # reversed
        })
        self.assertIn(("RELATION_ENDPOINT_TYPE", "error"), codes)

    def test_custom_type_missing(self) -> None:
        codes = self._codes({
            "scenarios": [{"scenario_id": "S"}],
            "episodes": [{"episode_id": "E"}],
            "slot_relations": [_rel("R1", "S", "custom", "E")],
        })
        self.assertIn(("CUSTOM_TYPE_MISSING", "error"), codes)

    def test_custom_type_not_registered(self) -> None:
        codes = self._codes({
            "scenarios": [{"scenario_id": "S"}],
            "episodes": [{"episode_id": "E"}],
            "slot_relations": [_rel("R1", "S", "custom", "E", custom_relation_type="weird")],
        })
        self.assertIn(("CUSTOM_TYPE_NOT_REGISTERED", "warning"), codes)
        self.assertNotIn(("CUSTOM_TYPE_MISSING", "error"), codes)

    def test_transition_endpoints(self) -> None:
        codes = self._codes({
            "transitions": [{"transition_id": "T"}],
            "situations": [{"situation_id": "ST"}],
            "slot_relations": [_rel("R1", "T", "from_situation", "ST")],  # no to_situation
        })
        self.assertIn(("TRANSITION_ENDPOINTS", "error"), codes)

    def test_situation_no_state_value(self) -> None:
        codes = self._codes({"situations": [{"situation_id": "ST"}]})
        self.assertIn(("SITUATION_NO_STATE_VALUE", "warning"), codes)

    def test_observation_no_observes(self) -> None:
        codes = self._codes({"observations": [{"observation_id": "O"}]})
        self.assertIn(("OBSERVATION_NO_OBSERVES", "warning"), codes)

    def test_isolated_event(self) -> None:
        codes = self._codes({
            "events": [{"event_id": "EV1"}, {"event_id": "EV2"}],
            "transitions": [{"transition_id": "T"}],
            "situations": [{"situation_id": "S1"}, {"situation_id": "S2"}],
            "slot_relations": [
                _rel("R1", "EV1", "triggers", "T"),
                _rel("R2", "T", "from_situation", "S1"),
                _rel("R3", "T", "to_situation", "S2"),
            ],
        })
        self.assertIn(("ISOLATED_EVENT", "warning"), codes)
        from t2a_sysml import validate_schema

        messages = [i.message for i in validate_schema(_model({
            "events": [{"event_id": "EV1"}, {"event_id": "EV2"}],
            "transitions": [{"transition_id": "T"}],
            "situations": [{"situation_id": "S1"}, {"situation_id": "S2"}],
            "slot_relations": [
                _rel("R1", "EV1", "triggers", "T"),
                _rel("R2", "T", "from_situation", "S1"),
                _rel("R3", "T", "to_situation", "S2"),
            ],
        })) if i.code == "ISOLATED_EVENT"]
        self.assertTrue(any("EV2" in m for m in messages))
        self.assertFalse(any("EV1" in m for m in messages))

    def test_action_no_episode(self) -> None:
        codes = self._codes({"actions": [{"action_id": "A"}]})
        self.assertIn(("ACTION_NO_EPISODE", "warning"), codes)

    def test_action_multi_episode(self) -> None:
        codes = self._codes({
            "episodes": [{"episode_id": "E1"}, {"episode_id": "E2"}],
            "actions": [{"action_id": "A"}],
            "slot_relations": [
                _rel("R1", "E1", "contains_action", "A"),
                _rel("R2", "E2", "contains_action", "A"),
            ],
        })
        self.assertIn(("ACTION_MULTI_EPISODE", "warning"), codes)

    def test_aux_text_without_relation(self) -> None:
        cases = [
            ({"episodes": [{"episode_id": "E", "entry_situation_text": "entry"}]}, "E"),
            ({"episodes": [{"episode_id": "E", "exit_situation_text": "exit"}]}, "E"),
            ({"actions": [{"action_id": "A", "context": {"causes_transition_text": "transition"}}]}, "A"),
            ({"actions": [{"action_id": "A", "why": {"reason_texts": ["because"]}}]}, "A"),
            ({"reasons": [{"reason_id": "R", "evidence": {"observation_texts": ["Observe"]}}]}, "R"),
        ]
        for inner, sid in cases:
            with self.subTest(slot=sid):
                codes = self._codes(inner)
                self.assertIn(("AUX_TEXT_WITHOUT_RELATION", "warning"), codes)
        # backed by the relation -> no warning
        codes = self._codes({
            "actions": [{"action_id": "A", "why": {"reason_texts": ["because"]}}],
            "reasons": [{"reason_id": "R", "reason_type": ["cause"]}],
            "slot_relations": [_rel("R1", "A", "has_reason", "R")],
        })
        self.assertNotIn(("AUX_TEXT_WITHOUT_RELATION", "warning"), codes)

    def test_coffee_example_has_no_schema_errors(self) -> None:
        from t2a_sysml import validate_schema

        path = ROOT / "src" / "examples" / "coffee_order_T2A-ESS.json"
        if not path.is_file():
            self.skipTest("coffee example not present")
        issues = validate_schema(load_model(path))
        errors = [i for i in issues if i.severity == "error"]
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
