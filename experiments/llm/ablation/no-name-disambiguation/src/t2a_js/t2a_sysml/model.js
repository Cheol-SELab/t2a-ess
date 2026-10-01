/**
 * Load and index a T2A-ESS extraction model + its slot_relations graph.
 * JS port of src/t2a_sysml/model.py (behaviour-identical).
 */
import { readFileSync } from "node:fs";

// Slot collections we map to SysML (order = declaration preference).
export const SLOT_COLLECTIONS = [
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
];

// All 17 T2A-ESS slot collections (SLOT_COLLECTIONS plus the non-EFFBD ones);
// `byId` indexes all of them so schema validation can resolve every endpoint.
export const ALL_SLOT_COLLECTIONS = [
  ...SLOT_COLLECTIONS,
  "state_values",
  "events",
  "observations",
  "reasons",
  "domain_extension_rules",
  "semantic_bindings",
];

const ID_FIELDS = [
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
];

export function slotId(slot) {
  for (const f of ID_FIELDS) {
    if (slot != null && Object.prototype.hasOwnProperty.call(slot, f)) return String(slot[f]);
  }
  return null;
}

/** Indexed view over the inner `text2activity_extraction_model` object. */
export class T2AModel {
  constructor(raw, model) {
    this.raw = raw;
    this.model = model;
    /** @type {Map<string, [string, object]>} id -> [collection, slot] */
    this.byId = new Map();
    /** @type {object[]} */
    this.relations = [];
    this._bySource = new Map();
    this._byTarget = new Map();
  }

  collection(name) {
    const v = this.model[name];
    return Array.isArray(v) ? v : [];
  }

  get title() {
    return String(this.model.title || this.model.model_id || "Text2ActivityModel");
  }

  get modelId() {
    return String(this.model.model_id || "T2A_MODEL");
  }

  slotId(slot) {
    return slotId(slot);
  }

  outRelations(sourceId, relationType = null) {
    const rels = this._bySource.get(sourceId) ?? [];
    if (relationType === null) return rels;
    return rels.filter((r) => r.relation_type === relationType);
  }

  inRelations(targetId, relationType = null) {
    const rels = this._byTarget.get(targetId) ?? [];
    if (relationType === null) return rels;
    return rels.filter((r) => r.relation_type === relationType);
  }

  targets(sourceId, relationType) {
    return this.outRelations(sourceId, relationType).map((r) => r.target_slot_id);
  }

  sources(targetId, relationType) {
    return this.inRelations(targetId, relationType).map((r) => r.source_slot_id);
  }
}

export function loadModelFromObject(raw) {
  const inner = raw.text2activity_extraction_model ?? raw;
  const model = new T2AModel(raw, inner);

  for (const collection of ALL_SLOT_COLLECTIONS) {
    for (const slot of model.collection(collection)) {
      const sid = slotId(slot);
      if (sid && !model.byId.has(sid)) model.byId.set(sid, [collection, slot]);
    }
  }

  for (const relation of inner.slot_relations ?? []) {
    const source = relation.source_slot_id;
    const target = relation.target_slot_id;
    if (!source || !target) continue;
    model.relations.push(relation);
    if (!model._bySource.has(source)) model._bySource.set(source, []);
    model._bySource.get(source).push(relation);
    if (!model._byTarget.has(target)) model._byTarget.set(target, []);
    model._byTarget.get(target).push(relation);
  }
  return model;
}

export function loadModel(path) {
  let text = readFileSync(path, "utf8");
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1); // utf-8-sig
  return loadModelFromObject(JSON.parse(text));
}
