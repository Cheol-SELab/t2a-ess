"""Convert an indexed T2A-ESS model to selab-effbd-editor EFFBD SysML.

Targets the EFFBD editor's SysML dialect (see
data/sysml-script-files-of-effbd-editor/*.sysml):

  #Performer  part '<performer>' : Performer;              (top level)
  #Function   action '<scenario>' {                        (root function)
      #Function action '<action>' {
          in  item '<item>' : ItemInputEdge;
          out item '<item>' : ItemOutputEdge;
      }
      item '<item>';
      allocate '<action>' to '<performer>';                (performed_by)
      succession first start then '<first>';
      succession first '<A>' then '<B>';                   (flows / temporal_before)
      succession first '<last>' then done;
      flow from '<A>'.'<item>' to '<B>'.'<item>';          (object flows)
  }

Elements are named by their (quoted) T2A-ESS labels, which is what the editor keys
on. IMM metadata tags (#Performer/#Function/#Item...) and the edge/Performer defs
match the editor's injected definitions.
"""

from __future__ import annotations

import re
from pathlib import Path

from .model import T2AModel, load_model

CONVERTER_VERSION = "t2a_sysml.effbd.v0.3"

# EFFBD edge/performer defs (the editor injects these; we inline them so output is
# self-contained). The plain form omits IMMBaseSchema so it validates standalone on
# the SysML v2 Pilot parser; the --imm-tags form adds the editor's IMM metadata.
_DEFS = (
    "item def ItemInputEdge;\n"
    "item def ItemOutputEdge;\n"
    "item def TriggeringItemInputEdge;\n"
    "part def Performer;\n"
)


def _header(imm_tags: bool) -> str:
    imports = "private import IMMBaseSchema::*;\n" if imm_tags else ""
    return (
        f"{imports}private import ScalarValues::*;\n\n"
        "// self-contained EFFBD edge/performer definitions (editor-injected set)\n"
        f"{_DEFS}"
    )

_BAD_NAME = re.compile(r"['\r\n\\]")


def _clean(label: str) -> str:
    return _BAD_NAME.sub("", str(label)).strip()


def _q(label: str) -> str:
    return f"'{label}'"


def _label(slot: dict) -> str:
    """Display label of a slot: ``label`` (T2A-ESS), then ``title``, then legacy ``name``."""
    return _clean(slot.get("label") or slot.get("title") or slot.get("name") or "")


def _unique_labels(slots, slot_id_fn, fallback: str) -> dict[str, str]:
    """Map slot_id -> a unique, quote-safe label within this collection."""
    mapping: dict[str, str] = {}
    used: dict[str, int] = {}
    for index, slot in enumerate(slots):
        sid = slot_id_fn(slot)
        if sid is None:
            continue
        label = _label(slot) or f"{fallback}_{index + 1}"
        count = used.get(label, 0)
        used[label] = count + 1
        mapping[sid] = label if count == 0 else f"{label} #{count + 1}"
    return mapping


def _free_name(base: str, taken: set) -> str:
    """``base``, or ``base #k`` (k = 2, 3, ...) -- the first name not in ``taken``."""
    if base not in taken:
        return base
    k = 2
    while f"{base} #{k}" in taken:
        k += 1
    return f"{base} #{k}"


class _EffbdConverter:
    def __init__(self, model: T2AModel, imm_tags: bool = False) -> None:
        self.m = model
        self.imm_tags = imm_tags
        self.perf = _unique_labels(model.collection("performers"), model.slot_id, "Performer")
        self.act = _unique_labels(model.collection("actions"), model.slot_id, "Function")
        self.item = _unique_labels(model.collection("items"), model.slot_id, "Item")
        # fork/join names must be unique across the whole file: the EFFBD editor keys
        # nodes by quoted label globally, so per-group numbering collides across
        # sibling episodes ("node is outside the parent region envelope").
        self._fork_seq = 0
        self._join_seq = 0
        self._root_label = ""
        self._out_port: dict | None = None

    # --- action item ports ----------------------------------------------------
    def _ports(self, action_id: str):
        outs = [i for i in self.m.targets(action_id, "produces_item") if i in self.item]
        ins = [i for i in self.m.targets(action_id, "uses_item") if i in self.item]
        ins += [i for i in self.m.targets(action_id, "provided_to") if i in self.item and i not in ins]
        return outs, ins

    def _all_ports(self, action_id: str):
        """(outs, ins) of an action including the ports that object flows need -- a
        cross-episode `flow from ep.A.item to ep.B.item` needs both endpoint ports
        declared or the editor/LSP cannot resolve the target path."""
        outs, ins = self._ports(action_id)
        obj = self._object_flows()
        outs = list(dict.fromkeys(outs + [i for a, _, i in obj if a == action_id]))
        ins = list(dict.fromkeys(ins + [i for _, b, i in obj if b == action_id]))
        return outs, ins

    def _out_port_name(self, action_id: str, iid: str) -> str:
        """Name of the output port of ``action_id`` for item ``iid``. An action that uses
        and produces the same item (a relay) cannot have two ports of that name in one
        namespace, so its output port gets ``<item> #k`` and names the item as payload."""
        if self._out_port is None:
            self._out_port = {}
            for action in self.m.collection("actions"):
                aid = self.m.slot_id(action)
                outs, ins = self._all_ports(aid)
                taken = {self.item[i] for i in ins + outs}
                for i in outs:
                    if i not in ins:
                        continue
                    name = _free_name(self.item[i], taken)
                    taken.add(name)
                    self._out_port[(aid, i)] = name
        return self._out_port.get((action_id, iid), self.item[iid])

    def _out_port_line(self, pad: str, action_id: str, iid: str) -> str:
        name = self._out_port_name(action_id, iid)
        if name == self.item[iid]:
            return f"{pad}    out item {_q(name)} : ItemOutputEdge;"
        # payload by subsetting (the editor reads it only from an untyped port)
        return f"{pad}    out item {_q(name)} :> {_q(self._root_label)}::{_q(self.item[iid])};"

    def _performers_of(self, action_id: str):
        return [p for p in self.m.targets(action_id, "performed_by") if p in self.perf]

    # --- ordering -------------------------------------------------------------
    def _edges(self):
        """Directed action->action edges: (a, b, note, flow_id|None)."""
        edges: list[tuple[str, str, str, str | None]] = []
        seen = set()

        def add(a, b, note, flow_id):
            if a in self.act and b in self.act and a != b and (a, b) not in seen:
                seen.add((a, b))
                edges.append((a, b, note, flow_id))

        for flow in self.m.collection("flows"):
            fid = self.m.slot_id(flow)
            for a in self.m.targets(fid, "flow_source"):
                for b in self.m.targets(fid, "flow_target"):
                    add(a, b, _clean(flow.get("label") or ""), fid)
        for rel in self.m.relations:
            if rel.get("relation_type") == "temporal_before":
                add(rel["source_slot_id"], rel["target_slot_id"], "temporal_before", None)
        return edges

    def _flow_controls(self):
        """flow_id -> control slot, from `control controls_flow flow` relations."""
        mapping: dict[str, dict] = {}
        for rel in self.m.relations:
            if rel.get("relation_type") != "controls_flow":
                continue
            entry = self.m.by_id.get(rel["source_slot_id"])
            if entry and entry[0] == "controls":
                mapping[rel["target_slot_id"]] = entry[1]
        return mapping

    def _control_flow(self, edges, guard_attr, flow_controls, action_ids, has_in, has_out):
        """Insert fork(concurrency)/join nodes by inferring branch sets from the graph.

        Unguarded multi-outgoing -> fork; multi-incoming -> join. Guarded edges stay
        as decision (guarded) successions. Returns (fork_names, join_names, succ_lines).
        """
        START, DONE = ("kw", "start"), ("kw", "done")
        adj: dict = {}

        def akey(aid):
            return ("A", aid)

        def add(u, v, guard=None):
            adj.setdefault(u, []).append([v, guard])

        starts = [a for a in action_ids if a not in has_in]
        sinks = [a for a in action_ids if a not in has_out]
        for a in starts:
            add(START, akey(a))
        for a, b, _, fid in edges:
            control = flow_controls.get(fid) if fid else None
            guard = guard_attr[self.m.slot_id(control)] if control else None
            add(akey(a), akey(b), guard)
        for a in sinks:
            add(akey(a), DONE)

        forks: list[str] = []
        joins: list[str] = []

        # fork pass: group unguarded multi-outgoing edges through a fork
        for u in list(adj.keys()):
            unguarded = [e for e in adj[u] if e[1] is None]
            if len(unguarded) > 1:
                self._fork_seq += 1
                name = f"New Start Concurrency_{self._fork_seq}"
                forks.append(name)
                fk = ("F", name)
                for e in unguarded:
                    adj[u].remove(e)
                adj[u].append([fk, None])
                adj[fk] = [[e[0], None] for e in unguarded]

        # join pass: group multi-incoming edges through a join
        def predecessors():
            preds: dict = {}
            for src, es in adj.items():
                for target, guard in es:
                    preds.setdefault(target, []).append((src, guard))
            return preds

        for w, ps in list(predecessors().items()):
            if len(ps) > 1:
                self._join_seq += 1
                name = f"New End Concurrency_{self._join_seq}"
                joins.append(name)
                jn = ("J", name)
                for src, guard in ps:
                    for e in adj.get(src, []):
                        if e[0] == w and e[1] == guard:
                            e[0] = jn
                            break
                adj[jn] = [[w, None]]

        def ref(node):
            kind, val = node
            if kind == "kw":
                return val
            if kind == "A":
                return _q(self.act[val])
            return _q(val)  # F / J

        lines: list[str] = []
        for u, es in adj.items():
            for target, guard in es:
                cond = f" if {_q(guard)} == true" if guard else ""
                lines.append(f"succession first {ref(u)}{cond} then {ref(target)};")
        return forks, joins, lines

    def _object_flows(self):
        """(producer_action, consumer_action, item) triples from object flows."""
        triples = []
        for flow in self.m.collection("flows"):
            if "object" not in str(flow.get("flow_kind", "")):
                continue
            fid = self.m.slot_id(flow)
            items = [i for i in self.m.targets(fid, "carries_item") if i in self.item]
            srcs = [a for a in self.m.targets(fid, "flow_source") if a in self.act]
            tgts = [b for b in self.m.targets(fid, "flow_target") if b in self.act]
            for i in items:
                for a in srcs:
                    for b in tgts:
                        triples.append((a, b, i))
        return triples

    # --- grouped emission -----------------------------------------------------
    def _guard_attrs(self, edges, reserved=frozenset()):
        """control_id -> boolean guard attr label, for controls governing these edges.
        ``reserved``: other member names of the same namespace (actions, flat-mode items)."""
        flow_controls = self._flow_controls()
        guard_attr: dict[str, str] = {}
        used: dict[str, int] = {}
        for _, _, _, fid in edges:
            control = flow_controls.get(fid) if fid else None
            if not control:
                continue
            cid = self.m.slot_id(control)
            if cid in guard_attr:
                continue
            guards = control.get("guard_texts") or []
            base = (_clean(guards[0]) if guards else (_label(control) or _clean(cid))) or "guard"
            count = used.get(base, 1 if base in reserved else 0)
            used[base] = count + 1
            guard_attr[cid] = base if count == 0 else f"{base} #{count + 1}"
        return guard_attr, flow_controls

    def _emit_group(self, aids, indent, reserved=frozenset()):
        """Emit actions + fork/join + guards + allocations + successions + intra-group
        object flows for one action subset, at the given indent (in 4-space units)."""
        pad = "    " * indent
        aidset = set(aids)
        obj = [(a, b, i) for (a, b, i) in self._object_flows() if a in aidset and b in aidset]

        L: list[str] = []
        for aid in aids:
            outs, ins = self._all_ports(aid)
            if self.imm_tags:
                L.append(f"{pad}#Function")
            head = f"{pad}action {_q(self.act[aid])}"
            if not outs and not ins:
                L.append(f"{head};")
                continue
            L.append(f"{head} {{")
            for i in ins:
                L.append(f"{pad}    in item {_q(self.item[i])} : ItemInputEdge;")
            for i in outs:
                L.append(self._out_port_line(pad, aid, i))
            L.append(f"{pad}}}")
        L.append("")

        edges = [e for e in self._edges() if e[0] in aidset and e[1] in aidset]
        has_in = {b for _, b, _, _ in edges}
        has_out = {a for a, _, _, _ in edges}
        names = set(reserved) | {self.act[a] for a in aids}
        guard_attr, flow_controls = self._guard_attrs(edges, names)
        forks, joins, succ = self._control_flow(edges, guard_attr, flow_controls, list(aids), has_in, has_out)

        for name in forks:
            L.append(f"{pad}fork {_q(name)};")
        for name in joins:
            L.append(f"{pad}join {_q(name)};")
        if forks or joins:
            L.append("")
        for cid, attr in guard_attr.items():
            ct = self.m.by_id[cid][1].get("control_type")
            L.append(f"{pad}attribute {_q(attr)} : ScalarValues::Boolean;  // control: {ct}")
        if guard_attr:
            L.append("")
        for aid in aids:
            for pid in self._performers_of(aid):
                L.append(f"{pad}allocate {_q(self.act[aid])} to {_q(self.perf[pid])};")
        L.append("")
        for line in succ:
            L.append(f"{pad}{line}")
        if obj:
            L.append("")
            for a, b, i in obj:
                L.append(
                    f"{pad}flow from {_q(self.act[a])}.{_q(self._out_port_name(a, i))} "
                    f"to {_q(self.act[b])}.{_q(self.item[i])};"
                )
        return L

    def _episode_groups(self):
        """[(episode_slot, [action_id])] ordered by order_index, iff episodes fully cover
        the actions; else None (falls back to a flat function)."""
        episodes = self.m.collection("episodes")
        if not episodes:
            return None
        action_ids = {self.m.slot_id(a) for a in self.m.collection("actions")}
        groups = []
        assigned: set = set()
        for episode in sorted(episodes, key=lambda e: e.get("order_index", 0)):
            eid = self.m.slot_id(episode)
            aids = []
            # canonical first, then the legacy spellings for backward compatibility
            for t in self.m.targets(eid, "contains_action"):
                if t in action_ids and t not in aids and t not in assigned:
                    aids.append(t)
            for rel in self.m.out_relations(eid):
                rt = rel.get("relation_type")
                if rt == "custom" and rel.get("custom_relation_type") not in (None, "contains_action"):
                    continue
                if rt in ("custom", "has_action", "contains"):
                    t = rel.get("target_slot_id")
                    if t in action_ids and t not in aids and t not in assigned:
                        aids.append(t)
            assigned.update(aids)
            if aids:
                groups.append((episode, aids))
        if assigned != action_ids or not groups:
            return None
        return groups

    def _used_items(self):
        used = set()
        for action in self.m.collection("actions"):
            o, n = self._ports(self.m.slot_id(action))
            used.update(o + n)
        used.update(i for _, _, i in self._object_flows())
        return used

    # --- emit -----------------------------------------------------------------
    def convert(self) -> str:
        scenarios = self.m.collection("scenarios")
        scenario_label = (_label(scenarios[0]) if scenarios else "") or self.m.title
        L: list[str] = [_header(self.imm_tags), ""]
        L.append(f"// {self.m.title}")
        L.append(f"// Generated from T2A-ESS by {CONVERTER_VERSION}")
        L.append("")

        # top-level performers
        for performer in self.m.collection("performers"):
            pid = self.m.slot_id(performer)
            if self.imm_tags:
                L.append("#Performer")
            L.append(f"part {_q(self.perf[pid])} : Performer;")
        L.append("")

        used_items = self._used_items()
        groups = self._episode_groups()
        # members of the root function share one namespace with its item declarations
        item_names = {self.item[self.m.slot_id(i)] for i in self.m.collection("items") if self.m.slot_id(i) in used_items}
        self._root_label = scenario_label

        if self.imm_tags:
            L.append("#Function")
        L.append(f"action {_q(scenario_label)} {{")

        if groups:
            # nested: each episode is a #Function action with its own start->done body
            ep_label: dict[str, str] = {}
            ep_names: list[str] = []
            taken = set(item_names)
            for episode, aids in groups:
                label = _free_name(_label(episode) or self.m.slot_id(episode), taken)
                taken.add(label)
                ep_names.append(label)
                for aid in aids:
                    ep_label[aid] = label
                if self.imm_tags:
                    L.append("    #Function")
                L.append(f"    action {_q(label)} {{")
                L.extend(self._emit_group(aids, indent=2))
                L.append("    }")
            L.append("")
            for item in self.m.collection("items"):
                iid = self.m.slot_id(item)
                if iid in used_items:
                    L.append(f"    item {_q(self.item[iid])};")
            if used_items:
                L.append("")
            # episode sequencing: start -> ep1 -> ... -> epN -> done
            prev = None
            for label in ep_names:
                src = "start" if prev is None else _q(prev)
                L.append(f"    succession first {src} then {_q(label)};")
                prev = label
            if prev is not None:
                L.append(f"    succession first {_q(prev)} then done;")
            # cross-episode object flows (dotted path: episode.action.item)
            cross = [(a, b, i) for (a, b, i) in self._object_flows() if ep_label.get(a) != ep_label.get(b)]
            if cross:
                L.append("")
                for a, b, i in cross:
                    L.append(
                        f"    flow from {_q(ep_label[a])}.{_q(self.act[a])}.{_q(self._out_port_name(a, i))} "
                        f"to {_q(ep_label[b])}.{_q(self.act[b])}.{_q(self.item[i])};"
                    )
        else:
            # flat: one function containing all actions (actions and items share its namespace)
            all_aids = [self.m.slot_id(a) for a in self.m.collection("actions")]
            taken = set(item_names)
            for aid in all_aids:
                name = _free_name(self.act[aid], taken)
                taken.add(name)
                self.act[aid] = name
            L.extend(self._emit_group(all_aids, indent=1, reserved=item_names))
            L.append("")
            for item in self.m.collection("items"):
                iid = self.m.slot_id(item)
                if iid in used_items:
                    L.append(f"    item {_q(self.item[iid])};")

        L.append("}")
        return "\n".join(L) + "\n"


def convert_model(model: T2AModel, imm_tags: bool = True) -> str:
    return _EffbdConverter(model, imm_tags=imm_tags).convert()


def convert_file(path: str | Path, imm_tags: bool = True) -> str:
    return convert_model(load_model(path), imm_tags=imm_tags)
