/**
 * Convert an indexed T2A-ESS model to selab-effbd-editor EFFBD SysML.
 * JS port of src/t2a_sysml/converter.py — output must be byte-identical to the
 * Python converter for the same input (see test/parity.test.js).
 *
 *   #Performer  part '<performer>' : Performer;              (top level)
 *   #Function   action '<scenario>' {                        (root function)
 *       #Function action '<action>' {
 *           in  item '<item>' : ItemInputEdge;
 *           out item '<item>' : ItemOutputEdge;
 *       }
 *       item '<item>';
 *       allocate '<action>' to '<performer>';                (performed_by)
 *       succession first start then '<first>';
 *       succession first '<A>' then '<B>';                   (flows / temporal_before)
 *       succession first '<last>' then done;
 *       flow from '<A>'.'<item>' to '<B>'.'<item>';          (object flows)
 *   }
 */
import { loadModel } from "./model.js";

export const CONVERTER_VERSION = "t2a_sysml.effbd.v0.3";

const DEFS =
  "item def ItemInputEdge;\n" +
  "item def ItemOutputEdge;\n" +
  "item def TriggeringItemInputEdge;\n" +
  "part def Performer;\n";

function header(immTags) {
  const imports = immTags ? "private import IMMBaseSchema::*;\n" : "";
  return (
    `${imports}private import ScalarValues::*;\n\n` +
    "// self-contained EFFBD edge/performer definitions (editor-injected set)\n" +
    DEFS
  );
}

const BAD_NAME = /['\r\n\\]/g;

export function clean(label) {
  return String(label).replace(BAD_NAME, "").trim();
}

export const q = (label) => `'${label}'`;

/** Display label of a slot: `label` (T2A-ESS), then `title`, then legacy `name`. */
export const labelOf = (slot) => clean(slot.label || slot.title || slot.name || "");

/** Map slot_id -> a unique, quote-safe label within this collection. */
export function uniqueLabels(slots, slotIdFn, fallback) {
  const mapping = new Map();
  const used = new Map();
  slots.forEach((slot, index) => {
    const sid = slotIdFn(slot);
    if (sid === null) return;
    const label = labelOf(slot) || `${fallback}_${index + 1}`;
    const count = used.get(label) ?? 0;
    used.set(label, count + 1);
    mapping.set(sid, count === 0 ? label : `${label} #${count + 1}`);
  });
  return mapping;
}

const uniq = (arr) => [...new Set(arr)];

/** `base`, or `base #k` (k = 2, 3, ...) — the first name not in `taken`. */
function freeName(base, taken) {
  if (!taken.has(base)) return base;
  let k = 2;
  while (taken.has(`${base} #${k}`)) k += 1;
  return `${base} #${k}`;
}

class EffbdConverter {
  constructor(model, immTags = false) {
    this.m = model;
    this.immTags = immTags;
    const sid = (s) => model.slotId(s);
    this.perf = uniqueLabels(model.collection("performers"), sid, "Performer");
    this.act = uniqueLabels(model.collection("actions"), sid, "Function");
    this.item = uniqueLabels(model.collection("items"), sid, "Item");
    // fork/join names must be unique across the whole file: the EFFBD editor keys
    // nodes by quoted label globally, so per-group numbering collides across
    // sibling episodes ("node is outside the parent region envelope").
    this._forkSeq = 0;
    this._joinSeq = 0;
    this._rootLabel = "";
    this._outPort = null;
  }

  // --- action item ports ------------------------------------------------------
  _ports(actionId) {
    const outs = this.m.targets(actionId, "produces_item").filter((i) => this.item.has(i));
    const ins = this.m.targets(actionId, "uses_item").filter((i) => this.item.has(i));
    for (const i of this.m.targets(actionId, "provided_to")) {
      if (this.item.has(i) && !ins.includes(i)) ins.push(i);
    }
    return [outs, ins];
  }

  /**
   * [outs, ins] of an action including the ports that object flows need — a
   * cross-episode `flow from ep.A.item to ep.B.item` needs both endpoint ports
   * declared or the editor/LSP cannot resolve the target path.
   */
  _allPorts(actionId) {
    let [outs, ins] = this._ports(actionId);
    const obj = this._objectFlows();
    outs = uniq([...outs, ...obj.filter(([a]) => a === actionId).map(([, , i]) => i)]);
    ins = uniq([...ins, ...obj.filter(([, b]) => b === actionId).map(([, , i]) => i)]);
    return [outs, ins];
  }

  /**
   * Name of the output port of `actionId` for item `iid`. An action that uses and
   * produces the same item (a relay) cannot have two ports of that name in one
   * namespace, so its output port gets `<item> #k` and names the item as payload.
   */
  _outPortName(actionId, iid) {
    if (this._outPort === null) {
      this._outPort = new Map();
      for (const action of this.m.collection("actions")) {
        const aid = this.m.slotId(action);
        const [outs, ins] = this._allPorts(aid);
        const taken = new Set([...ins, ...outs].map((i) => this.item.get(i)));
        for (const i of outs) {
          if (!ins.includes(i)) continue;
          const name = freeName(this.item.get(i), taken);
          taken.add(name);
          this._outPort.set(`${aid}\u0000${i}`, name);
        }
      }
    }
    return this._outPort.get(`${actionId}\u0000${iid}`) ?? this.item.get(iid);
  }

  _outPortLine(pad, actionId, iid) {
    const name = this._outPortName(actionId, iid);
    if (name === this.item.get(iid)) return `${pad}    out item ${q(name)} : ItemOutputEdge;`;
    // payload by subsetting (the editor reads it only from an untyped port)
    return `${pad}    out item ${q(name)} :> ${q(this._rootLabel)}::${q(this.item.get(iid))};`;
  }

  _performersOf(actionId) {
    return this.m.targets(actionId, "performed_by").filter((p) => this.perf.has(p));
  }

  // --- ordering ---------------------------------------------------------------
  /** Directed action->action edges: [a, b, note, flowId|null]. */
  _edges() {
    const edges = [];
    const seen = new Set();
    const add = (a, b, note, flowId) => {
      const key = `${a}\u0000${b}`;
      if (this.act.has(a) && this.act.has(b) && a !== b && !seen.has(key)) {
        seen.add(key);
        edges.push([a, b, note, flowId]);
      }
    };
    for (const flow of this.m.collection("flows")) {
      const fid = this.m.slotId(flow);
      for (const a of this.m.targets(fid, "flow_source")) {
        for (const b of this.m.targets(fid, "flow_target")) {
          add(a, b, clean(flow.label || ""), fid);
        }
      }
    }
    for (const rel of this.m.relations) {
      if (rel.relation_type === "temporal_before") {
        add(rel.source_slot_id, rel.target_slot_id, "temporal_before", null);
      }
    }
    return edges;
  }

  /** flow_id -> control slot, from `control controls_flow flow` relations. */
  _flowControls() {
    const mapping = new Map();
    for (const rel of this.m.relations) {
      if (rel.relation_type !== "controls_flow") continue;
      const entry = this.m.byId.get(rel.source_slot_id);
      if (entry && entry[0] === "controls") mapping.set(rel.target_slot_id, entry[1]);
    }
    return mapping;
  }

  /**
   * Insert fork(concurrency)/join nodes by inferring branch sets from the graph.
   * Unguarded multi-outgoing -> fork; multi-incoming -> join. Guarded edges stay
   * as decision (guarded) successions. Returns [forkNames, joinNames, succLines].
   *
   * Nodes are string keys: "kw:start" | "kw:done" | "A:<action_id>" | "F:<name>" | "J:<name>".
   * `adj` is an insertion-ordered Map, mirroring Python dict semantics.
   */
  _controlFlow(edges, guardAttr, flowControls, actionIds, hasIn, hasOut) {
    const START = "kw:start";
    const DONE = "kw:done";
    const adj = new Map();
    const akey = (aid) => `A:${aid}`;
    const add = (u, v, guard = null) => {
      if (!adj.has(u)) adj.set(u, []);
      adj.get(u).push([v, guard]);
    };

    const starts = actionIds.filter((a) => !hasIn.has(a));
    const sinks = actionIds.filter((a) => !hasOut.has(a));
    for (const a of starts) add(START, akey(a));
    for (const [a, b, , fid] of edges) {
      const control = fid ? flowControls.get(fid) : undefined;
      const guard = control ? guardAttr.get(this.m.slotId(control)) : null;
      add(akey(a), akey(b), guard ?? null);
    }
    for (const a of sinks) add(akey(a), DONE);

    const forks = [];
    const joins = [];

    // fork pass: group unguarded multi-outgoing edges through a fork
    for (const u of [...adj.keys()]) {
      const es = adj.get(u);
      const unguarded = es.filter((e) => e[1] === null);
      if (unguarded.length > 1) {
        this._forkSeq += 1;
        const name = `New Start Concurrency_${this._forkSeq}`;
        forks.push(name);
        const fk = `F:${name}`;
        for (const e of unguarded) es.splice(es.indexOf(e), 1);
        es.push([fk, null]);
        adj.set(fk, unguarded.map((e) => [e[0], null]));
      }
    }

    // join pass: group multi-incoming edges through a join
    const predecessors = () => {
      const preds = new Map();
      for (const [src, es] of adj) {
        for (const [target, guard] of es) {
          if (!preds.has(target)) preds.set(target, []);
          preds.get(target).push([src, guard]);
        }
      }
      return preds;
    };

    for (const [w, ps] of [...predecessors()]) {
      if (ps.length > 1) {
        this._joinSeq += 1;
        const name = `New End Concurrency_${this._joinSeq}`;
        joins.push(name);
        const jn = `J:${name}`;
        for (const [src, guard] of ps) {
          for (const e of adj.get(src) ?? []) {
            if (e[0] === w && e[1] === guard) {
              e[0] = jn;
              break;
            }
          }
        }
        adj.set(jn, [[w, null]]);
      }
    }

    const ref = (node) => {
      const kind = node.slice(0, node.indexOf(":"));
      const val = node.slice(node.indexOf(":") + 1);
      if (kind === "kw") return val;
      if (kind === "A") return q(this.act.get(val));
      return q(val); // F / J
    };

    const lines = [];
    for (const [u, es] of adj) {
      for (const [target, guard] of es) {
        const cond = guard ? ` if ${q(guard)} == true` : "";
        lines.push(`succession first ${ref(u)}${cond} then ${ref(target)};`);
      }
    }
    return [forks, joins, lines];
  }

  /** [producerAction, consumerAction, item] triples from object flows. */
  _objectFlows() {
    const triples = [];
    for (const flow of this.m.collection("flows")) {
      if (!String(flow.flow_kind ?? "").includes("object")) continue;
      const fid = this.m.slotId(flow);
      const items = this.m.targets(fid, "carries_item").filter((i) => this.item.has(i));
      const srcs = this.m.targets(fid, "flow_source").filter((a) => this.act.has(a));
      const tgts = this.m.targets(fid, "flow_target").filter((b) => this.act.has(b));
      for (const i of items) for (const a of srcs) for (const b of tgts) triples.push([a, b, i]);
    }
    return triples;
  }

  // --- grouped emission -------------------------------------------------------
  /** control_id -> boolean guard attr label, for controls governing these edges. */
  _guardAttrs(edges, reserved = new Set()) {
    // `reserved`: other member names of the same namespace (actions, flat-mode items)
    const flowControls = this._flowControls();
    const guardAttr = new Map();
    const used = new Map();
    for (const [, , , fid] of edges) {
      const control = fid ? flowControls.get(fid) : undefined;
      if (!control) continue;
      const cid = this.m.slotId(control);
      if (guardAttr.has(cid)) continue;
      const guards = control.guard_texts || [];
      const base = (guards.length ? clean(guards[0]) : labelOf(control) || clean(cid)) || "guard";
      const count = used.get(base) ?? (reserved.has(base) ? 1 : 0);
      used.set(base, count + 1);
      guardAttr.set(cid, count === 0 ? base : `${base} #${count + 1}`);
    }
    return [guardAttr, flowControls];
  }

  /**
   * Emit actions + fork/join + guards + allocations + successions + intra-group
   * object flows for one action subset, at the given indent (in 4-space units).
   */
  _emitGroup(aids, indent, reserved = new Set()) {
    const pad = "    ".repeat(indent);
    const aidset = new Set(aids);
    const obj = this._objectFlows().filter(([a, b]) => aidset.has(a) && aidset.has(b));

    const L = [];
    for (const aid of aids) {
      const [outs, ins] = this._allPorts(aid);
      if (this.immTags) L.push(`${pad}#Function`);
      const head = `${pad}action ${q(this.act.get(aid))}`;
      if (!outs.length && !ins.length) {
        L.push(`${head};`);
        continue;
      }
      L.push(`${head} {`);
      for (const i of ins) L.push(`${pad}    in item ${q(this.item.get(i))} : ItemInputEdge;`);
      for (const i of outs) L.push(this._outPortLine(pad, aid, i));
      L.push(`${pad}}`);
    }
    L.push("");

    const edges = this._edges().filter(([a, b]) => aidset.has(a) && aidset.has(b));
    const hasIn = new Set(edges.map((e) => e[1]));
    const hasOut = new Set(edges.map((e) => e[0]));
    const names = new Set([...reserved, ...aids.map((a) => this.act.get(a))]);
    const [guardAttr, flowControls] = this._guardAttrs(edges, names);
    const [forks, joins, succ] = this._controlFlow(edges, guardAttr, flowControls, [...aids], hasIn, hasOut);

    for (const name of forks) L.push(`${pad}fork ${q(name)};`);
    for (const name of joins) L.push(`${pad}join ${q(name)};`);
    if (forks.length || joins.length) L.push("");
    for (const [cid, attr] of guardAttr) {
      const ct = this.m.byId.get(cid)[1].control_type;
      L.push(`${pad}attribute ${q(attr)} : ScalarValues::Boolean;  // control: ${ct}`);
    }
    if (guardAttr.size) L.push("");
    for (const aid of aids) {
      for (const pid of this._performersOf(aid)) {
        L.push(`${pad}allocate ${q(this.act.get(aid))} to ${q(this.perf.get(pid))};`);
      }
    }
    L.push("");
    for (const line of succ) L.push(`${pad}${line}`);
    if (obj.length) {
      L.push("");
      for (const [a, b, i] of obj) {
        L.push(
          `${pad}flow from ${q(this.act.get(a))}.${q(this._outPortName(a, i))} ` +
            `to ${q(this.act.get(b))}.${q(this.item.get(i))};`,
        );
      }
    }
    return L;
  }

  /**
   * [[episodeSlot, [actionId]]] ordered by order_index, iff episodes fully cover
   * the actions; else null (falls back to a flat function).
   */
  _episodeGroups() {
    const episodes = this.m.collection("episodes");
    if (!episodes.length) return null;
    const actionIds = new Set(this.m.collection("actions").map((a) => this.m.slotId(a)));
    const groups = [];
    const assigned = new Set();
    const sorted = [...episodes].sort((x, y) => (x.order_index ?? 0) - (y.order_index ?? 0)); // stable
    for (const episode of sorted) {
      const eid = this.m.slotId(episode);
      const aids = [];
      // canonical first, then the legacy spellings for backward compatibility
      for (const t of this.m.targets(eid, "contains_action")) {
        if (actionIds.has(t) && !aids.includes(t) && !assigned.has(t)) aids.push(t);
      }
      for (const rel of this.m.outRelations(eid)) {
        const rt = rel.relation_type;
        if (rt === "custom" && rel.custom_relation_type != null && rel.custom_relation_type !== "contains_action") {
          continue;
        }
        if (rt === "custom" || rt === "has_action" || rt === "contains") {
          const t = rel.target_slot_id;
          if (actionIds.has(t) && !aids.includes(t) && !assigned.has(t)) aids.push(t);
        }
      }
      for (const a of aids) assigned.add(a);
      if (aids.length) groups.push([episode, aids]);
    }
    if (assigned.size !== actionIds.size || [...actionIds].some((a) => !assigned.has(a)) || !groups.length) {
      return null;
    }
    return groups;
  }

  _usedItems() {
    const used = new Set();
    for (const action of this.m.collection("actions")) {
      const [o, n] = this._ports(this.m.slotId(action));
      for (const i of [...o, ...n]) used.add(i);
    }
    for (const [, , i] of this._objectFlows()) used.add(i);
    return used;
  }

  // --- emit -------------------------------------------------------------------
  convert() {
    const scenarios = this.m.collection("scenarios");
    const scenarioLabel = (scenarios.length ? labelOf(scenarios[0]) : "") || this.m.title;
    const L = [header(this.immTags), ""];
    L.push(`// ${this.m.title}`);
    L.push(`// Generated from T2A-ESS by ${CONVERTER_VERSION}`);
    L.push("");

    // top-level performers
    for (const performer of this.m.collection("performers")) {
      const pid = this.m.slotId(performer);
      if (this.immTags) L.push("#Performer");
      L.push(`part ${q(this.perf.get(pid))} : Performer;`);
    }
    L.push("");

    const usedItems = this._usedItems();
    const groups = this._episodeGroups();
    // members of the root function share one namespace with its item declarations
    const itemNames = new Set(this.m.collection("items").map((i) => this.m.slotId(i))
      .filter((iid) => usedItems.has(iid)).map((iid) => this.item.get(iid)));
    this._rootLabel = scenarioLabel;

    if (this.immTags) L.push("#Function");
    L.push(`action ${q(scenarioLabel)} {`);

    if (groups) {
      // nested: each episode is a #Function action with its own start->done body
      const epLabel = new Map();
      const epNames = [];
      const taken = new Set(itemNames);
      for (const [episode, aids] of groups) {
        const label = freeName(labelOf(episode) || this.m.slotId(episode), taken);
        taken.add(label);
        epNames.push(label);
        for (const aid of aids) epLabel.set(aid, label);
        if (this.immTags) L.push("    #Function");
        L.push(`    action ${q(label)} {`);
        L.push(...this._emitGroup(aids, 2));
        L.push("    }");
      }
      L.push("");
      for (const item of this.m.collection("items")) {
        const iid = this.m.slotId(item);
        if (usedItems.has(iid)) L.push(`    item ${q(this.item.get(iid))};`);
      }
      if (usedItems.size) L.push("");
      // episode sequencing: start -> ep1 -> ... -> epN -> done
      let prev = null;
      for (const label of epNames) {
        const src = prev === null ? "start" : q(prev);
        L.push(`    succession first ${src} then ${q(label)};`);
        prev = label;
      }
      if (prev !== null) L.push(`    succession first ${q(prev)} then done;`);
      // cross-episode object flows (dotted path: episode.action.item)
      const cross = this._objectFlows().filter(([a, b]) => epLabel.get(a) !== epLabel.get(b));
      if (cross.length) {
        L.push("");
        for (const [a, b, i] of cross) {
          L.push(
            `    flow from ${q(epLabel.get(a))}.${q(this.act.get(a))}.${q(this._outPortName(a, i))} ` +
              `to ${q(epLabel.get(b))}.${q(this.act.get(b))}.${q(this.item.get(i))};`,
          );
        }
      }
    } else {
      // flat: one function containing all actions (actions and items share its namespace)
      const allAids = this.m.collection("actions").map((a) => this.m.slotId(a));
      const taken = new Set(itemNames);
      for (const aid of allAids) {
        const name = freeName(this.act.get(aid), taken);
        taken.add(name);
        this.act.set(aid, name);
      }
      L.push(...this._emitGroup(allAids, 1, itemNames));
      L.push("");
      for (const item of this.m.collection("items")) {
        const iid = this.m.slotId(item);
        if (usedItems.has(iid)) L.push(`    item ${q(this.item.get(iid))};`);
      }
    }

    L.push("}");
    return L.join("\n") + "\n";
  }
}

export function convertModel(model, { immTags = true } = {}) {
  return new EffbdConverter(model, immTags).convert();
}

export function convertFile(path, { immTags = true } = {}) {
  return convertModel(loadModel(path), { immTags });
}
