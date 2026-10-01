/**
 * Tests for validateSchema (mirrors SchemaValidationTests in tests/test_t2a_sysml.py).
 * One test per issue code (docs §Slot Relation contract).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { loadModelFromObject, validateSchema } from "../t2a_sysml/index.js";
import { COFFEE, skipUnless } from "./fixtures.js";

const model = (inner) => loadModelFromObject({ text2activity_extraction_model: inner });
const rel = (rid, src, rt, tgt, extra = {}) =>
  ({ relation_id: rid, source_slot_id: src, relation_type: rt, target_slot_id: tgt, ...extra });
const codes = (inner) => validateSchema(model(inner)).map((i) => [i.code, i.severity]);

test("DUPLICATE_SLOT_ID", () => {
  const c = codes({ scenarios: [{ scenario_id: "X" }], episodes: [{ episode_id: "X" }] });
  assert.ok(c.some(([code, sev]) => code === "DUPLICATE_SLOT_ID" && sev === "error"));
});

test("DANGLING_RELATION_ENDPOINT", () => {
  const c = codes({
    scenarios: [{ scenario_id: "S" }],
    slot_relations: [rel("R1", "S", "has_episode", "NOPE")],
  });
  assert.ok(c.some(([code, sev]) => code === "DANGLING_RELATION_ENDPOINT" && sev === "error"));
});

test("UNKNOWN_RELATION_TYPE", () => {
  const c = codes({
    scenarios: [{ scenario_id: "S" }],
    episodes: [{ episode_id: "E" }],
    slot_relations: [rel("R1", "S", "bogus_rel", "E")],
  });
  assert.ok(c.some(([code, sev]) => code === "UNKNOWN_RELATION_TYPE" && sev === "error"));
});

test("RELATION_ENDPOINT_TYPE", () => {
  const c = codes({
    scenarios: [{ scenario_id: "S" }],
    episodes: [{ episode_id: "E" }],
    slot_relations: [rel("R1", "E", "has_episode", "S")], // reversed
  });
  assert.ok(c.some(([code, sev]) => code === "RELATION_ENDPOINT_TYPE" && sev === "error"));
});

test("CUSTOM_TYPE_MISSING", () => {
  const c = codes({
    scenarios: [{ scenario_id: "S" }],
    episodes: [{ episode_id: "E" }],
    slot_relations: [rel("R1", "S", "custom", "E")],
  });
  assert.ok(c.some(([code, sev]) => code === "CUSTOM_TYPE_MISSING" && sev === "error"));
});

test("CUSTOM_TYPE_NOT_REGISTERED", () => {
  const c = codes({
    scenarios: [{ scenario_id: "S" }],
    episodes: [{ episode_id: "E" }],
    slot_relations: [rel("R1", "S", "custom", "E", { custom_relation_type: "weird" })],
  });
  assert.ok(c.some(([code, sev]) => code === "CUSTOM_TYPE_NOT_REGISTERED" && sev === "warning"));
  assert.ok(!c.some(([code]) => code === "CUSTOM_TYPE_MISSING"));
});

test("TRANSITION_ENDPOINTS", () => {
  const c = codes({
    transitions: [{ transition_id: "T" }],
    situations: [{ situation_id: "ST" }],
    slot_relations: [rel("R1", "T", "from_situation", "ST")], // no to_situation
  });
  assert.ok(c.some(([code, sev]) => code === "TRANSITION_ENDPOINTS" && sev === "error"));
});

test("SITUATION_NO_STATE_VALUE", () => {
  const c = codes({ situations: [{ situation_id: "ST" }] });
  assert.ok(c.some(([code, sev]) => code === "SITUATION_NO_STATE_VALUE" && sev === "warning"));
});

test("OBSERVATION_NO_OBSERVES", () => {
  const c = codes({ observations: [{ observation_id: "O" }] });
  assert.ok(c.some(([code, sev]) => code === "OBSERVATION_NO_OBSERVES" && sev === "warning"));
});

test("ISOLATED_EVENT", () => {
  const inner = {
    events: [{ event_id: "EV1" }, { event_id: "EV2" }],
    transitions: [{ transition_id: "T" }],
    situations: [{ situation_id: "S1" }, { situation_id: "S2" }],
    slot_relations: [
      rel("R1", "EV1", "triggers", "T"),
      rel("R2", "T", "from_situation", "S1"),
      rel("R3", "T", "to_situation", "S2"),
    ],
  };
  const messages = validateSchema(model(inner))
    .filter((i) => i.code === "ISOLATED_EVENT")
    .map((i) => i.message);
  assert.ok(messages.some((m) => m.includes("EV2")));
  assert.ok(!messages.some((m) => m.includes("EV1")));
});

test("ACTION_NO_EPISODE", () => {
  const c = codes({ actions: [{ action_id: "A" }] });
  assert.ok(c.some(([code, sev]) => code === "ACTION_NO_EPISODE" && sev === "warning"));
});

test("ACTION_MULTI_EPISODE", () => {
  const c = codes({
    episodes: [{ episode_id: "E1" }, { episode_id: "E2" }],
    actions: [{ action_id: "A" }],
    slot_relations: [rel("R1", "E1", "contains_action", "A"), rel("R2", "E2", "contains_action", "A")],
  });
  assert.ok(c.some(([code, sev]) => code === "ACTION_MULTI_EPISODE" && sev === "warning"));
});

test("AUX_TEXT_WITHOUT_RELATION", () => {
  for (const inner of [
    { episodes: [{ episode_id: "E", entry_situation_text: "entry" }] },
    { episodes: [{ episode_id: "E", exit_situation_text: "exit" }] },
    { actions: [{ action_id: "A", context: { causes_transition_text: "transition" } }] },
    { actions: [{ action_id: "A", why: { reason_texts: ["because"] } }] },
    { reasons: [{ reason_id: "R", evidence: { observation_texts: ["Observe"] } }] },
  ]) {
    assert.ok(
      codes(inner).some(([code, sev]) => code === "AUX_TEXT_WITHOUT_RELATION" && sev === "warning"),
      JSON.stringify(inner),
    );
  }
  // backed by the relation -> no warning
  const c = codes({
    actions: [{ action_id: "A", why: { reason_texts: ["because"] } }],
    reasons: [{ reason_id: "R", reason_type: ["cause"] }],
    slot_relations: [rel("R1", "A", "has_reason", "R")],
  });
  assert.ok(!c.some(([code]) => code === "AUX_TEXT_WITHOUT_RELATION"));
});

test("coffee example has no schema errors", (t) => {
  if (skipUnless(t, COFFEE)) return;
  const errors = validateSchema(loadModelFromObject(JSON.parse(readFileSync(COFFEE, "utf8"))))
    .filter((i) => i.severity === "error");
  assert.deepEqual(errors, []);
});
