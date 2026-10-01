# LLM experiment — results

All runs: Claude Sonnet 5 and Claude Opus 5.5 through the isolated CLI call (`experiments/common/claude_cli.py`),
scorer v3.1 (`scoring/score.py`, embedding threshold 0.87, 0.93 for flow labels), gold fixtures of `data/`.

## Benchmark texts (easy realizations of MUM-T, NGHE, AV) — `benchmark.md`, `goldsg.json`

Repository prompt, 3 runs per cell; corrected contract, 6 runs per cell. Model rows weight the scenarios equally.

| Model | Condition | Weak-3 P / R / F1 | Slot F1 | Rel. F1 |
|---|---|---|---|---|
| Sonnet 5 | repository prompt | 0.48 / 0.10 / 0.16 | 0.68 | 0.46 |
| Opus 5.5 | repository prompt | 0.47 / 0.39 / 0.42 | 0.71 | 0.51 |
| Sonnet 5 | corrected contract | 0.38 / 0.42 / 0.39 | 0.68 | 0.46 |
| Opus 5.5 | corrected contract | 0.36 / 0.58 / 0.43 | 0.69 | 0.48 |

- Sonnet 5 with the repository prompt produced no control slot in 9 of 9 runs and no flow in 8 of 9;
  with the corrected contract it produced flows in every run and no control in 5 of 18.
- Opus 5.5 on NGHE with the repository prompt: 5–12 predicted flows, 0–1 aligned with the gold.
- Predicted actions / gold: Sonnet 25.0/14, 32.3/18, 17.3/16; Opus 27.0/14, 35.3/18, 18.7/16 (about twice the gold on MUM-T and NGHE).
- Schema-granularity gold (`goldsg.json`, `data/gold-sg/GUIDELINE.md`): predicted actions / derived gold 0.96–1.35;
  corrected contract slot F1 0.74–0.75 for both models; gain of the corrected contract over the repository prompt
  in S: +0.056 (3/6 cells) on the original gold, +0.129 (6/6) on the derived gold.

## Nine sealed scenarios, corrected contract, 9 runs per model and scenario — `stability.json`

| | Sonnet 5 | Opus 5.5 |
|---|---|---|
| Slot F1 (95% bootstrap) | 0.761 [0.741, 0.783] | 0.806 [0.791, 0.822] |
| Relation F1 | 0.635 [0.611, 0.658] | 0.656 [0.632, 0.681] |
| Weak-3 F1 | 0.723 [0.689, 0.748] | 0.775 [0.739, 0.806] |
| SD of S within a cell | 0.036 | 0.025 |
| Inter-run agreement, slots / relations | 0.851 / 0.756 | 0.925 / 0.853 |
| Cell range, slot F1 | 0.715–0.822 | 0.772–0.855 |

Mean cost per result USD 0.75; all 162 calls succeeded.

## End to end — `endtoend_rows.json`, `endtoend_rows-no-name-disambiguation.json`

The second file uses `experiments/llm/ablation/no-name-disambiguation/`, the same code without the converter's
disambiguation of names that would repeat within one namespace.

| Gate | converter | without name disambiguation |
|---|---|---|
| parse and convert | 162 | 162 |
| contract validator without error | 153 (Sonnet 81, Opus 72) | 153 |
| language server without ERROR | 162 | 122 (Sonnet 76, Opus 46) |
| all gates | 153 = 94% | 121 = 75% |

Remaining validator errors: 9 Opus results, all `UNREACHABLE_ACTION` (34) with item-balance warnings. Traceability
report: 2.9 defects per result (isolated slots 1.6, transitions without trigger 0.7, slots without source_ref 0.5).
All 40 language-server rejections without name disambiguation are duplicate definitions.

## Majority vote over six extractions (TUNNEL, COLD, SHIP) — `consensus_mix.json`

Three Sonnet + three Opus runs per group, 4 of 6 votes: mean dS +0.0385, 6/6 cells positive,
stratified permutation p = 0.0001 (20,000 permutations); USD 3.93 per consensus result vs 0.65 per single run.

## Similarity threshold — `tau_sensitivity.json`

Slot F1 (Sonnet / Opus) at tau 0.83: 0.804 / 0.832; 0.85: 0.789 / 0.822; **0.87 (frozen): 0.761 / 0.806**;
0.89: 0.730 / 0.785; 0.91: 0.688 / 0.750. The ranking of the two models and the gap to the gold do not change.

## What the remaining differences are — `errors.json`, `errors_judged.json`, `errors_summary.json`

Per result the scorer leaves 15.5 gold slots and 34.3 gold relations unmatched, and 29.3 predicted slots and 74.9
predicted relations; 68% of the missed and 74% of the extra relations follow from an unmatched endpoint slot.
Judged sample (25 per group, one author): errors among missed slots 16/25 (64%, Wilson 45–80%), extra slots 3/25,
missed relations 7/25, extra relations 1/25. Extrapolated: about 26 of the 154 differences per result
(17%) are errors, most of them omissions (device states and their transitions, controls, flows).
