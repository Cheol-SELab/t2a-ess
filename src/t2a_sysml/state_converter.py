"""Convert the T2A-ESS state axis to standard SysML v2 ``state def`` text.

Emits plain standard SysML v2 (no IMM tags; SysML-v2-Release training/23 style):

  package '<title>' {
      private import ScalarValues::*;
      attribute def '<event>';                        // triggers a transition
      state def '<scenario>'[ parallel] {
          attribute '<constraint>' : Boolean;         // transition guard
          state '<region>' {
              entry; then '<initial state>';
              state '<situation>' { doc /* var = value; ... */ }
              transition '<label>'
                  first '<from>'
                  accept '<event>'
                  if '<guard>'
                  do action '<causes action>'
                  then '<to>';
          }
      }
  }

Regions are connected components of situations via resolved from/to_situation
transitions. Output must be byte-identical to the JS port
(src/t2a_js/t2a_sysml/state_converter.js).
"""

from __future__ import annotations

from pathlib import Path

from .converter import _clean, _label, _q, _unique_labels
from .model import T2AModel, load_model

STATE_CONVERTER_VERSION = "t2a_sysml.state.v0.1"


def _doc_safe(text: str) -> str:
    return str(text).replace("*/", "")


class _StateConverter:
    def __init__(self, model: T2AModel) -> None:
        self.m = model
        sid = model.slot_id
        self.sit = _unique_labels(model.collection("situations"), sid, "State")
        self.tr = _unique_labels(model.collection("transitions"), sid, "Transition")
        self.evt = _unique_labels(model.collection("events"), sid, "Event")
        self.con = _unique_labels(model.collection("constraints"), sid, "Constraint")
        self.act = _unique_labels(model.collection("actions"), sid, "Function")

    # --- relation views -------------------------------------------------------
    def _resolved_transitions(self):
        """transition_id -> (from_situation_id, to_situation_id), both situations."""
        resolved: dict[str, tuple[str, str]] = {}
        for transition in self.m.collection("transitions"):
            tid = self.m.slot_id(transition)
            froms = [s for s in self.m.targets(tid, "from_situation") if s in self.sit]
            tos = [s for s in self.m.targets(tid, "to_situation") if s in self.sit]
            if froms and tos:
                resolved[tid] = (froms[0], tos[0])
        return resolved

    def _regions(self, resolved):
        """Union-find over situations; returns [region] where each region is a dict
        {states: [situation_id, collection order], transitions: [transition_id]}."""
        parent = {sid: sid for sid in self.sit}
        order = {sid: i for i, sid in enumerate(self.sit)}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for a, b in resolved.values():
            parent[find(a)] = find(b)

        by_root: dict[str, list[str]] = {}
        for sid in self.sit:  # situations collection order
            by_root.setdefault(find(sid), []).append(sid)

        regions = []
        for states in by_root.values():
            in_region = set(states)
            transitions = [
                tid for tid, (a, b) in resolved.items() if a in in_region and b in in_region
            ]
            regions.append({"states": states, "transitions": transitions})

        for region in regions:
            region["initial"] = self._initial(region, resolved, order)
        regions.sort(key=lambda r: order[r["initial"]])
        return regions

    def _initial(self, region, resolved, order_index):
        """Initial state: no incoming resolved transition in the region, earliest
        owning episode (has_situation) order_index, then collection index."""
        in_region = set(region["states"])
        has_in = {b for a, b in resolved.values() if a in in_region and b in in_region}
        candidates = [s for s in region["states"] if s not in has_in] or region["states"]

        def key(sid):
            ep_order = float("inf")
            for owner in self.m.sources(sid, "has_situation"):
                entry = self.m.by_id.get(owner)
                if entry and entry[0] == "episodes":
                    ep_order = min(ep_order, entry[1].get("order_index", float("inf")))
            return (ep_order, order_index[sid])

        return min(candidates, key=key)

    def _region_label(self, region):
        """Label = the state variable(s) shared by the most states in the region."""
        counts: dict[str, int] = {}
        all_vars: list[str] = []
        for sid in region["states"]:
            variables = []
            for svid in self.m.targets(sid, "has_state_value"):
                entry = self.m.by_id.get(svid)
                if entry and entry[0] == "state_values":
                    var = _clean(entry[1].get("variable") or "")
                    if var and var not in variables:
                        variables.append(var)
            for var in variables:
                counts[var] = counts.get(var, 0) + 1
                if var not in all_vars:
                    all_vars.append(var)
        if not all_vars:
            return None
        best = max(counts.values())
        chosen = [v for v in all_vars if counts[v] == best] if best >= 2 else all_vars
        return " / ".join(sorted(set(chosen)))

    # --- emission ---------------------------------------------------------------
    def convert(self) -> str:
        scenarios = self.m.collection("scenarios")
        scenario_label = (_label(scenarios[0]) if scenarios else "") or self.m.title
        L: list[str] = [
            f"package {_q(_clean(self.m.title))} {{",
            "    private import ScalarValues::*;",
            "",
            f"    // {self.m.title}",
            f"    // Generated from T2A-ESS by {STATE_CONVERTER_VERSION}",
        ]

        resolved = self._resolved_transitions()
        if not self.sit:
            L.append("")
            L.append(f"    state def {_q(scenario_label)};")
            L.append("}")
            return "\n".join(L) + "\n"

        # events that trigger an emitted transition (events collection order)
        trigger_events = [
            eid for eid in self.evt
            if any(t in resolved for t in self.m.targets(eid, "triggers"))
        ]
        if trigger_events:
            L.append("")
            L.append("    // events that trigger transitions (accept payloads)")
            for eid in trigger_events:
                L.append(f"    attribute def {_q(self.evt[eid])};")
        L.append("")

        # guard attributes: constraints targeted by constrained_by from a transition
        guard_ids = [cid for cid in self.con if any(
            r.get("relation_type") == "constrained_by"
            and r["source_slot_id"] in resolved
            and r["target_slot_id"] == cid
            for r in self.m.relations
        )]

        regions = self._regions(resolved)
        region_labels = {}
        used: dict[str, int] = {}
        for i, region in enumerate(regions):
            base = self._region_label(region) or f"Region {i + 1}"
            count = used.get(base, 0)
            used[base] = count + 1
            region_labels[i] = base if count == 0 else f"{base} #{count + 1}"

        parallel = " parallel" if len(regions) > 1 else ""
        L.append(f"    state def {_q(scenario_label)}{parallel} {{")
        if guard_ids:
            L.append("        // guards (constrained_by on transitions)")
            for cid in guard_ids:
                L.append(f"        attribute {_q(self.con[cid])} : Boolean;")
            L.append("")

        for ri, region in enumerate(regions):
            pad = "        "
            L.append(f"{pad}state {_q(region_labels[ri])} {{")
            L.append(f"{pad}    entry; then {_q(self.sit[region['initial']])};")
            L.append("")
            for sid in region["states"]:
                owners = [
                    _label(self.m.by_id[o][1]) or o
                    for o in self.m.sources(sid, "has_situation")
                    if o in self.m.by_id
                ]
                if owners:
                    L.append(f"{pad}    // has_situation: {', '.join(owners)}")
                values = [
                    self.m.by_id[v][1]
                    for v in self.m.targets(sid, "has_state_value")
                    if self.m.by_id.get(v) and self.m.by_id[v][0] == "state_values"
                ]
                if not values:
                    L.append(f"{pad}    state {_q(self.sit[sid])};")
                    continue
                doc = "; ".join(
                    f"{_clean(sv.get('variable') or '')} = {sv.get('value')}"
                    + (f" {_clean(sv.get('unit'))}" if sv.get("unit") else "")
                    for sv in values
                )
                L.append(f"{pad}    state {_q(self.sit[sid])} {{")
                L.append(f"{pad}        doc /* {_doc_safe(doc)} */")
                L.append(f"{pad}    }}")
            if region["transitions"]:
                L.append("")
                for tid in region["transitions"]:
                    a, b = resolved[tid]
                    events = [e for e in self.m.sources(tid, "triggers") if e in self.evt]
                    causes = [c for c in self.m.sources(tid, "causes") if c in self.act]
                    guards = [c for c in self.m.targets(tid, "constrained_by") if c in self.con]
                    count = max(len(events), 1)
                    for n in range(count):
                        label = self.tr[tid] if n == 0 else f"{self.tr[tid]} #{n + 1}"
                        for extra in causes[1:]:
                            L.append(f"{pad}    // causes: {self.act[extra]}")
                        L.append(f"{pad}    transition {_q(label)}")
                        L.append(f"{pad}        first {_q(self.sit[a])}")
                        if events:
                            L.append(f"{pad}        accept {_q(self.evt[events[n]])}")
                        if guards:
                            L.append(
                                f"{pad}        if " + " and ".join(_q(self.con[c]) for c in guards)
                            )
                        if causes:
                            L.append(f"{pad}        do action {_q(self.act[causes[0]])}")
                        L.append(f"{pad}        then {_q(self.sit[b])};")
            L.append(f"{pad}}}")
            if ri != len(regions) - 1:
                L.append("")
        L.append("    }")
        L.append("}")
        return "\n".join(L) + "\n"

    def summary(self) -> dict:
        resolved = self._resolved_transitions()
        regions = self._regions(resolved) if self.sit else []
        transition_count = sum(
            max(len([e for e in self.m.sources(tid, "triggers") if e in self.evt]), 1)
            for tid in resolved
        )
        return {
            "regions": len(regions),
            "states": len(self.sit),
            "transitions": transition_count,
        }


def convert_state_model(model: T2AModel) -> str:
    return _StateConverter(model).convert()


def convert_state_file(path: str | Path) -> str:
    return convert_state_model(load_model(path))


def state_summary(model: T2AModel) -> dict:
    return _StateConverter(model).summary()
