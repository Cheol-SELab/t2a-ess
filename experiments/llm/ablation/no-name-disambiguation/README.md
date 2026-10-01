# Converter without name disambiguation

A copy of `src/t2a_js/` in which only `t2a_sysml/converter.js` differs: it does not disambiguate names that would
repeat within one namespace of the emitted text (the `#k` suffix for such names and the payload subsetting of a
relay action's renamed output port). It is used only for the end-to-end comparison of the paper:

```sh
python experiments/llm/analysis/endtoend.py --converter experiments/llm/ablation/no-name-disambiguation --tag no-name-disambiguation
```

Result: `experiments/llm/analysis/results/endtoend_rows-no-name-disambiguation.json` (the language server rejects
40 of the 162 sealed-scenario results as duplicate definitions; 121 pass all three gates). Do not use this copy for
anything else; the four synthetic regression cases of these collisions fail with it.
