# T2A-ESS: Text2Activity Extraction Slot Schema

Research artifact of the paper *Evidence-Preserving Transformation from Natural-Language Operational Scenarios to
SysML v2 Activity and EFFBD Views* (IEEE Access, under review).

T2A-ESS is an evidence-preserving intermediate representation between natural-language operational scenarios
and SysML v2/KerML behavior models. A scenario is extracted into slots (actions, performers, items, situations,
state values, events, transitions, observations, flows, controls, constraints, goals, reasons) whose relations
are recorded in `slot_relations`; every slot cites its source text. Converters project the slot graph into an
EFFBD-oriented SysML v2 dialect and into standard SysML v2 state definitions, and validators check the relation
contract before a view is trusted.

## Contents

| Path | What |
|---|---|
| `docs/` | Schema, schema guide, relation contract, converter guide, and the ground-truth authoring prompts |
| `src/t2a_sysml/`, `src/convert_t2a_to_sysml.py` | Python converters (EFFBD SysML, state view) and validators |
| `src/t2a_js/` | JavaScript implementation (byte-identical output), state diagrams, language-server checker |
| `src/examples/` | Cafe-order example and its conversions |
| `tests/`, `src/t2a_js/test/` | Python (31) and JavaScript (149) tests, including 24 synthetic edge cases |
| `tools/` | Traceability graph and report builder, benchmark coverage check |
| `data/gold/` | Gold fixtures MUM-T, NGHE, AV with easy/medium/hard benchmark texts and coverage requirements |
| `data/gold-sg/` | Schema-granularity variants of the gold fixtures and their guideline (sensitivity analysis) |
| `data/diagnostic/` | Four non-gold/exhaustive LLM outputs used as diagnostic evidence |
| `data/sealed/` | Nine sealed synthetic scenarios and their gold fixtures |
| `experiments/structural/` | Structural evaluation of the seven reported outputs, editor rendering |
| `experiments/llm/` | LLM extraction experiment: prompts, runner, scorer, runs, analyses (`analysis/results/SUMMARY.md`) |
| `experiments/llm/ablation/` | The converter without name disambiguation, for the end-to-end comparison |
| `experiments/case-study/` | MUM-T and NGHE case studies (EFFBD and state views of the paper's figures) |

## Running

Requirements: Python 3.11 (numpy, scipy; the scorer also needs torch and transformers for
`intfloat/multilingual-e5-large`; the case study needs pymupdf and Graphviz), Node.js 20, and, for the
language-server checks, the `sysml-lsp` binary of the SELab EFFBD editor (`SELAB_LSP_BIN`). The LLM runs use
the Claude CLI (`claude -p`) with the isolation flags of `experiments/common/claude_cli.py`.

```sh
python -m unittest discover -s tests                     # Python tests
(cd src/t2a_js && node --test "test/**/*.test.js")       # JavaScript tests (+ LSP round trip with SELAB_LSP_BIN)
python tools/validate_coverage.py                        # benchmark coverage, 3 domains x 3 difficulties
python experiments/structural/run_structural.py          # structural evaluation of the seven reported outputs
python experiments/case-study/make_case_study.py . experiments/case-study/outputs   # case-study views
python experiments/llm/make_inputs.py                    # LLM inputs and scorer manifest
python experiments/llm/run_llm.py --condition corrected --models claude-sonnet-5 claude-opus-5-5 \
       --inputs PORT_sealed DC_sealed FIRE_sealed GREEN_sealed WATER_sealed BLACKOUT_sealed TUNNEL_sealed COLD_sealed SHIP_sealed --repeats 9
python experiments/llm/analysis/stability.py             # accuracy and run-to-run stability (sealed)
```

The runs of the paper are included under `experiments/llm/runs/` (every attempt with its raw answer and cost).

## Citing

The version submitted with the paper is tagged `v1.0-submission`. Please cite the paper and this tag:

> C. Y. Park, S. Matsumoto, J. Choi, J. Jang, J. Cho, and J. Lee, "Evidence-Preserving Transformation from
> Natural-Language Operational Scenarios to SysML v2 Activity and EFFBD Views," IEEE Access, under review, 2026.
> Artifact: https://github.com/Cheol-SELab/t2a-ess (tag `v1.0-submission`).

## License

MIT (see `LICENSE`). The license covers the code, the data, and the documentation of this repository.
