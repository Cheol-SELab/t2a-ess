/**
 * Tests for the JS T2A-ESS -> SysML v2 state view converter
 * (mirrors tests/test_t2a_state.py).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

import { convertStateFile, convertStateModel, loadModelFromObject } from "../t2a_sysml/index.js";
import { ROOT, MUMT, GOLD_JSONS, COFFEE, balanced, skipUnless } from "./fixtures.js";

test("MUM-T state view structure", (t) => {
  if (skipUnless(t, MUMT)) return;
  const sysml = convertStateFile(MUMT);
  assert.ok(sysml.includes("state def 'MUM-T-based attack maneuver and electronic warfare response' parallel {"));
  for (const region of ["communication_mode", "combat_power", "available_drone_count"]) {
    assert.ok(sysml.includes(`state '${region}' {`), `region ${region}`);
  }
  assert.ok(sysml.includes("entry; then 'Normal communication state';"));
  assert.ok(
    sysml.includes(
      "transition 'Transition from normal communication to limited communication'\n" +
        "                first 'Normal communication state'\n" +
        "                accept 'Packet loss rate persistently exceeds the threshold'\n" +
        "                if 'Condition: packet loss rate persistently exceeds the threshold'\n" +
        "                then 'Limited communication state';",
    ),
  );
  assert.ok(sysml.includes("doc /* communication_mode = normal; data_mode = video_stream */"));
  assert.ok(sysml.endsWith("\n"));
});

test("golds convert clean (balanced braces, no fallback names)", (t) => {
  for (const file of GOLD_JSONS) {
    if (skipUnless(t, file)) continue;
    const sysml = convertStateFile(file);
    assert.ok(balanced(sysml), path.basename(file));
    for (const fallback of ["State_", "Transition_", "Event_", "Constraint_"]) {
      assert.ok(!sysml.includes(fallback), `${path.basename(file)}: ${fallback}`);
    }
  }
});

test("NGHE / AV expected regions and initials", (t) => {
  if (skipUnless(t, GOLD_JSONS[1]) || skipUnless(t, GOLD_JSONS[2])) return;
  const nghe = convertStateFile(GOLD_JSONS[1]);
  assert.ok(nghe.includes("state 'autonomy_level' {"));
  assert.ok(nghe.includes("entry; then 'Initial Level 3 supervised autonomy mode';"));
  const av = convertStateFile(GOLD_JSONS[2]);
  assert.ok(av.includes("state def '"));
  assert.ok(av.includes("entry; then 'Manual driving state';"));
});

test("coffee state view", (t) => {
  if (skipUnless(t, COFFEE)) return;
  const sysml = convertStateFile(COFFEE);
  assert.ok(!sysml.includes("parallel"));
  assert.ok(sysml.includes("state 'order_status' {"));
  assert.ok(sysml.includes("entry; then 'Order waiting state';"));
  assert.ok(sysml.includes("doc /* order_status = waiting; queue_length = 0 orders */"));
  assert.ok(
    sysml.includes(
      "transition 'Transition from order waiting to payment completed'\n" +
        "                first 'Order waiting state'\n" +
        "                accept 'Payment approval'\n" +
        "                if 'Payment within 3 min'\n" +
        "                do action 'Payment'\n" +
        "                then 'Payment completed state';",
    ),
  );
});

test("committed example .state.sysml files are in sync", (t) => {
  const pairs = [
    [COFFEE, path.join(ROOT, "src", "examples", "coffee_order.state.sysml")],
    [MUMT, path.join(ROOT, "src", "examples", "mumt.state.sysml")],
  ];
  for (const [json, state] of pairs) {
    if (skipUnless(t, json) || skipUnless(t, state)) continue;
    assert.equal(convertStateFile(json), readFileSync(state, "utf8"), path.basename(state));
  }
});

test("empty state axis -> single-line state def", () => {
  const model = loadModelFromObject({
    text2activity_extraction_model: {
      title: "empty",
      scenarios: [{ scenario_id: "S", label: "Scenario" }],
      slot_relations: [],
    },
  });
  const sysml = convertStateModel(model);
  assert.ok(sysml.includes("state def 'Scenario';"));
  assert.ok(balanced(sysml));
});

test("multiple triggers on one transition -> duplicate transition usages", () => {
  const model = loadModelFromObject({
    text2activity_extraction_model: {
      title: "multi",
      scenarios: [{ scenario_id: "S", label: "Scenario" }],
      situations: [
        { situation_id: "SIT_A", label: "A state" },
        { situation_id: "SIT_B", label: "B state" },
      ],
      events: [
        { event_id: "E1", label: "Event1" },
        { event_id: "E2", label: "Event2" },
      ],
      transitions: [{ transition_id: "TR", label: "A to B" }],
      slot_relations: [
        { source_slot_id: "TR", relation_type: "from_situation", target_slot_id: "SIT_A" },
        { source_slot_id: "TR", relation_type: "to_situation", target_slot_id: "SIT_B" },
        { source_slot_id: "E1", relation_type: "triggers", target_slot_id: "TR" },
        { source_slot_id: "E2", relation_type: "triggers", target_slot_id: "TR" },
      ],
    },
  });
  const sysml = convertStateModel(model);
  assert.ok(sysml.includes("transition 'A to B'\n"));
  assert.ok(sysml.includes("transition 'A to B #2'\n"));
  assert.ok(sysml.includes("accept 'Event1'"));
  assert.ok(sysml.includes("accept 'Event2'"));
  assert.ok(balanced(sysml));
});
