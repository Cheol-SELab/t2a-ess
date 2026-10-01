/**
 * Convert the T2A-ESS state axis to standard SysML v2 `state def` text.
 * JS port of src/t2a_sysml/state_converter.py — output must be byte-identical
 * to the Python state converter for the same input (see test/parity.test.js).
 *
 *   package '<title>' {
 *       private import ScalarValues::*;
 *       attribute def '<event>';                        // triggers a transition
 *       state def '<scenario>'[ parallel] {
 *           attribute '<constraint>' : Boolean;         // transition guard
 *           state '<region>' {
 *               entry; then '<initial state>';
 *               state '<situation>' { doc /* var = value; ... *\/ }
 *               transition '<label>'
 *                   first '<from>'
 *                   accept '<event>'
 *                   if '<guard>'
 *                   do action '<causes action>'
 *                   then '<to>';
 *           }
 *       }
 *   }
 *
 * Regions are connected components of situations via resolved
 * from/to_situation transitions. `stateGraph(model)` exposes the same
 * derivation as a renderable IR (used by state_diagram.js for the HTML
 * state machine diagram); the text emitter consumes it.
 */
import { loadModel } from "./model.js";
import { clean, q, labelOf, uniqueLabels } from "./converter.js";

export const STATE_CONVERTER_VERSION = "t2a_sysml.state.v0.1";

const docSafe = (text) => String(text).replace(/\*\//g, "");

/** transition_id -> [fromSituationId, toSituationId], both situations. */
function resolvedTransitions(model, sitIds) {
  const resolved = new Map();
  for (const transition of model.collection("transitions")) {
    const tid = model.slotId(transition);
    const froms = model.targets(tid, "from_situation").filter((s) => sitIds.has(s));
    const tos = model.targets(tid, "to_situation").filter((s) => sitIds.has(s));
    if (froms.length && tos.length) resolved.set(tid, [froms[0], tos[0]]);
  }
  return resolved;
}

/** Label = the state variable(s) shared by the most states in the region. */
function regionLabel(model, stateIds) {
  const counts = new Map();
  const allVars = [];
  for (const sid of stateIds) {
    const variables = [];
    for (const svid of model.targets(sid, "has_state_value")) {
      const entry = model.byId.get(svid);
      if (entry && entry[0] === "state_values") {
        const v = clean(entry[1].variable || "");
        if (v && !variables.includes(v)) variables.push(v);
      }
    }
    for (const v of variables) {
      counts.set(v, (counts.get(v) ?? 0) + 1);
      if (!allVars.includes(v)) allVars.push(v);
    }
  }
  if (!allVars.length) return null;
  const best = Math.max(...counts.values());
  const chosen = best >= 2 ? allVars.filter((v) => counts.get(v) === best) : allVars;
  return [...new Set(chosen)].sort().join(" / ");
}

/**
 * Derive the state-view IR from the model: regions (connected components via
 * resolved transitions), per-state doc values, trigger/guard/causes labels.
 * Pure — no I/O. The text emitter and the SVG/HTML renderer both consume this.
 */
export function stateGraph(model) {
  const sit = uniqueLabels(model.collection("situations"), (s) => model.slotId(s), "State");
  const tr = uniqueLabels(model.collection("transitions"), (s) => model.slotId(s), "Transition");
  const evt = uniqueLabels(model.collection("events"), (s) => model.slotId(s), "Event");
  const con = uniqueLabels(model.collection("constraints"), (s) => model.slotId(s), "Constraint");
  const act = uniqueLabels(model.collection("actions"), (s) => model.slotId(s), "Function");

  const resolved = resolvedTransitions(model, sit);

  // events that trigger an emitted transition (events collection order)
  const events = [...evt.keys()]
    .filter((eid) => model.targets(eid, "triggers").some((t) => resolved.has(t)))
    .map((id) => ({ id, label: evt.get(id) }));

  // guards: constraints targeted by constrained_by from an emitted transition
  const guards = [...con.keys()]
    .filter((cid) =>
      model.relations.some(
        (r) => r.relation_type === "constrained_by" && resolved.has(r.source_slot_id) && r.target_slot_id === cid,
      ),
    )
    .map((id) => ({ id, label: con.get(id) }));

  // union-find over situations
  const order = new Map([...sit.keys()].map((sid, i) => [sid, i]));
  const parent = new Map([...sit.keys()].map((sid) => [sid, sid]));
  const find = (x) => {
    while (parent.get(x) !== x) {
      parent.set(x, parent.get(parent.get(x)));
      x = parent.get(x);
    }
    return x;
  };
  for (const [a, b] of resolved.values()) parent.set(find(a), find(b));
  const byRoot = new Map();
  for (const sid of sit.keys()) {
    const root = find(sid);
    if (!byRoot.has(root)) byRoot.set(root, []);
    byRoot.get(root).push(sid);
  }

  const initial = (states) => {
    const inRegion = new Set(states);
    const hasIn = new Set(
      [...resolved.values()].filter(([a, b]) => inRegion.has(a) && inRegion.has(b)).map(([, b]) => b),
    );
    const pool = states.filter((s) => !hasIn.has(s));
    const candidates = pool.length ? pool : states;
    let best = null;
    let bestKey = null;
    for (const sid of candidates) {
      let epOrder = Infinity;
      for (const owner of model.sources(sid, "has_situation")) {
        const entry = model.byId.get(owner);
        if (entry && entry[0] === "episodes") {
          const o = entry[1].order_index ?? Infinity;
          if (o < epOrder) epOrder = o;
        }
      }
      const key = [epOrder, order.get(sid)];
      if (bestKey === null || key[0] < bestKey[0] || (key[0] === bestKey[0] && key[1] < bestKey[1])) {
        best = sid;
        bestKey = key;
      }
    }
    return best;
  };

  const regions = [];
  for (const states of byRoot.values()) {
    const inRegion = new Set(states);
    const transitions = [...resolved.keys()].filter((tid) => {
      const [a, b] = resolved.get(tid);
      return inRegion.has(a) && inRegion.has(b);
    });
    regions.push({
      states: states.map((id) => ({
        id,
        label: sit.get(id),
        owners: model
          .sources(id, "has_situation")
          .filter((o) => model.byId.has(o))
          .map((o) => labelOf(model.byId.get(o)[1]) || o),
        values: model
          .targets(id, "has_state_value")
          .map((v) => model.byId.get(v))
          .filter((e) => e && e[0] === "state_values")
          .map((e) => ({
            variable: clean(e[1].variable || ""),
            value: e[1].value,
            unit: e[1].unit ? clean(e[1].unit) : "",
          })),
      })),
      transitions: transitions.map((tid) => {
        const [a, b] = resolved.get(tid);
        return {
          id: tid,
          label: tr.get(tid),
          from: a,
          to: b,
          events: model
            .sources(tid, "triggers")
            .filter((e) => evt.has(e))
            .map((e) => evt.get(e)),
          guards: model
            .targets(tid, "constrained_by")
            .filter((c) => con.has(c))
            .map((c) => con.get(c)),
          actions: model
            .sources(tid, "causes")
            .filter((c) => act.has(c))
            .map((c) => act.get(c)),
        };
      }),
    });
  }
  regions.forEach((r) => {
    r.initial = initial(r.states.map((s) => s.id));
  });
  regions.sort((x, y) => order.get(x.initial) - order.get(y.initial));

  // region labels: shared-variable label, "#2" dedupe across regions
  const used = new Map();
  regions.forEach((r, i) => {
    const base = regionLabel(model, r.states.map((s) => s.id)) ?? `Region ${i + 1}`;
    const count = used.get(base) ?? 0;
    used.set(base, count + 1);
    r.id = `r${i}`;
    r.label = count === 0 ? base : `${base} #${count + 1}`;
  });

  const scenarios = model.collection("scenarios");
  return {
    title: clean(model.title),
    scenario: (scenarios.length ? labelOf(scenarios[0]) : "") || model.title,
    parallel: regions.length > 1,
    events,
    guards,
    regions,
  };
}

/** Emit the SysML v2 text for a stateGraph IR. */
function emitText(g) {
  const L = [
    `package ${q(g.title)} {`,
    "    private import ScalarValues::*;",
    "",
    `    // ${g.title}`,
    `    // Generated from T2A-ESS by ${STATE_CONVERTER_VERSION}`,
  ];

  if (!g.regions.length) {
    L.push("");
    L.push(`    state def ${q(g.scenario)};`);
    L.push("}");
    return L.join("\n") + "\n";
  }

  if (g.events.length) {
    L.push("");
    L.push("    // events that trigger transitions (accept payloads)");
    for (const e of g.events) L.push(`    attribute def ${q(e.label)};`);
  }
  L.push("");

  L.push(`    state def ${q(g.scenario)}${g.parallel ? " parallel" : ""} {`);
  if (g.guards.length) {
    L.push("        // guards (constrained_by on transitions)");
    for (const c of g.guards) L.push(`        attribute ${q(c.label)} : Boolean;`);
    L.push("");
  }

  g.regions.forEach((region, ri) => {
    const sit = new Map(region.states.map((s) => [s.id, s.label]));
    const pad = "        ";
    L.push(`${pad}state ${q(region.label)} {`);
    L.push(`${pad}    entry; then ${q(sit.get(region.initial))};`);
    L.push("");
    for (const s of region.states) {
      if (s.owners.length) L.push(`${pad}    // has_situation: ${s.owners.join(", ")}`);
      if (!s.values.length) {
        L.push(`${pad}    state ${q(s.label)};`);
        continue;
      }
      const doc = s.values
        .map((v) => `${v.variable} = ${v.value}` + (v.unit ? ` ${v.unit}` : ""))
        .join("; ");
      L.push(`${pad}    state ${q(s.label)} {`);
      L.push(`${pad}        doc /* ${docSafe(doc)} */`);
      L.push(`${pad}    }`);
    }
    if (region.transitions.length) {
      L.push("");
      for (const t of region.transitions) {
        const count = Math.max(t.events.length, 1);
        for (let n = 0; n < count; n += 1) {
          const label = n === 0 ? t.label : `${t.label} #${n + 1}`;
          for (const extra of t.actions.slice(1)) L.push(`${pad}    // causes: ${extra}`);
          L.push(`${pad}    transition ${q(label)}`);
          L.push(`${pad}        first ${q(sit.get(t.from))}`);
          if (t.events.length) L.push(`${pad}        accept ${q(t.events[n])}`);
          if (t.guards.length) L.push(`${pad}        if ${t.guards.map(q).join(" and ")}`);
          if (t.actions.length) L.push(`${pad}        do action ${q(t.actions[0])}`);
          L.push(`${pad}        then ${q(sit.get(t.to))};`);
        }
      }
    }
    L.push(`${pad}}`);
    if (ri !== g.regions.length - 1) L.push("");
  });
  L.push("    }");
  L.push("}");
  return L.join("\n") + "\n";
}

export function convertStateModel(model) {
  return emitText(stateGraph(model));
}

export function convertStateFile(path) {
  return convertStateModel(loadModel(path));
}

export function stateSummary(model) {
  const g = stateGraph(model);
  return {
    regions: g.regions.length,
    states: g.regions.reduce((n, r) => n + r.states.length, 0),
    transitions: g.regions.reduce(
      (n, r) => n + r.transitions.reduce((m, t) => m + Math.max(t.events.length, 1), 0),
      0,
    ),
  };
}
