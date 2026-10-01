// State view of a T2A-ESS JSON with the repository's own State View converter (src/t2a_js):
// standard SysML v2 state def text, its selab-rust-lsp diagnostics, the state graph IR, and the repository's SVG
// state diagram. Nothing is redrawn by this script.
// usage: node state_view.mjs <t2a-root> <in.json> <out-prefix>
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [root, inFile, prefix] = process.argv.slice(2);
const imp = (p) => import(pathToFileURL(path.join(root, p)).href);
const { MiniLsp, analyze } = await imp("src/t2a_js/tools/lsp_check.js");
const { loadModelFromObject, convertStateModel, stateGraph, stateSummary, renderStateSvg } = await imp("src/t2a_js/t2a_sysml/index.js");

const model = loadModelFromObject(JSON.parse(readFileSync(inFile, "utf8").replace(/^﻿/, "")));
const text = convertStateModel(model);
const graph = stateGraph(model);
writeFileSync(`${prefix}.state.sysml`, text, "utf8");
writeFileSync(`${prefix}.state.graph.json`, JSON.stringify(graph, null, 2), "utf8");
writeFileSync(`${prefix}.state.svg`, renderStateSvg(graph), "utf8");

const lsp = new MiniLsp();
await lsp.initialize();
let a;
try {
  a = await analyze(lsp, text, path.basename(prefix) + ".state");
} finally {
  await lsp.shutdown();
}
const SEV = { 1: "error", 2: "warning", 3: "info", 4: "hint" };
const diagnostics = a.diagnostics.map((d) => ({ severity: SEV[d.severity] ?? d.severity, line: (d.range?.start?.line ?? -1) + 1, message: d.message }));
const counts = {};
for (const d of diagnostics) counts[d.severity] = (counts[d.severity] ?? 0) + 1;
const out = { lines: text.split("\n").length, summary: stateSummary(model), diagnostics: counts, diagnosticList: diagnostics };
writeFileSync(`${prefix}.state.check.json`, JSON.stringify(out, null, 2), "utf8");
console.log(path.basename(prefix), "state lines", out.lines, "diag", JSON.stringify(counts), "summary", JSON.stringify(out.summary));
