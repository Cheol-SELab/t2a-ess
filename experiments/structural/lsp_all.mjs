// Structural layers on the seven reported T2A-ESS outputs (3 gold, 4 diagnostic): EFFBD conversion, language-server
// round trip (checks (i), (iii)-(v), and (ii) with the performer count), EFFBD validator, contract (schema) validator,
// standard state view and its language-server diagnostics, and the EFFBD validator's warning codes.
// usage: node experiments/structural/lsp_all.mjs <data-root: data> <out.json>
// (SELAB_LSP_BIN: path to the sysml-lsp binary of the EFFBD editor)
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const imp = (p) => import(pathToFileURL(path.join(ROOT, p)).href);
const { MiniLsp, analyze, checkCase, LSP_BIN } = await imp("src/t2a_js/tools/lsp_check.js");
const { loadModelFromObject, convertModel, convertStateModel, validateEffbd, validateSchema, summarize } = await imp("src/t2a_js/t2a_sysml/index.js");

export const FILES = [
  "gold/mumt/mumt.gold.json", "gold/nghe/nghe.gold.json", "gold/av/av.gold.json",
  "diagnostic/mumt/mumt.nongold.json", "diagnostic/mumt/mumt.exhaustive.json",
  "diagnostic/nghe/nghe.nongold.json", "diagnostic/nghe/nghe.exhaustive.json",
];
const [dataRoot, out] = process.argv.slice(2);
const lsp = new MiniLsp();
await lsp.initialize();
const rows = [];
try {
  for (const f of FILES) {
    const model = loadModelFromObject(JSON.parse(readFileSync(path.join(path.resolve(dataRoot), f), "utf8").replace(/^﻿/, "")));
    const id = path.basename(f, ".json");
    const sysml = convertModel(model, { immTags: true });
    const r = checkCase({ id, sysml, model, expect: { performers: model.collection("performers").length } }, await analyze(lsp, sysml, id));
    const issues = validateEffbd(model);
    const v = summarize(issues);
    const codes = {};
    for (const i of issues) codes[i.code] = (codes[i.code] ?? 0) + 1;
    const sch = validateSchema(model);
    const schema = { errors: sch.filter((i) => i.severity === "error").length, warnings: sch.filter((i) => i.severity === "warning").length, codes: {} };
    for (const i of sch) schema.codes[`${i.severity}:${i.code}`] = (schema.codes[`${i.severity}:${i.code}`] ?? 0) + 1;
    const stateText = convertStateModel(model);
    const sa = await analyze(lsp, stateText, id + ".state");
    const stateDiag = { error: 0, warning: 0, hint: 0 };
    for (const d of sa.diagnostics) { const k = { 1: "error", 2: "warning", 3: "info", 4: "hint" }[d.severity] ?? d.severity; stateDiag[k] = (stateDiag[k] ?? 0) + 1; }
    rows.push({ file: f, lspOk: r.ok, problems: r.problems, stats: r.stats, validator: { errors: v.errors, warnings: v.warnings, codes },
      schema, state: { lines: stateText.split("\n").length, diagnostics: stateDiag }, sysmlLines: sysml.split("\n").length,
      nestedEpisodeBlocks: (sysml.match(/^ {4}#Function\n {4}action '|^ {4}action '/gm) ?? []).length,
      counts: Object.fromEntries(["episodes", "performers", "actions", "items", "flows", "controls"].map((c) => [c, model.collection(c).length])) });
  }
} finally {
  await lsp.shutdown();
}
console.log(`LSP: ${LSP_BIN}`);
for (const r of rows) {
  const d = r.stats.diagnostics;
  console.log([path.basename(r.file, ".json").padEnd(18), r.lspOk ? "ok" : "FAIL", `lines=${r.sysmlLines}`, `nodes=${r.stats.nodes}`, `succ=${r.stats.succession}`,
    `fork=${r.stats.ForkNode ?? 0}`, `join=${r.stats.JoinNode ?? 0}`, `flow=${r.stats.flow}`, `alloc=${r.stats.allocation}`,
    `diag=${d.error ?? 0}/${d.warning ?? 0}/${d.hint ?? 0}`, `validator=${r.validator.errors}E/${r.validator.warnings}W`, `schema=${r.schema.errors}E/${r.schema.warnings}W`,
    `state=${r.state.lines}l ${r.state.diagnostics.error}/${r.state.diagnostics.warning}/${r.state.diagnostics.hint}`].join("  "));
  console.log("    validator codes " + JSON.stringify(r.validator.codes) + "  schema codes " + JSON.stringify(r.schema.codes));
  for (const p of r.problems) console.log(`    - ${p}`);
}
writeFileSync(out, JSON.stringify(rows, null, 2), "utf8");
