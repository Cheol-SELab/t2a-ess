/**
 * Render the T2A-ESS state view as a UML state machine diagram.
 *
 *   renderStateSvg(graph, opts?)  -> "<svg ...>...</svg>"  (deterministic)
 *   renderStateHtml(model, opts?) -> full self-contained HTML document
 *
 * The IR comes from stateGraph(model) in state_converter.js — the .sysml text
 * is never parsed back. No external libraries, no JS in the output page.
 */
import { stateGraph, convertStateModel } from "./state_converter.js";

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

/** Display-width estimate: CJK/fullwidth = 1.0em, ASCII ~0.55em. */
function textWidth(text, em) {
  let w = 0;
  for (const ch of String(text)) {
    const c = ch.codePointAt(0);
    w += c >= 0x1100 && (c <= 0x11ff || c >= 0x2e80) ? 1.0 : 0.55;
  }
  return w * em;
}

const FONT = 14;
const NODE_PAD_X = 16;
const NODE_LABEL_H = 30;
const NODE_LINE_H = 18;
const NODE_MIN_W = 120;
const GAP_X = 90;
const GAP_Y = 22;
const REGION_PAD = 16;
const REGION_LABEL_H = 22;
const ROOT_PAD = 12;
const TAB_H = 26;
const MARGIN = 40;

/** transition display label: `ev1, ev2 [g1 and g2] / action` (UML trigger [guard] / effect). */
function transitionLabel(t) {
  const parts = [];
  if (t.events.length) parts.push(t.events.join(", "));
  if (t.guards.length) parts.push(`[${t.guards.join(" and ")}]`);
  if (t.actions.length) parts.push(`/ ${t.actions[0]}`);
  return parts.join(" ");
}

/** Rank states inside a region: DFS longest-path from initial over forward
 *  transitions (back edges skipped for ranking); unreachable -> maxRank+1. */
function rankStates(region) {
  const adj = new Map();
  for (const t of region.transitions) {
    if (t.from === t.to) continue;
    if (!adj.has(t.from)) adj.set(t.from, []);
    adj.get(t.from).push(t.to);
  }
  const rank = new Map();
  const back = new Set(); // edges drawn as humps above (rank(to) <= rank(from))
  const skip = new Set(); // forward edges spanning >1 rank -> hump below
  const visit = (u, depth, onPath) => {
    for (const v of adj.get(u) ?? []) {
      if (onPath.has(v)) continue; // cycle -> back edge
      const cand = depth + 1;
      if (!rank.has(v) || rank.get(v) < cand) {
        rank.set(v, cand);
        visit(v, cand, new Set([...onPath, v]));
      }
    }
  };
  rank.set(region.initial, 0);
  visit(region.initial, 0, new Set([region.initial]));
  const maxRank = Math.max(0, ...rank.values());
  for (const s of region.states) if (!rank.has(s.id)) rank.set(s.id, maxRank + 1);
  for (const t of region.transitions) {
    if (t.from === t.to) continue;
    const span = rank.get(t.to) - rank.get(t.from);
    if (span <= 0) back.add(t);
    else if (span > 1) skip.add(t);
  }
  return { rank, back, skip };
}

/**
 * Render a stateGraph IR to a standalone <svg> string. Deterministic
 * (no timestamps, no random ids).
 */
export function renderStateSvg(graph, opts = {}) {
  const pad = opts.padding ?? MARGIN;
  const elts = [];
  const defs = `<defs><marker id="t2a-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="context-stroke"/></marker></defs>`;
  const css = `<style>
    text{font-family:"IBM Plex Sans KR","Noto Sans KR",system-ui,sans-serif;fill:#1E2328}
    .region-label{font-size:12px;font-style:italic;fill:#6F6C66}
    .state rect{fill:#FFFFFF;stroke:#4B4F55;stroke-width:1.2;rx:6}
    .state .sv{font-size:11px;fill:#4B4F55}
    .region rect.frame{fill:none;stroke:#4B4F55;stroke-width:1.4;rx:10}
    .region-sep{stroke:#4B4F55;stroke-width:1;stroke-dasharray:6 4}
    .transition path{fill:none;stroke:#1E6E8C;stroke-width:1.4;marker-end:url(#t2a-arrow)}
    .transition text{font-size:11px;fill:#1E2328}
    .transition rect.lbl{fill:#F6F5F0;stroke:#D9D6CE;stroke-width:.6;rx:3}
    .transition:hover path{stroke-width:2.6}
    .transition:hover text{font-weight:600}
    .initial circle{fill:#1E2328}
    .initial line{stroke:#1E2328;stroke-width:1.4;marker-end:url(#t2a-arrow)}
    .tab{fill:#F6F5F0;stroke:#4B4F55;stroke-width:1.4}
    .frame{fill:none;stroke:#4B4F55;stroke-width:1.4;rx:10}
    @media (prefers-color-scheme: dark){
      text{fill:#E6E4DE} .region-label{fill:#8B8880}
      .state rect{fill:#1C2026;stroke:#B8B5AE} .state .sv{fill:#B8B5AE}
      .region rect.frame,.frame{stroke:#B8B5AE} .region-sep{stroke:#B8B5AE}
      .transition path{stroke:#5FAFD0} .transition text{fill:#E6E4DE}
      .transition rect.lbl{fill:#15181C;stroke:#333941}
      .initial circle{fill:#E6E4DE} .initial line{stroke:#E6E4DE}
      .tab{fill:#1C2026;stroke:#B8B5AE}
    }
  </style>`;

  const tabW = Math.max(120, Math.ceil(textWidth(graph.scenario, 13)) + 24);

  // --- layout: per region, columns by rank ----------------------------------
  const regionBoxes = [];
  let cursorY = pad + TAB_H + ROOT_PAD;
  for (const region of graph.regions) {
    const { rank, back, skip } = rankStates(region);
    const placed = new Map(); // id -> {x,y,w,h,state}
    const byRank = new Map();
    for (const s of region.states) {
      const valueLines = s.values.map((v) => `${v.variable} = ${v.value}${v.unit ? ` ${v.unit}` : ""}`);
      const w = Math.max(
        NODE_MIN_W,
        Math.ceil(Math.max(textWidth(s.label, FONT), ...valueLines.map((l) => textWidth(l, 11))) + NODE_PAD_X * 2),
      );
      const h = NODE_LABEL_H + (s.values.length ? s.values.length * NODE_LINE_H + 8 : 4);
      placed.set(s.id, { w, h, state: s });
      const r = rank.get(s.id);
      if (!byRank.has(r)) byRank.set(r, []);
      byRank.get(r).push(s.id);
    }
    const colW = Math.max(...[...placed.values()].map((p) => p.w));
    const maxRank = Math.max(...byRank.keys());

    // per-gap column spacing: wide enough for the widest transition label
    const gapX = [];
    for (let k = 0; k < maxRank; k += 1) {
      let need = GAP_X;
      for (const t of region.transitions) {
        if (rank.get(t.from) === k && rank.get(t.to) === k + 1) {
          need = Math.max(need, textWidth(transitionLabel(t), 11) + 28);
        }
      }
      gapX[k] = need;
    }
    const xOf = (r) => {
      let x = pad + ROOT_PAD;
      for (let k = 0; k < r; k += 1) x += colW + gapX[k];
      return x;
    };

    // hump clearance above (back edges) and below (rank-skipping forward edges)
    const dupAbove = Math.max(0, ...region.transitions.filter((t) => back.has(t)).map((t) => {
      const k = `${t.from}\u0000${t.to}`;
      const idx = region.transitions.filter((o) => back.has(o) && `${o.from}\u0000${o.to}` === k).indexOf(t);
      return idx;
    }));
    const dupBelow = Math.max(0, ...region.transitions.filter((t) => skip.has(t)).map((t) => {
      const k = `${t.from}\u0000${t.to}`;
      const idx = region.transitions.filter((o) => skip.has(o) && `${o.from}\u0000${o.to}` === k).indexOf(t);
      return idx;
    }));
    const humpTop = back.size ? 34 + dupAbove * 16 + 12 : 0;
    const humpBottom = skip.size ? 34 + dupBelow * 16 + 12 : 0;

    let maxBottom = 0;
    for (const [r, ids] of [...byRank.entries()].sort((a, b) => a[0] - b[0])) {
      let y = cursorY + REGION_PAD + REGION_LABEL_H + humpTop;
      for (const id of ids.sort((a, b) => region.states.findIndex((s) => s.id === a) - region.states.findIndex((s) => s.id === b))) {
        const p = placed.get(id);
        p.x = xOf(r);
        p.y = y;
        y += p.h + GAP_Y;
        maxBottom = Math.max(maxBottom, y);
      }
    }
    const regionW = xOf(maxRank) + colW - pad + REGION_PAD;
    const regionH = maxBottom - cursorY - GAP_Y + REGION_PAD + humpBottom;
    regionBoxes.push({ region, placed, rank, back, skip, gapX, x: pad, y: cursorY, w: regionW + ROOT_PAD, h: regionH });
    cursorY += regionH + REGION_PAD + (graph.parallel ? 14 : 0);
  }
  const width = Math.max(...regionBoxes.map((b) => b.x + b.w), tabW) + pad;
  const height = cursorY + pad - 14;

  // --- emit ------------------------------------------------------------------
  elts.push(css, defs);
  // root frame + name tab
  elts.push(`<rect class="frame" x="${pad - 12}" y="${pad - 12}" width="${width - 2 * pad + 24}" height="${height - 2 * pad + 24}" rx="10"/>`);
  elts.push(`<path class="tab" d="M${pad - 12} ${pad - 12} h${tabW} v${TAB_H} h-${tabW} z"/>`);
  elts.push(`<text x="${pad}" y="${pad + 5}" font-size="13" font-weight="600">${esc(graph.scenario)}</text>`);

  regionBoxes.forEach((box, ri) => {
    const { region, placed, rank, back, skip } = box;
    elts.push(`<g class="region" data-id="${esc(region.id)}">`);
    elts.push(
      `<text class="region-label" x="${box.x + 6}" y="${box.y + REGION_LABEL_H - 4}">${esc(region.label)}</text>`,
    );
    // initial pseudo-state
    const ini = placed.get(region.initial);
    const ix = ini.x - 40;
    const iy = ini.y + ini.h / 2;
    elts.push(`<g class="initial"><circle cx="${ix}" cy="${iy}" r="7"/><line x1="${ix + 7}" y1="${iy}" x2="${ini.x - 3}" y2="${iy}" marker-end="url(#t2a-arrow)"/></g>`);
    // states
    for (const s of region.states) {
      const p = placed.get(s.id);
      elts.push(`<g class="state" data-id="${esc(s.id)}">`);
      elts.push(`<rect x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" rx="6"/>`);
      elts.push(`<text x="${p.x + NODE_PAD_X}" y="${p.y + 20}" font-size="${FONT}">${esc(s.label)}</text>`);
      if (s.values.length) {
        elts.push(`<line x1="${p.x}" y1="${p.y + NODE_LABEL_H}" x2="${p.x + p.w}" y2="${p.y + NODE_LABEL_H}" stroke="#4B4F55" stroke-width=".8"/>`);
        s.values.forEach((v, i) => {
          elts.push(
            `<text class="sv" x="${p.x + NODE_PAD_X}" y="${p.y + NODE_LABEL_H + 16 + i * NODE_LINE_H}">${esc(
              `${v.variable} = ${v.value}${v.unit ? ` ${v.unit}` : ""}`,
            )}</text>`,
          );
        });
      }
      elts.push(`</g>`);
    }
    // transitions
    const pairCount = new Map();
    for (const t of region.transitions) {
      const a = placed.get(t.from);
      const b = placed.get(t.to);
      const key = `${t.from}\u0000${t.to}`;
      const dup = pairCount.get(key) ?? 0;
      pairCount.set(key, dup + 1);
      const label = transitionLabel(t);
      const dy = Math.min(dup * 26, Math.max(0, Math.min(a.h, b.h) / 2 - 8));
      const isHump = back.has(t) || skip.has(t) || t.from === t.to;
      let d;
      if (t.from === t.to) {
        // self-loop off the top-right corner, ending on the right edge
        const x = a.x + a.w;
        const y = a.y;
        d = `M${x - 24} ${y} C${x} ${y - 30}, ${x + 26} ${y - 34}, ${x} ${y + 6}`;
      } else if (back.has(t)) {
        // hump above both nodes
        const top = Math.min(a.y, b.y) - 34 - dup * 16;
        d = `M${a.x + a.w / 2} ${a.y} C${a.x + a.w / 2} ${top}, ${b.x + b.w / 2} ${top}, ${b.x + b.w / 2} ${b.y}`;
      } else if (skip.has(t)) {
        // forward edge spanning >1 rank: hump below the nodes
        const bottom = Math.max(a.y + a.h, b.y + b.h) + 34 + dup * 16;
        d = `M${a.x + a.w / 2} ${a.y + a.h} C${a.x + a.w / 2} ${bottom}, ${b.x + b.w / 2} ${bottom}, ${b.x + b.w / 2} ${b.y + b.h}`;
      } else {
        const gap = (b.x - (a.x + a.w)) / 2;
        d = `M${a.x + a.w} ${a.y + a.h / 2 + dy} C${a.x + a.w + gap} ${a.y + a.h / 2 + dy}, ${b.x - gap} ${b.y + b.h / 2 + dy}, ${b.x} ${b.y + b.h / 2 + dy}`;
      }
      elts.push(`<g class="transition" data-id="${esc(t.id)}">`);
      elts.push(`<path d="${d}"/>`);
      if (label) {
        const mid = midpoint(d);
        const lw = Math.ceil(textWidth(label, 11)) + 10;
        // forward edges: label floats just above the path; humps: at the apex
        const rectY = isHump ? mid.y - 11 : mid.y - 21;
        elts.push(`<rect class="lbl" x="${mid.x - lw / 2}" y="${rectY}" width="${lw}" height="18"/>`);
        elts.push(`<text x="${mid.x}" y="${rectY + 13}" text-anchor="middle">${esc(label)}</text>`);
      }
      elts.push(`</g>`);
    }
    elts.push(`</g>`);
    if (graph.parallel && ri < regionBoxes.length - 1) {
      const sepY = box.y + box.h + 7;
      elts.push(`<line class="region-sep" x1="${pad - 4}" y1="${sepY}" x2="${width - pad + 4}" y2="${sepY}"/>`);
    }
  });

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${Math.ceil(width)} ${Math.ceil(height)}" role="img" aria-label="state machine">${elts.join("\n")}</svg>`;
}

/** Approximate bezier midpoint for label placement. */
function midpoint(d) {
  const nums = d.match(/-?\d+(?:\.\d+)?/g).map(Number);
  const [x0, y0, x1, y1, x2, y2, x3, y3] = nums.slice(-8);
  return {
    x: (x0 + 3 * x1 + 3 * x2 + x3) / 8,
    y: (y0 + 3 * y1 + 3 * y2 + y3) / 8,
  };
}

/** Full self-contained HTML page wrapping the SVG + transitions table + SysML text. */
export function renderStateHtml(model, opts = {}) {
  const graph = opts.graph ?? stateGraph(model);
  const sysml = opts.sysml ?? convertStateModel(model);
  const svg = renderStateSvg(graph);
  const counts = {
    regions: graph.regions.length,
    states: graph.regions.reduce((n, r) => n + r.states.length, 0),
    transitions: graph.regions.reduce((n, r) => n + r.transitions.length, 0),
    events: graph.events.length,
    guards: graph.guards.length,
  };
  const rows = graph.regions
    .flatMap((r) =>
      r.transitions.map((t) => {
        const lbl = (id) => r.states.find((s) => s.id === id)?.label ?? id;
        return `<tr><td>${esc(lbl(t.from))}</td><td>→ ${esc(lbl(t.to))}</td><td>${esc(t.events.join(", "))}</td><td>${esc(t.guards.join(" and "))}</td><td>${esc(t.actions.join(", "))}</td><td class="mono">${esc(t.label)}</td></tr>`;
      }),
    )
    .join("\n");
  return `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>${esc(graph.title)} — State View</title>
<style>
:root{
  --bg:#F6F5F0; --bg2:#FFFFFF; --bg3:#ECEAE3; --ink:#1E2328; --ink2:#4B4F55; --mute:#6F6C66; --line:#D9D6CE;
  --accent:#1E6E8C; --pass:#2C7A4B;
}
@media (prefers-color-scheme: dark){ :root{
  --bg:#15181C; --bg2:#1C2026; --bg3:#232830; --ink:#E6E4DE; --ink2:#B8B5AE; --mute:#8B8880; --line:#333941;
  --accent:#5FAFD0; --pass:#6CC38F;
}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 "IBM Plex Sans KR","Noto Sans KR",system-ui,sans-serif}
.mono,pre{font-family:"IBM Plex Mono",ui-monospace,Consolas,monospace}
.wrap{max-width:1240px;margin:0 auto;padding:32px 24px 72px}
h1{font-size:24px;margin:0} h2{font-size:17px;margin:0 0 12px}
.eyebrow{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--mute)}
.meta{font-size:13px;color:var(--mute);margin-top:6px}
.tiles{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0 28px}
.tile{background:var(--bg2);border:1px solid var(--line);border-radius:8px;padding:10px 16px}
.tile .k{font-size:11px;color:var(--mute);text-transform:uppercase;letter-spacing:.04em}
.tile .v{font-size:20px;font-weight:600}
.diagram{background:var(--bg2);border:1px solid var(--line);border-radius:8px;padding:16px;overflow:auto;margin-bottom:28px}
table{width:100%;border-collapse:collapse;background:var(--bg2);border:1px solid var(--line);border-radius:8px;overflow:hidden;margin-bottom:28px}
th,td{text-align:left;padding:8px 12px;border-top:1px solid var(--line);font-size:13px}
thead th{border-top:0;background:var(--bg3);font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:var(--mute)}
details{background:var(--bg2);border:1px solid var(--line);border-radius:8px;padding:12px 16px}
summary{cursor:pointer;color:var(--accent);font-weight:500}
pre{margin:12px 0 0;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:12px 14px;font-size:12.5px;line-height:1.5;overflow:auto}
section.block{margin-bottom:28px}
</style>
</head>
<body>
<div class="wrap">
<header>
  <p class="eyebrow">T2A-ESS State View · t2a_sysml.state.v0.1</p>
  <h1>${esc(graph.scenario)}</h1>
  <p class="meta">${esc(graph.title)}</p>
</header>
<div class="tiles">
  <div class="tile"><div class="k">regions</div><div class="v">${counts.regions}</div></div>
  <div class="tile"><div class="k">states</div><div class="v">${counts.states}</div></div>
  <div class="tile"><div class="k">transitions</div><div class="v">${counts.transitions}</div></div>
  <div class="tile"><div class="k">events</div><div class="v">${counts.events}</div></div>
  <div class="tile"><div class="k">guards</div><div class="v">${counts.guards}</div></div>
</div>
<section class="block">
  <h2>State Machine Diagram</h2>
  <div class="diagram">${svg}</div>
</section>
<section class="block">
  <h2>Transitions</h2>
  <table>
    <thead><tr><th>from</th><th>to</th><th>events</th><th>guards</th><th>actions</th><th>transition</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>
</section>
<details><summary>Generated SysML v2 (state def)</summary><pre>${esc(sysml)}</pre></details>
</div>
</body>
</html>
`;
}
