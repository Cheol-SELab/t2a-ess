"""Re-render every EFFBD input through the editor's headless pipeline (editor-render.test.mjs, vitest from the editor).

Jobs: the case-study conversions (MUM-T all expanded; NGHE all expanded, E2 kept collapsed, only E2 expanded,
none expanded) and the seven reported outputs plus the coffee example converted from <t2a-root> (all expanded).
usage: python render_all.py <t2a-root>
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(sys.argv[1])
EDITOR = "G:/SW/SW-SELab/selab-ex-system-modeler/packages/selab-effbd-editor"
CASE = os.path.join(HERE, "..", "outputs")
OUT, ALL = os.path.join(HERE, "..", "outputs"), os.path.join(HERE, "..", "..", "structural", "editor-render")
os.makedirs(OUT, exist_ok=True)
os.makedirs(ALL, exist_ok=True)
FILES = ["data/gold/mumt/mumt.gold.json", "data/gold/nghe/nghe.gold.json", "data/gold/av/av.gold.json",
         "data/diagnostic/mumt/mumt.nongold.json", "data/diagnostic/mumt/mumt.exhaustive.json",
         "data/diagnostic/nghe/nghe.nongold.json", "data/diagnostic/nghe/nghe.exhaustive.json",
         "src/examples/coffee_order_T2A-ESS.json"]
CONV = ("import {readFileSync, writeFileSync} from 'node:fs'; import {pathToFileURL} from 'node:url';"
        "const [root, src, dst] = process.argv.slice(1);"
        "const {loadModelFromObject, convertModel} = await import(pathToFileURL(root + '/src/t2a_js/t2a_sysml/index.js').href);"
        "const m = loadModelFromObject(JSON.parse(readFileSync(src, 'utf8').replace(/^\\uFEFF/, '')));"
        "writeFileSync(dst, convertModel(m, {immTags: true}), 'utf8');")
jobs, index = [], []
for i, f in enumerate(FILES, 1):
    sp = os.path.join(ALL, f"{i:02d}.sysml")
    subprocess.run(["node", "--input-type=module", "-e", CONV, ROOT, os.path.join(ROOT, f), sp], check=True)
    jobs.append({"in": sp, "out": sp[:-6] + ".png"})
    index.append(f"{i:02d} {f}")
open(os.path.join(ALL, "index.txt"), "w", encoding="utf-8", newline="
").write("\n".join(index) + "\n")
mumt, nghe = os.path.join(CASE, "mumt-en.sysml"), os.path.join(CASE, "nghe-en.sysml")
E = ["E1 Site setup and Level 3 start", "E2 Level 4 autonomous production", "E3 Fog and cyber threat response",
     "E4 Heavy rain and work stop", "E5 Recovery and mission completion"]
EM = ["E1 Preparation under normal comms", "E2 Observation post and FPV threat", "E3 EW jamming and comms degradation",
      "E4 Comms recovery and attack resumption"]
jobs += [{"in": mumt, "out": os.path.join(OUT, "editor-mumt.png")},
         {"in": mumt, "out": os.path.join(OUT, "editor-mumt-none.png"), "keepCollapsed": EM},
         {"in": nghe, "out": os.path.join(OUT, "editor-nghe.png")},
         {"in": nghe, "out": os.path.join(OUT, "editor-nghe-e2collapsed.png"), "keepCollapsed": [E[1]]},
         {"in": nghe, "out": os.path.join(OUT, "editor-nghe-e2only.png"), "keepCollapsed": [E[0], E[2], E[3], E[4]]},
         {"in": nghe, "out": os.path.join(OUT, "editor-nghe-none.png"), "keepCollapsed": E}]
jobs = [{**j, "in": os.path.abspath(j["in"]), "out": os.path.abspath(j["out"])} for j in jobs]
env = dict(os.environ, EFFBD_RENDER_JOBS=json.dumps(jobs, ensure_ascii=False))
r = subprocess.run(["npx", "vitest", "run", "--config", os.path.join(HERE, "vitest.render.config.mjs")], cwd=EDITOR, env=env,
                   capture_output=True, text=True, encoding="utf-8", errors="replace", shell=(os.name == "nt"))
open(os.path.join(OUT, "render_all.log"), "w", encoding="utf-8").write(r.stdout + "\n" + r.stderr)
print(r.stdout[-3000:], r.stderr[-2000:])
