/**
 * Structural validation of the EFFBD derived from a T2A-ESS model.
 * JS port of src/t2a_sysml/validate.py.
 *
 * Checks reference resolution, start->done reachability, item-flow completeness
 * and performer allocation on the slot graph (the EFFBD SysML dialect itself is
 * only validated at runtime by the selab-effbd-editor).
 */

import { ALL_SLOT_COLLECTIONS } from "./model.js";

/** @typedef {{severity: "error"|"warning", code: string, message: string}} Issue */

// ---------------------------------------------------------------------------
// Schema-level validation ("Slot Relation contract", docs/Text2Activity-Extraction-
// Slot-Schema.md §Slot Relation contract + pipeline step 14 validation).
// ---------------------------------------------------------------------------

// Registered custom_relation_type values; extend when a custom meaning is
// promoted into the contract.
export const REGISTERED_CUSTOM_TYPES = [];

// relation_type -> allowed [source_collection, target_collection] pairs.
export const RELATION_CONTRACT = {
  has_episode: [["scenarios", "episodes"]],
  contains_action: [["episodes", "actions"]],
  has_situation: [["scenarios", "situations"], ["episodes", "situations"]],
  entry_situation: [["episodes", "situations"]],
  exit_situation: [["episodes", "situations"]],
  has_part: [["performers", "performers"]],
  performed_by: [["actions", "performers"]],
  acts_on: [["actions", "items"], ["actions", "performers"]],
  provided_to: [["actions", "performers"], ["actions", "items"]],
  uses_item: [["actions", "items"]],
  produces_item: [["actions", "items"]],
  flow_source: [["flows", "actions"]],
  flow_target: [["flows", "actions"]],
  carries_item: [["flows", "items"]],
  controls_flow: [["controls", "flows"]],
  // temporal_* : source and target each in {actions, transitions, events}
  ...Object.fromEntries(
    ["temporal_before", "temporal_after", "temporal_during", "temporal_while",
     "temporal_overlaps", "temporal_starts_with", "temporal_ends_with"].map((rt) => [
      rt,
      ["actions", "transitions", "events"].flatMap((s) =>
        ["actions", "transitions", "events"].map((t) => [s, t])),
    ]),
  ),
  has_state_value: [["situations", "state_values"]],
  from_situation: [["transitions", "situations"]],
  to_situation: [["transitions", "situations"]],
  observes: [["observations", "events"], ["observations", "state_values"]],
  triggers: [["events", "transitions"], ["events", "actions"]],
  causes_event: [["events", "events"]],
  originates_event: [["performers", "events"]],
  causes: [["actions", "transitions"]],
  constrained_by: [["actions", "constraints"], ["transitions", "constraints"]],
  has_goal: [["scenarios", "goals"], ["actions", "goals"], ["reasons", "goals"]],
  has_reason: [["actions", "reasons"], ["transitions", "reasons"]],
  has_evidence: [["reasons", "observations"]],
  has_binding: [["domain_extension_rules", "semantic_bindings"]],
  binds_to: [
    ["semantic_bindings", "actions"],
    ["semantic_bindings", "performers"],
    ["semantic_bindings", "items"],
    ["semantic_bindings", "events"],
    ["semantic_bindings", "state_values"],
    ["semantic_bindings", "situations"],
    ["semantic_bindings", "transitions"],
  ],
  // "custom": any -> any (requires custom_relation_type; handled inline).
};

/** @returns {Issue[]} */
export function validateSchema(model) {
  const issues = [];
  const issue = (severity, code, message) => issues.push({ severity, code, message });

  // duplicate slot ids across collections
  const owner = new Map();
  for (const collection of ALL_SLOT_COLLECTIONS) {
    for (const slot of model.collection(collection)) {
      const sid = model.slotId(slot);
      if (!sid) continue;
      if (owner.has(sid) && owner.get(sid) !== collection) {
        issue("error", "DUPLICATE_SLOT_ID", `${sid}: id in both ${owner.get(sid)} and ${collection}`);
      } else if (!owner.has(sid)) {
        owner.set(sid, collection);
      }
    }
  }

  const byId = model.byId;
  const touched = new Set();
  const rid = (rel) => String(rel.relation_id ?? rel.id ?? "?");

  for (const rel of model.relations) {
    const relId = rid(rel);
    const rt = rel.relation_type;
    const src = rel.source_slot_id;
    const tgt = rel.target_slot_id;
    for (const x of [src, tgt]) if (x) touched.add(x);

    const dangling = [src, tgt].filter((x) => x && !byId.has(x));
    if (dangling.length) {
      issue("error", "DANGLING_RELATION_ENDPOINT", `${relId}: endpoint not found: ${dangling.join(", ")}`);
      continue;
    }

    if (rt === "custom") {
      const crt = rel.custom_relation_type;
      if (crt == null || !String(crt).trim()) {
        issue("error", "CUSTOM_TYPE_MISSING", `${relId}: custom relation without custom_relation_type`);
      } else if (!REGISTERED_CUSTOM_TYPES.includes(crt)) {
        issue("warning", "CUSTOM_TYPE_NOT_REGISTERED", `${relId}: unregistered custom_relation_type: ${crt}`);
      }
      continue;
    }

    if (!(rt in RELATION_CONTRACT)) {
      issue("error", "UNKNOWN_RELATION_TYPE", `${relId}: unknown relation_type: ${rt}`);
      continue;
    }

    const srcType = byId.get(src)[0];
    const tgtType = byId.get(tgt)[0];
    const allowed = RELATION_CONTRACT[rt];
    if (!allowed.some(([s, t]) => s === srcType && t === tgtType)) {
      const allowedS = allowed.map(([s, t]) => `${s}→${t}`).join(", ");
      issue("error", "RELATION_ENDPOINT_TYPE",
        `${relId}: ${rt} ${srcType}→${tgtType} not allowed (allowed: ${allowedS})`);
    }
  }

  // state-axis completeness
  for (const tr of model.collection("transitions")) {
    const tid = model.slotId(tr);
    const from = model.outRelations(tid, "from_situation").length;
    const to = model.outRelations(tid, "to_situation").length;
    if (from !== 1 || to !== 1) {
      issue("error", "TRANSITION_ENDPOINTS",
        `${tid}: transition needs exactly 1 from_situation and 1 to_situation (from=${from}, to=${to})`);
    }
  }
  for (const st of model.collection("situations")) {
    const sid = model.slotId(st);
    if (!model.outRelations(sid, "has_state_value").length) {
      issue("warning", "SITUATION_NO_STATE_VALUE", `${sid}: situation has no has_state_value`);
    }
  }
  for (const ob of model.collection("observations")) {
    const oid = model.slotId(ob);
    if (!model.outRelations(oid, "observes").length) {
      issue("warning", "OBSERVATION_NO_OBSERVES", `${oid}: observation has no observes`);
    }
  }
  for (const ev of model.collection("events")) {
    const eid = model.slotId(ev);
    if (!touched.has(eid)) {
      issue("warning", "ISOLATED_EVENT", `${eid}: event appears in no relation`);
    }
  }

  // episode coverage of actions
  for (const action of model.collection("actions")) {
    const aid = model.slotId(action);
    const parents = new Set(model.sources(aid, "contains_action"));
    if (!parents.size) {
      issue("warning", "ACTION_NO_EPISODE", `${aid}: action not target of any contains_action`);
    } else if (parents.size > 1) {
      issue("warning", "ACTION_MULTI_EPISODE",
        `${aid}: action target of contains_action from ${parents.size} episodes`);
    }
  }

  // auxiliary *_text fields must be backed by the canonical relation they mirror
  const nonempty = (v) => {
    if (typeof v === "string") return v.trim().length > 0;
    if (Array.isArray(v)) return v.some((x) => String(x).trim().length > 0);
    return Boolean(v);
  };

  for (const episode of model.collection("episodes")) {
    const eid = model.slotId(episode);
    for (const [field, rt] of [["entry_situation_text", "entry_situation"],
                               ["exit_situation_text", "exit_situation"]]) {
      if (nonempty(episode[field]) && !model.outRelations(eid, rt).length) {
        issue("warning", "AUX_TEXT_WITHOUT_RELATION", `${eid}: ${field} set but no ${rt} relation`);
      }
    }
  }
  for (const action of model.collection("actions")) {
    const aid = model.slotId(action);
    const context = action.context ?? {};
    if (nonempty(context.causes_transition_text) && !model.outRelations(aid, "causes").length) {
      issue("warning", "AUX_TEXT_WITHOUT_RELATION",
        `${aid}: context.causes_transition_text set but no causes relation`);
    }
    const why = action.why ?? {};
    if (nonempty(why.reason_texts) && !model.outRelations(aid, "has_reason").length) {
      issue("warning", "AUX_TEXT_WITHOUT_RELATION",
        `${aid}: why.reason_texts set but no has_reason relation`);
    }
  }
  for (const reason of model.collection("reasons")) {
    const rid2 = model.slotId(reason);
    const evidence = reason.evidence ?? {};
    if (nonempty(evidence.observation_texts) && !model.outRelations(rid2, "has_evidence").length) {
      issue("warning", "AUX_TEXT_WITHOUT_RELATION",
        `${rid2}: evidence.observation_texts set but no has_evidence relation`);
    }
  }

  return issues;
}

function edgesOf(model) {
  const actionIds = new Set(model.collection("actions").map((a) => model.slotId(a)));
  const edges = [];
  const seen = new Set();
  const add = (a, b) => {
    const key = `${a} ${b}`;
    if (actionIds.has(a) && actionIds.has(b) && a !== b && !seen.has(key)) {
      seen.add(key);
      edges.push([a, b]);
    }
  };
  for (const flow of model.collection("flows")) {
    const fid = model.slotId(flow);
    for (const a of model.targets(fid, "flow_source")) {
      for (const b of model.targets(fid, "flow_target")) add(a, b);
    }
  }
  for (const rel of model.relations) {
    if (rel.relation_type === "temporal_before") add(rel.source_slot_id, rel.target_slot_id);
  }
  return edges;
}

/** @returns {Issue[]} */
export function validateEffbd(model) {
  const issues = [];
  const issue = (severity, code, message) => issues.push({ severity, code, message });
  const actionIds = model.collection("actions").map((a) => model.slotId(a));
  const actionSet = new Set(actionIds);
  const edges = edgesOf(model);

  // 1) reachability: start -> (no-incoming) ... -> (no-outgoing) -> done.
  const outAdj = new Map(actionIds.map((a) => [a, []]));
  const hasIn = new Set();
  for (const [a, b] of edges) {
    outAdj.get(a).push(b);
    hasIn.add(b);
  }
  const starts = actionIds.filter((a) => !hasIn.has(a));
  const reached = new Set(starts);
  const queue = [...starts];
  while (queue.length) {
    const node = queue.shift();
    for (const nxt of outAdj.get(node) ?? []) {
      if (!reached.has(nxt)) {
        reached.add(nxt);
        queue.push(nxt);
      }
    }
  }
  for (const a of actionIds) {
    if (!reached.has(a)) {
      issue("error", "UNREACHABLE_ACTION", `action not reachable from start (isolated cycle?): ${a}`);
    }
  }

  // 2) item-flow completeness: every item should have a producer and a consumer.
  const producers = new Set();
  const consumers = new Set();
  for (const a of actionIds) {
    for (const i of model.targets(a, "produces_item")) producers.add(i);
    for (const rt of ["uses_item", "provided_to"]) for (const i of model.targets(a, rt)) consumers.add(i);
  }
  for (const flow of model.collection("flows")) {
    if (String(flow.flow_kind ?? "").includes("object")) {
      const fid = model.slotId(flow);
      for (const i of model.targets(fid, "carries_item")) {
        if (model.targets(fid, "flow_source").length) producers.add(i);
        if (model.targets(fid, "flow_target").length) consumers.add(i);
      }
    }
  }
  for (const item of model.collection("items")) {
    const iid = model.slotId(item);
    const hasP = producers.has(iid);
    const hasC = consumers.has(iid);
    if (hasP && !hasC) issue("warning", "ITEM_NO_CONSUMER", `item produced but never consumed: ${iid}`);
    else if (hasC && !hasP) issue("warning", "ITEM_NO_PRODUCER", `item consumed but never produced: ${iid}`);
  }

  // 3) allocation coverage: every action should be allocated to a performer.
  for (const a of actionIds) {
    if (!model.targets(a, "performed_by").length) {
      issue("warning", "ACTION_NO_PERFORMER", `action has no performer (allocation): ${a}`);
    }
  }

  // 4) dangling flow endpoints (references to non-actions).
  for (const [a, b] of edges) {
    for (const end of [a, b]) {
      if (!actionSet.has(end)) issue("error", "DANGLING_FLOW_ENDPOINT", `flow endpoint is not an action: ${end}`);
    }
  }

  return issues;
}

export function summarize(issues) {
  const errors = issues.filter((i) => i.severity === "error").length;
  const warnings = issues.filter((i) => i.severity === "warning").length;
  return { ok: errors === 0, errors, warnings };
}
