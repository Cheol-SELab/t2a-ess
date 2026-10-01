#!/usr/bin/env node
/**
 * CLI: T2A-ESS slot JSON -> EFFBD SysML (JS port of src/convert_t2a_to_sysml.py).
 *
 *   node src/t2a_js/convert_t2a_to_sysml.js <t2a-ess.json> [-o out.sysml] [--no-imm-tags] [--validate]
 */
import { parseArgs } from "node:util";
import { existsSync, statSync, writeFileSync } from "node:fs";
import {
  convertFile,
  convertStateModel,
  loadModel,
  renderStateHtml,
  stateSummary,
  summarize,
  validateEffbd,
  validateSchema,
} from "./t2a_sysml/index.js";

function main(argv) {
  const { values, positionals } = parseArgs({
    args: argv,
    allowPositionals: true,
    options: {
      output: { type: "string", short: "o" },
      "imm-tags": { type: "boolean", default: true },
      "no-imm-tags": { type: "boolean", default: false },
      validate: { type: "boolean", default: false },
      "validate-only": { type: "boolean", default: false },
      state: { type: "boolean", default: false },
      "state-output": { type: "string" },
      "state-html": { type: "string" },
      help: { type: "boolean", short: "h", default: false },
    },
  });

  if (values.help || positionals.length !== 1) {
    console.error("usage: convert_t2a_to_sysml.js <t2a-ess.json> [-o out.sysml] [--no-imm-tags] [--validate|--validate-only] [--state [--state-output path] [--state-html path]]");
    return values.help ? 0 : 2;
  }
  const input = positionals[0];
  if (!existsSync(input) || !statSync(input).isFile()) {
    console.error(`input file not found: ${input}`);
    return 2;
  }
  const immTags = values["imm-tags"] && !values["no-imm-tags"];

  const model = loadModel(input);
  const sysml = convertFile(input, { immTags });
  const validateOnly = values["validate-only"];
  let output = null;
  if (!validateOnly) {
    output = values.output ?? input.replace(/\.[^./\\]*$/, "") + ".sysml";
    writeFileSync(output, sysml, "utf8");
  }

  const wantState = values.state || values["state-output"] !== undefined || values["state-html"] !== undefined;
  const stateSysml = wantState ? convertStateModel(model) : null;
  let stateOutput = null;
  if (wantState && !validateOnly) {
    if (values["state-output"]) {
      stateOutput = values["state-output"];
    } else {
      const b = values.output ?? input.replace(/\.[^./\\]*$/, "") + ".sysml";
      stateOutput = b.endsWith(".sysml") ? b.slice(0, -".sysml".length) + ".state.sysml" : b + ".state.sysml";
    }
    writeFileSync(stateOutput, stateSysml, "utf8");
  }
  let stateHtmlPath = null;
  if (values["state-html"] !== undefined && !validateOnly) {
    stateHtmlPath = values["state-html"];
    writeFileSync(stateHtmlPath, renderStateHtml(model), "utf8");
  }

  const base = (p) => p.split(/[\\/]/).pop();
  console.log(
    `OK  ${base(input)} -> ${output ? base(output) : "(not written)"}\n` +
      `  performers=${model.collection("performers").length} ` +
      `actions=${model.collection("actions").length} ` +
      `items=${model.collection("items").length} ` +
      `flows=${model.collection("flows").length} ` +
      `relations=${model.relations.length}\n` +
      `  sysml lines=${(sysml.match(/\n/g) ?? []).length}`,
  );
  if (wantState) {
    const s = stateSummary(model);
    console.log(
      `  state: regions=${s.regions} states=${s.states} ` +
        `transitions=${s.transitions} -> ${stateOutput ? base(stateOutput) : "(not written)"}`,
    );
    if (values["state-html"] !== undefined) {
      console.log(`  state html -> ${stateHtmlPath ? base(stateHtmlPath) : "(not written)"}`);
    }
  }
  if (values.validate || validateOnly) {
    const schemaIssues = validateSchema(model);
    const effbdIssues = validateEffbd(model);
    const ss = summarize(schemaIssues);
    const es = summarize(effbdIssues);
    console.log(
      `  validate: schema errors=${ss.errors} warnings=${ss.warnings} | ` +
        `effbd ok=${es.ok} errors=${es.errors} warnings=${es.warnings}`,
    );
    for (const i of schemaIssues) console.log(`    schema: [${i.severity}] ${i.code}: ${i.message}`);
    for (const i of effbdIssues) console.log(`    effbd: [${i.severity}] ${i.code}: ${i.message}`);
    if (ss.errors || !es.ok) return 4;
  }
  return 0;
}

process.exitCode = main(process.argv.slice(2));
