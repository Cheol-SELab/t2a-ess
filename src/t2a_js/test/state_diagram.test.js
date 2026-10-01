/**
 * Tests for the state machine diagram renderer (t2a_sysml/state_diagram.js).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

import { loadModel, loadModelFromObject, renderStateHtml, renderStateSvg, stateGraph, convertStateModel } from "../t2a_sysml/index.js";
import { ROOT, MUMT, COFFEE, skipUnless } from "./fixtures.js";

const svgOf = (file) => renderStateSvg(stateGraph(loadModel(file)));
const count = (s, re) => (s.match(re) ?? []).length;

test("coffee diagram structure", (t) => {
  if (skipUnless(t, COFFEE)) return;
  const svg = svgOf(COFFEE);
  assert.equal(count(svg, /class="state"/g), 4);
  assert.equal(count(svg, /class="transition"/g), 3);
  assert.equal(count(svg, /class="region"/g), 1);
  assert.equal(count(svg, /class="initial"/g), 1);
  assert.ok(svg.includes("Transition from order waiting to payment completed") || svg.includes("data-id=\"TR_WAITING_TO_PAID\""));
  assert.ok(svg.includes("Payment approval [Payment within 3 min] / Payment"));
  assert.ok(!/NaN|undefined/.test(svg));
});

test("coffee: no transition label overlaps a state box", (t) => {
  if (skipUnless(t, COFFEE)) return;
  const svg = svgOf(COFFEE);
  const rects = (cls) =>
    [...svg.matchAll(new RegExp(`<g class="${cls}"[^>]*>\\s*<rect x="([\\d.-]+)" y="([\\d.-]+)" width="([\\d.-]+)" height="([\\d.-]+)"`, "g"))]
      .map((m) => ({ x: +m[1], y: +m[2], w: +m[3], h: +m[4] }));
  // state rects: first rect inside each state group; labels: rect.lbl
  const states = [...svg.matchAll(/<g class="state"[^>]*>\s*<rect x="([\d.-]+)" y="([\d.-]+)" width="([\d.-]+)" height="([\d.-]+)"/g)]
    .map((m) => ({ x: +m[1], y: +m[2], w: +m[3], h: +m[4] }));
  const labels = [...svg.matchAll(/<rect class="lbl" x="([\d.-]+)" y="([\d.-]+)" width="([\d.-]+)" height="([\d.-]+)"/g)]
    .map((m) => ({ x: +m[1], y: +m[2], w: +m[3], h: +m[4] }));
  assert.ok(labels.length > 0);
  for (const l of labels) {
    for (const s of states) {
      const overlap = l.x < s.x + s.w && l.x + l.w > s.x && l.y < s.y + s.h && l.y + l.h > s.y;
      assert.ok(!overlap, `label rect (${l.x},${l.y},${l.w},${l.h}) overlaps state (${s.x},${s.y},${s.w},${s.h})`);
    }
  }
});

test("MUM-T diagram: regions, separators, no NaN", (t) => {
  if (skipUnless(t, MUMT)) return;
  const svg = svgOf(MUMT);
  assert.equal(count(svg, /class="region"/g), 3);
  assert.equal(count(svg, /class="state"/g), 6);
  assert.equal(count(svg, /class="region-sep"/g), 2);
  assert.ok(!/NaN|undefined/.test(svg));
});

test("synthetic: self-loop, back edge, escaping, empty, unreachable", () => {
  const base = {
    text2activity_extraction_model: {
      title: "t",
      scenarios: [{ scenario_id: "S", label: "sc" }],
      slot_relations: [],
    },
  };
  const inner = base.text2activity_extraction_model;

  // self-loop A->A
  const loop = loadModelFromObject({
    text2activity_extraction_model: {
      ...inner,
      situations: [{ situation_id: "A", label: "a" }],
      transitions: [{ transition_id: "T1", label: "loop" }],
      slot_relations: [
        { source_slot_id: "T1", relation_type: "from_situation", target_slot_id: "A" },
        { source_slot_id: "T1", relation_type: "to_situation", target_slot_id: "A" },
      ],
    },
  });
  const loopSvg = renderStateSvg(stateGraph(loop));
  assert.equal(count(loopSvg, /class="transition"/g), 1);
  assert.ok(loopSvg.includes("<path"));
  assert.ok(!/NaN|undefined/.test(loopSvg));

  // back edge A->B->A renders two transitions
  const cyc = loadModelFromObject({
    text2activity_extraction_model: {
      ...inner,
      situations: [
        { situation_id: "A", label: "a" },
        { situation_id: "B", label: "b" },
      ],
      transitions: [
        { transition_id: "T1", label: "f" },
        { transition_id: "T2", label: "back" },
      ],
      slot_relations: [
        { source_slot_id: "T1", relation_type: "from_situation", target_slot_id: "A" },
        { source_slot_id: "T1", relation_type: "to_situation", target_slot_id: "B" },
        { source_slot_id: "T2", relation_type: "from_situation", target_slot_id: "B" },
        { source_slot_id: "T2", relation_type: "to_situation", target_slot_id: "A" },
      ],
    },
  });
  const cycSvg = renderStateSvg(stateGraph(cyc));
  assert.equal(count(cycSvg, /class="transition"/g), 2);
  assert.ok(!/NaN|undefined/.test(cycSvg));

  // escaping: label with <&"' must not emit raw < inside text content
  const escModel = loadModelFromObject({
    text2activity_extraction_model: {
      ...inner,
      situations: [
        { situation_id: "A", label: "a<&\"'" },
        { situation_id: "B", label: "b" },
      ],
      transitions: [{ transition_id: "T1", label: "x<y" }],
      slot_relations: [
        { source_slot_id: "T1", relation_type: "from_situation", target_slot_id: "A" },
        { source_slot_id: "T1", relation_type: "to_situation", target_slot_id: "B" },
      ],
    },
  });
  const escSvg = renderStateSvg(stateGraph(escModel));
  assert.match(escSvg, /<text[^>]*>[^<]*&lt;/);

  // empty state axis: HTML still renders with 0 states
  const empty = loadModelFromObject(base);
  const html = renderStateHtml(empty);
  assert.ok(html.includes("state def"));
  assert.ok(!/NaN|undefined/.test(html));

  // states unreachable from initial still appear
  const unr = loadModelFromObject({
    text2activity_extraction_model: {
      ...inner,
      situations: [
        { situation_id: "A", label: "a" },
        { situation_id: "B", label: "b" },
        { situation_id: "C", label: "c" },
      ],
      transitions: [{ transition_id: "T1", label: "f" }],
      slot_relations: [
        { source_slot_id: "T1", relation_type: "from_situation", target_slot_id: "A" },
        { source_slot_id: "T1", relation_type: "to_situation", target_slot_id: "B" },
      ],
    },
  });
  const unrSvg = renderStateSvg(stateGraph(unr));
  assert.equal(count(unrSvg, /class="state"/g), 3);
});

test("determinism + committed example sync", (t) => {
  for (const [json, html] of [
    [COFFEE, path.join(ROOT, "src", "examples", "coffee_order.state.html")],
    [MUMT, path.join(ROOT, "src", "examples", "mumt.state.html")],
  ]) {
    if (skipUnless(t, json) || skipUnless(t, html)) continue;
    const model = loadModel(json);
    const fresh = renderStateHtml(model);
    assert.equal(renderStateHtml(model), fresh, "renderStateHtml must be deterministic");
    assert.equal(fresh, readFileSync(html, "utf8"), `${path.basename(html)} out of sync`);
  }
});

test("stateGraph IR: coffee + multi-trigger fan-out", (t) => {
  if (skipUnless(t, COFFEE)) return;
  const g = stateGraph(loadModel(COFFEE));
  assert.equal(g.regions.length, 1);
  assert.equal(g.regions[0].label, "order_status");
  const sitLabel = (id) => g.regions[0].states.find((s) => s.id === id)?.label;
  assert.equal(sitLabel(g.regions[0].initial), "Order waiting state");
  const t1 = g.regions[0].transitions.find((x) => x.id === "TR_WAITING_TO_PAID");
  assert.deepEqual(t1.events, ["Payment approval"]);
  assert.deepEqual(t1.guards, ["Payment within 3 min"]);
  assert.deepEqual(t1.actions, ["Payment"]);

  // multi-trigger: ONE IR transition with 2 events, text still emits `#2`
  const multi = loadModelFromObject({
    text2activity_extraction_model: {
      title: "m",
      scenarios: [{ scenario_id: "S", label: "s" }],
      situations: [
        { situation_id: "A", label: "a" },
        { situation_id: "B", label: "b" },
      ],
      events: [
        { event_id: "E1", label: "e1" },
        { event_id: "E2", label: "e2" },
      ],
      transitions: [{ transition_id: "T", label: "go" }],
      slot_relations: [
        { source_slot_id: "T", relation_type: "from_situation", target_slot_id: "A" },
        { source_slot_id: "T", relation_type: "to_situation", target_slot_id: "B" },
        { source_slot_id: "E1", relation_type: "triggers", target_slot_id: "T" },
        { source_slot_id: "E2", relation_type: "triggers", target_slot_id: "T" },
      ],
    },
  });
  const gm = stateGraph(multi);
  assert.equal(gm.regions[0].transitions.length, 1);
  assert.equal(gm.regions[0].transitions[0].events.length, 2);
  assert.ok(convertStateModel(multi).includes("transition 'go #2'"));
});
