"""Case-study figures for the MUM-T and NGHE gold fixtures.

Pipeline (per fixture):
  1. gold T2A-ESS JSON (data/gold/)        -> shorter presentation labels (ids/relations unchanged)
  2. repository converter (JS)              -> EFFBD SysML text
  3. selab-rust-lsp                         -> diagnostics + diagram graph
  4. structural identity check: the data labels and the presentation labels give identical LSP graph statistics
  5. Graphviz rendering of the LSP diagram graph (EFFBD view, one panel per episode + scenario strip)
  6. state view with the repository's State View converter (standard SysML v2 state def, selab-rust-lsp
     diagnostics, state graph IR, the repository's SVG state diagram; state_view.mjs), converted to PDF unchanged.
Data and converters are taken from <repository-root>.
usage: python experiments/case-study/make_case_study.py <repository-root> <out-dir>
"""
import copy, json, os, re, subprocess, sys, textwrap
import pymupdf
from labels_en import MUMT, MUMT_GUARDS, NGHE, NGHE_GUARDS

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

FIXTURES = {
    "mumt": ("data/gold/mumt/mumt.gold.json", MUMT, MUMT_GUARDS),
    "nghe": ("data/gold/nghe/nghe.gold.json", NGHE, NGHE_GUARDS),
}
DIAGRAM_COLLECTIONS = ["scenarios", "episodes", "performers", "actions", "items", "flows", "controls",
                       "situations", "events", "transitions"]
FONT = "Arial"


def slot_id(slot):
    for k, v in slot.items():
        if k.endswith("_id") and k not in ("source_unit_id",) and isinstance(v, str):
            return v
    return None


def presentation(doc, labels, guards):
    doc = copy.deepcopy(doc)
    m = doc["text2activity_extraction_model"]
    missing = []
    for coll in DIAGRAM_COLLECTIONS:
        for slot in m.get(coll, []):
            sid = slot_id(slot)
            if sid in labels:
                slot["label"] = labels[sid]
            else:
                missing.append(sid)
    for c in m.get("constraints", []):  # constraints are shown by the state view with their formal expression
        c["label"] = c["expression_text"]
    for c in m.get("controls", []):
        cid = slot_id(c)
        if cid in guards:
            assert len(guards[cid]) == len(c.get("guard_texts", [])), cid
            c["guard_texts"] = guards[cid]
    for su in m.get("source_units", []):
        su["planned_content"] = labels[su["source_unit_id"]]
    m["title"] = labels[slot_id(m["scenarios"][0])]
    assert not missing, f"slots without a presentation label: {missing}"
    return doc


def run_lsp(json_path, prefix):
    r = subprocess.run(["node", os.path.join(HERE, "lsp_graph.mjs"), json_path, prefix],
                       capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, T2A_ROOT=os.path.abspath(ROOT)))
    print(r.stdout.strip(), r.stderr.strip())
    return json.load(open(prefix + ".check.json", encoding="utf-8"))


# ------------------------------------------------------------------ EFFBD rendering
def wrap(s, width=24):
    return "<BR/>".join(html(x) for x in textwrap.wrap(s, width)) or html(s)


def html(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def parse_ports(sysml):
    """action name -> {'in': [...], 'out': [...]} from the emitted SysML text."""
    ports, stack = {}, []
    for line in sysml.splitlines():
        m = re.match(r"\s*action '([^']+)' \{", line)
        if m:
            stack.append(m.group(1)); ports.setdefault(m.group(1), {"in": [], "out": []}); continue
        m = re.match(r"\s*(in|out) item '([^']+)'", line)
        if m and stack:
            ports[stack[-1]][m.group(1)].append(m.group(2)); continue
        if line.strip() == "}" and stack:
            stack.pop()
    return ports


def last(q):
    return q.split("::")[-1]


def render_effbd(key, graph, sysml, out_pdf):
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = graph["edges"]
    root = next(n["id"] for n in graph["nodes"] if n["kind"] == "ActionUsage" and "::" not in n["id"])
    episodes = [e["target"] for e in edges if e["kind"] == "containment" and e["source"] == root
                and nodes.get(e["target"], {}).get("kind") == "ActionUsage"]
    # episode order from the scenario-level successions
    succ_root = [e for e in edges if e["kind"] == "succession" and e.get("data", {}).get("ownerQualifiedName") == root]
    nxt = {e["source"]: e["target"] for e in succ_root}
    order, cur = [], f"{root}::start"
    while cur in nxt and nxt[cur] != f"{root}::done":
        cur = nxt[cur]; order.append(cur)
    assert sorted(order) == sorted(episodes), (order, episodes)
    alloc = {}
    for e in edges:
        if e["kind"] == "allocation":
            alloc.setdefault(e["source"], []).append(last(e["target"]))
    ports = parse_ports(sysml)
    parts = []

    # scenario strip with cross-episode item flows
    strip = [f'digraph G {{ rankdir=LR; nodesep=0.25; ranksep=0.35; bgcolor="white";',
             f'node [fontname="{FONT}", fontsize=10]; edge [fontname="{FONT}", fontsize=9, color="#555555"];',
             f'label=<<B>Lv.0 {html(last(root))}</B>>; labelloc=t; labeljust=l; fontname="{FONT}"; fontsize=12;',
             '"s" [shape=circle, style=filled, fillcolor=black, label="", width=0.18];',
             '"d" [shape=doublecircle, style=filled, fillcolor=black, label="", width=0.13];']
    for i, ep in enumerate(order):
        strip.append(f'"e{i}" [shape=box, style="rounded", penwidth=1.3, label=<{wrap(last(ep), 20)}>];')
    chain = ['"s"'] + [f'"e{i}"' for i in range(len(order))] + ['"d"']
    for a, b in zip(chain, chain[1:]):
        strip.append(f"{a} -> {b};")
    for e in edges:
        if e["kind"] == "flow" and e.get("data", {}).get("ownerQualifiedName") == root:
            src_ep = "::".join(e["source"].split("::")[:2]); dst_ep = "::".join(e["target"].split("::")[:2])
            item = last(e["source"])
            strip.append(f'"e{order.index(src_ep)}" -> "e{order.index(dst_ep)}" [style=dashed, color="#1f5fa8", '
                         f'fontcolor="#1f5fa8", label=<{html(item)}>, constraint=false];')
    strip.append("}")
    parts.append(("strip", "\n".join(strip)))

    # one panel per episode
    for i, ep in enumerate(order):
        g = [f'digraph G {{ rankdir=LR; nodesep=0.22; ranksep=0.32; bgcolor="white"; compound=true;',
             f'node [fontname="{FONT}", fontsize=10]; edge [fontname="{FONT}", fontsize=9, color="#444444", arrowsize=0.7];',
             f'label=<<B>Lv.1 {html(last(ep))}</B>>; labelloc=t; labeljust=l; fontname="{FONT}"; fontsize=12;']
        children = [e["target"] for e in edges if e["kind"] == "containment" and e["source"] == ep]
        for c in children:
            n = nodes.get(c)
            if not n:
                continue
            k = n["kind"]
            if k == "ActionUsage":
                name = last(c)
                perf = ", ".join(alloc.get(c, [])) or "(unallocated)"
                rows = [f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="7" COLOR="#777777">Lv.2</FONT></TD><TD ALIGN="RIGHT"><FONT POINT-SIZE="7" COLOR="#777777">#Function</FONT></TD></TR>',
                        f'<TR><TD COLSPAN="2"><B>{wrap(name, 22)}</B></TD></TR>']
                p = ports.get(name, {"in": [], "out": []})
                for d, arrow in (("in", "in"), ("out", "out")):
                    for it in p[d]:
                        rows.append(f'<TR><TD COLSPAN="2"><FONT POINT-SIZE="7" COLOR="#1f5fa8">{arrow}: {html(it)}</FONT></TD></TR>')
                rows.append(f'<TR><TD COLSPAN="2"><FONT POINT-SIZE="8"><I>{html(perf)}</I></FONT></TD></TR>')
                g.append(f'"{c}" [shape=box, style="rounded", margin=0.04, label=<<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="1">{"".join(rows)}</TABLE>>];')
        for c in list(nodes):
            n = nodes[c]
            if not c.startswith(ep + "::") or c.count("::") != ep.count("::") + 1:
                continue
            if n["kind"] == "StartAction":
                g.append(f'"{c}" [shape=circle, style=filled, fillcolor=black, label="", width=0.16];')
            elif n["kind"] == "DoneAction":
                g.append(f'"{c}" [shape=doublecircle, style=filled, fillcolor=black, label="", width=0.11];')
            elif n["kind"] in ("ForkNode", "JoinNode"):
                g.append(f'"{c}" [shape=circle, label="AND", fontsize=8, width=0.42, fixedsize=true, penwidth=1.2];')
        for e in edges:
            if e["kind"] == "succession" and e.get("data", {}).get("ownerQualifiedName") == ep:
                guard = e.get("data", {}).get("guardCondition")
                attr = ""
                if guard:
                    gtxt = re.sub(r"^'(.*)' == true$", r"\1", guard)
                    attr = f' [label=<<FONT COLOR="#9a3c00">[{wrap(gtxt, 22)}]</FONT>>, color="#9a3c00", penwidth=1.2]'
                g.append(f'"{e["source"]}" -> "{e["target"]}"{attr};')
            if e["kind"] == "flow" and e.get("data", {}).get("ownerQualifiedName") == ep:
                s_act = "::".join(e["source"].split("::")[:-1]); t_act = "::".join(e["target"].split("::")[:-1])
                g.append(f'"{s_act}" -> "{t_act}" [style=dashed, color="#1f5fa8", fontcolor="#1f5fa8", label=<{html(last(e["source"]))}>];')
        g.append("}")
        parts.append((f"ep{i+1}", "\n".join(g)))

    pdfs = []
    for name, dot in parts:
        dp = os.path.join(OUT, f"{key}-effbd-{name}.dot")
        open(dp, "w", encoding="utf-8").write(dot)
        pp = dp[:-4] + ".pdf"
        subprocess.run(["dot", "-Tpdf", dp, "-o", pp], check=True)
        # panels dominated by parallel branches are taller than wide in LR; lay them out top-to-bottom instead
        with pymupdf.open(pp) as d:
            c = content_box(d[0])
        if name != "strip" and c.height > 0.9 * c.width:
            open(dp, "w", encoding="utf-8").write(dot.replace("rankdir=LR;", "rankdir=TB;", 1))
            subprocess.run(["dot", "-Tpdf", dp, "-o", pp], check=True)
        pdfs.append(pp)
    stack_pdfs(pdfs, out_pdf)
    return pdfs


def content_box(page, pad=4):
    """Bounding box of everything drawn on a Graphviz page (the white background rectangle is ignored)."""
    boxes = [pymupdf.Rect(b[:4]) for b in page.get_text("blocks")]
    for d in page.get_drawings():
        if d.get("fill") == (1.0, 1.0, 1.0) and d["rect"].width >= page.rect.width * 0.95:
            continue
        boxes.append(d["rect"])
    r = boxes[0]
    for b in boxes[1:]:
        r |= b
    return pymupdf.Rect(r.x0 - pad, r.y0 - pad, r.x1 + pad, r.y1 + pad) & page.rect


def stack_pdfs(pdfs, out_pdf, gap=12, width=None):
    """First part spans the full width; the remaining panels are packed greedily into rows."""
    srcs = [pymupdf.open(p) for p in pdfs]
    clips = [content_box(s[0]) for s in srcs]
    width = width or max(c.width for c in clips)
    rows, row, row_w = [[0]], [], 0.0
    for i in range(1, len(srcs)):
        w = clips[i].width
        if row and row_w + gap + w > width:
            rows.append(row); row, row_w = [], 0.0
        row.append(i); row_w += (gap if row_w else 0) + w
    if row:
        rows.append(row)
    layout, y = [], 0.0
    for row in rows:
        total = sum(clips[i].width for i in row) + gap * (len(row) - 1)
        scale = min(1.0, width / total)
        h = max(clips[i].height for i in row) * scale
        x = 0.0
        for i in row:
            w_i, h_i = clips[i].width * scale, clips[i].height * scale
            layout.append((i, pymupdf.Rect(x, y, x + w_i, y + h_i)))
            x += w_i + gap * scale
        y += h + gap
    out = pymupdf.open()
    page = out.new_page(width=width, height=y - gap)
    for i, rect in layout:
        page.show_pdf_page(rect, srcs[i], 0, clip=clips[i])
        page.draw_rect(rect, color=(0.82, 0.82, 0.82), width=0.4)
    out.save(out_pdf)
    for s in srcs:
        s.close()


# ------------------------------------------------------------------ state view
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def svg_to_pdf(svg_path, out_pdf):
    """Print the repository's SVG unchanged through headless Edge (its CSS needs a browser), one page of SVG size."""
    svg = open(svg_path, encoding="utf-8").read()
    w, h = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg).groups())
    html_path = svg_path[:-4] + ".print.html"
    open(html_path, "w", encoding="utf-8").write(
        f"<!doctype html><html><head><meta charset='utf-8'><style>@page{{size:{w}px {h}px;margin:0}}"
        f"html,body{{margin:0;padding:0}}svg{{display:block;width:{w}px;height:{h}px}}</style></head><body>{svg}</body></html>")
    subprocess.run([EDGE, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={os.path.abspath(out_pdf)}",
                    "file:///" + os.path.abspath(html_path).replace("\\", "/")], check=True, capture_output=True)
    with pymupdf.open(out_pdf) as d:
        assert len(d) == 1, (out_pdf, len(d))


def render_state_view(key, en_path, out_pdf):
    prefix = os.path.join(OUT, f"{key}")
    r = subprocess.run(["node", os.path.join(HERE, "state_view.mjs"), os.path.abspath(ROOT), en_path, prefix],
                       capture_output=True, text=True, encoding="utf-8")
    print(r.stdout.strip(), r.stderr.strip())
    assert r.returncode == 0
    svg_to_pdf(prefix + ".state.svg", prefix + ".state.repo-svg.pdf")  # the repository's own drawing, kept as an artifact
    graph = json.load(open(prefix + ".state.graph.json", encoding="utf-8"))
    render_state_ir(graph, prefix + ".state.dot", out_pdf)
    return json.load(open(prefix + ".state.check.json", encoding="utf-8"))


def render_state_ir(graph, dot_path, out_pdf):
    """Paper figure: the converter's state graph IR (regions, states, initial states, transitions with events and
    guards) laid out compactly with Graphviz; nothing is added to or removed from the IR."""
    g = ['digraph S { rankdir=LR; newrank=true; nodesep=0.3; ranksep=0.55; bgcolor="white"; compound=true; pad=0.05;',
         f'node [fontname="{FONT}", fontsize=10, shape=plain]; edge [fontname="{FONT}", fontsize=8, color="#1E6E8C", arrowsize=0.6];',
         f'label=<<B>{html(graph["title"])}</B>>; labelloc=t; labeljust=l; fontname="{FONT}"; fontsize=11;']
    inits = []
    for r in graph["regions"][::-1]:  # Graphviz stacks clusters bottom-up in LR: declare in reverse to show IR order top-down
        g.append(f'subgraph "cluster_{r["id"]}" {{ label=<<I>{html(r["label"])}</I>>; labeljust=l; fontsize=9; fontcolor="#6F6C66"; '
                 f'style="dashed,rounded"; color="#8A8F96";')
        for st in r["states"]:
            vals = "".join(f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="8" COLOR="#4B4F55">{html(v["variable"])} = {html(str(v["value"]))}'
                           f'{(" " + html(v["unit"])) if v.get("unit") else ""}</FONT></TD></TR>' for v in st["values"])
            g.append(f'"{st["id"]}" [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3" STYLE="ROUNDED" COLOR="#4B4F55">'
                     f'<TR><TD ALIGN="LEFT"><B>{wrap(st["label"], 22)}</B></TD></TR>{vals}</TABLE>>];')
        ini = f'init_{r["id"]}'
        inits.append(ini)
        g.append(f'"{ini}" [shape=circle, style=filled, fillcolor=black, label="", width=0.12, fixedsize=true];')
        if r.get("initial"):
            g.append(f'"{ini}" -> "{r["initial"]}" [color=black];')
        for t in r["transitions"]:
            parts = [f"{wrap(e, 24)}" for e in t["events"]] + [f'<FONT COLOR="#9a3c00">[{wrap(x, 26)}]</FONT>' for x in t["guards"]]
            lab = "<BR/>".join(parts) or html(t["label"])
            g.append(f'"{t["from"]}" -> "{t["to"]}" [label=<{lab}>];')
        g.append("}")
    g.append("{ rank=same; " + " ".join(f'"{i}";' for i in inits) + " }")
    for a, b in zip(inits, inits[1:]):
        g.append(f'"{a}" -> "{b}" [style=invis];')
    g.append("}")
    open(dot_path, "w", encoding="utf-8").write("\n".join(g))
    subprocess.run(["dot", "-Tpdf", dot_path, "-o", out_pdf], check=True)
    d = pymupdf.open(out_pdf)
    d[0].set_cropbox(content_box(d[0]))
    d.save(out_pdf + ".tmp")
    d.close()
    os.replace(out_pdf + ".tmp", out_pdf)


# ------------------------------------------------------------------ main
summary = {}
for key, (rel_path, labels, guards) in FIXTURES.items():
    src = os.path.join(ROOT, rel_path)
    doc = json.load(open(src, encoding="utf-8-sig"))
    en = presentation(doc, labels, guards)
    en_path = os.path.join(OUT, f"{key}-gold-en.json")
    json.dump(en, open(en_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    ko = run_lsp(src, os.path.join(OUT, f"{key}-data"))
    enc = run_lsp(en_path, os.path.join(OUT, f"{key}-en"))
    # Behavioral structure must be identical. The only tolerated difference is ItemUsage nodes that the
    # language server surfaces for root-level items whose data label collides with an action label.
    keys = ["ActionUsage", "PartUsage", "ForkNode", "JoinNode", "StartAction", "DoneAction",
            "succession", "flow", "allocation", "diagnostics"]
    same = all(ko["stats"].get(k) == enc["stats"].get(k) for k in keys) and ko["validator"] == enc["validator"]
    assert same, ("structure differs with the presentation labels", ko["stats"], enc["stats"])
    item_nodes_diff = ko["stats"].get("ItemUsage", 0) - enc["stats"].get("ItemUsage", 0)
    ko_actions = {s["label"] for s in doc["text2activity_extraction_model"]["actions"]}
    collisions = [s["label"] for s in doc["text2activity_extraction_model"]["items"] if s["label"] in ko_actions]
    assert item_nodes_diff == len(collisions), (item_nodes_diff, collisions)
    assert enc["ok"] and ko["ok"]
    graph = json.load(open(os.path.join(OUT, f"{key}-en.graph.json"), encoding="utf-8"))
    sysml = open(os.path.join(OUT, f"{key}-en.sysml"), encoding="utf-8").read()
    panels = render_effbd(key, graph, sysml, os.path.join(OUT, f"{key}-effbd.pdf"))
    if key == "nghe":  # too tall for one page: scenario strip + E1-E2, then E3-E5
        width = max(content_box(pymupdf.open(p)[0]).width for p in panels)
        stack_pdfs(panels[:3], os.path.join(OUT, f"{key}-effbd-a.pdf"), width=width)
        stack_pdfs(panels[3:], os.path.join(OUT, f"{key}-effbd-b.pdf"), width=width)
    state = render_state_view(key, en_path, os.path.join(OUT, f"{key}-state.pdf"))
    m = en["text2activity_extraction_model"]
    summary[key] = {"stats": enc["stats"], "validator": enc["validator"], "lsp_ok": enc["ok"],
                    "identical_to_data_labels": same, "data_item_action_label_collisions": collisions,
                    "state_view": {k: state[k] for k in ("lines", "summary", "diagnostics")},
                    "slots": {c: len(m.get(c, [])) for c in DIAGRAM_COLLECTIONS},
                    "relations": len(m["slot_relations"])}
json.dump(summary, open(os.path.join(OUT, "case-study-summary.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(json.dumps(summary, indent=1, ensure_ascii=False))
