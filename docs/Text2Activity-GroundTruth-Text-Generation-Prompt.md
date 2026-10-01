# Text2Activity Ground Truth Text Generation Prompt

## Purpose

This prompt is the **second stage** of ground truth construction.

It takes as input the **gold slot model (gold model)** produced by `Text2Activity-GroundTruth-Slot-Authoring-Prompt.md` (Prompt 1), and generates **natural unstructured scenario text** that serves as test input for the forward extractor.

```
gold T2A-ESS JSON  ──(this prompt)──▶  unstructured input text (.md) + gold JSON with text filled in
```

This text is later fed into the forward extraction prompt (`Text2Activity-LLM-Slot-Extraction-Prompt.md`), and the extraction result is compared with the gold model to evaluate extractor quality (precision/recall, relation closure).

## Core Principle: Information Preservation + Natural Difficulty

The success of this stage depends on satisfying two conditions at the same time.

1. **Information preservation (completeness)**: Every slot and relation in the gold model must be **recoverable in principle** from the text. No performer, action, item, situation, event, transition, or relation may lose its supporting evidence in the text.
2. **Natural difficulty (fidelity)**: The text must not be a mechanical one-sentence-per-slot listing; it must read like an actual concept-of-operations/scenario document. It **deliberately** includes coreference, dropped subjects, temporal expressions, and compound sentences.

These two conflict. Rule: **Never delete information; only make the expression harder.**

### Atomic Information Preservation Rule

Even as difficulty increases, the atomic information in the gold must not disappear. The following information must, even in hard, be expressed directly or kept as an equivalent expression from which a single value can be derived.

- Quantitative values and units: `43 seconds`, `200ms`, `10Hz`, `30km/h`, `15%`, `72 hours`, `38,000m3`, etc.
- Individual performer identifiers: `Drone 1`, `Drone 3`, `U-EEX 1`, `U-EDT 7`, etc.
- mode/state names: `Level 3`, `Level 4`, `communication loss`, `degraded autonomous driving`, etc.
- The trigger and from/to states of a transition
- The threshold, deadline, duration, and count condition of a constraint

Qualitative expressions may be used as a supplement, but they must not replace quantitative values. For example, writing `43 seconds` only as `barely a breath` is forbidden. If needed, spell it out naturally, as in `43 seconds, that is, 17 seconds short of a minute`.

Use a referring expression only when its antecedent is uniquely resolvable from context. If several drones appear together and you then write only `one of them`, the individual performer cannot be recovered; so leave an anchor such as `Unit 1` at first, and refer to it afterwards as `the same aircraft`.

## Role

You are a Text2Activity ground truth text realizer.

You must:

- Read the gold T2A-ESS JSON.
- Produce natural, unstructured English scenario prose that expresses **every** slot and relation in the gold model.
- Deliberately introduce realistic natural-language difficulty (coreference, dropped subjects, temporal expressions, compound sentences) WITHOUT removing recoverable information.
- Preserve `source_unit_id`s: for each gold `source_unit`, realize its `planned_content` into real sentence(s), and fill that unit's `text`. You may reorder or merge units for flow, but keep the id-to-text mapping recorded.

You must NOT:

- Add new entities, actions, items, or facts that are absent from the gold model. (No content the gold does not sanction — it would corrupt precision scoring.)
- Delete or omit any gold slot's supporting information. (It would corrupt recall scoring.)
- Print slot IDs, relation types, or schema keywords inside the narrative text. The narrative must read as a human-written scenario.

## Input

```json
{
  "gold_model": { "text2activity_extraction_model": { ... } },
  "difficulty": "medium",          // easy | medium | hard (default medium)
  "style": "operational_narrative"  // operational_narrative | after_action_report | mixed
}
```

## Natural-Language Phenomena to Introduce Deliberately

Adjust the intensity according to `difficulty`, but give information preservation top priority.

### 1. Coreference (referring/anaphoric expressions)

Do not repeat the canonical performer/item/situation; refer to it with referring expressions.

- "TDSS ... after that, this system ...", "the equipment in question", "through this", "the previously mentioned threat", "the site", "the operator"
- However, each referring expression must be **uniquely resolvable** from the preceding context. It must not ambiguously refer to two targets.

### 2. Dropped subject

Subjects may be dropped where the context makes them clear. However, a dropped subject must be recoverable from the immediately preceding context.

- "Drone 1 detected a heat source. (Drone 1) Immediately maintained the track and updated the coordinates."

### 3. Temporal expressions

Turn the gold's normalized time information back into natural-language expressions.

- Duration: "for 5 minutes", "for more than a certain time"
- Count: "3 times in a row", "several times"
- deadline: "within 72 hours", "immediately", "within 30 seconds"
- Relative: "after recovery", "right after that", "once jamming began"
- Simultaneity/condition: "simultaneously", "in parallel with ~", "if delayed", "once the threshold was exceeded"

### 4. Compound sentences

Weave multiple slots into one sentence. Combine action/event/transition/reason with connectives ("and ~", "while ~", "after ~", "once ~", "because ~").

- Example: "As the state in which the packet loss rate exceeded the threshold persisted, TDSS transitioned from normal to limited communication mode to maintain survivability and replaced the video stream with summary tracks." → Observation + Event + Reason + Transition + Action + Item + Flow in one sentence.

### Intensity by Difficulty

| Phenomenon | easy | medium | hard |
| --- | --- | --- | --- |
| coreference | Rare | Moderate | Frequent, multi-level |
| Dropped subject | Almost none | Occasional | Frequent |
| Reversing temporal-expression normalization | Keep explicit numbers | Numbers + some natural-language equivalents | Preserve numbers and units + add relative/qualitative expressions |
| Slots per sentence | 1-2 | 2-4 | 3-6 |

## Output

Produce two outputs.

### 1. Unstructured test text (Markdown)

`data/gold/<k>/<k>.<difficulty>.md`

- Title + natural paragraphs/sentences. No slot IDs or schema terms.
- Follow the order of the gold's planned source units by default, but reorder/merge them if it reads more naturally.
- It must read like an actual scenario document (see the existing `data/diagnostic/*/*.text.md`).

### 2. Gold JSON linked to per-difficulty realizations

`data/gold/<k>/<k>.gold.json`

- **Same slots/relations/IDs** as the input gold model. Do not change them.
- If several difficulty levels share one gold, keep `source_units[].planned_content` as the canonical proposition and leave `text` empty.
- The slot's `source_ref` stays unchanged and continues to point to the planned unit.
- Attach `benchmark_realizations` to record which paragraph of each difficulty-level document realized which source unit.

```json
"benchmark_realizations": [
  {
    "difficulty": "hard",
    "document": "<k>.hard.md",
    "source_unit_map": [
      { "source_unit_id": "GT_L05", "paragraph_index": [1] }
    ]
  }
]
```

If you create a separate gold JSON for each difficulty level, you may fill `source_units[].text` directly in that file. Do not mix the approach of sharing one canonical gold with the approach of per-difficulty golds.

## Coverage Self-Check

Before output, walk through the gold model and check the following. If any check fails, strengthen the text before output.

- [ ] Does every `performer` appear in the text (directly or through a resolvable referring expression)?
- [ ] Are the agent, act, and target of every `action` recoverable from the text?
- [ ] Does every `item` appear?
- [ ] Is every `situation` / `state_value` / `event` / `transition` described?
- [ ] Does every relation (performed_by, from/to_situation, triggers, flow_source/target, has_reason, has_goal, etc.) have supporting evidence in some sentence of the text?
- [ ] Did you avoid adding new facts that are not in the gold?
- [ ] Is every referring expression and dropped subject uniquely resolvable from context?
- [ ] Is every `source_units[].planned_content` filled in?
- [ ] Do easy, medium, and hard each have `benchmark_realizations` that include every source unit?

## Evaluation Loop (Purpose of This Pipeline)

1. Prompt 1 → gold slot model
2. Prompt 2 (this prompt) → unstructured text + gold JSON with text filled in
3. Feed the unstructured text into `Text2Activity-LLM-Slot-Extraction-Prompt.md` (forward extractor)
4. Compare the extraction result JSON with the gold JSON → quantitative evaluation of slot/relation precision and recall, isolated slots, missing performer/transition/flow, etc.
5. Build graphs for both sides with `tools/t2a_traceability_graph.py` and cross-validate

## Final Instruction

First output the unstructured test text (Markdown), then, after a `---` separator line, output the gold JSON with text filled in. JSON must be valid JSON only.
