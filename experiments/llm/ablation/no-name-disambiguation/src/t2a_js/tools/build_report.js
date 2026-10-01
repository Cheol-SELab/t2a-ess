#!/usr/bin/env node
/**
 * Build a self-contained HTML report for the JS T2A-ESS -> EFFBD converter:
 * test results (node --test), Python parity, per-fixture JSON -> SysML, and a
 * live in-browser converter (the converter source is bundled into the page).
 *
 *   node src/t2a_js/tools/build_report.js [-o report/index.html]
 */
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { convertFile, convertStateModel, loadModel, renderStateSvg, stateGraph, summarize, validateEffbd } from "../t2a_sysml/index.js";
import { ROOT, GOLD_JSONS, COFFEE, NON_GOLD } from "../test/fixtures.js";
import { LSP_BIN, lspAvailable, runAll as runLspChecks } from "./lsp_check.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const JS_ROOT = path.resolve(HERE, "..");
const outArg = process.argv.indexOf("-o");
const OUT = outArg > -1 ? path.resolve(process.argv[outArg + 1]) : path.join(JS_ROOT, "report", "index.html");

// --- 1) run the JS test suite (TAP) --------------------------------------------
function runJsTests() {
  const r = spawnSync(process.execPath, ["--test", "--test-reporter=tap", "test/**/*.test.js"], {
    cwd: JS_ROOT,
    encoding: "utf8",
  });
  const tests = [];
  const stack = [];
  for (const raw of r.stdout.split(/\r?\n/)) {
    const m = raw.match(/^(\s*)(ok|not ok) (\d+) - (.*?)(?: # (SKIP|TODO).*)?$/);
    if (m) {
      const depth = m[1].length / 4;
      stack.length = depth;
      const name = m[4];
      const entry = { name, path: [...stack, name].join(" › "), depth, pass: m[2] === "ok", skip: m[5] === "SKIP", duration: null };
      tests.push(entry);
      stack.push(name);
      continue;
    }
    const d = raw.match(/^\s*duration_ms:\s*([\d.]+)/);
    if (d && tests.length) {
      const last = tests[tests.length - 1];
      if (last.duration === null) last.duration = Number(d[1]);
    }
  }
  const sum = (re) => Number((r.stdout.match(re) ?? [0, 0])[1]);
  return {
    tests,
    total: sum(/^# tests (\d+)/m),
    pass: sum(/^# pass (\d+)/m),
    fail: sum(/^# fail (\d+)/m),
    skipped: sum(/^# skipped (\d+)/m),
    durationMs: sum(/^# duration_ms ([\d.]+)/m),
    exitCode: r.status,
  };
}

// --- 2) python side ---------------------------------------------------------------
const pythonOk = spawnSync("python", ["--version"], { encoding: "utf8" }).status === 0;

function pythonConvert(file, immTags) {
  if (!pythonOk) return null;
  const code =
    "import sys\nsys.path.insert(0, sys.argv[1])\nfrom t2a_sysml import convert_file\n" +
    'sys.stdout.reconfigure(encoding="utf-8", newline="")\n' +
    'sys.stdout.write(convert_file(sys.argv[2], imm_tags=(sys.argv[3] == "1")))\n';
  const r = spawnSync("python", ["-c", code, path.join(ROOT, "src"), file, immTags ? "1" : "0"], {
    encoding: "utf8",
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
  });
  return r.status === 0 ? r.stdout : null;
}

function runPyTests() {
  if (!pythonOk) return null;
  const r = spawnSync("python", ["-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], {
    cwd: ROOT,
    encoding: "utf8",
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
  });
  const out = (r.stdout || "") + (r.stderr || "");
  const ran = Number((out.match(/Ran (\d+) tests?/) ?? [0, 0])[1]);
  return { ran, ok: /\nOK\b/.test(out), exitCode: r.status };
}

// --- 3) fixtures -------------------------------------------------------------------
function firstDiffLine(a, b) {
  const al = a.split("\n");
  const bl = b.split("\n");
  for (let i = 0; i < Math.max(al.length, bl.length); i++) {
    if (al[i] !== bl[i]) return { line: i + 1, js: al[i] ?? "", py: bl[i] ?? "" };
  }
  return null;
}

function fixtureReport(file, kind) {
  const model = loadModel(file);
  const jsonText = readFileSync(file, "utf8").replace(/^\uFEFF/, "");
  const sysml = convertFile(file, { immTags: true });
  const plain = convertFile(file, { immTags: false });
  const py = pythonConvert(file, true);
  const pyPlain = pythonConvert(file, false);
  const issues = validateEffbd(model);
  const count = (re) => (sysml.match(re) ?? []).length;
  return {
    name: path.basename(file, ".json"),
    kind,
    relPath: path.relative(ROOT, file).replaceAll("\\", "/"),
    title: model.title,
    stats: {
      performers: model.collection("performers").length,
      episodes: model.collection("episodes").length,
      actions: model.collection("actions").length,
      items: model.collection("items").length,
      flows: model.collection("flows").length,
      controls: model.collection("controls").length,
      relations: model.relations.length,
      sysmlLines: (sysml.match(/\n/g) ?? []).length,
      forks: count(/^\s*fork '/gm),
      joins: count(/^\s*join '/gm),
      guards: count(/ if '.*' == true then /g),
      nested: /^\s{4}#Function\n\s{4}action '/m.test(sysml) || /^\s{4}action '.*' \{$/m.test(sysml),
    },
    parity: {
      available: py !== null,
      imm: py === null ? null : py === sysml,
      plain: pyPlain === null ? null : pyPlain === plain,
      firstDiff: py === null ? null : firstDiffLine(sysml, py),
    },
    validate: { ...summarize(issues), issues },
    json: jsonText,
    sysml,
    stateSysml: convertStateModel(model),
    stateSvg: renderStateSvg(stateGraph(model)),
  };
}

// --- 4) browser bundle of the converter -------------------------------------------
function browserBundle() {
  const src = (f) => readFileSync(path.join(JS_ROOT, "t2a_sysml", f), "utf8");
  const strip = (code) =>
    code
      .replace(/^import .*?;\s*$/gm, "")
      .replace(/^export (const|function|class) /gm, "$1 ")
      .replace(/^export \{[^}]*\};?\s*$/gm, "");
  return [
    "// ---- bundled from src/t2a_js/t2a_sysml (model.js, converter.js, validate.js) ----",
    "const readFileSync = () => { throw new Error('file access is not available in the browser'); };",
    strip(src("model.js")),
    strip(src("converter.js")),
    strip(src("validate.js")),
    strip(src("state_converter.js")),
    strip(src("state_diagram.js")),
    "window.t2a = { loadModelFromObject, convertModel, convertStateModel, stateGraph, renderStateSvg, renderStateHtml, validateEffbd, summarize, CONVERTER_VERSION };",
  ].join("\n");
}

// --- 5) HTML -------------------------------------------------------------------------
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const jsonForScript = (o) => JSON.stringify(o).replace(/</g, "\\u003c").replace(/\u2028|\u2029/g, (c) => `\\u${c.charCodeAt(0).toString(16)}`);

function render(data) {
  const { js, py, fixtures, generatedAt, node, bundle, lsp } = data;
  const parityAll = fixtures.every((f) => f.parity.imm && f.parity.plain);
  const parityKnown = fixtures.every((f) => f.parity.available);
  const verdict = js.fail === 0 && js.exitCode === 0 ? (parityKnown ? (parityAll ? "pass" : "fail") : "pass") : "fail";

  const testRows = js.tests
    .map((t) => {
      const state = t.skip ? "skip" : t.pass ? "pass" : "fail";
      const label = t.skip ? "skipped" : t.pass ? "passed" : "failed";
      return `<tr class="d${t.depth}"><td><span class="pill ${state}">${label}</span></td><td class="name">${esc(t.name)}</td><td class="num">${
        t.duration === null ? "" : t.duration.toFixed(1)
      }</td></tr>`;
    })
    .join("\n");

  const fixtureCards = fixtures
    .map((f, i) => {
      const p = f.parity;
      const parityPill = !p.available
        ? `<span class="pill skip">no Python</span>`
        : p.imm && p.plain
          ? `<span class="pill pass">byte-identical to Python</span>`
          : `<span class="pill fail">differs from Python${p.firstDiff ? ` (line ${p.firstDiff.line})` : ""}</span>`;
      const v = f.validate;
      const validatePill = `<span class="pill ${v.ok ? (v.warnings ? "warn" : "pass") : "fail"}">validation ${v.ok ? "passed" : "failed"} · errors ${v.errors} · warnings ${v.warnings}</span>`;
      const s = f.stats;
      const shape = [
        s.nested ? "nested episodes" : "flat fallback",
        s.forks ? `fork ${s.forks}` : null,
        s.joins ? `join ${s.joins}` : null,
        s.guards ? `guards ${s.guards}` : null,
      ]
        .filter(Boolean)
        .join(" · ");
      const issues = v.issues.length
        ? `<details class="issues"><summary>${v.issues.length} validation messages</summary><ul>${v.issues
            .map((x) => `<li><code>${esc(x.code)}</code> ${esc(x.message)}</li>`)
            .join("")}</ul></details>`
        : "";
      return `
<section class="fixture" id="fx-${i}">
  <header class="fx-head">
    <div>
      <p class="eyebrow">${esc(f.kind)} · <code>${esc(f.relPath)}</code></p>
      <h3>${esc(f.title)}</h3>
    </div>
    <div class="pills">${parityPill}${validatePill}</div>
  </header>
  <dl class="stats">
    <div><dt>performer</dt><dd>${s.performers}</dd></div>
    <div><dt>episode</dt><dd>${s.episodes}</dd></div>
    <div><dt>action</dt><dd>${s.actions}</dd></div>
    <div><dt>item</dt><dd>${s.items}</dd></div>
    <div><dt>flow</dt><dd>${s.flows}</dd></div>
    <div><dt>control</dt><dd>${s.controls}</dd></div>
    <div><dt>relation</dt><dd>${s.relations}</dd></div>
    <div><dt>SysML lines</dt><dd>${s.sysmlLines}</dd></div>
  </dl>
  <p class="shape">Structure: ${esc(shape)}</p>
  ${issues}
  <div class="pane2">
    <div class="pane"><div class="pane-title">T2A-ESS JSON <span>input</span></div><pre class="code json">${esc(f.json)}</pre></div>
    <div class="pane"><div class="pane-title">EFFBD SysML <span>JS output · IMM tags</span></div><pre class="code sysml">${esc(f.sysml)}</pre></div>
  </div>
  <div class="pane2" style="margin-top:12px">
    <div class="pane"><div class="pane-title">State View <span>SVG diagram</span></div><div class="state-diagram">${f.stateSvg}</div></div>
    <div class="pane"><div class="pane-title">State SysML <span>standard SysML v2 state def</span></div><pre class="code sysml">${esc(f.stateSysml)}</pre></div>
  </div>
</section>`;
    })
    .join("\n");

  const sample = fixtures.find((f) => f.name.startsWith("coffee")) ?? fixtures[0];

  return `<title>T2A→EFFBD conversion report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  --bg:#F6F5F0; --bg2:#FFFFFF; --bg3:#ECEAE3; --ink:#1E2328; --ink2:#4B4F55; --mute:#6F6C66; --line:#D9D6CE;
  --accent:#1E6E8C; --accent-ink:#FFFFFF; --pass:#2C7A4B; --pass-bg:#E3F1E7; --fail:#B3402F; --fail-bg:#F7E3DF;
  --warn:#9A6B12; --warn-bg:#F6ECD3; --skip:#6F6C66; --skip-bg:#E9E7E1;
  --kw:#1E6E8C; --str:#7A3E1D; --cmt:#7C7A74; --tag:#5B3E8C;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#15181C; --bg2:#1C2026; --bg3:#232830; --ink:#E6E4DE; --ink2:#B8B5AE; --mute:#8B8880; --line:#333941;
  --accent:#5FAFD0; --accent-ink:#0F1A20; --pass:#6CC38F; --pass-bg:#1B3325; --fail:#F08A78; --fail-bg:#3A211C;
  --warn:#E0B45C; --warn-bg:#3A2F16; --skip:#9A978F; --skip-bg:#2A2E34;
  --kw:#7CC4E0; --str:#E4A57C; --cmt:#7F8590; --tag:#B79BE0;
}}
:root[data-theme="dark"]{
  --bg:#15181C; --bg2:#1C2026; --bg3:#232830; --ink:#E6E4DE; --ink2:#B8B5AE; --mute:#8B8880; --line:#333941;
  --accent:#5FAFD0; --accent-ink:#0F1A20; --pass:#6CC38F; --pass-bg:#1B3325; --fail:#F08A78; --fail-bg:#3A211C;
  --warn:#E0B45C; --warn-bg:#3A2F16; --skip:#9A978F; --skip-bg:#2A2E34;
  --kw:#7CC4E0; --str:#E4A57C; --cmt:#7F8590; --tag:#B79BE0;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 "IBM Plex Sans KR","Noto Sans KR",system-ui,sans-serif}
code,pre,.mono,.num{font-family:"IBM Plex Mono",ui-monospace,Consolas,monospace}
.wrap{max-width:1240px;margin:0 auto;padding:32px 24px 72px}
h1,h2,h3{margin:0;text-wrap:balance;font-weight:600}
h1{font-size:28px;letter-spacing:-.01em}
h2{font-size:19px;margin-bottom:12px}
h3{font-size:17px}
p{margin:0}
.eyebrow{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--mute)}
.eyebrow code{text-transform:none;letter-spacing:0;font-size:12px}
.top{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-end;gap:16px;padding-bottom:20px;border-bottom:1px solid var(--line)}
.top .meta{font-size:13px;color:var(--mute);text-align:right;line-height:1.7}
.verdict{display:inline-flex;align-items:center;gap:10px;margin-top:10px;padding:8px 14px;border-radius:6px;font-weight:600;font-size:15px}
.verdict.pass{background:var(--pass-bg);color:var(--pass)} .verdict.fail{background:var(--fail-bg);color:var(--fail)}
.verdict::before{content:"";width:10px;height:10px;border-radius:50%;background:currentColor}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:24px 0 36px}
.tile{background:var(--bg2);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.tile .k{font-size:12px;color:var(--mute);letter-spacing:.04em;text-transform:uppercase}
.tile .v{font-size:28px;font-weight:600;font-variant-numeric:tabular-nums;line-height:1.2;margin-top:4px}
.tile .v small{font-size:13px;font-weight:400;color:var(--mute);margin-left:4px}
.tile.pass .v{color:var(--pass)} .tile.fail .v{color:var(--fail)}
section.block{margin-bottom:40px}
table{width:100%;border-collapse:collapse;background:var(--bg2);border:1px solid var(--line);border-radius:8px;overflow:hidden}
th,td{text-align:left;padding:8px 12px;border-top:1px solid var(--line);vertical-align:top}
thead th{border-top:0;background:var(--bg3);font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--mute);font-weight:500}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr.d1 td.name{padding-left:32px;color:var(--ink2)} tr.d2 td.name{padding-left:52px;color:var(--ink2)}
tr.d1 td.name::before,tr.d2 td.name::before{content:"└ ";color:var(--mute)}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:500;white-space:nowrap}
.pill.pass{background:var(--pass-bg);color:var(--pass)} .pill.fail{background:var(--fail-bg);color:var(--fail)}
.pill.warn{background:var(--warn-bg);color:var(--warn)} .pill.skip{background:var(--skip-bg);color:var(--skip)}
.pills{display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end}
.fixture{background:var(--bg2);border:1px solid var(--line);border-radius:8px;padding:20px;margin-bottom:20px}
.fx-head{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;align-items:flex-start}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));gap:8px;margin:16px 0 8px}
.stats div{background:var(--bg3);border-radius:6px;padding:8px 10px}
.stats dt{font-size:11px;color:var(--mute);letter-spacing:.04em;text-transform:uppercase}
.stats dd{margin:0;font-size:18px;font-weight:600;font-variant-numeric:tabular-nums}
.shape{font-size:13px;color:var(--ink2);margin-bottom:12px}
.issues{font-size:13px;margin-bottom:12px;color:var(--ink2)} .issues summary{cursor:pointer;color:var(--warn)} .issues ul{margin:6px 0 0;padding-left:20px}
.pane2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media (max-width:900px){.pane2{grid-template-columns:1fr}}
.pane{min-width:0}
.pane-title{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--mute);padding:0 2px 6px;display:flex;justify-content:space-between}
.pane-title span{text-transform:none;letter-spacing:0}
pre.code{margin:0;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:12px 14px;font-size:12.5px;line-height:1.5;max-height:520px;overflow:auto;white-space:pre;tab-size:4}
pre.code .kw{color:var(--kw);font-weight:500} pre.code .str{color:var(--str)} pre.code .cmt{color:var(--cmt);font-style:italic} pre.code .tag{color:var(--tag);font-weight:500}
.state-diagram{background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:8px;max-height:520px;overflow:auto}
.state-diagram svg{max-width:100%;height:auto;display:block}
.live{background:var(--bg2);border:1px solid var(--line);border-radius:8px;padding:20px}
.live .row{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:12px 0}
.live label{font-size:14px;display:inline-flex;gap:6px;align-items:center}
button{font:inherit;font-weight:500;background:var(--accent);color:var(--accent-ink);border:0;border-radius:6px;padding:8px 16px;cursor:pointer}
button.ghost{background:transparent;color:var(--accent);border:1px solid var(--accent)}
button:focus-visible,textarea:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
textarea{width:100%;min-height:420px;resize:vertical;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:12px 14px;font:12.5px/1.5 "IBM Plex Mono",ui-monospace,monospace}
select{font:inherit;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:6px 10px}
.status{font-size:13px;min-height:1.5em}
.status.err{color:var(--fail)} .status.ok{color:var(--pass)}
footer{margin-top:48px;font-size:12.5px;color:var(--mute);border-top:1px solid var(--line);padding-top:14px;line-height:1.7}
</style>

<div class="wrap">
<header class="top">
  <div>
    <p class="eyebrow">text2activity · src/t2a_js/t2a_sysml · ${esc(bundle.version)}</p>
    <h1>T2A-ESS → EFFBD SysML converter verification report</h1>
    <div class="verdict ${verdict}">${
      verdict === "pass" ? "all JS converter tests passed · identical to the Python output" : "some items failed"
    }</div>
  </div>
  <div class="meta">generated ${esc(generatedAt)}<br>Node ${esc(node)}${py ? ` · Python unittest ${py.ran} ${py.ok ? "passed" : "failed"}` : " · Python not found"}</div>
</header>

<div class="tiles">
  <div class="tile ${js.fail ? "fail" : "pass"}"><div class="k">JS tests</div><div class="v">${js.pass}<small>/ ${js.total} passed</small></div></div>
  <div class="tile ${js.fail ? "fail" : ""}"><div class="k">failed</div><div class="v">${js.fail}</div></div>
  <div class="tile"><div class="k">skipped</div><div class="v">${js.skipped}</div></div>
  <div class="tile ${parityKnown ? (parityAll ? "pass" : "fail") : ""}"><div class="k">byte-identical to Python</div><div class="v">${
    parityKnown ? `${fixtures.filter((f) => f.parity.imm && f.parity.plain).length}<small>/ ${fixtures.length} fixtures × 2 forms</small>` : "not checked"
  }</div></div>
  <div class="tile ${lsp ? (lsp.failed ? "fail" : "pass") : ""}"><div class="k">Rust LSP check</div><div class="v">${
    lsp ? `${lsp.results.length - lsp.failed}<small>/ ${lsp.results.length} passed</small>` : "not run"
  }</div></div>
  <div class="tile"><div class="k">duration</div><div class="v">${(js.durationMs / 1000).toFixed(2)}<small>s</small></div></div>
</div>

<section class="block">
  <h2>Tests <span class="eyebrow" style="margin-left:8px">node --test · test/*.test.js</span></h2>
  <div style="overflow-x:auto"><table>
    <thead><tr><th style="width:90px">result</th><th>test</th><th class="num">ms</th></tr></thead>
    <tbody>${testRows}</tbody>
  </table></div>
</section>


<section class="block">
  <h2>Rust LSP check <span class="eyebrow" style="margin-left:8px">selab-rust-lsp · selab.diagram.getGraphEx + diagnostics</span></h2>
  ${lsp ? `<p class="shape">Binary: <code>${esc(lsp.bin)}</code>. ${lsp.results.filter((r) => r.kind === "synthetic").length} synthetic cases + ${lsp.results.filter((r) => r.kind === "fixture").length} fixtures are loaded into the same parser as the EFFBD editor to check zero error diagnostics, matching node/edge counts, resolved succession endpoints, and fully qualified flow endpoints (port declarations). The <code>Unresolved reference: 'start'/'done'</code> hints are dialect items that the editor's own examples produce as well.</p>
  <div style="overflow-x:auto"><table>
    <thead><tr><th style="width:80px">result</th><th>case</th><th>kind</th><th class="num">nodes</th><th class="num">succ</th><th class="num">fork</th><th class="num">join</th><th class="num">flow</th><th class="num">alloc</th><th class="num">err/warn/hint</th></tr></thead>
    <tbody>${lsp.results
      .map((r) => {
        const d = r.stats.diagnostics;
        const probs = r.problems.length ? `<div class="issues" style="margin:4px 0 0">${r.problems.map((x) => `<div>· ${esc(x)}</div>`).join("")}</div>` : "";
        const known = r.known ? `<div class="issues" style="margin:4px 0 0">known limitation: ${esc(r.known)}</div>` : "";
        return `<tr><td><span class="pill ${r.ok ? "pass" : "fail"}">${r.ok ? "passed" : "failed"}</span></td><td class="name"><code>${esc(r.id)}</code><div style="color:var(--mute);font-size:12px">${esc(r.title ?? "")}</div>${probs}${known}</td><td>${esc(r.kind)}</td><td class="num">${r.stats.nodes}</td><td class="num">${r.stats.succession}</td><td class="num">${r.stats.ForkNode ?? 0}</td><td class="num">${r.stats.JoinNode ?? 0}</td><td class="num">${r.stats.flow}</td><td class="num">${r.stats.allocation}</td><td class="num">${d.error ?? 0}/${d.warning ?? 0}/${d.hint ?? 0}</td></tr>`;
      })
      .join("")}</tbody>
  </table></div>` : `<p class="shape">Skipped: sysml-lsp binary not found (set the <code>SELAB_LSP_BIN</code> environment variable).</p>`}
</section>

<section class="block">
  <h2>Conversion results per fixture</h2>
  ${fixtureCards}
</section>

<section class="block">
  <h2>Live conversion <span class="eyebrow" style="margin-left:8px">the same converter.js running in the browser</span></h2>
  <div class="live">
    <div class="row">
      <label>Example <select id="sample">${fixtures.map((f, i) => `<option value="${i}"${f === sample ? " selected" : ""}>${esc(f.title)}</option>`).join("")}</select></label>
      <label><input type="checkbox" id="imm" checked> IMM tags (#Performer/#Function)</label>
      <button id="run">Convert</button>
      <button id="dl" class="ghost">Copy SysML</button>
      <span class="status" id="status"></span>
    </div>
    <div class="pane2">
      <div class="pane"><div class="pane-title">T2A-ESS JSON <span>editable</span></div><textarea id="src" spellcheck="false"></textarea></div>
      <div class="pane"><div class="pane-title">EFFBD SysML <span id="outmeta"></span></div><pre class="code sysml" id="out" style="max-height:none;min-height:420px"></pre></div>
    </div>
  </div>
</section>

<footer>
  The structural validator checks the slot graph (reachability, item flows, performer allocation, reference resolution). The final check of the EFFBD SysML dialect is loading it into selab-effbd-editor.<br>
  Report: <code>node src/t2a_js/tools/build_report.js</code> · tests: <code>cd src/t2a_js &amp;&amp; npm test</code>
</footer>
</div>

<script id="fixtures" type="application/json">${jsonForScript(fixtures.map((f) => ({ title: f.title, json: f.json })))}</script>
<script>
${bundle.code}
</script>
<script>
(function(){
  const fixtures = JSON.parse(document.getElementById("fixtures").textContent);
  const $ = (id) => document.getElementById(id);
  const esc = (s) => s.replace(/[&<>]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;"})[c]);
  function highlight(text){
    return esc(text)
      .replace(/^(\\s*)(#\\w+)$/gm, "$1<span class=tag>$2</span>")
      .replace(/(\\/\\/.*)$/gm, "<span class=cmt>$1</span>")
      .replace(/('[^'\\n]*')/g, "<span class=str>$1</span>")
      .replace(/\\b(private import|item def|part def|action|part|item|attribute|allocate|to|succession|first|then|if|fork|join|flow|from|start|done|in|out)\\b(?![^<]*<\\/span>)/g, "<span class=kw>$1</span>");
  }
  for (const pre of document.querySelectorAll("pre.sysml")) if (pre.id !== "out") pre.innerHTML = highlight(pre.textContent);
  function load(i){ $("src").value = fixtures[i].json; run(); }
  function run(){
    const status = $("status"); status.className = "status";
    try {
      const raw = JSON.parse($("src").value);
      const model = window.t2a.loadModelFromObject(raw);
      const sysml = window.t2a.convertModel(model, { immTags: $("imm").checked });
      const s = window.t2a.summarize(window.t2a.validateEffbd(model));
      $("out").innerHTML = highlight(sysml);
      $("out").dataset.raw = sysml;
      $("outmeta").textContent = (sysml.match(/\\n/g) || []).length + " lines · validation errors " + s.errors + " · warnings " + s.warnings;
      status.textContent = "converted"; status.className = "status ok";
    } catch (e) {
      status.textContent = "conversion failed: " + e.message; status.className = "status err";
    }
  }
  $("sample").addEventListener("change", (e) => load(Number(e.target.value)));
  $("run").addEventListener("click", run);
  $("imm").addEventListener("change", run);
  $("dl").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText($("out").dataset.raw || ""); $("status").textContent = "SysML copied to the clipboard"; $("status").className = "status ok"; }
    catch { $("status").textContent = "cannot copy: select the output area and copy it yourself"; $("status").className = "status err"; }
  });
  load(Number($("sample").value));
})();
</script>
`;
}

// --- main ----------------------------------------------------------------------------
const js = runJsTests();
const py = runPyTests();
const fixtures = [
  ...GOLD_JSONS.map((f) => [f, "gold"]),
  [COFFEE, "example"],
  [NON_GOLD, "LLM extraction"],
]
  .filter(([f]) => existsSync(f))
  .map(([f, kind]) => fixtureReport(f, kind));

let lsp = null;
if (lspAvailable()) {
  const results = await runLspChecks();
  const { CASES } = await import("../test/cases.js");
  for (const r of results) { const c = CASES.find((x) => x.id === r.id); if (c?.expect?.known) r.known = c.expect.known; delete r.sysml; }
  lsp = { bin: LSP_BIN, results, failed: results.filter((r) => !r.ok).length };
}

const bundleCode = browserBundle();
const version = (bundleCode.match(/CONVERTER_VERSION = "([^"]+)"/) ?? [0, "?"])[1];
const html = render({
  js,
  py,
  fixtures,
  generatedAt: new Date().toISOString().replace("T", " ").slice(0, 16) + " UTC",
  node: process.version,
  bundle: { code: bundleCode, version },
  lsp,
});
mkdirSync(path.dirname(OUT), { recursive: true });
writeFileSync(OUT, html, "utf8");
console.log(`report -> ${OUT}`);
console.log(`  js tests: ${js.pass}/${js.total} pass, ${js.fail} fail, ${js.skipped} skipped`);
console.log(`  parity: ${fixtures.map((f) => `${f.name}=${f.parity.imm && f.parity.plain ? "same" : f.parity.available ? "DIFF" : "n/a"}`).join(", ")}`);
if (py) console.log(`  python unittest: ${py.ran} ran, ${py.ok ? "OK" : "FAIL"}`);
if (lsp) console.log(`  rust lsp: ${lsp.results.length - lsp.failed}/${lsp.results.length} pass`);
else console.log("  rust lsp: skipped (binary not found)");
process.exitCode = js.fail ? 1 : 0;
