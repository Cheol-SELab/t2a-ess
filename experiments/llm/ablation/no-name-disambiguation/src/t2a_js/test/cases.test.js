/**
 * Structural tests over the synthetic cases (test/cases.js): converter output shape,
 * validator error counts, and Python parity per case. No LSP needed.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import os from "node:os";
import path from "node:path";

import { convertModel, loadModelFromObject, summarize, validateEffbd } from "../t2a_sysml/index.js";
import { CASES } from "./cases.js";
import { ROOT, balanced } from "./fixtures.js";

const pythonAvailable = spawnSync("python", ["--version"], { encoding: "utf8" }).status === 0;
const tmp = mkdtempSync(path.join(os.tmpdir(), "t2a-cases-"));

const PY = `
import sys
sys.path.insert(0, sys.argv[1])
from t2a_sysml import convert_file
sys.stdout.reconfigure(encoding="utf-8", newline="")
sys.stdout.write(convert_file(sys.argv[2], imm_tags=(sys.argv[3] == "1")))
`;

for (const c of CASES) {
  test(`case ${c.id}: ${c.title}`, async (t) => {
    const model = loadModelFromObject(c.model);
    const sysml = convertModel(model);
    const e = c.expect;

    assert.ok(balanced(sysml), "unbalanced braces");
    const count = (re) => (sysml.match(re) ?? []).length;
    assert.equal(count(/^\s*fork '/gm), e.forks, "fork count");
    assert.equal(count(/^\s*join '/gm), e.joins, "join count");
    assert.equal(count(/ if '[^']*' == true then /g), e.guards, "guard count");
    assert.equal(count(/^\s*flow from /gm), e.flows, "flow line count");
    assert.equal(count(/^\s*allocate '/gm), e.allocations, "allocate count");
    assert.equal(count(/^\s*part '.*' : Performer;/gm), e.performers, "performer count");
    // nested => episode bodies carry their own successions at indent 8; flat => indent 4 only
    const nestedSucc = count(/^ {8}succession first /gm);
    assert.equal(nestedSucc > 0, e.nested, `nested=${e.nested} but found ${nestedSucc} episode-level successions`);
    // fork/join names unique
    const fj = [...sysml.matchAll(/^\s*(?:fork|join) '([^']+)';/gm)].map((m) => m[1]);
    assert.equal(new Set(fj).size, fj.length, `duplicate fork/join names: ${fj}`);
    for (const s of e.expectText ?? []) assert.ok(sysml.includes(s), `missing: ${s}`);
    for (const s of e.forbidText ?? []) assert.ok(!sysml.includes(s), `forbidden: ${s}`);
    // no raw quotes/newlines/backslashes inside quoted labels
    assert.ok(!/'[^'\n]*\\[^'\n]*'/.test(sysml), "backslash leaked into a label");

    const v = summarize(validateEffbd(model));
    assert.equal(v.errors, e.validateErrors, `validator errors: ${JSON.stringify(validateEffbd(model))}`);

    await t.test("python parity", (tt) => {
      if (!pythonAvailable) return tt.skip("python not on PATH");
      const file = path.join(tmp, `${c.id}.json`);
      writeFileSync(file, JSON.stringify(c.model), "utf8");
      for (const imm of [true, false]) {
        const r = spawnSync("python", ["-c", PY, path.join(ROOT, "src"), file, imm ? "1" : "0"], {
          encoding: "utf8", env: { ...process.env, PYTHONIOENCODING: "utf-8" },
        });
        assert.equal(r.status, 0, `python failed: ${r.stderr}`);
        assert.equal(convertModel(model, { immTags: imm }), r.stdout, `parity immTags=${imm}`);
      }
    });
  });
}
