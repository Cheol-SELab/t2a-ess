#!/usr/bin/env node
/**
 * Validate converter output against the selab-rust-lsp SysML server (the same parser
 * the EFFBD editor uses). For every synthetic case (test/cases.js) and every gold /
 * example fixture:
 *
 *   1. convert T2A-ESS -> EFFBD SysML with the JS converter
 *   2. didOpen the text on the LSP, fetch diagnostics (selab.diagnostics.filter)
 *   3. fetch the diagram graph (selab.diagram.getGraphEx)
 *   4. assert: no ERROR diagnostics (except allow-listed), node/edge counts match the
 *      case expectations, every succession endpoint resolves, every flow endpoint is
 *      fully qualified (i.e. its item port was declared), allocation count matches.
 *
 * Usage:
 *   node tools/lsp_check.js [--json out.json] [--only id,id] [--verbose]
 * Env:
 *   SELAB_LSP_BIN  path to sysml-lsp(.exe); default = sibling repo release build
 */
import { spawn } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

import { convertModel, convertStateModel, loadModelFromObject, validateEffbd, summarize } from "../t2a_sysml/index.js";
import { CASES } from "../test/cases.js";
import { GOLD_JSONS, COFFEE, NON_GOLD } from "../test/fixtures.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const DEFAULT_LSP_BIN = path.resolve(
  HERE, "..", "..", "..", "..", "..", "selab-ex-system-modeler", "packages", "selab-rust-lsp", "target", "release",
  process.platform === "win32" ? "sysml-lsp.exe" : "sysml-lsp",
);
export const LSP_BIN = process.env.SELAB_LSP_BIN || DEFAULT_LSP_BIN;
export const lspAvailable = () => existsSync(LSP_BIN);

// ---------------------------------------------------------------------------
// Minimal JSON-RPC-over-stdio LSP client (no dependency on the LSP repo's test lib).
// ---------------------------------------------------------------------------
export class MiniLsp {
  constructor(bin = LSP_BIN, { timeoutMs = 30000 } = {}) {
    this.proc = spawn(bin, [], { stdio: ["pipe", "pipe", "pipe"] });
    this.buf = Buffer.alloc(0);
    this.nextId = 1;
    this.pending = new Map();
    this.diagnostics = new Map(); // uri -> Diagnostic[]
    this.timeoutMs = timeoutMs;
    this.proc.stdout.on("data", (d) => { this.buf = Buffer.concat([this.buf, d]); this._drain(); });
    this.proc.stderr.on("data", () => {});
  }
  _drain() {
    for (;;) {
      const sep = this.buf.indexOf("\r\n\r\n");
      if (sep === -1) break;
      const m = this.buf.subarray(0, sep).toString("ascii").match(/Content-Length:\s*(\d+)/i);
      if (!m) { this.buf = this.buf.subarray(sep + 4); continue; }
      const len = Number(m[1]);
      if (this.buf.length < sep + 4 + len) break;
      const body = this.buf.subarray(sep + 4, sep + 4 + len).toString("utf8");
      this.buf = this.buf.subarray(sep + 4 + len);
      let msg;
      try { msg = JSON.parse(body); } catch { continue; }
      if (msg.method && msg.id !== undefined) { // server -> client request
        const result = msg.method === "workspace/configuration" ? (msg.params?.items ?? []).map(() => null) : null;
        this._send({ jsonrpc: "2.0", id: msg.id, result });
      } else if (msg.method) { // notification
        if (msg.method === "textDocument/publishDiagnostics") this.diagnostics.set(msg.params.uri, msg.params.diagnostics ?? []);
      } else if (this.pending.has(msg.id)) {
        const h = this.pending.get(msg.id); this.pending.delete(msg.id); h(msg);
      }
    }
  }
  _send(msg) { const j = JSON.stringify(msg); this.proc.stdin.write(`Content-Length: ${Buffer.byteLength(j)}\r\n\r\n${j}`); }
  req(method, params) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const t = setTimeout(() => { this.pending.delete(id); reject(new Error(`${method} timeout`)); }, this.timeoutMs);
      this.pending.set(id, (msg) => { clearTimeout(t); msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result); });
      this._send({ jsonrpc: "2.0", id, method, params });
    });
  }
  notify(method, params) { this._send({ jsonrpc: "2.0", method, params }); }
  async initialize() {
    await this.req("initialize", { processId: process.pid, rootUri: null, capabilities: {} });
    this.notify("initialized", {});
  }
  didOpen(uri, text) { this.notify("textDocument/didOpen", { textDocument: { uri, languageId: "sysml", version: 1, text } }); }
  didClose(uri) { this.notify("textDocument/didClose", { textDocument: { uri } }); }
  exec(command, args) { return this.req("workspace/executeCommand", { command, arguments: args }); }
  async shutdown() { try { await this.req("shutdown", {}); } catch {} this.notify("exit", {}); setTimeout(() => this.proc.kill(), 200); }
}

const settle = (ms) => new Promise((r) => setTimeout(r, ms));

/** Open `text` on the server and return { diagnostics, graph }. */
export async function analyze(lsp, text, name = "case") {
  const uri = pathToFileURL(path.join(HERE, "..", "report", "_lsp", `${name}.sysml`)).href;
  lsp.didOpen(uri, text);
  const graphResp = await lsp.exec("selab.diagram.getGraphEx", [{ uri, text, includeCst: false }]);
  const graph = graphResp?.result ?? graphResp ?? { nodes: [], edges: [] };
  // diagnostics: prefer the direct filter command (bypasses the 60ms debounce); fall back to publish.
  let diagnostics = null;
  try { const r = await lsp.exec("selab.diagnostics.filter", [{ uri }]); diagnostics = Array.isArray(r) ? r : r?.diagnostics ?? null; } catch {}
  if (diagnostics === null) { await settle(250); diagnostics = lsp.diagnostics.get(uri) ?? []; }
  lsp.didClose(uri);
  return { diagnostics, graph };
}

// ---------------------------------------------------------------------------
// Checks
// ---------------------------------------------------------------------------
const countBy = (arr, key) => arr.reduce((m, x) => ((m[x[key]] = (m[x[key]] ?? 0) + 1), m), {});
const SEV = { 1: "error", 2: "warning", 3: "info", 4: "hint" };

export function checkCase({ id, expect = {}, sysml, model }, { diagnostics, graph }) {
  const problems = [];
  const note = (msg) => problems.push(msg);
  const nodes = graph.nodes ?? [];
  const edges = graph.edges ?? [];
  const nodeKinds = countBy(nodes, "kind");
  const edgeKinds = countBy(edges, "kind");
  const ids = new Set(nodes.map((n) => n.id));

  // 1) diagnostics
  const errors = diagnostics.filter((d) => d.severity === 1);
  const allowed = expect.lspErrorsAllowed ?? [];
  const unexpected = errors.filter((d) => !allowed.some((s) => d.message.includes(s)));
  for (const d of unexpected) note(`LSP error: ${d.message} @${d.range?.start?.line + 1}`);

  // 2) node counts
  const cmp = (label, actual, want) => { if (want !== undefined && actual !== want) note(`${label}: got ${actual}, want ${want}`); };
  if (expect.actions !== undefined) {
    const rootActions = 1 + expect.actions + (expect.nested ? expect.episodes ?? 0 : 0);
    cmp("ActionUsage nodes", nodeKinds.ActionUsage ?? 0, rootActions);
  }
  cmp("PartUsage nodes", nodeKinds.PartUsage ?? 0, expect.performers);
  cmp("ForkNode nodes", nodeKinds.ForkNode ?? 0, expect.forks);
  cmp("JoinNode nodes", nodeKinds.JoinNode ?? 0, expect.joins);
  cmp("allocation edges", edgeKinds.allocation ?? 0, expect.allocations);
  cmp("flow edges", edgeKinds.flow ?? 0, expect.flows);

  // 3) succession edges resolve, and match the emitted succession lines
  const succ = edges.filter((e) => e.kind === "succession");
  for (const e of succ) {
    if (!ids.has(e.source)) note(`succession source unresolved: ${e.source}`);
    if (!ids.has(e.target)) note(`succession target unresolved: ${e.target}`);
  }
  const succLines = (sysml.match(/^\s*succession first /gm) ?? []).length;
  if (succ.length !== succLines) note(`succession edges ${succ.length} != succession lines ${succLines}`);
  const guardedEdges = succ.filter((e) => e.data?.guard || e.label || e.data?.condition).length;
  if (expect.guards !== undefined && expect.guards > 0 && guardedEdges === 0) {
    // the LSP may not surface the guard on the edge; verify in the text instead
    const g = (sysml.match(/ if '[^']*' == true then /g) ?? []).length;
    cmp("guarded successions (text)", g, expect.guards);
  }

  // 4) flow endpoints fully qualified (item port declared on both actions)
  const root = nodes.find((n) => n.kind === "ActionUsage" && !n.id.includes("::"))?.id;
  for (const e of edges.filter((e) => e.kind === "flow")) {
    for (const end of [e.source, e.target]) {
      if (root && !end.startsWith(`${root}::`)) note(`flow endpoint not fully qualified (missing item port?): ${end}`);
    }
  }

  // 5) fork/join names unique in text
  const fj = [...sysml.matchAll(/^\s*(?:fork|join) '([^']+)';/gm)].map((m) => m[1]);
  if (new Set(fj).size !== fj.length) note(`duplicate fork/join names: ${fj.join(", ")}`);

  // 6) text expectations
  for (const t of expect.expectText ?? []) if (!sysml.includes(t)) note(`missing text: ${t}`);
  for (const t of expect.forbidText ?? []) if (sysml.includes(t)) note(`forbidden text present: ${t}`);
  for (const [action, port] of expect.expectPorts ?? []) {
    const re = new RegExp(`action '${action.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}' \\{[^}]*${port.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`, "s");
    if (!re.test(sysml)) note(`missing port ${port} on action '${action}'`);
  }

  // 7) structural validator
  if (model && expect.validateErrors !== undefined) {
    const s = summarize(validateEffbd(model));
    cmp("validator errors", s.errors, expect.validateErrors);
  }

  return {
    id, ok: problems.length === 0, problems,
    stats: { nodes: nodes.length, edges: edges.length, ...nodeKinds, succession: succ.length, flow: edgeKinds.flow ?? 0, allocation: edgeKinds.allocation ?? 0,
      diagnostics: countBy(diagnostics.map((d) => ({ s: SEV[d.severity] ?? d.severity })), "s") },
    diagnostics: diagnostics.map((d) => ({ severity: SEV[d.severity] ?? d.severity, line: (d.range?.start?.line ?? -1) + 1, message: d.message })),
  };
}

/** All inputs: synthetic cases + gold/example fixtures (fixtures get loose expectations). */
export function allInputs() {
  const inputs = CASES.map((c) => ({ id: c.id, title: c.title, model: loadModelFromObject(c.model), expect: c.expect, kind: "synthetic" }));
  for (const f of [...GOLD_JSONS, COFFEE, NON_GOLD].filter(existsSync)) {
    const model = loadModelFromObject(JSON.parse(readFileSync(f, "utf8").replace(/^\uFEFF/, "")));
    inputs.push({ id: path.basename(f, ".json"), title: model.title, model, kind: "fixture",
      expect: { performers: model.collection("performers").length, validateErrors: 0 } });
  }
  return inputs;
}

export async function runAll({ only = null, immTags = true } = {}) {
  const lsp = new MiniLsp();
  await lsp.initialize();
  const results = [];
  try {
    for (const input of allInputs()) {
      if (only && !only.includes(input.id)) continue;
      const sysml = convertModel(input.model, { immTags });
      const analysis = await analyze(lsp, sysml, input.id);
      const r = checkCase({ ...input, sysml }, analysis);
      results.push({ ...r, title: input.title, kind: input.kind, sysml });
      if (input.kind === "fixture") {
        // State view (standard SysML v2 state def): no graph expectations, just
        // assert the parser emits no severity-1 diagnostics.
        const stateSysml = convertStateModel(input.model);
        const { diagnostics } = await analyze(lsp, stateSysml, `${input.id}.state`);
        const errors = diagnostics.filter((d) => d.severity === 1);
        results.push({
          id: `${input.id}.state`, title: input.title, kind: "state", sysml: stateSysml,
          ok: errors.length === 0,
          problems: errors.map((d) => `LSP error: ${d.message} @${(d.range?.start?.line ?? -1) + 1}`),
          stats: { nodes: 0, edges: 0, diagnostics: countBy(diagnostics.map((d) => ({ s: SEV[d.severity] ?? d.severity })), "s") },
          diagnostics: diagnostics.map((d) => ({ severity: SEV[d.severity] ?? d.severity, line: (d.range?.start?.line ?? -1) + 1, message: d.message })),
        });
      }
    }
  } finally {
    await lsp.shutdown();
  }
  return results;
}

// ---------------------------------------------------------------------------
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const argv = process.argv.slice(2);
  const only = argv.includes("--only") ? argv[argv.indexOf("--only") + 1].split(",") : null;
  const jsonOut = argv.includes("--json") ? argv[argv.indexOf("--json") + 1] : null;
  const verbose = argv.includes("--verbose");
  if (!lspAvailable()) { console.error(`sysml-lsp binary not found: ${LSP_BIN} (set SELAB_LSP_BIN)`); process.exit(2); }
  const results = await runAll({ only });
  const pad = (s, n) => String(s).padEnd(n);
  console.log(`LSP: ${LSP_BIN}\n`);
  console.log(`${pad("case", 34)} ${pad("ok", 5)} ${pad("nodes", 6)} ${pad("succ", 5)} ${pad("fork", 5)} ${pad("join", 5)} ${pad("flow", 5)} ${pad("alloc", 6)} diag(err/warn/hint)`);
  for (const r of results) {
    const d = r.stats.diagnostics;
    console.log(`${pad(r.id, 34)} ${pad(r.ok ? "ok" : "FAIL", 5)} ${pad(r.stats.nodes, 6)} ${pad(r.stats.succession, 5)} ${pad(r.stats.ForkNode ?? 0, 5)} ${pad(r.stats.JoinNode ?? 0, 5)} ${pad(r.stats.flow, 5)} ${pad(r.stats.allocation, 6)} ${d.error ?? 0}/${d.warning ?? 0}/${d.hint ?? 0}`);
    for (const p of r.problems) console.log(`    - ${p}`);
    if (verbose) for (const d of r.diagnostics) console.log(`    [${d.severity}] L${d.line}: ${d.message}`);
  }
  const failed = results.filter((r) => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} passed`);
  if (jsonOut) { writeFileSync(jsonOut, JSON.stringify(results.map(({ sysml, ...r }) => r), null, 2), "utf8"); console.log(`json -> ${jsonOut}`); }
  process.exit(failed.length ? 1 : 0);
}
