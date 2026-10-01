/**
 * Tests for the JS T2A-ESS -> EFFBD SysML converter (mirrors tests/test_t2a_sysml.py).
 *
 *   cd text2activity/src/t2a_js && npm test
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { convertFile, convertModel, loadModel, loadModelFromObject, summarize, validateEffbd } from "../t2a_sysml/index.js";
import { MUMT, GOLD_JSONS, COFFEE, NON_GOLD, balanced, skipUnless } from "./fixtures.js";
import path from "node:path";

test("MUM-T EFFBD structure", (t) => {
  if (skipUnless(t, MUMT)) return;
  const sysml = convertFile(MUMT);

  assert.ok(sysml.includes("private import IMMBaseSchema::*;"));
  assert.ok(sysml.includes("item def ItemInputEdge;"));
  assert.ok(sysml.includes("part def Performer;"));
  assert.ok(sysml.includes("#Performer"));
  assert.ok(sysml.includes("part 'TDSS' : Performer;"));
  assert.ok(sysml.includes("#Function"));
  assert.ok(sysml.includes("action 'MUM-T-based attack maneuver and electronic warfare response' {"));
  assert.ok(sysml.includes("out item 'Summary track data' : ItemOutputEdge;"));
  assert.ok(sysml.includes("in item 'Drone video stream' : ItemInputEdge;"));
  assert.ok(sysml.includes("allocate 'SA resynchronization' to 'TDSS';"));
  assert.ok(sysml.includes("action 'Preparation and normal communication maneuver' {"));
  assert.ok(
    sysml.includes("succession first 'TDSS self-diagnosis and normal communication confirmation' then 'Sequential reconnaissance drone launch and surveillance deployment';"),
  );
  assert.ok(sysml.includes("succession first start then 'Preparation and normal communication maneuver';"));
  assert.ok(sysml.includes("then done;"));
  assert.ok(
    sysml.includes(
      "flow from 'Electronic warfare jamming and communication degradation response'.'Drone switch to Edge AI analysis mode'.'Summary track data' " +
        "to 'Communication recovery and attack resumption'.'SA resynchronization'.'Summary track data';",
    ),
  );
  assert.ok(balanced(sysml));
});

test("all gold fixtures convert and are well-formed", async (t) => {
  for (const file of GOLD_JSONS) {
    await t.test(path.basename(file), (tt) => {
      if (skipUnless(tt, file)) return;
      const model = loadModel(file);
      const sysml = convertFile(file);
      assert.ok(balanced(sysml), "unbalanced braces");
      for (const performer of model.collection("performers")) {
        const label = String(performer.label ?? "");
        if (label) assert.ok(sysml.includes(`part '${label}'`), `missing performer ${label}`);
      }
      if (model.collection("actions").length) {
        assert.ok(sysml.includes("succession first start then"));
        assert.ok(sysml.includes("then done;"));
      }
    });
  }
});

test("plain form drops IMM tags", (t) => {
  if (skipUnless(t, MUMT)) return;
  const plain = convertFile(MUMT, { immTags: false });
  assert.ok(!plain.includes("IMMBaseSchema"));
  assert.ok(!plain.includes("#Performer"));
  assert.ok(!plain.includes("#Function"));
  assert.ok(plain.includes("part 'TDSS' : Performer;"));
  assert.ok(plain.includes("succession first start then"));
  assert.ok(balanced(plain));
});

test("controls become guarded successions", (t) => {
  if (skipUnless(t, MUMT)) return;
  const sysml = convertFile(MUMT);
  assert.ok(sysml.includes("attribute 'While the communication blackout state persists' : ScalarValues::Boolean;"));
  assert.ok(sysml.includes("// control: loop"));
  assert.ok(sysml.includes("// control: guarded_sequence"));
  assert.ok(sysml.includes("if 'While the communication blackout state persists' == true then"));
});

test("episode nesting + fork at episode level", (t) => {
  if (skipUnless(t, MUMT)) return;
  const model = loadModel(MUMT);
  const sysml = convertFile(MUMT);
  for (const episode of model.collection("episodes")) {
    assert.ok(sysml.includes(`action '${episode.label}' {`), `episode ${episode.label}`);
  }
  assert.ok(sysml.includes("fork 'New Start Concurrency_1';"));
});

test("structural validation of gold fixtures", async (t) => {
  for (const file of GOLD_JSONS) {
    await t.test(path.basename(file), (tt) => {
      if (skipUnless(tt, file)) return;
      const issues = validateEffbd(loadModel(file));
      const s = summarize(issues);
      assert.equal(s.ok, true, JSON.stringify(issues));
      assert.equal(s.errors, 0);
      for (const i of issues) assert.ok(["warning", "error"].includes(i.severity));
    });
  }
});

test("guide coffee example", (t) => {
  if (skipUnless(t, COFFEE)) return;
  const model = loadModel(COFFEE);
  const sysml = convertFile(COFFEE);
  assert.ok(sysml.includes("action 'Order taking' {"));
  assert.ok(sysml.includes("fork 'New Start Concurrency_1';"));
  assert.ok(sysml.includes("succession first 'Order entry' if 'Payment completed' == true then 'Payment';"));
  assert.ok(
    sysml.includes("flow from 'Order taking'.'Order entry'.'Order ticket' to 'Beverage preparation'.'Beverage making'.'Order ticket';"),
  );
  const s = summarize(validateEffbd(model));
  assert.deepEqual([s.ok, s.errors, s.warnings], [true, 0, 0]);
});

test("non-gold LLM extraction converts (flat fallback allowed)", (t) => {
  if (skipUnless(t, NON_GOLD)) return;
  const sysml = convertFile(NON_GOLD);
  assert.ok(sysml.includes("action '"));
  assert.ok(balanced(sysml));
});

test("fork/join names are unique across the whole file", async (t) => {
  // EFFBD editor keys nodes by quoted label globally; duplicates in sibling episodes
  // render as "node is outside the parent region envelope".
  for (const file of GOLD_JSONS) {
    await t.test(path.basename(file), (tt) => {
      if (skipUnless(tt, file)) return;
      const sysml = convertFile(file);
      const names = [...sysml.matchAll(/^\s*(?:fork|join) '([^']+)';/gm)].map((m) => m[1]);
      assert.equal(names.length, new Set(names).size, `duplicate fork/join names: ${names}`);
    });
  }
});

test("legacy `name` field falls back to label", () => {
  const model = loadModelFromObject({
    text2activity_extraction_model: {
      model_id: "LEGACY", title: "legacy",
      scenarios: [{ scenario_id: "S", name: "Legacy scenario" }],
      performers: [{ performer_id: "P", name: "Operator" }],
      actions: [{ action_id: "A1", name: "Observe" }, { action_id: "A2", name: "Report" }],
      flows: [{ flow_id: "F", flow_kind: "control_flow" }],
      slot_relations: [
        { source_slot_id: "A1", relation_type: "performed_by", target_slot_id: "P" },
        { source_slot_id: "F", relation_type: "flow_source", target_slot_id: "A1" },
        { source_slot_id: "F", relation_type: "flow_target", target_slot_id: "A2" },
      ],
    },
  });
  const sysml = convertModel(model);
  assert.ok(sysml.includes("action 'Legacy scenario' {"));
  assert.ok(sysml.includes("part 'Operator' : Performer;"));
  assert.ok(sysml.includes("succession first 'Observe' then 'Report';"));
  assert.ok(!sysml.includes("Function_"));
});
