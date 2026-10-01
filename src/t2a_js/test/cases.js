/**
 * Synthetic T2A-ESS test cases covering the converter's structural features.
 *
 * Each case: { id, title, model, expect } where `model` is a T2A-ESS object (already
 * wrapped in text2activity_extraction_model) and `expect` drives both the structural
 * assertions (t2a_sysml.test.js) and the Rust LSP graph checks (tools/lsp_check.js):
 *
 *   nested        episodes fully cover actions -> nested functions (else flat fallback)
 *   forks/joins   number of fork/join nodes the converter must emit (file-wide unique)
 *   guards        number of guarded successions
 *   flows         number of `flow from … to …` lines (object flows)
 *   validateErrors number of structural validator *errors* (warnings not counted)
 *   lspErrorsAllowed  substrings of LSP ERROR diagnostics that are tolerated if they appear
 */

let rel = 0;
const R = (source, type, target, extra = {}) => ({
  relation_id: `r${++rel}`,
  source_slot_id: source,
  relation_type: type,
  target_slot_id: target,
  ...extra,
});
const contains = (ep, ...actions) => actions.map((a) => R(ep, "custom", a, { custom_relation_type: "contains_action" }));
const flow = (id, a, b, kind = "control_flow", label = id) => ({
  slot: { flow_id: id, label, flow_kind: kind },
  rels: [R(id, "flow_source", a), R(id, "flow_target", b)],
});
const wrap = (m) => ({ text2activity_extraction_model: m });

function build({ model_id, title, scenario, episodes = [], performers = [], actions = [], items = [], flows = [], controls = [], relations = [] }) {
  const m = { model_id, title };
  if (scenario) m.scenarios = [{ scenario_id: "SCN", label: scenario }];
  if (episodes.length) m.episodes = episodes.map((e, i) => ({ episode_id: e.id, label: e.label, order_index: e.order ?? i + 1 }));
  m.performers = performers.map(([id, label]) => ({ performer_id: id, label }));
  m.actions = actions.map(([id, label]) => ({ action_id: id, label }));
  if (items.length) m.items = items.map(([id, label]) => ({ item_id: id, label, item_type: "data" }));
  const rels = [...relations];
  if (flows.length) {
    m.flows = flows.map((f) => f.slot);
    for (const f of flows) rels.push(...f.rels);
  }
  if (controls.length) m.controls = controls;
  if (scenario) for (const e of episodes) rels.push(R("SCN", "has_episode", e.id));
  m.slot_relations = rels;
  return wrap(m);
}

export const CASES = [];
const add = (c) => CASES.push(c);

// A. flat linear chain, single performer
add({
  id: "flat_linear",
  title: "flat: 3 actions in a chain, no episodes",
  model: build({
    model_id: "C_FLAT", title: "flat linear", scenario: "Simple sequence",
    performers: [["P1", "Operator"]],
    actions: [["A", "Prepare"], ["B", "Execute"], ["C", "Finish"]],
    flows: [flow("F1", "A", "B"), flow("F2", "B", "C")],
    relations: [R("A", "performed_by", "P1"), R("B", "performed_by", "P1"), R("C", "performed_by", "P1")],
  }),
  expect: { nested: false, actions: 3, episodes: 0, performers: 1, forks: 0, joins: 0, guards: 0, flows: 0, allocations: 3, validateErrors: 0 },
});

// B. two sequential episodes
add({
  id: "nested_two_episodes",
  title: "nested: 2 episodes, each a chain",
  model: build({
    model_id: "C_NEST", title: "nested", scenario: "Two episodes",
    episodes: [{ id: "E1", label: "Preparation phase" }, { id: "E2", label: "Execution phase" }],
    performers: [["P1", "Pilot"], ["P2", "Control"]],
    actions: [["A", "Inspect"], ["B", "Take off"], ["C", "Cruise"], ["D", "Land"]],
    flows: [flow("F1", "A", "B"), flow("F2", "C", "D")],
    relations: [...contains("E1", "A", "B"), ...contains("E2", "C", "D"),
      R("A", "performed_by", "P1"), R("B", "performed_by", "P1"), R("C", "performed_by", "P1"), R("D", "performed_by", "P2")],
  }),
  expect: { nested: true, actions: 4, episodes: 2, performers: 2, forks: 0, joins: 0, guards: 0, flows: 0, allocations: 4, validateErrors: 0 },
});

// C. fork/join in two sibling episodes -> names must be file-wide unique (Concurrency_1, _2)
add({
  id: "fork_join_multi_episode",
  title: "fork/join in 2 sibling episodes (unique naming regression)",
  model: build({
    model_id: "C_FJ2", title: "fork join x2", scenario: "Concurrency twice",
    episodes: [{ id: "E1", label: "Detection" }, { id: "E2", label: "Response" }],
    performers: [["P1", "Drone"], ["P2", "TDSS"]],
    actions: [["A1", "Heat-source detection"], ["A2", "Acoustic detection"], ["A3", "Fuse detections"], ["B1", "Alarm"], ["B2", "Evade"], ["B3", "Report"]],
    flows: [flow("F1", "A1", "A3"), flow("F2", "A2", "A3"), flow("F3", "B1", "B3"), flow("F4", "B2", "B3")],
    relations: [...contains("E1", "A1", "A2", "A3"), ...contains("E2", "B1", "B2", "B3"),
      ...["A1", "A2", "A3"].map((a) => R(a, "performed_by", "P1")), ...["B1", "B2", "B3"].map((a) => R(a, "performed_by", "P2"))],
  }),
  expect: { nested: true, actions: 6, episodes: 2, performers: 2, forks: 2, joins: 2, guards: 0, flows: 0, allocations: 6, validateErrors: 0 },
});

// D. decision: one guarded + one unguarded outgoing edge -> no fork, one guarded succession
add({
  id: "decision_guard",
  title: "decision guard on one of two outgoing edges",
  model: build({
    model_id: "C_DEC", title: "decision", scenario: "Decision branch",
    performers: [["P1", "Commander"]],
    actions: [["A", "Assess threat"], ["B", "Bypass maneuver"], ["C", "Frontal breakthrough"], ["D", "End mission"]],
    flows: [flow("F1", "A", "B"), flow("F2", "A", "C"), flow("F3", "B", "D"), flow("F4", "C", "D")],
    controls: [{ control_id: "CT1", label: "High-threat decision", control_type: "decision", guard_texts: ["threat level high"] }],
    relations: [R("CT1", "controls_flow", "F1"), ...["A", "B", "C", "D"].map((a) => R(a, "performed_by", "P1"))],
  }),
  expect: { nested: false, actions: 4, episodes: 0, performers: 1, forks: 0, joins: 1, guards: 1, flows: 0, allocations: 4, validateErrors: 0 },
});

// E. guarded loop back-edge into the entry action.
//    KNOWN LIMITATION: the back-edge B->A gives A an incoming edge, so A is no longer a
//    "start" action: no `start ->` succession is emitted and the validator reports all
//    actions unreachable. The EFFBD editor models loops with decide/merge
//    (`New Start Loop` / `New End Loop`) nodes, which the converter does not emit yet.
//    The LSP still parses the file without errors. Expectations below pin the *current*
//    behaviour so a future decide/merge implementation must update them deliberately.
add({
  id: "loop_control",
  title: "loop back-edge into the entry action (known limitation: no start, no decide/merge)",
  model: build({
    model_id: "C_LOOP", title: "loop", scenario: "Repeat",
    performers: [["P1", "Operator"]],
    actions: [["A", "Check status"], ["B", "Retry"], ["C", "Report completion"]],
    flows: [flow("F1", "A", "B"), flow("F2", "B", "A"), flow("F3", "A", "C")],
    controls: [{ control_id: "CT1", label: "Repeat on failure", control_type: "loop", guard_texts: ["check failed"] }],
    relations: [R("CT1", "controls_flow", "F2"), ...["A", "B", "C"].map((a) => R(a, "performed_by", "P1"))],
  }),
  expect: { nested: false, actions: 3, episodes: 0, performers: 1, forks: 1, joins: 0, guards: 1, flows: 0, allocations: 3, validateErrors: 3,
    forbidText: ["succession first start then"], lspErrorsAllowed: ["cycle", "Cycle"], known: "loop back-edge hides start; decide/merge not emitted" },
});

// F. object flow within one group -> ports on both ends + flow line
add({
  id: "object_flow_intra",
  title: "object flow inside one function",
  model: build({
    model_id: "C_OBJ", title: "object flow", scenario: "Data handoff",
    performers: [["P1", "Sensor"], ["P2", "Analyzer"]],
    actions: [["A", "Acquire video"], ["B", "Analyze video"]],
    items: [["I1", "Video stream"]],
    flows: [flow("F1", "A", "B", "object_flow", "Video handoff")],
    relations: [R("F1", "carries_item", "I1"), R("A", "produces_item", "I1"), R("B", "uses_item", "I1"),
      R("A", "performed_by", "P1"), R("B", "performed_by", "P2")],
  }),
  expect: { nested: false, actions: 2, episodes: 0, performers: 2, forks: 0, joins: 0, guards: 0, flows: 1, allocations: 2, validateErrors: 0 },
});

// G. object flow across episodes -> 3-level dotted path, ports on both endpoints (port regression)
add({
  id: "object_flow_cross_episode",
  title: "object flow crossing an episode boundary",
  model: build({
    model_id: "C_XOBJ", title: "cross-episode object flow", scenario: "Data across episodes",
    episodes: [{ id: "E1", label: "Collect" }, { id: "E2", label: "Use" }],
    performers: [["P1", "Drone"], ["P2", "Command post"]],
    actions: [["A", "Create tracks"], ["B", "Send tracks"], ["C", "SA update"]],
    items: [["I1", "Summary tracks"]],
    flows: [flow("F1", "A", "B"), flow("F2", "A", "C", "object_flow", "Track handoff")],
    relations: [...contains("E1", "A", "B"), ...contains("E2", "C"), R("F2", "carries_item", "I1"),
      R("A", "performed_by", "P1"), R("B", "performed_by", "P1"), R("C", "performed_by", "P2")],
  }),
  expect: { nested: true, actions: 3, episodes: 2, performers: 2, forks: 0, joins: 0, guards: 0, flows: 1, allocations: 3, validateErrors: 0,
    expectPorts: [["SA update", "in item 'Summary tracks'"], ["Create tracks", "out item 'Summary tracks'"]] },
});

// H. duplicate labels -> " #2" suffix, LSP must not report DuplicateName
add({
  id: "duplicate_labels",
  title: "two actions and two performers share a label",
  model: build({
    model_id: "C_DUP", title: "duplicates", scenario: "Duplicate labels",
    performers: [["P1", "Platoon"], ["P2", "Platoon"]],
    actions: [["A", "Move"], ["B", "Move"], ["C", "Stop"]],
    flows: [flow("F1", "A", "B"), flow("F2", "B", "C")],
    relations: [R("A", "performed_by", "P1"), R("B", "performed_by", "P2"), R("C", "performed_by", "P2")],
  }),
  expect: { nested: false, actions: 3, episodes: 0, performers: 2, forks: 0, joins: 0, guards: 0, flows: 0, allocations: 3, validateErrors: 0,
    expectText: ["action 'Move #2'", "part 'Platoon #2' : Performer;"] },
});

// I. labels with quotes, newlines, backslashes, colons
add({
  id: "special_chars",
  title: "labels containing ' \\n \\\\ :: and unicode",
  model: build({
    model_id: "C_CHARS", title: "special chars", scenario: "Special characters 'test'",
    performers: [["P1", "O'Brien Team"]],
    actions: [["A", "Stage 1\nprep"], ["B", "path C:\\temp set"], ["C", "Pkg::Name check"], ["D", "Done ✓"]],
    flows: [flow("F1", "A", "B"), flow("F2", "B", "C"), flow("F3", "C", "D")],
    relations: [...["A", "B", "C", "D"].map((a) => R(a, "performed_by", "P1"))],
  }),
  expect: { nested: false, actions: 4, episodes: 0, performers: 1, forks: 0, joins: 0, guards: 0, flows: 0, allocations: 4, validateErrors: 0,
    expectText: ["action 'Special characters test' {", "part 'OBrien Team' : Performer;", "action 'Stage 1prep'", "action 'path C:temp set'"] },
});

// J. legacy `name` field instead of `label`
add({
  id: "legacy_name_fields",
  title: "slots use legacy `name` instead of `label`",
  model: wrap({
    model_id: "C_LEGACY", title: "legacy",
    scenarios: [{ scenario_id: "SCN", name: "Legacy scenario" }],
    performers: [{ performer_id: "P1", name: "Operator" }],
    actions: [{ action_id: "A", name: "Observe" }, { action_id: "B", name: "Report" }],
    flows: [{ flow_id: "F1", name: "Report after observation", flow_kind: "control_flow" }],
    slot_relations: [R("A", "performed_by", "P1"), R("F1", "flow_source", "A"), R("F1", "flow_target", "B")],
  }),
  expect: { nested: false, actions: 2, episodes: 0, performers: 1, forks: 0, joins: 0, guards: 0, flows: 0, allocations: 1, validateErrors: 0,
    expectText: ["action 'Legacy scenario' {", "succession first 'Observe' then 'Report';"], forbidText: ["Function_"] },
});

// K. no scenario and no title -> root named after model_id
add({
  id: "no_scenario_no_title",
  title: "no scenarios[] and no title",
  model: wrap({
    model_id: "C_NOSCN",
    actions: [{ action_id: "A", label: "Single task" }],
    slot_relations: [],
  }),
  expect: { nested: false, actions: 1, episodes: 0, performers: 0, forks: 0, joins: 0, guards: 0, flows: 0, allocations: 0, validateErrors: 0,
    expectText: ["action 'C_NOSCN' {"] },
});

// L. one action allocated to two performers; a performer with no actions
add({
  id: "multi_performer",
  title: "action with 2 performers, plus an unused performer",
  model: build({
    model_id: "C_MP", title: "multi performer", scenario: "Joint execution",
    performers: [["P1", "Tank"], ["P2", "Drone"], ["P3", "Reserve"]],
    actions: [["A", "Joint reconnaissance"], ["B", "Share results"]],
    flows: [flow("F1", "A", "B")],
    relations: [R("A", "performed_by", "P1"), R("A", "performed_by", "P2"), R("B", "performed_by", "P1")],
  }),
  expect: { nested: false, actions: 2, episodes: 0, performers: 3, forks: 0, joins: 0, guards: 0, flows: 0, allocations: 3, validateErrors: 0 },
});

// M. ordering from temporal_before only (no flows)
add({
  id: "temporal_before_only",
  title: "successions from temporal_before relations, no flows",
  model: build({
    model_id: "C_TB", title: "temporal", scenario: "Temporal order",
    performers: [["P1", "Operator"]],
    actions: [["A", "Earlier"], ["B", "Next"], ["C", "Last"]],
    relations: [R("A", "temporal_before", "B"), R("B", "temporal_before", "C"), ...["A", "B", "C"].map((a) => R(a, "performed_by", "P1"))],
  }),
  expect: { nested: false, actions: 3, episodes: 0, performers: 1, forks: 0, joins: 0, guards: 0, flows: 0, allocations: 3, validateErrors: 0,
    expectText: ["succession first 'Earlier' then 'Next';", "succession first 'Next' then 'Last';"] },
});

// N. episodes cover only some actions -> flat fallback
add({
  id: "partial_episode_coverage",
  title: "episode covers 2 of 3 actions -> flat fallback",
  model: build({
    model_id: "C_PART", title: "partial", scenario: "Partial coverage",
    episodes: [{ id: "E1", label: "Episode 1" }],
    performers: [["P1", "Operator"]],
    actions: [["A", "alpha"], ["B", "bravo"], ["C", "charlie"]],
    flows: [flow("F1", "A", "B"), flow("F2", "B", "C")],
    relations: [...contains("E1", "A", "B"), ...["A", "B", "C"].map((a) => R(a, "performed_by", "P1"))],
  }),
  expect: { nested: false, actions: 3, episodes: 1, performers: 1, forks: 0, joins: 0, guards: 0, flows: 0, allocations: 3, validateErrors: 0,
    forbidText: ["action 'Episode 1'"] },
});

// O. relations to unknown ids and a flow to a non-action are ignored
add({
  id: "dangling_relations",
  title: "relations to unknown slot ids / flow to a performer",
  model: build({
    model_id: "C_DANG", title: "dangling", scenario: "Loose relations",
    performers: [["P1", "Operator"]],
    actions: [["A", "alpha"], ["B", "bravo"]],
    flows: [flow("F1", "A", "B"), flow("F2", "A", "P1"), flow("F3", "A", "GHOST")],
    relations: [R("A", "performed_by", "P1"), R("A", "performed_by", "NOBODY"), R("A", "produces_item", "NOITEM"), R("GHOST", "temporal_before", "B")],
  }),
  expect: { nested: false, actions: 2, episodes: 0, performers: 1, forks: 0, joins: 0, guards: 0, flows: 0, allocations: 1, validateErrors: 0 },
});

// P. isolated cycle with no entry -> validator error, LSP cycle error
add({
  id: "isolated_cycle",
  title: "A<->B cycle with no start action",
  model: build({
    model_id: "C_CYC", title: "cycle", scenario: "Isolated cycle",
    performers: [["P1", "Operator"]],
    actions: [["A", "alpha"], ["B", "bravo"]],
    flows: [flow("F1", "A", "B"), flow("F2", "B", "A")],
    relations: [R("A", "performed_by", "P1"), R("B", "performed_by", "P1")],
  }),
  expect: { nested: false, actions: 2, episodes: 0, performers: 1, forks: 0, joins: 0, guards: 0, flows: 0, allocations: 2, validateErrors: 2,
    lspErrorsAllowed: ["cycle", "Cycle"] },
});

// Q. wide fork: 5 parallel branches
add({
  id: "wide_fork",
  title: "start -> fork -> 5 branches -> join -> done",
  model: build({
    model_id: "C_WIDE", title: "wide fork", scenario: "5-way parallel",
    performers: [["P1", "Department"]],
    actions: [["A1", "HR"], ["A2", "Planning"], ["A3", "Sales"], ["A4", "Development"], ["A5", "Quality"], ["Z", "Consolidate"]],
    flows: ["A1", "A2", "A3", "A4", "A5"].map((a, i) => flow(`F${i}`, a, "Z")),
    relations: ["A1", "A2", "A3", "A4", "A5", "Z"].map((a) => R(a, "performed_by", "P1")),
  }),
  expect: { nested: false, actions: 6, episodes: 0, performers: 1, forks: 1, joins: 1, guards: 0, flows: 0, allocations: 6, validateErrors: 0 },
});

// R. empty model: no actions at all
add({
  id: "empty_model",
  title: "no actions, only a scenario",
  model: build({ model_id: "C_EMPTY", title: "empty", scenario: "Empty scenario" }),
  expect: { nested: false, actions: 0, episodes: 0, performers: 0, forks: 0, joins: 0, guards: 0, flows: 0, allocations: 0, validateErrors: 0 },
});

// T. guarded + 2 unguarded outgoing from one action -> fork for the unguarded pair, guard kept separate
add({
  id: "guarded_fork_mix",
  title: "1 guarded + 2 unguarded edges from the same action",
  model: build({
    model_id: "C_MIX", title: "mix", scenario: "Guards mixed with concurrency",
    performers: [["P1", "Operator"]],
    actions: [["A", "Decide"], ["B", "Emergency stop"], ["C", "Write log"], ["D", "Send status"]],
    flows: [flow("F1", "A", "B"), flow("F2", "A", "C"), flow("F3", "A", "D")],
    controls: [{ control_id: "CT1", label: "Emergency", control_type: "decision", guard_texts: ["emergency"] }],
    relations: [R("CT1", "controls_flow", "F1"), ...["A", "B", "C", "D"].map((a) => R(a, "performed_by", "P1"))],
  }),
  // B, C, D are all sinks -> the three edges into `done` are grouped by one join.
  expect: { nested: false, actions: 4, episodes: 0, performers: 1, forks: 1, joins: 1, guards: 1, flows: 0, allocations: 4, validateErrors: 0 },
});

// U. three episodes with out-of-order order_index and an item used across all
add({
  id: "episode_ordering",
  title: "episodes declared out of order; order_index decides sequence",
  model: build({
    model_id: "C_ORD", title: "ordering", scenario: "Reordering",
    episodes: [{ id: "E3", label: "Third", order: 3 }, { id: "E1", label: "First", order: 1 }, { id: "E2", label: "Second", order: 2 }],
    performers: [["P1", "Operator"]],
    actions: [["A", "a"], ["B", "b"], ["C", "c"]],
    relations: [...contains("E1", "A"), ...contains("E2", "B"), ...contains("E3", "C"), ...["A", "B", "C"].map((a) => R(a, "performed_by", "P1"))],
  }),
  expect: { nested: true, actions: 3, episodes: 3, performers: 1, forks: 0, joins: 0, guards: 0, flows: 0, allocations: 3, validateErrors: 0,
    expectText: ["succession first start then 'First';", "succession first 'First' then 'Second';", "succession first 'Second' then 'Third';", "succession first 'Third' then done;"] },
});

// V. relay: an action uses and produces the same item. Two ports of one name would be a
//    duplicate definition (LSP error); the output port is renamed and names the item as its
//    payload by subsetting, untyped, because the editor reads the payload only from an
//    untyped port (typed `: ItemOutputEdge` ports fall back to the port name).
add({
  id: "relay_item_port",
  title: "relay action: same item in and out (port naming regression)",
  model: build({
    model_id: "C_RELAY", title: "relay", scenario: "Video relay",
    episodes: [{ id: "E1", label: "Relay phase" }],
    performers: [["P1", "Drone"], ["P2", "Situation room"]],
    actions: [["A", "Capture video"], ["B", "Transmit video"], ["C", "Interpret video"]],
    items: [["I1", "Video"]],
    flows: [flow("F1", "A", "B", "object_flow", "Video handoff"), flow("F2", "B", "C", "object_flow", "Video relay")],
    relations: [...contains("E1", "A", "B", "C"), R("F1", "carries_item", "I1"), R("F2", "carries_item", "I1"),
      R("A", "produces_item", "I1"), R("B", "uses_item", "I1"), R("B", "produces_item", "I1"), R("C", "uses_item", "I1"),
      R("A", "performed_by", "P1"), R("B", "performed_by", "P1"), R("C", "performed_by", "P2")],
  }),
  expect: { nested: true, actions: 3, episodes: 1, performers: 2, forks: 0, joins: 0, guards: 0, flows: 2, allocations: 3, validateErrors: 0,
    expectPorts: [["Transmit video", "in item 'Video' : ItemInputEdge;"], ["Transmit video", "out item 'Video #2' :> 'Video relay'::'Video';"]],
    expectText: ["flow from 'Capture video'.'Video' to 'Transmit video'.'Video';", "flow from 'Transmit video'.'Video #2' to 'Interpret video'.'Video';"] },
});

// W. a guard text equal to an action label of the same function -> the attribute is renamed
add({
  id: "guard_action_name",
  title: "guard attribute named like an action (naming regression)",
  model: build({
    model_id: "C_GNAME", title: "guard name", scenario: "Guard name collision",
    performers: [["P1", "Commander"]],
    actions: [["A", "Assess threat"], ["B", "Evasive maneuver"], ["C", "Frontal breakthrough"], ["D", "End mission"]],
    flows: [flow("F1", "A", "B"), flow("F2", "A", "C"), flow("F3", "B", "D"), flow("F4", "C", "D")],
    controls: [{ control_id: "CT1", label: "Evasion decision", control_type: "decision", guard_texts: ["Evasive maneuver"] }],
    relations: [R("CT1", "controls_flow", "F1"), ...["A", "B", "C", "D"].map((a) => R(a, "performed_by", "P1"))],
  }),
  expect: { nested: false, actions: 4, episodes: 0, performers: 1, forks: 0, joins: 1, guards: 1, flows: 0, allocations: 4, validateErrors: 0,
    expectText: ["attribute 'Evasive maneuver #2' : ScalarValues::Boolean;", "succession first 'Assess threat' if 'Evasive maneuver #2' == true then 'Evasive maneuver';"] },
});

// X. an episode labelled like an item of the root function -> the episode is renamed
add({
  id: "episode_item_name",
  title: "episode named like an item (naming regression)",
  model: build({
    model_id: "C_ENAME", title: "episode name", scenario: "Incident handling",
    episodes: [{ id: "E1", label: "On-site response" }, { id: "E2", label: "Incident report" }],
    performers: [["P1", "Control operator"]],
    actions: [["Z", "Close the barrier"], ["A", "Compile the account"], ["B", "Submit the report"]],
    items: [["I1", "Incident report"]],
    flows: [flow("F1", "A", "B", "object_flow", "Report handoff")],
    relations: [...contains("E1", "Z"), ...contains("E2", "A", "B"), R("F1", "carries_item", "I1"), R("A", "produces_item", "I1"),
      R("B", "uses_item", "I1"), ...["Z", "A", "B"].map((a) => R(a, "performed_by", "P1"))],
  }),
  expect: { nested: true, actions: 3, episodes: 2, performers: 1, forks: 0, joins: 0, guards: 0, flows: 1, allocations: 3, validateErrors: 0,
    expectText: ["    action 'Incident report #2' {", "    item 'Incident report';", "succession first 'On-site response' then 'Incident report #2';"] },
});

// Y. flat function: an action labelled like an item -> the action is renamed (they share one namespace)
add({
  id: "flat_action_item_name",
  title: "flat: action named like an item (naming regression)",
  model: build({
    model_id: "C_FNAME", title: "flat action name", scenario: "Alarm handling",
    performers: [["P1", "Sensor"], ["P2", "Operator"]],
    actions: [["A", "Alarm"], ["B", "Acknowledge alarm"]],
    items: [["I1", "Alarm"]],
    flows: [flow("F1", "A", "B", "object_flow", "Alarm handoff")],
    relations: [R("F1", "carries_item", "I1"), R("A", "produces_item", "I1"), R("B", "uses_item", "I1"),
      R("A", "performed_by", "P1"), R("B", "performed_by", "P2")],
  }),
  expect: { nested: false, actions: 2, episodes: 0, performers: 2, forks: 0, joins: 0, guards: 0, flows: 1, allocations: 2, validateErrors: 0,
    expectText: ["    action 'Alarm #2' {", "    item 'Alarm';", "flow from 'Alarm #2'.'Alarm' to 'Acknowledge alarm'.'Alarm';"] },
});

export const caseById = (id) => CASES.find((c) => c.id === id);
