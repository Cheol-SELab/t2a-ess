// Render converter output with the selab-effbd-editor's own pipeline and PNG renderer, headless.
//
// Mirrors the panel-less path of EffbdPanel.processDiagramPipeline for an unbound .sysml file:
//   selab-rust-lsp getGraphEx -> normalizeGraphEx -> decodeEffbdSysML -> connectReferenceNodes
//   -> decomposeFunctionNode for every nested function that has children, in the editor's expansion
//      restore order (depth ascending, then id) -> resolveEdgeProcessPerformer -> generateGraphTopology
//   -> scripts/provide-effbd-image.mjs renderEffbdModelToDataUri (headless Chromium, editor webview assets).
// The only replaced step is the VS Code store read: instead of saved expansion states, every nested
// function is expanded (the editor's `expandContainersByDefault` override). The editor repository is not
// modified; it runs under the editor's own vitest setup (vscode mock) plus the metamodel-manager stub
// used by the editor's browser tests.
//
// Inputs: EFFBD_RENDER_JOBS = JSON array of {in, out, scale?}.
import { describe, it, expect } from "vitest";
import Module from "node:module";
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const EDITOR = "G:/SW/SW-SELab/selab-ex-system-modeler/packages/selab-effbd-editor";
const HEAVY_STUB = path.join(EDITOR, "tests/mocks/metamodel-manager-heavy-stub.js");
const HEAVY = new Set(["selab-metamodel-manager/vscode", "selab-metamodel-manager", "selab-metamodel-manager/client"]);
const JOBS = JSON.parse(process.env.EFFBD_RENDER_JOBS || "[]");

const raw = (id) => String(id ?? "").replace(/^['"]+|['"]+$/g, "");

async function renderJob(job) {
  const origResolve = Module._resolveFilename;
  Module._resolveFilename = function resolveHeavy(request, ...rest) {
    if (HEAVY.has(request)) return HEAVY_STUB;
    return origResolve.call(this, request, ...rest);
  };
  try {
    const { normalizeGraphEx, decodeEffbdSysML, resolveEdgeProcessPerformer } = await import(
      "G:/SW/SW-SELab/selab-ex-system-modeler/packages/selab-effbd-editor/src/adapters/effbdSysMLConventionAdapter/entrance.js");
    const { connectReferenceNodes } = await import(
      "G:/SW/SW-SELab/selab-ex-system-modeler/packages/selab-effbd-editor/src/abstracting-model-assembly/reference-nodes-connection.js");
    const { decomposeFunctionNode } = await import(
      "G:/SW/SW-SELab/selab-ex-system-modeler/packages/selab-effbd-editor/src/handlers/function-decomposition-handling.js");
    const { generateGraphTopology } = await import(
      "G:/SW/SW-SELab/selab-ex-system-modeler/packages/selab-effbd-editor/src/abstracting-model-assembly/graph-topology-generation.js");
    // derived from scripts/provide-effbd-image.mjs by make_capture_module.py (same render, plus element boxes)
    const { renderEffbdModelToDataUri } = await import("./provide-effbd-image.boxes.mjs");
    const { LspClient } = await import(
      "G:/SW/SW-SELab/selab-ex-system-modeler/packages/selab-effbd-editor/tests/helpers/rust-lsp-client.js");

    const sysml = readFileSync(job.in, "utf8");
    const uri = "file:///" + job.in.replace(/\\/g, "/");
    const rust = new LspClient("rust", process.env.SELAB_LSP_BIN);
    await rust.initialize();
    rust.didOpen(uri, sysml);
    const response = await rust.exec("selab.diagram.getGraphEx", [{ uri, text: sysml, includeCst: false }]);
    rust.didClose(uri);
    await rust.shutdown();

    const decoded = await decodeEffbdSysML(normalizeGraphEx(response?.result ?? response));
    let model = connectReferenceNodes(decoded).fullResult;
    const parentOf = new Map(model.nodes.map((n) => [raw(n.nodeIdentifier ?? n.id),
      n.parentFunctionNodeIdentifier == null ? null : raw(n.parentFunctionNodeIdentifier)]));
    const depth = (id) => { let d = 0; let c = parentOf.get(id); const seen = new Set();
      while (c != null && !seen.has(c)) { seen.add(c); d += 1; c = parentOf.get(c); } return d; };
    const hasChildren = new Set([...parentOf.values()].filter((p) => p != null));
    const targets = model.nodes
      .filter((n) => n.nodeElement === "FunctionNode" && n.parentFunctionNodeIdentifier != null && hasChildren.has(raw(n.nodeIdentifier)))
      .map((n) => ({ nodeId: String(n.nodeIdentifier), rawId: raw(n.nodeIdentifier) }))
      // optional: keep selected functions collapsed (job.keepCollapsed = list of id suffixes)
      .filter((t) => !(job.keepCollapsed || []).some((suffix) => t.rawId.endsWith(suffix)))
      .sort((a, b) => depth(a.rawId) - depth(b.rawId) || a.rawId.localeCompare(b.rawId));
    for (const { nodeId } of targets) model = decomposeFunctionNode(model, nodeId);
    resolveEdgeProcessPerformer(model);
    model.packageQualifiedName = decoded.packageQualifiedName || null;
    model.packageQualifiedNames = decoded.packageQualifiedNames || [];
    model.parts = decoded.parts || [];
    const topology = generateGraphTopology(model, null);

    const { dataUri, boxes } = await renderEffbdModelToDataUri(
      { model: topology.updatedModel || model, metrics: topology.metrics || {}, mode: "EFFBD", offsetStates: {}, timeColumnStates: {} },
      { deviceScaleFactor: job.scale || 2 },
    );
    expect(dataUri, "renderer returned an empty image").toBeTruthy();
    writeFileSync(job.out, Buffer.from(dataUri.replace(/^data:image\/png;base64,/, ""), "base64"));
    writeFileSync(job.out.replace(/\.png$/, ".boxes.json"), JSON.stringify({ deviceScaleFactor: 2, boxes }, null, 2), "utf8");
    const kinds = {};
    for (const n of model.nodes) kinds[n.nodeElement] = (kinds[n.nodeElement] || 0) + 1;
    const summary = { in: path.basename(job.in), out: path.basename(job.out), expanded: targets.map((t) => t.rawId), nodeKinds: kinds,
      edges: (model.edges || []).length, metrics: Object.keys(topology.metrics || {}) };
    writeFileSync(job.out.replace(/\.png$/, ".render.json"), JSON.stringify(summary, null, 2), "utf8");
    return summary;
  } finally {
    Module._resolveFilename = origResolve;
  }
}

describe("EFFBD editor headless render", () => {
  for (const job of JOBS) {
    it(path.basename(job.out), async () => {
      const s = await renderJob(job);
      console.log(JSON.stringify(s));
    }, 10 * 60_000);
  }
});
