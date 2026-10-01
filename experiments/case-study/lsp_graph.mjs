// Convert a T2A-ESS JSON with the repository converter, parse it with selab-rust-lsp,
// and save the SysML text, the LSP diagram graph, the diagnostics, and the round-trip check result.
// usage: node lsp_graph.mjs <in.json> <out-prefix>
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const T2A = process.env.T2A_ROOT || "G:/SW/SW-SELab/selab-research-t2sysml/text2activity";
const imp = (p) => import(pathToFileURL(path.join(T2A, p)).href);
const { MiniLsp, analyze, checkCase } = await imp("src/t2a_js/tools/lsp_check.js");
const { loadModelFromObject, convertModel, validateEffbd, summarize } = await imp("src/t2a_js/t2a_sysml/index.js");

const [inFile, prefix] = process.argv.slice(2);
const model = loadModelFromObject(JSON.parse(readFileSync(inFile, "utf8").replace(/^\uFEFF/, "")));
const sysml = convertModel(model, { immTags: true });
writeFileSync(`${prefix}.sysml`, sysml, "utf8");

const lsp = new MiniLsp();
await lsp.initialize();
let analysis;
try {
  analysis = await analyze(lsp, sysml, path.basename(prefix));
} finally {
  await lsp.shutdown();
}
const check = checkCase({ id: path.basename(prefix), sysml, model, expect: { performers: model.collection("performers").length } }, analysis);
const v = summarize(validateEffbd(model));
writeFileSync(`${prefix}.graph.json`, JSON.stringify(analysis.graph, null, 2), "utf8");
writeFileSync(`${prefix}.check.json`, JSON.stringify({ ok: check.ok, problems: check.problems, stats: check.stats, diagnostics: check.diagnostics, validator: v }, null, 2), "utf8");
console.log(path.basename(prefix), check.ok ? "LSP ok" : "LSP FAIL", JSON.stringify(check.stats), `validator ${v.errors}E/${v.warnings}W`);
for (const p of check.problems) console.log("  -", p);
