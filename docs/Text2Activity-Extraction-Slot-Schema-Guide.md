# T2A-ESS Developer Guide — Understanding the Slot Schema Through Examples

`Text2Activity-Extraction-Slot-Schema.md` (hereafter "original schema") focuses on definitions and principles, so it is hard to follow on a first reading.
This document **explains the same content again through examples**. The original schema remains the authority on the rules; this document is a commentary on it.
Most examples come from the MUM-T attack maneuver scenario (gold: `data/ground-truth/mumt/mumt.gold.json`).

Suggested reading order: §1 one-page summary → §3 slot table → §3.1 behavior axis and state axis → §5 confusing pairs → §4 per-slot examples and §6 relation catalog when needed.

---

## 1. One-page summary: what T2A-ESS JSON looks like

This is a minimal example with only two actions, "Enter order → Payment". Remember this shape; everything else extends it.

```json
{
  "text2activity_extraction_model": {
    "model_id": "EX_MIN_001",
    "title": "Minimal example",
    "scenarios":  [{ "scenario_id": "SCN", "label": "Coffee order" }],
    "performers": [{ "performer_id": "P_CUSTOMER", "label": "Customer" },
                   { "performer_id": "P_CASHIER",  "label": "Cashier" }],
    "actions":    [{ "action_id": "A_ORDER", "label": "Enter order" },
                   { "action_id": "A_PAY",   "label": "Payment" }],
    "items":      [{ "item_id": "I_TICKET", "label": "Order ticket", "item_type": "document" }],
    "flows":      [{ "flow_id": "F_ORDER_PAY", "label": "Payment after order", "flow_kind": "control_flow" }],
    "slot_relations": [
      { "relation_id": "r1", "source_slot_id": "A_ORDER",     "relation_type": "performed_by",  "target_slot_id": "P_CUSTOMER" },
      { "relation_id": "r2", "source_slot_id": "A_PAY",       "relation_type": "performed_by",  "target_slot_id": "P_CASHIER" },
      { "relation_id": "r3", "source_slot_id": "A_ORDER",     "relation_type": "produces_item", "target_slot_id": "I_TICKET" },
      { "relation_id": "r4", "source_slot_id": "F_ORDER_PAY", "relation_type": "flow_source",   "target_slot_id": "A_ORDER" },
      { "relation_id": "r5", "source_slot_id": "F_ORDER_PAY", "relation_type": "flow_target",   "target_slot_id": "A_PAY" }
    ]
  }
}
```

The three points visible here cover most of the schema.

1. **Slots are nodes.** Each element of an array such as `performers`, `actions`, `items`, `flows` is one slot. A slot contains only its own attributes (`label`, `item_type`, `flow_kind` …).
2. **Relations exist only in `slot_relations`.** "The customer orders" is not written by putting `performer_id` inside the action slot, but as a single `performed_by` relation line. Likewise, a flow connects its two ends with two relations, `flow_source`/`flow_target`.
3. **Every slot has `*_id` and `label`.** The id is the key for relations, and `label` is the human-readable name that is printed as-is in the diagram. It is **`label`**, not `name` or `title`.

Feeding this JSON into the converter produces the EFFBD SysML below.

```text
part 'Customer' : Performer;   part 'Cashier' : Performer;
action 'Coffee order' {
    action 'Enter order' { out item 'Order ticket' : ItemOutputEdge; }
    action 'Payment';
    item 'Order ticket';
    allocate 'Enter order' to 'Customer';   allocate 'Payment' to 'Cashier';
    succession first start then 'Enter order';
    succession first 'Enter order' then 'Payment';
    succession first 'Payment' then done;
}
```

---

## 2. Five rules you must follow


| #   | Rule                                                               | Why                                            | If violated                                                 |
| --- | ---------------------------------------------------------------- | -------------------------------------------- | --------------------------------------------------- |
| 1   | Do not put `*_id` or `*_ids` fields that point to other slots inside a slot (the slot's own primary id is the exception) | Relations must have a single source of truth, `slot_relations`, so that validation and conversion stay simple | The converter cannot see the relation. The graph validator flags it as dangling              |
| 2   | Names go in `label`                                                      | The editor uses quoted labels as keys                           | Nodes are displayed as `Function_1`, `Performer_2`               |
| 3   | `*_text` and `*_label` fields are auxiliary                                      | They are hints for understanding the source text, not canonical relations                | If you write only `target_text` and omit the `flow_target` relation, the flow is not drawn |
| 4   | Keep source evidence (`source_ref`, `source_units`)                        | Traceability. You must be able to trace back which sentence a slot came from               | Review and evaluation become impossible                                            |
| 5   | Do not copy the same value into multiple slots                                            | Keep it only in one canonical owner slot (table below)            | Duplication and inconsistency until normalization                                      |


canonical owner table (original schema "Duplication and Reference Principles Between Slots"):


| This information              | goes only here     |
| ------------------- | ----------- |
| Performing agent               | Performer   |
| Performed action               | Action      |
| Object, message, resource, payload | Item        |
| A single state value              | State Value |
| A set of state values              | Situation   |
| Occurring event               | Event       |
| State change               | Transition  |
| Order, transfer, dependency            | Flow        |
| Condition, branch, parallel, loop         | Control     |
| Constraint expression, threshold, deadline          | Constraint  |
| Purpose, success criteria            | Goal        |
| Reason, evidence               | Reason      |


---

## 3. The 17 slots at a glance


| Group  | Slot                        | One-line definition                     | Test question                     | Minimum fields                                 | Read by EFFBD converter?             |
| --- | ------------------------- | -------------------------- | ------------------------- | ------------------------------------- | ------------------------- |
| Scope  | **Scenario**              | Top-level execution scope                  | Is it the mission or use case of the whole document?          | `scenario_id`, `label`                | Yes (root function)           |
| Scope  | **Episode**               | Section or phase within a scenario           | Is it a heading that groups multiple actions?   | `episode_id`, `label`, `order_index`  | Yes (nested function)           |
| State  | **Situation**             | Set of states true during a specific period             | Is it a state snapshot rather than execution?     | `situation_id`, `label`               | No (state view planned)       |
| State  | **State Value**           | One subject-variable-value | Is it an atomic state fact?               | `state_value_id`, `variable`, `value` | No                       |
| State  | **Observation**           | Basis of a detection, measurement, or judgment               | Who came to know what?             | `observation_id`, `label`             | No                       |
| State  | **Event**                 | Occurrence that caused a flow or transition              | Is it something that actually happened?               | `event_id`, `label`, `event_type`     | No                       |
| State  | **Transition**            | Change from A to B                 | Does the state change?                  | `transition_id`, `label`              | No                       |
| Flow  | **Performer**             | Acting agent                      | Is it a person, organization, system, or equipment?            | `performer_id`, `label`               | Yes (`part`, `allocate`)    |
| Flow  | **Action**                | Atomic act of one agent               | One verb, one agent?            | `action_id`, `label`                  | Yes (`action`)              |
| Flow  | **Item**                  | What flows between actions               | Is it an output, message, or resource?              | `item_id`, `label`                    | Yes (`in/out item`, `flow`) |
| Flow  | **Flow**                  | Order or transfer between actions             | B after A, or what goes from A→B?    | `flow_id`, `flow_kind`                | Yes (`succession`, `flow`)  |
| Flow  | **Control**               | Condition, branch, parallel, loop                | Is structure needed even though the text has no action? | `control_id`, `control_type`          | Yes (`guard_texts` → guard)    |
| Rule  | **Constraint**            | Threshold, deadline, rule                  | Is it a numeric condition or a prohibition?              | `constraint_id`, `label`              | No                       |
| Rule  | **Goal**                  | Target state to achieve                | Why is this done (objective)?             | `goal_id`, `label`                    | No                       |
| Rule  | **Reason**                | Reason, evidence, rationale            | Why is this choice justified?              | `reason_id`, `label`                  | No                       |
| Extension  | **Domain Extension Rule** | Domain concept dictionary                  | Is it domain vocabulary such as physics or military?         | `domain_extension_rule_id`, `domain`  | No                       |
| Extension  | **Semantic Binding**      | Link between a slot and a domain concept               | Which concept does this slot correspond to?         | `semantic_binding_id`                 | No                       |


"Read by EFFBD converter?" reflects the current `src/t2a_sysml` (Python) and `src/t2a_js` (JS). Slots marked No **must still be extracted**. They are inputs to the state view, requirements, and metadata export, and they are subject to traceability validation.

### 3.1 Reading along two axes: behavior axis and state axis

The "Scope/Flow" groups and the "State" group in the table above are **two axes that cut the same source text span with different questions**. Seventeen slots look like a lot, but once you know which axis a node belongs to, the relation direction is almost determined.

| | Behavior axis (behavior) | State axis (state) |
| --- | --- | --- |
| Question | Who **does what** | **What state the world is in and how it changes** |
| Nodes | Scenario, Episode, Action, Performer, Item, Flow, Control | Situation, State Value, Transition, Event, Observation |
| Backbone relations | `has_episode`, `contains_action`, `performed_by`, `flow_source`/`flow_target` | `has_state_value`, `from_situation`/`to_situation`, `triggers`, `observes` |
| Shape | **Containment hierarchy** (Scenario ⊃ Episode ⊃ Action) | **Transition graph** (Situation —Transition→ Situation) |
| EFFBD converter | Reads it (function nesting, succession, allocate) | Does not read it (state view planned) |

The backbones of the two axes are shown below. The behavior axis is a containment hierarchy, and the state axis is a transition graph. An Action never sits under a Situation, but Scenario and Episode **can own** the Situations of their span through `has_situation` (original schema "Slot Class Multiplicity" diagram). In other words, scope slots (Scenario, Episode) are containers for both behavior and state.

```text
[Behavior axis — containment hierarchy]    [State axis — transition graph]

Scenario                                   Situation ──has_state_value──▶ State Value
  └─has_episode─▶ Episode                       ▲              ▲
        └─contains_action─▶ Action        from_situation   to_situation
                 ├─performed_by─▶ Performer      └── Transition ──┘
                 ├─uses/produces_item─▶ Item             ▲
                 └─(Flow: flow_source/flow_target)   triggers
                                                          │
                                                        Event ◀──observes── Observation

[Bridges between the two axes]

Scenario ─has_situation─▶ Situation        Episode   ─has_situation─▶ Situation
Action   ─causes────────▶ Transition       Event     ─triggers──────▶ Action
Performer ─originates_event─▶ Event        Event     ─causes_event──▶ Event
Action   ─has_reason────▶ Reason ─has_evidence─▶ Observation ─observes─▶ Event / State Value
Action / Transition ─constrained_by─▶ Constraint
```

**Behavior axis example** (MUM-T gold, episode 3):

> Sentence: under `### Responding to electronic warfare jamming and communication degradation`, `The 3 reconnaissance drones switch to Edge AI analysis mode. TDSS activates the local sensor-based survival loop. …`

```text
MUMT_SCN_ATTACK_OPERATION  ─has_episode─▶  MUMT_EP_EW_DEGRADATION ("Responding to electronic warfare jamming and communication degradation")
MUMT_EP_EW_DEGRADATION     ─contains_action─▶  MUMT_A_SWITCH_EDGE_MODE        ("Drone Edge AI analysis mode switch")
MUMT_EP_EW_DEGRADATION     ─contains_action─▶  MUMT_A_ACTIVATE_LOCAL_SURVIVAL ("Local sensor-based survival loop activation")
MUMT_EP_EW_DEGRADATION     ─contains_action─▶  MUMT_A_EMERGENCY_BROADCAST     ("Drone emergency broadcast transmission")
MUMT_EP_EW_DEGRADATION     ─contains_action─▶  MUMT_A_SMOKE_EVASION           ("Smoke deployment and evasive maneuver after ATGM warning")
MUMT_A_SWITCH_EDGE_MODE    ─performed_by─▶  MUMT_P3_DRONE_TEAM
MUMT_A_SWITCH_EDGE_MODE    ─uses_item─▶  MUMT_I_VIDEO_STREAM,  ─produces_item─▶  MUMT_I_TRACK_SUMMARY
```

The converter nests this as `action 'Responding to electronic warfare jamming and communication degradation' { action 'Drone Edge AI analysis mode switch'; … }`. An Episode does not get a separate representative Action; **the Episode itself becomes the parent action**.

**State axis example** (same episode span):

> Sentence: `With persistent packet loss as the direct condition, TDSS transitions from normal communication to limited communication mode. In the limited communication state, the communication mode is limited and the drone data is summary tracks.`

```text
MUMT_SIT_COMM_NORMAL   ("Normal communication state")  ─has_state_value─▶  MUMT_SV_COMM_NORMAL, MUMT_SV_DATA_VIDEO
MUMT_SIT_COMM_LIMITED  ("Limited communication state")  ─has_state_value─▶  MUMT_SV_COMM_LIMITED, MUMT_SV_DATA_TRACK_SUMMARY
MUMT_TR_NORMAL_TO_LIMITED ("Transition from normal to limited communication")
    ─from_situation─▶ MUMT_SIT_COMM_NORMAL
    ─to_situation──▶ MUMT_SIT_COMM_LIMITED
MUMT_EVT_PACKET_LOSS_PERSISTED ─triggers─▶ MUMT_TR_NORMAL_TO_LIMITED
MUMT_OBS_PACKET_LOSS           ─observes─▶ MUMT_EVT_PACKET_LOSS_PERSISTED
```

Here a State Value is an atom (`communication state = limited`), a Situation is a set of those atoms that are **true at the same time**, a Transition is the move between sets, an Event is the trigger of the move, and an Observation is the basis for knowing about that Event. This axis is not drawn in EFFBD, but it must still be extracted.

**Bridges between the two axes** — the cross-axis relations defined by the original schema's "Slot Relation contract" are the following seven kinds. All of them are canonical `relation_type`s.

| Relation | Direction | Meaning | gold example |
| --- | --- | --- | --- |
| `has_situation` | Scenario / Episode → Situation | Owns the set of states that are true during that scope. An Episode has both Actions and Situations | `MUMT_EP_EW_DEGRADATION → MUMT_SIT_COMM_LIMITED` |
| `entry_situation` / `exit_situation` | Episode → Situation | Boundary state at the start or end of the episode. Only when the boundaries need to be distinguished | (not used in gold) |
| `causes` | Action → Transition | The action causes a state transition | (not used in gold) |
| `triggers` | Event → Action | An occurrence immediately starts an action ("if ~", "when ~") | `MUMT_EVT_ATGM_LAUNCH → MUMT_A_SMOKE_EVASION` |
| `originates_event` | Performer → Event | The agent that caused the event | `MUMT_P6_ENEMY → MUMT_EVT_ATGM_LAUNCH` |
| `has_reason` → `has_evidence` | Action / Transition → Reason → Observation | The **reason** for an action and the **observation** that supports that reason. There is no direct Action ↔ Observation relation; the path must always go through Reason | `MUMT_A_DECIDE_DETOUR → MUMT_R_DETOUR → MUMT_OBS_ENEMY_OP` |
| `constrained_by` | Action / Transition → Constraint | The same Constraint constrains both axes | `MUMT_TR_NORMAL_TO_LIMITED → MUMT_C_PACKET_LOSS_THRESHOLD` |

`*_text` fields such as Action's `causes_transition_text`, Episode's `entry_situation_text`, and Reason's `evidence.observation_texts` are **auxiliary** to these relations (rule 3). If you omit the relation and write only `*_text`, the validator issues a warning, and if the two differ, the relation takes precedence.

Test tip: if a sentence **changes the world** (performing, transferring, producing), it belongs to the behavior axis; if it **says what state the world is in or how it changed** ("is ~", "is in a ~ state", "transitions to ~"), it belongs to the state axis. "Transitions" is a verb, but no agent performs anything; the state of the world changes, so it belongs to the state axis (Transition). The exception is **"detects, measures, judges"**. These verbs do not change the world; they **make something known**. So the evidence is always kept as an Observation on the state axis, and an Action is added on the behavior axis only when the detection is a step in the execution flow (connected by succession to the preceding and following actions) (see 4.10). If both axes appear in one sentence, create both (see 5.1, 5.2).

---

## 4. Per-slot mini examples

The format is the same: **sentence → slot JSON → relations → common mistakes**. The JSON shows only required fields; `source_ref`, `confidence_by_llm`, and `standard_mapping` are omitted (you can attach them, and attaching them is recommended).

### 4.1 Scenario

> Sentence: `## MUM-T-based attack maneuver and electronic warfare response scenario` (top-level heading of the document)

```json
{ "scenario_id": "MUMT_SCN_ATTACK_OPERATION", "label": "MUM-T-based attack maneuver and electronic warfare response",
  "success_criteria_texts": ["Secure the objective", "Maintain combat power"] }
```

Relations: `MUMT_SCN_ATTACK_OPERATION —has_episode→ MUMT_EP_PREP_NORMAL` (one line per episode), `—has_goal→ MUMT_G_SECURE_TARGET`

Common mistake: creating multiple scenarios. The converter uses only `scenarios[0]` as the root. The default is one scenario per document.

### 4.2 Episode

> Sentence: `### Responding to electronic warfare jamming and communication degradation` (section heading within the scenario)

```json
{ "episode_id": "MUMT_EP_EW_DEGRADATION", "label": "Responding to electronic warfare jamming and communication degradation", "order_index": 3 }
```

Relations: `MUMT_EP_EW_DEGRADATION —contains_action→ MUMT_A_SWITCH_EDGE_MODE` (one line per contained action), `MUMT_EP_EW_DEGRADATION —has_situation→ MUMT_SIT_COMM_LIMITED` (one line per set of states true in that span)

Two common mistakes. ① Episodes cover only some of the actions. The converter builds the nested structure **only when every action belongs to some episode**; if even one is missing, it falls back to flat (validator `ACTION_NO_EPISODE` warning). ② Even if the label contains "state" or "mode", a heading that groups multiple actions is an Episode. Make the conditions that are true in that span into separate Situations and attach them to the Episode with `has_situation`. If you want to record the boundary states at the start and end separately, use `entry_situation`/`exit_situation` (3.1 bridge table).

### 4.3 Performer

> Sentence: `The 3 reconnaissance drones consist of No. 1, No. 2, and No. 3. The Edge AI of Drone No. 1 detects the threat.`

```json
[{ "performer_id": "MUMT_P3_DRONE_TEAM", "label": "3 reconnaissance drones", "performer_kind": "aggregate" },
 { "performer_id": "MUMT_P3_1_DRONE",    "label": "Drone No. 1",    "performer_kind": "component" },
 { "performer_id": "MUMT_P3_1_EDGE_AI",  "label": "Drone No. 1 Edge AI", "performer_kind": "software_component", "performer_scope": "internal" }]
```

Relations: `MUMT_P3_DRONE_TEAM —has_part→ MUMT_P3_1_DRONE`, `MUMT_P3_1_DRONE —has_part→ MUMT_P3_1_EDGE_AI`

Common mistake: creating a new Component slot for internal software. The schema has no Component slot. If an internal component is an acting agent, **reuse Performer** and attach it to its parent with `has_part`.

Difference between `performer_kind` and `part_structure.role`: `performer_kind` is the **kind** of agent (`individual`/`aggregate`/`component`/`software_component` …), and
`part_structure.role` records the **position** within a containment relation (`standalone`/`whole`/`part`) as an export hint. The correspondence is almost 1:1 (`aggregate`↔`whole`,
`component`↔`part`), so fill in `part_structure` only when there is information that cannot be written as a relation, such as `member_cardinality` (19 units). Neither is a relation,
and the authoritative record of actual containment is the single `has_part` line. There is no field called `part_structure.kind`.

### 4.4 Action

> Sentence: `TDSS provides an FPV threat warning by displaying the threat direction, approach speed, and an estimated time of arrival of about 43 seconds on the HMI.`

```json
{ "action_id": "MUMT_A_ALERT_FPV", "label": "Provide FPV threat warning", "verb": "provide",
  "primary_actor_text": "TDSS", "object_text": "FPV threat warning" }
```

Relations: `—performed_by→ MUMT_P2_TDSS`, `—produces_item→ MUMT_I_FPV_ALERT`, `—constrained_by→ MUMT_C_FPV_ETA`

Atomic action splitting criteria (original schema): split when the agent changes. Split when there are two verbs. Split when the input or output items differ. "Receives and processes" is two actions.

> Splitting example: `The company commander shares the surveillance status with subordinate platoons, and TDSS transmits company SA summary information to the battalion server.`
> → 2 actions (`Share surveillance status` performed_by company commander, `Transmit SA summary information` performed_by TDSS), 2 items.

Common mistake: writing only `primary_actor_text` and forgetting the `performed_by` relation. `*_text` is only a hint, so the converter cannot create `allocate`.

### 4.5 Item

> Sentence: `The 3 reconnaissance drones stop transmitting the video stream and … transmit summary track data.`

```json
[{ "item_id": "MUMT_I_VIDEO_STREAM",  "label": "Drone video stream", "item_type": "sensor_stream" },
 { "item_id": "MUMT_I_TRACK_SUMMARY", "label": "Summary track data", "item_type": "track_payload" }]
```

Relations: `MUMT_A_SWITCH_EDGE_MODE —uses_item→ MUMT_I_VIDEO_STREAM`, `—produces_item→ MUMT_I_TRACK_SUMMARY`

Conversion: `uses_item` and `provided_to` become `in item` ports, and `produces_item` becomes an `out item` port. Items not connected to any action are dropped from the output.

Common mistake: merging coordinated nouns into one. "Displays schedule information and business applications" is likely two items. If you are unsure, split them into two and lower the confidence.

### 4.6 Flow

> Sentence: `Switch to Edge AI analysis mode and transmit summary track data, and (after recovery) resynchronize SA with the summary track data.`

```json
{ "flow_id": "MUMT_F_EDGE_MODE_TO_TRACK_FLOW", "label": "Summary track transmission after Edge mode switch", "flow_kind": "object_flow" }
```

Relations: `—flow_source→ MUMT_A_SWITCH_EDGE_MODE`, `—flow_target→ MUMT_A_RESYNC_SA`, `—carries_item→ MUMT_I_TRACK_SUMMARY`

`flow_kind` has two variants. `control_flow` expresses order only ("B after A", `succession`), and `object_flow` means something passes across (`flow from A.item to B.item`). An object flow **must have `carries_item`**.

Common mistake: writing only `source_action_text`/`target_action_text` and forgetting the relations. The converter reads only relations.

### 4.7 Control

> Sentence: `Transmit summary track data while the limited communication state persists.` / `Order dispersed maneuver and air defense alert simultaneously.`

```json
[{ "control_id": "MUMT_CTRL_COMM_MODE_GUARD", "label": "Communication mode transition guard", "control_type": "guarded_sequence",
   "guard_texts": ["While the communication loss state persists"] },
 { "control_id": "CTRL_FORK_1", "label": "Dispersed maneuver / air defense alert in parallel", "control_type": "fork" }]
```

Relations: `MUMT_CTRL_COMM_MODE_GUARD —controls_flow→ MUMT_F_EDGE_MODE_TO_TRACK_FLOW`

Conversion: `guard_texts[0]` becomes the name of a Boolean attribute, and `if 'guard' == true` is attached to that flow's succession. fork/join are **inferred automatically** from the graph shape (multiple unguarded outgoing or incoming edges) even without a control slot. Still, if the source text says "simultaneously" or "when all are complete", keeping it as a Control is better for traceability.

`control_type` recommended values: `decision`, `merge`, `fork`, `join`, `fork_join`, `loop`, `initial`, `final`, `wait`, `accept`, `timeout`, `temporal_exclusion`.

Common mistake: turning a conditional into an Action (an action such as "Check condition"). A condition is a Control (structure), and the numeric condition itself is a Constraint.

### 4.8 Situation

> Sentence: `While the packet loss rate remains above the threshold, the system is in the limited communication state.`

```json
{ "situation_id": "MUMT_SIT_COMM_LIMITED", "label": "Limited communication state",
  "situation_type": ["operational_state", "communication_state"],
  "valid_time": { "text": "While the packet loss rate remains above the threshold" } }
```

Relations: `—has_state_value→ MUMT_SV_COMM_LIMITED`, `—has_state_value→ MUMT_SV_DATA_TRACK_SUMMARY`, `MUMT_EP_EW_DEGRADATION —has_situation→ MUMT_SIT_COMM_LIMITED`

Situation answers "what state is the world in during that span", and Episode answers "what is done during that span". Both can exist for the same span, and the Scenario or Episode that owns the span holds the Situation through `has_situation`. A Situation itself does not contain Actions. A Situation must have at least one `has_state_value` (`SITUATION_NO_STATE_VALUE` warning).

### 4.9 State Value

> Sentence: `The communication mode is limited and the drone data is summary tracks.`

```json
[{ "state_value_id": "MUMT_SV_COMM_LIMITED", "label": "Communication state is limited", "subject_text": "MUM-T system",
   "variable": "communication state", "value": { "raw": "limited", "normalized": "limited", "value_type": "enum" } },
 { "state_value_id": "MUMT_SV_DATA_TRACK_SUMMARY", "label": "Data mode is summary track", "subject_text": "Reconnaissance drone",
   "variable": "data mode", "value": { "raw": "summary track", "normalized": "summarized_track", "value_type": "enum" } }]
```

If a sentence contains two state values, there are two slots. `value_type` values include `enum`, `boolean`, `quantity`, `location`, `capability`, `probability`, and so on.

### 4.10 Observation

> Sentence: `TDSS detects that the packet loss rate exceeds 30% for 10 seconds.`

```json
{ "observation_id": "MUMT_OBS_PACKET_LOSS", "label": "Packet loss rate spike detection",
  "observer_text": "TDSS", "observed_text": "Packet loss rate above 30% persisting for 10 seconds" }
```

Relations: `—observes→ MUMT_EVT_PACKET_LOSS_PERSISTED`

An Observation is **the basis for knowing**. It records who (TDSS) detected it and by what method and value (loss rate 30%, 10 seconds), so that the Event does not become "an event declared without a source". Here the detection is a transition condition, not a step in the execution flow, so only an Observation is created and no Action.

**When the detection is a step in the behavior flow — create both an Action and an Observation.**

> Sentence: `Drone No. 1 detects a heat source suspected to be an enemy observation post behind the ridgeline. The company commander decides on a right-flank detour maneuver based on the battalion analysis results.`

```text
[Behavior axis]  MUMT_A_DETECT_OBSERVATION_POST ("Detect suspected enemy observation post heat source", verb=detect)
             ─performed_by─▶ MUMT_P3_1_DRONE
             ◀─flow_source─ MUMT_F_OP_DETECT_TO_DETOUR ─flow_target─▶ MUMT_A_DECIDE_DETOUR
           MUMT_A_DECIDE_DETOUR ("Right-flank detour maneuver decision")
             ─has_reason─▶ MUMT_R_DETOUR ("Detour because anti-tank positions may be deployed")

[State axis]  MUMT_OBS_ENEMY_OP ("Suspected enemy observation post heat source captured", observer=Drone No. 1)
             ─observes─▶ MUMT_EVT_ENEMY_OP_HEAT_SIGNATURE ("Appearance of suspected enemy observation post heat source behind the ridgeline")
           MUMT_R_DETOUR ─has_evidence─▶ MUMT_OBS_ENEMY_OP
```

Criteria for dividing the roles: put only **performance** (`performed_by`, preceding and following Flows, owning Episode) in the Action, and only **perception** (`observer_text`, `observed_text`, method, measured value, time) in the Observation. Do not copy the same information to both (rule 5). There is no direct relation type between the two slots. Their pairing shows through the same `source_ref` (both `MUMT_GT_U02`), and if the observation is the basis for a subsequent decision, connect them through the canonical path **Action ─has_reason→ Reason ─has_evidence→ Observation**. A direct Observation → Action relation (`supports_action` in the old gold) is not used, because it skips the Reason and loses the intermediate judgment in "observation → some judgment → action". An Observation must always connect through `observes` to the Event or State Value it confirmed (`OBSERVATION_NO_OBSERVES` warning).

There is one condition for adding an Action: is the detection **a step followed by succession to the next step**? Of the 6 Observations in the MUM-T gold, only `MUMT_OBS_ENEMY_OP` has an Action pair through the Reason path. The 4 communication state detections (`PACKET_LOSS`, `HEARTBEAT_LOSS`, `LINK_RECOVERY`, `BANDWIDTH_RECOVERY`) are transition conditions, so they exist only as Observations. The remaining `MUMT_OBS_FPV_DETECTED` is the basis that confirms `MUMT_EVT_FPV_APPROACH` through `observes`, and the follow-up action (`MUMT_A_ALERT_FPV`) is handled by that Event's `triggers`.

**Three cases in which an observation connects to an action** — the "there is no reason" situation actually splits in two.

| Source text cue | Path | Reason |
| --- | --- | --- |
| "if ~ / when ~ / immediately" + reaction action (no judgment) | Observation ─observes→ Event ─triggers→ Action | None |
| "decide / judge / choose / based on" + explicit reason | Action ─has_reason→ Reason (with `rationale_text`) ─has_evidence→ Observation | `evidence_level: explicit` |
| "decide / judge / choose" present but no reason given | Same path; Reason has `reason_type: [evidence]`, `rationale_text: null` | `evidence_level: inferred` |
| No dependency cue | Observation ─observes→ only | None |

What separates cases 1 and 2 is whether the acting agent **"decided" (Reason) or "reacted" (Event)**. Example: `MUMT_EVT_ATGM_LAUNCH —triggers→ MUMT_A_SMOKE_EVASION` (reaction), `MUMT_A_DECIDE_DETOUR —has_reason→ MUMT_R_DETOUR —has_evidence→ MUMT_OBS_ENEMY_OP` (decision). Because of rule 5, do not copy the observation content into the Reason in case 3 — leave `rationale_text` empty and point to the observation with `has_evidence`.

### 4.11 Event

> Same sentence.

```json
{ "event_id": "MUMT_EVT_PACKET_LOSS_PERSISTED", "label": "Packet loss rate above threshold persisting",
  "event_type": "communication", "trigger_type": "internal" }
```

Relations: `—triggers→ MUMT_TR_NORMAL_TO_LIMITED`

An Event is what happened and is the trigger of the transition. An Observation is how it became known. A State Value is the fact that became true as a result.

### 4.12 Transition

> Sentence: `With persistent packet loss as the direct condition, TDSS transitions from normal communication to limited communication mode.`

```json
{ "transition_id": "MUMT_TR_NORMAL_TO_LIMITED", "label": "Transition from normal to limited communication",
  "change_kind": ["mode_change"], "trigger_text": "Packet loss rate above threshold persisting",
  "guard": { "text": "The packet loss rate remains above the threshold" } }
```

Relations: `—from_situation→ MUMT_SIT_COMM_NORMAL`, `—to_situation→ MUMT_SIT_COMM_LIMITED`, `MUMT_EVT_PACKET_LOSS_PERSISTED —triggers→ MUMT_TR_NORMAL_TO_LIMITED`

Common mistake: modeling a transition only as an Action. "Transitions" is a state change, so create a Transition, and if a separate action causes it, connect it to that Action.

### 4.13 Constraint

> Sentence: `Estimated time of arrival about 43 seconds` / `In fog, equipment movement speed is 5km/h or less`

```json
{ "constraint_id": "MUMT_C_FPV_ETA", "label": "FPV estimated time of arrival 43 seconds", "constraint_type": "quantitative_limit",
  "expression_text": "eta ≈ 43 s" }
```

Relations: `MUMT_A_ALERT_FPV —constrained_by→ MUMT_C_FPV_ETA`

`constraint_kind` recommended values: `quantitative_limit`, `deadline`, `duration_limit`, `periodicity`, `count_condition`, `guard_condition`, `temporal_exclusion`, `safety_rule`, `resource_limit`. If the condition creates a branch, also create a Control, and keep the numeric value itself in the Constraint.

### 4.14 Goal

> Sentence: `To maintain survivability-focused functions and minimum SA …`

```json
{ "goal_id": "MUMT_G_MAINTAIN_MIN_SA", "label": "Maintain minimum SA", "goal_type": "mission",
  "desired_state_text": "A state in which minimum situational awareness is maintained even during limited communication" }
```

Relations: `MUMT_A_SWITCH_EDGE_MODE —has_goal→ MUMT_G_MAINTAIN_MIN_SA`

"in order to ~" and "for the purpose of ~" are the cues.

### 4.15 Reason

> Sentence: `This transition is a graceful degradation based on the deterioration of communication quality.`

```json
{ "reason_id": "MUMT_R_GRACEFUL_DEGRADATION", "label": "Graceful degradation due to communication quality deterioration",
  "reason_type": ["cause", "rationale"], "rationale_text": "Scale down functions step by step based on communication quality deterioration" }
```

Relations: `MUMT_A_SWITCH_EDGE_MODE —has_reason→ MUMT_R_GRACEFUL_DEGRADATION`

Goal answers "what is to be achieved", and Reason answers "why was that judgment made". If the basis of a Reason is a detection, point to the Observation with `hasEvidence`.

### 4.16 Domain Extension Rule

> Sentence: `FPV drones, ATGMs, and electronic warfare jamming are threat types.`

```json
{ "domain_extension_rule_id": "MUMT_DER_THREAT_TYPES", "label": "MUM-T threat vocabulary", "domain": "military_threat",
  "terms": ["FPV kamikaze drone", "ATGM", "Electronic warfare jamming"] }
```

Domain vocabulary is not turned into core slots; it is kept separately as a dictionary. The converter does not read it.

### 4.17 Semantic Binding

```json
{ "semantic_binding_id": "MUMT_SB_TRACK_DATA_ITEM", "label": "Summary track data to SysML Item",
  "binding_kind": "sysml_element", "source_slot_text": "Summary track data", "target_standard_element": "Item" }
```

Relations: `MUMT_SB_TRACK_DATA_ITEM —binds_to→ MUMT_I_TRACK_SUMMARY`, `MUMT_DER_COMM_DEGRADATION —has_binding→ MUMT_SB_TRACK_DATA_ITEM`

Use this to explicitly bind a slot to a domain concept or a standard element. In most extractions it can stay empty.

---

## 5. Comparing confusing pairs

### 5.1 Situation vs Episode — same span, different questions


|     | Episode                           | Situation                        |
| --- | --------------------------------- | -------------------------------- |
| Question  | **What is done** during that span                  | **What state the world is in** during that span            |
| Nature  | behavior scope (groups actions)       | state snapshot (groups state values) |
| Example   | `Responding to electronic warfare jamming and communication degradation` (contains 4 actions) | `Limited communication state` (communication state=limited, data=summary track) |
| Conversion  | nested `action { … }`                 | state view (not used by the EFFBD converter)      |


Even if the label contains "state", a heading that groups actions is an Episode. Create both, and let the Episode own the Situation through `has_situation`. To distinguish the boundary states at the start and end, use `entry_situation`/`exit_situation` (3.1 bridge table).

### 5.2 Event vs Observation vs State Value — one sentence yields all three

> `TDSS detects that the packet loss rate exceeds 30%.`


| Slot          | What it holds                              | In this sentence               |
| ----------- | --------------------------------- | -------------------- |
| Event       | Something that happened in the world                        | Packet loss rate above threshold persisting  |
| Observation | The **basis for knowing** it (who, how, when, what value) | TDSS detects the loss rate above 30% |
| State Value | The fact that became true as a result                      | Packet loss rate > 30%         |


Without an Observation, the Event becomes a declaration without a source. The trigger of a transition is the Event, and the basis of the Event is the Observation.

### 5.3 Flow vs Control — lines and structure

A Flow is a single **line** between actions (A→B). A Control is the **structure** that determines how those lines execute (branch, parallel, loop, guard). "B after A" is a Flow; "A if the condition holds, otherwise B" is two Flows + Control (decision); "A and B simultaneously" is two Flows + Control (fork).

### 5.4 Constraint vs Goal vs Reason — the three rule slots


|            | Question            | Cues                           | Example                        |
| ---------- | ------------- | ---------------------------- | ------------------------ |
| Constraint | What condition must be satisfied | `or less`, `within`, `or more`, `every`, `prohibited` | speed ≤ 5 km/h, within 43 seconds      |
| Goal       | What is to be achieved    | `in order to ~`, `the objective is`              | Maintain minimum SA, secure the objective          |
| Reason     | Why was that judgment made    | `because of ~`, `based on ~`             | degradation because of communication quality deterioration |


### 5.5 Performer vs Item — agent and object

If it **performs** an action, it is a Performer; if it **flows between actions or is used** by them, it is an Item. The same noun can be either, depending on context. "Battalion server" is a Performer (recipient, `provided_to`) when it is the target that receives a report; when analysis results from the server flow onward, those results are an Item.

### 5.6 One action or several?

- `receives and processes` → 2 (two verbs)
- `the company commander shares, and TDSS transmits` → 2 (two agents)
- `stops the video stream, switches to Edge AI mode, and transmits summary tracks` → 3 (three verbs, different inputs and outputs). The gold groups this into a single action, `Drone Edge AI analysis mode switch`, and expresses the rest with uses/produces item. Either way, be **consistent**, and indicate uncertainty with confidence.

---

## 6. Relation type catalog

These are the `relation_type`s and allowed directions (source → target) from the original schema's "Slot Relation contract". The validator (`--validate`) flags combinations outside this table as `UNKNOWN_RELATION_TYPE` / `RELATION_ENDPOINT_TYPE` errors. Relations read by the EFFBD converter are marked ✔.

**Scope and structure**

| relation_type | source → target | Meaning | EFFBD conversion |
| --- | --- | --- | --- |
| `has_episode` | Scenario → Episode | The scenario contains the episode | (document structure) |
| `contains_action` | Episode → Action | The episode contains the action. Every action belongs to exactly one episode | ✔ nested `action { … }` |
| `has_situation` | Scenario / Episode → Situation | Owns the set of states that are true during that scope | |
| `entry_situation` / `exit_situation` | Episode → Situation | Boundary state at the start or end of the episode | |
| `has_part` | Performer → Performer | Parent and child performers | (structure; part nesting planned) |

**Behavior axis**

| relation_type | source → target | Meaning | EFFBD conversion |
| --- | --- | --- | --- |
| `performed_by` | Action → Performer | Acting agent | ✔ `allocate` |
| `acts_on` | Action → Item / Performer | Target of the action | |
| `provided_to` | Action → Performer / Item | Recipient of the output | ✔ `in item` (when it is an item) |
| `uses_item` | Action → Item | Used as input | ✔ `in item` |
| `produces_item` | Action → Item | Produced as output | ✔ `out item` |
| `flow_source` / `flow_target` | Flow → Action | The two ends of the flow | ✔ `succession` |
| `carries_item` | Flow → Item | Item carried by the object flow | ✔ `flow from A.item to B.item` |
| `controls_flow` | Control → Flow | Applies a guard or structure to this flow | ✔ guarded succession |
| `temporal_before` / `_after` / `_during` / `_while` / `_overlaps` / `_starts_with` / `_ends_with` | Action / Transition / Event → Action / Transition / Event | Temporal relation (between KerML Occurrences) | ✔ only Action→Action `temporal_before` becomes succession |

**State axis**

| relation_type | source → target | Meaning | EFFBD conversion |
| --- | --- | --- | --- |
| `has_state_value` | Situation → State Value | Composition of the state set (at least one per Situation) | |
| `from_situation` / `to_situation` | Transition → Situation | The two ends of the transition (exactly one each) | |
| `observes` | Observation → Event / State Value | What the observation confirmed (at least one per Observation) | |
| `triggers` | Event → Transition / Action | The event causes a transition / immediately starts an action | |
| `causes_event` | Event → Event | Event causality | |
| `originates_event` | Performer → Event | The agent that caused the event | |
| `causes` | Action → Transition | The action causes a state transition | |

**Explanation and rules / semantic extension**

| relation_type | source → target | Meaning | EFFBD conversion |
| --- | --- | --- | --- |
| `constrained_by` | Action / Transition → Constraint | Applies a constraint | |
| `has_goal` | Scenario / Action / Reason → Goal | Goal or objective | |
| `has_reason` | Action / Transition → Reason | Reason | |
| `has_evidence` | Reason → Observation | Observation that supports the reason. Action → Observation only through this path | |
| `has_binding` | Domain Extension Rule → Semantic Binding | The rule contains the binding | |
| `binds_to` | Semantic Binding → Action / Performer / Item / Event / State Value / Situation / Transition | Concept link | |
| `custom` | Any → Any | A meaning not listed above. `custom_relation_type` is required | |

A single relation line always has the same shape.

```json
{ "relation_id": "MUMT_GT_REL_112", "source_slot_id": "MUMT_EP_EW_DEGRADATION", "relation_type": "contains_action",
  "target_slot_id": "MUMT_A_SWITCH_EDGE_MODE", "evidence_level": "explicit", "confidence": 1.0 }
```

Use `custom` only for meanings that the table above cannot express, and even then always write `custom_relation_type` (missing → `CUSTOM_TYPE_MISSING` error; unregistered value → `CUSTOM_TYPE_NOT_REGISTERED` warning). If you use `custom` for the same meaning more than once, the rule is to promote it into the contract; do not invent a different name for each scenario. `supports_action`, `triggers_action`, `triggers_local_stop`, `results_in_situation`, and `action_target` from the old gold have all been replaced with the canonical types above. `observed_on_performer` (the observer is the Observation's `observer_text` attribute) and `collaborates_with` (work that two performers do together is expressed as each one's Action + `performed_by`) were resolved without relations.

---

## 7. Full decomposition of one sentence

This is the original schema's compound sentence example written out completely in JSON.

> `When TDSS detects that the packet loss rate exceeds 30% for 10 seconds, it switches from the normal communication state to the limited communication state to maintain survivability-focused functions, and replaces the drone video stream with summary track data.`

```json
{
  "performers": [{ "performer_id": "P_TDSS", "label": "TDSS" }],
  "observations": [{ "observation_id": "OBS_LOSS", "label": "Detection of packet loss rate above 30% for 10 seconds", "observer_text": "TDSS" }],
  "events": [{ "event_id": "EVT_LOSS", "label": "Packet loss rate above threshold persisting", "event_type": "communication" }],
  "constraints": [{ "constraint_id": "C_LOSS", "label": "Loss rate > 30%, 10 seconds or more", "constraint_type": "duration_limit",
                    "expression_text": "packet_loss_rate > 30% and duration >= 10 s" }],
  "goals": [{ "goal_id": "G_SURV", "label": "Maintain survivability-focused functions", "goal_type": "mission" }],
  "reasons": [{ "reason_id": "R_LOSS", "label": "Mode switch due to detected loss rate exceedance", "reason_type": ["cause", "evidence"] }],
  "situations": [{ "situation_id": "SIT_NORMAL", "label": "Normal communication state" },
                 { "situation_id": "SIT_LIMITED", "label": "Limited communication state" }],
  "state_values": [{ "state_value_id": "SV_NORMAL",  "label": "Communication mode=normal",     "variable": "communication mode", "value": { "raw": "normal", "normalized": "normal", "value_type": "enum" } },
                   { "state_value_id": "SV_LIMITED", "label": "Communication mode=limited",     "variable": "communication mode", "value": { "raw": "limited", "normalized": "limited", "value_type": "enum" } },
                   { "state_value_id": "SV_VIDEO",   "label": "Data mode=video",   "variable": "data mode", "value": { "raw": "video stream", "normalized": "video_stream", "value_type": "enum" } },
                   { "state_value_id": "SV_TRACK",   "label": "Data mode=summary track", "variable": "data mode", "value": { "raw": "summary track", "normalized": "summarized_track", "value_type": "enum" } }],
  "transitions": [{ "transition_id": "TR_N2L", "label": "Normal communication → limited communication", "change_kind": ["mode_change"],
                    "guard": { "text": "Loss rate above 30% persisting for 10 seconds" } }],
  "actions": [{ "action_id": "A_SWITCH", "label": "Switch to limited communication mode" },
              { "action_id": "A_REPLACE", "label": "Replace video stream with summary track" }],
  "items": [{ "item_id": "I_VIDEO", "label": "Drone video stream", "item_type": "sensor_stream" },
            { "item_id": "I_TRACK", "label": "Summary track data", "item_type": "track_payload" }],
  "flows": [{ "flow_id": "F_SWITCH_REPLACE", "label": "Replace after switch", "flow_kind": "control_flow" }],
  "controls": [{ "control_id": "CTRL_LOSS", "label": "Loss rate condition branch", "control_type": "decision", "guard_texts": ["Packet loss rate above 30% persisting for 10 seconds"] }],
  "slot_relations": [
    { "relation_id": "r01", "source_slot_id": "OBS_LOSS",  "relation_type": "observes",       "target_slot_id": "EVT_LOSS" },
    { "relation_id": "r02", "source_slot_id": "EVT_LOSS",  "relation_type": "triggers",       "target_slot_id": "TR_N2L" },
    { "relation_id": "r03", "source_slot_id": "TR_N2L",    "relation_type": "from_situation", "target_slot_id": "SIT_NORMAL" },
    { "relation_id": "r04", "source_slot_id": "TR_N2L",    "relation_type": "to_situation",   "target_slot_id": "SIT_LIMITED" },
    { "relation_id": "r05", "source_slot_id": "SIT_NORMAL",  "relation_type": "has_state_value", "target_slot_id": "SV_NORMAL" },
    { "relation_id": "r06", "source_slot_id": "SIT_NORMAL",  "relation_type": "has_state_value", "target_slot_id": "SV_VIDEO" },
    { "relation_id": "r07", "source_slot_id": "SIT_LIMITED", "relation_type": "has_state_value", "target_slot_id": "SV_LIMITED" },
    { "relation_id": "r08", "source_slot_id": "SIT_LIMITED", "relation_type": "has_state_value", "target_slot_id": "SV_TRACK" },
    { "relation_id": "r09", "source_slot_id": "TR_N2L",    "relation_type": "constrained_by", "target_slot_id": "C_LOSS" },
    { "relation_id": "r10", "source_slot_id": "A_SWITCH",  "relation_type": "performed_by",   "target_slot_id": "P_TDSS" },
    { "relation_id": "r11", "source_slot_id": "A_REPLACE", "relation_type": "performed_by",   "target_slot_id": "P_TDSS" },
    { "relation_id": "r12", "source_slot_id": "A_REPLACE", "relation_type": "uses_item",      "target_slot_id": "I_VIDEO" },
    { "relation_id": "r13", "source_slot_id": "A_REPLACE", "relation_type": "produces_item",  "target_slot_id": "I_TRACK" },
    { "relation_id": "r14", "source_slot_id": "A_SWITCH",  "relation_type": "has_goal",       "target_slot_id": "G_SURV" },
    { "relation_id": "r15", "source_slot_id": "A_SWITCH",  "relation_type": "has_reason",     "target_slot_id": "R_LOSS" },
    { "relation_id": "r16", "source_slot_id": "F_SWITCH_REPLACE", "relation_type": "flow_source", "target_slot_id": "A_SWITCH" },
    { "relation_id": "r17", "source_slot_id": "F_SWITCH_REPLACE", "relation_type": "flow_target", "target_slot_id": "A_REPLACE" },
    { "relation_id": "r18", "source_slot_id": "CTRL_LOSS", "relation_type": "controls_flow",  "target_slot_id": "F_SWITCH_REPLACE" }
  ]
}
```

One sentence produced 13 slot types, 17 slots, and 18 relations. Of these, EFFBD draws 1 performer, 2 actions, 2 items, 1 flow, 1 control, and 8 relations (r10~r13, r16~r18). The rest (observation, event, state, transition, constraint, goal, reason) are not drawn, but they are **material for the state view and for traceability**, so do not discard them.

---

## 8. What the EFFBD converter actually reads

This matches `src/t2a_js/README.md` §3. If the conversion result looks wrong, start here.


| Symptom                                         | Cause                                                               | Fix                                                  |
| ------------------------------------------ | ---------------------------------------------------------------- | ------------------------------------------------------ |
| Node name is `Function_3`                        | The slot has no `label` (only `name` or `title`)                            | Use `label`. Converter v0.3 also reads `name` as a fallback, but the schema's authoritative field is `label` |
| Episodes are not nested; output is flat                         | Some action is not grouped into any episode by `contains_action`                  | Assign every action to an episode                                    |
| No `allocate`                             | Missing `performed_by` relation (only `primary_actor_text`)                  | Add the relation                                                  |
| No `flow from … to …`                     | `flow_kind` does not contain `object`, or `carries_item` is missing                     | `flow_kind: "object_flow"` + `carries_item`            |
| No guard attached                                   | The control has no `guard_texts`, or `controls_flow` does not point to the flow         | Fill in both                                                 |
| An action does not start from `start` / validator UNREACHABLE | Every action has an incoming edge (including loop back-edges)                       | At least one first action with no incoming edge is required. loop is planned (decide/merge)      |
| An item is missing from the output                               | It is not connected to any action by `uses_item`/`produces_item`/`carries_item` | Add the relation                                                  |


Validation commands:

```powershell
# Convert + validate. schema: relation contract (type, direction, custom, state axis consistency) / effbd: reachability · item flow · performer allocation
node src/t2a_js/convert_t2a_to_sysml.js my_T2A-ESS.json -o my.sysml --validate
python src/convert_t2a_to_sysml.py my_T2A-ESS.json --validate-only     # validate only, without writing .sysml
# Load into the editor parser (selab-rust-lsp) to check nodes, edges, and diagnostics (when the binary is available)
cd src/t2a_js && npm run lsp
```

`schema:` check codes and their meanings:

| Code | Severity | Meaning |
| --- | --- | --- |
| `UNKNOWN_RELATION_TYPE` | error | A `relation_type` not in the Chapter 6 tables |
| `RELATION_ENDPOINT_TYPE` | error | A source/target slot type not allowed for that relation |
| `DANGLING_RELATION_ENDPOINT` | error | An id at either end of the relation matches no slot |
| `DUPLICATE_SLOT_ID` | error | The same id appears in two collections |
| `CUSTOM_TYPE_MISSING` / `CUSTOM_TYPE_NOT_REGISTERED` | error / warning | `custom` has no `custom_relation_type` / unregistered value |
| `TRANSITION_ENDPOINTS` | error | A Transition does not have exactly one `from_situation` and one `to_situation` |
| `SITUATION_NO_STATE_VALUE` / `OBSERVATION_NO_OBSERVES` / `ISOLATED_EVENT` | warning | A state axis slot is floating without connections |
| `ACTION_NO_EPISODE` / `ACTION_MULTI_EPISODE` | warning | An action belongs to 0 / 2 or more episodes (cause of the flat fallback) |
| `AUX_TEXT_WITHOUT_RELATION` | warning | Only the auxiliary `*_text` field exists, without the corresponding relation (`entry_situation`, `causes`, `has_reason`, `has_evidence`) |

---

## 9. Self-check checklist for extraction results

- [ ] Every slot has `*_id` and `label`.
- [ ] No field inside a slot points to another slot through `*_id`/`*_ids`. All relations are in `slot_relations`.
- [ ] Every `source_slot_id` and `target_slot_id` in `slot_relations` points to an actual slot id.
- [ ] There is one scenario, and every action is grouped into some episode by `contains_action`.
- [ ] Every action has `performed_by` (otherwise the validator issues a warning).
- [ ] Every flow has `flow_source` and `flow_target`, and every object flow has `carries_item`.
- [ ] Conditional expressions ("if ~", "while ~") are kept as Control + `guard_texts` + `controls_flow`.
- [ ] "Simultaneously" and "when all are complete" are kept as Control (fork/join).
- [ ] Detection and measurement expressions are kept as Observations and connected through `observes` to the Event/State Value they confirmed. If a detection is a step in the flow, an Action was also created and connected with a Flow.
- [ ] If an observation is the basis for an action or judgment, it is connected as Action `—has_reason→` Reason `—has_evidence→` Observation (no direct Observation → Action relation). If it is a reaction action, it is Event `—triggers→` Action.
- [ ] State changes are kept as Transition + from/to Situation. If an action causes the transition, Action `—causes→` Transition was added.
- [ ] Each Situation is attached through `has_situation` to the Scenario/Episode that owns its span and has at least one `has_state_value`.
- [ ] There are no `custom` relations. If there are, each has `custom_relation_type`, and it was confirmed that the meaning cannot be expressed with a canonical type.
- [ ] Numeric conditions are separated into Constraint, purposes into Goal, and reasons into Reason.
- [ ] The same value is not copied into two slots.
- [ ] Source sentences are in `source_units`, and each slot's `source_ref` points to them.
- [ ] `--validate` reports 0 errors.

---

## 10. Frequently asked questions

**Q. Must all 17 slots be filled?**
No. In the default output mode (`compact_canonical`), empty arrays are omitted. Do not invent content that is not in the source text. But do not push existing content into a different slot either.

**Q. What is `confidence_by_llm` for?**
It is the LLM's self-assessed confidence. It is not the probability of being correct; use it as a review priority and a signal for corrections. Do not discard or accept a slot based on it alone.

**Q. If the gold and an LLM extraction differ, which is right?**
The gold is a reference that a person created after reading the entire source text. But as in §5.6, the level of decomposition is a matter of choice, so the gold is also just one interpretation. When comparing, check **whether the relation graphs state the same facts** rather than the number of slots.

**Q. Why extract slots that are not drawn in EFFBD?**
Situation, State Value, and Transition are material for the state view; Constraint and Goal are material for requirements export; Observation and Reason are traceability evidence. The converter currently produces only EFFBD, but the schema holds more than that.

**Q. How does it differ from T2M?**
T2A-ESS already captures information as diagram elements (performer, action, flow, episode) at the extraction stage. T2M keeps only neutral propositions and evidence at the extraction stage and defers the choice of SysML elements. The comparison is in `docs/case-study/mumt-t2a-vs-t2m/`.

---

## References

- Original schema: `docs/Text2Activity-Extraction-Slot-Schema.md`
- Extraction prompt: `docs/Text2Activity-LLM-Slot-Extraction-Prompt.md` (examples corrected to use `label`)
- Converter rules: `src/t2a_js/README.md`, `docs/T2A-to-EFFBD-Converter-Guide.md`
- Actual gold: `data/ground-truth/mumt/mumt.gold.json`
- Full minimal example: `src/examples/coffee_order_T2A-ESS.json` → `coffee_order.sysml`
