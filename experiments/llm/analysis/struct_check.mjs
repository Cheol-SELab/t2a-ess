// Structural layers of Fig. 5 applied to LLM extractions: converter + slot-graph validator + language-server
// round trip (checks (i), (iii)-(v); (ii) with the performer count). One LSP session serves all files.
// usage: node struct_check.mjs <pred1.json> [...]   -> writes <pred>.struct.json next to each file
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const T2A = process.env.T2A_ROOT || path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "..");  // repository root
const imp = (p) => import(pathToFileURL(path.join(T2A, p)).href);
const { MiniLsp, analyze, checkCase } = await imp("src/t2a_js/tools/lsp_check.js");
const { loadModelFromObject, convertModel, validateEffbd, summarize } = await imp("src/t2a_js/t2a_sysml/index.js");

const files = process.argv.slice(2);
const lsp = new MiniLsp();
await lsp.initialize();
try {
  for (const f of files) {
    const id = path.basename(f, ".pred.json");
    const out = f.replace(/\.pred\.json$/, process.env.T2A_STRUCT_SUFFIX || ".struct.json");
    let rec;
    try {
      const model = loadModelFromObject(JSON.parse(readFileSync(f, "utf8").replace(/^\uFEFF/, "")));
      const sysml = convertModel(model, { immTags: true });
      writeFileSync(f.replace(/\.pred\.json$/, ".sysml"), sysml, "utf8");
      const r = checkCase({ id, sysml, model, expect: { performers: model.collection("performers").length } }, await analyze(lsp, sysml, id));
      const issues = validateEffbd(model);
      const codes = {};
      for (const i of issues) codes[i.code] = (codes[i.code] ?? 0) + 1;
      rec = { ok: true, lsp_ok: r.ok, lsp_problems: r.problems, lsp_errors: r.stats.diagnostics.error ?? 0, stats: r.stats,
              validator: { ...summarize(issues), codes }, nested: /^ {4}action '/m.test(sysml), sysml_lines: sysml.split("\n").length };
    } catch (e) {
      rec = { ok: false, error: String(e).slice(0, 400) };
    }
    writeFileSync(out, JSON.stringify(rec, null, 1), "utf8");
    console.log(id, rec.ok ? `lsp_ok=${rec.lsp_ok} err=${rec.lsp_errors} validator=${rec.validator.errors}E/${rec.validator.warnings}W nested=${rec.nested}` : rec.error);
  }
} finally {
  await lsp.shutdown();
}
