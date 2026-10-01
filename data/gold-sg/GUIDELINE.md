# Schema-granularity gold (gold-sg): authoring guideline

The benchmark gold in `data/gold/` is coarser than the schema's own rules for atomic actions
(`docs/Text2Activity-Extraction-Slot-Schema.md`, Action, "atomic action split criteria"); for example, it records
"deploy smoke and evade" as one action. The gold in this folder applies those rules to the easy texts, splitting
actions only. The benchmark runs are rescored against both golds without new LLM calls
(`experiments/llm/analysis/goldsg.py`), and both results are reported.

This gold was derived by the authors after the over-generation of the LLM runs had been diagnosed. It is not an
independent annotation.

## 1. Schema rules applied

- R1 A change of performer splits an action.
- R2 Two or more verbs give separate action candidates.
- R3 A change of input or output item splits an action.
- R4 A clear state change gives an action and a transition, linked by `causes`.
- R5 "Receive and process" gives a receiving action and a processing action.
- R6 A verification with several objects *may* be split per object (optional; not applied).
- Observation rule (Slot Relation contract): when a detection is also a step of the flow, an Action is created from
  the same source phrase in addition to the Observation; a detection, measurement, or judgment always has an
  Observation.

## 2. Operational rules (easy texts; the text takes precedence)

- G1 Unit: one verb predicate with a performer is one action. Coordinated predicates ("A checks the link and
  then reports") are separate actions. One verb with several objects ("orders A and B") is one action (R6 not
  applied). Nominalized activities ("the analysis result", "after the safety check is completed") are not actions.
- G2 Two performers sharing one verb ("the site supervisor and the ICCC confirm") give one action with two
  performers. Different verbs per performer split the action (R1).
- G3 State change: when the grammatical subject is the stateful object itself ("the TDSS switches to ... mode",
  "the vehicle transitions to ...", "all machines switch to ..."), only a transition is kept. When another performer
  brings the change about ("the vehicle control module switches to degraded mode", "the security system switches
  to the closed network", "the remote supervisor switches back to Level 4"), an action is added and linked to the
  transition by `causes` (R4).
- G4 Detection, sensing, measurement: existing Observations are kept. When the detection is linked to another
  activity by a connective or an ordering word ("then", "and so", "as soon as", "based on this"), an Action is added.
- G5 Activities of external or hostile actors (the enemy, a driver's request) and passive statements without an
  agent ("is approved", "is identified", "occurs") remain Events; no action is created.
- G6 Statements of composition, possession, goals, states, or constraints ("consists of", "aims at", "remains
  in ...", "is kept at or below 65 dB", limits without a subject), sentences about the scenario as a whole
  ("operates the MUM-T system"), and negated activities ("does not operate directly") are not actions.

## 3. Derivation procedure

- An action realized by several verbs is split. The original id stays with the fragment that carries the main verb
  of the original label; the other fragments get new ids.
- All fragments share the episode (`contains_action`) and the source unit of the original action; the performer
  follows the grammatical subject.
- A flow into the original action enters the first fragment; a flow out of it leaves the last fragment. Flows
  connect the fragments in text order.
- Item, trigger, reason, and constraint relations go to the fragment the text names; otherwise they stay with the
  fragment that keeps the original id. An event trigger of a split action moves to the first fragment, where the
  reaction starts.
- Actions stated by the text but missing in the gold are added with episode, performer, and source unit. A flow is
  added to such an action where the text marks order or dependency ("then", "as soon as", "based on this").
- Two detection Observations required by the observation rule (the ATGM launch in MUM-T, the pedestrian in NGHE)
  are added and linked to their Events by `observes`. In MUM-T, the item of "the TDSS sends the critical SA summary
  to the battalion server" is linked by `acts_on` (R3).
- No other slot (event, situation, transition, item, ...) is added or removed. The relations added are
  `performed_by`, `contains_action`, flows between fragments and to added actions, `causes`, `observes`, and the item
  relations named above. New flows and observations carry a `standard_mapping` in the form of the gold.

## 4. Checks

The derived gold has zero schema-validator errors and zero traceability-report defects
(`tools/t2a_traceability_graph.py`).
