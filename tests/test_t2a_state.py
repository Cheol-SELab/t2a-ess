"""Tests for the T2A-ESS -> SysML v2 state view converter
(text2activity/src/t2a_sysml/state_converter.py).

The state view is plain standard SysML v2 (no IMM tags), so the emitted text is
also fed to selab-rust-lsp via src/t2a_js/tools/lsp_check.js (kind "state").
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # text2activity/
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from t2a_sysml import (  # noqa: E402
    convert_state_file,
    convert_state_model,
    load_model,
    load_model_from_dict,
)

GOLD = ROOT / "data" / "gold"
MUMT = GOLD / "mumt" / "mumt.gold.json"
GOLD_JSONS = [
    MUMT,
    GOLD / "nghe" / "nghe.gold.json",
    GOLD / "av" / "av.gold.json",
]
COFFEE = SRC / "examples" / "coffee_order_T2A-ESS.json"


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


class StateViewGoldTests(unittest.TestCase):
    def test_mumt_structure(self):
        sysml = convert_state_file(MUMT)
        self.assertIn("state def 'MUM-T-based attack maneuver and electronic warfare response' parallel {", sysml)
        for region in ("communication_mode", "combat_power", "available_drone_count"):
            self.assertIn(f"state '{region}' {{", sysml)
        self.assertIn("entry; then 'Normal communication state';", sysml)
        # the comm transition carries first/accept/if/then with real labels
        self.assertIn(
            "transition 'Transition from normal communication to limited communication'\n"
            "                first 'Normal communication state'\n"
            "                accept 'Packet loss rate persistently exceeds the threshold'\n"
            "                if 'Condition: packet loss rate persistently exceeds the threshold'\n"
            "                then 'Limited communication state';",
            sysml,
        )
        self.assertIn("doc /* communication_mode = normal; data_mode = video_stream */", sysml)
        self.assertTrue(sysml.endswith("\n"))

    def test_golds_convert_clean(self):
        for path in GOLD_JSONS:
            with self.subTest(path=path.name):
                sysml = convert_state_file(path)
                self.assertTrue(_balanced(sysml))
                for fallback in ("State_", "Transition_", "Event_", "Constraint_"):
                    self.assertNotIn(fallback, sysml)

    def test_nghe_and_av_expected(self):
        nghe = convert_state_file(GOLD_JSONS[1])
        self.assertIn("state 'autonomy_level' {", nghe)
        self.assertIn("entry; then 'Initial Level 3 supervised autonomy mode';", nghe)
        av = convert_state_file(GOLD_JSONS[2])
        self.assertIn("state def '", av)
        self.assertIn("entry; then 'Manual driving state';", av)


class StateViewCoffeeTests(unittest.TestCase):
    def test_coffee_structure(self):
        sysml = convert_state_file(COFFEE)
        self.assertNotIn("parallel", sysml)
        self.assertIn("state 'order_status' {", sysml)
        self.assertIn("entry; then 'Order waiting state';", sysml)
        self.assertIn("doc /* order_status = waiting; queue_length = 0 orders */", sysml)
        self.assertIn(
            "transition 'Transition from order waiting to payment completed'\n"
            "                first 'Order waiting state'\n"
            "                accept 'Payment approval'\n"
            "                if 'Payment within 3 min'\n"
            "                do action 'Payment'\n"
            "                then 'Payment completed state';",
            sysml,
        )

    def test_example_files_in_sync(self):
        for json_path, state_path in (
            (COFFEE, SRC / "examples" / "coffee_order.state.sysml"),
            (MUMT, SRC / "examples" / "mumt.state.sysml"),
        ):
            with self.subTest(state=state_path.name):
                committed = state_path.read_text(encoding="utf-8")
                self.assertEqual(convert_state_file(json_path), committed)


class StateViewSyntheticTests(unittest.TestCase):
    def test_empty_state_axis(self):
        model = load_model_from_dict({
            "text2activity_extraction_model": {
                "title": "empty",
                "scenarios": [{"scenario_id": "S", "label": "Scenario"}],
                "slot_relations": [],
            }
        })
        sysml = convert_state_model(model)
        self.assertIn("state def 'Scenario';", sysml)
        self.assertTrue(_balanced(sysml))

    def test_multiple_triggers_duplicate_transition(self):
        model = load_model_from_dict({
            "text2activity_extraction_model": {
                "title": "multi",
                "scenarios": [{"scenario_id": "S", "label": "Scenario"}],
                "situations": [
                    {"situation_id": "SIT_A", "label": "A state"},
                    {"situation_id": "SIT_B", "label": "B state"},
                ],
                "events": [
                    {"event_id": "E1", "label": "Event1"},
                    {"event_id": "E2", "label": "Event2"},
                ],
                "transitions": [{"transition_id": "TR", "label": "A to B"}],
                "slot_relations": [
                    {"source_slot_id": "TR", "relation_type": "from_situation", "target_slot_id": "SIT_A"},
                    {"source_slot_id": "TR", "relation_type": "to_situation", "target_slot_id": "SIT_B"},
                    {"source_slot_id": "E1", "relation_type": "triggers", "target_slot_id": "TR"},
                    {"source_slot_id": "E2", "relation_type": "triggers", "target_slot_id": "TR"},
                ],
            }
        })
        sysml = convert_state_model(model)
        self.assertIn("transition 'A to B'\n", sysml)
        self.assertIn("transition 'A to B #2'\n", sysml)
        self.assertIn("accept 'Event1'", sysml)
        self.assertIn("accept 'Event2'", sysml)
        self.assertTrue(_balanced(sysml))


if __name__ == "__main__":
    unittest.main()
