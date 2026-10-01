"""Derive a capture module from the editor's scripts/provide-effbd-image.mjs.

The derived module is byte-for-byte the editor's renderer except for three mechanical edits:
  1. EFFBD_EDITOR_ROOT points to the editor package (the copy lives outside it),
  2. the bare import 'selab-image-capture' is resolved to that package's entry file,
  3. just before the screenshot, the bounding boxes of all function groups are collected and
     returned next to the PNG data URI (for cropping episode panels); the render itself is unchanged.
Every edit asserts that its anchor occurs exactly once, so an upstream change fails loudly.
"""
import json, os, sys

EDITOR = "G:/SW/SW-SELab/selab-ex-system-modeler/packages/selab-effbd-editor"
src_path = os.path.join(EDITOR, "scripts", "provide-effbd-image.mjs")
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "provide-effbd-image.boxes.mjs")
s = open(src_path, encoding="utf-8").read()

pkg = json.load(open(os.path.join(EDITOR, "..", "selab-image-capture", "package.json"), encoding="utf-8"))
entry = pkg.get("exports", {}).get(".", pkg.get("main", "src/index.js"))
if isinstance(entry, dict):
    entry = entry.get("import") or entry.get("default")
capture_entry = os.path.normpath(os.path.join(EDITOR, "..", "selab-image-capture", entry)).replace("\\", "/")


def edit(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)


edit("const EFFBD_EDITOR_ROOT = resolve(__dirname, '..');", f"const EFFBD_EDITOR_ROOT = '{EDITOR}';")
edit("} from 'selab-image-capture';", f"}} from 'file:///{capture_entry}';")
edit("""        const buf = await page.locator('#app').screenshot();
        return toDataUri(buf);""",
     """        const boxes = await page.evaluate(() => {
            const app = document.getElementById('app').getBoundingClientRect();
            const nodes = [...document.querySelectorAll('#app svg g[data-id][data-initial-model]')].map((g) => {
                let m = {};
                try { m = JSON.parse(g.getAttribute('data-initial-model')); } catch { /* ignore */ }
                const r = g.getBoundingClientRect();
                return { kind: 'node', id: g.getAttribute('data-id'), nodeElement: m.nodeElement, parent: m.parentFunctionNodeIdentifier ?? null,
                         x: r.left - app.left, y: r.top - app.top, width: r.width, height: r.height };
            });
            const regions = [...document.querySelectorAll('#app svg g[data-parent-id][data-region-type="subdivision"]')].map((g) => {
                const r = g.getBoundingClientRect();
                return { kind: 'region', id: g.getAttribute('data-parent-id'), x: r.left - app.left, y: r.top - app.top, width: r.width, height: r.height };
            });
            return [...nodes, ...regions];
        });
        const buf = await page.locator('#app').screenshot();
        return { dataUri: toDataUri(buf), boxes };""")
open(out_path, "w", encoding="utf-8").write(s)
print(out_path, capture_entry)
