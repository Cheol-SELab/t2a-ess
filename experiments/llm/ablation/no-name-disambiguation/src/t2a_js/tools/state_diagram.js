#!/usr/bin/env node
/**
 * Render a T2A-ESS model's state axis as a self-contained HTML state machine
 * diagram (thin wrapper over t2a_sysml/state_diagram.js).
 *
 *   node src/t2a_js/tools/state_diagram.js <t2a-ess.json> [-o out.html]
 *   (default output: <input stem>.state.html)
 */
import { writeFileSync } from "node:fs";
import path from "node:path";

import { loadModel, renderStateHtml } from "../t2a_sysml/index.js";

const argv = process.argv.slice(2);
const outArg = argv.indexOf("-o");
const input = argv.find((a, i) => !a.startsWith("-") && (i === 0 || argv[i - 1] !== "-o"));
if (!input) {
  console.error("usage: state_diagram.js <t2a-ess.json> [-o out.html]");
  process.exit(2);
}
const out = outArg > -1 ? argv[outArg + 1] : input.replace(/\.[^./\\]*$/, "") + ".state.html";
writeFileSync(out, renderStateHtml(loadModel(path.resolve(input))), "utf8");
console.log(`OK  ${input} -> ${out}`);
