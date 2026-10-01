/**
 * Byte-parity test: the JS converter must emit exactly what the Python converter
 * (src/t2a_sysml) emits for the same input, in both --imm-tags and plain forms.
 * Skips when `python` is not on PATH.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";

import { convertFile, convertStateFile, loadModel, validateSchema } from "../t2a_sysml/index.js";
import { ROOT, GOLD_JSONS, COFFEE, NON_GOLD } from "./fixtures.js";

const FIXTURES = [...GOLD_JSONS, COFFEE, NON_GOLD].filter(existsSync);

const PY = `
import sys, json
sys.path.insert(0, sys.argv[1])
from t2a_sysml import convert_file
sys.stdout.reconfigure(encoding="utf-8", newline="")
sys.stdout.write(convert_file(sys.argv[2], imm_tags=(sys.argv[3] == "1")))
`;

function pythonConvert(file, immTags) {
  const r = spawnSync("python", ["-c", PY, path.join(ROOT, "src"), file, immTags ? "1" : "0"], {
    encoding: "utf8",
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
  });
  if (r.error || r.status !== 0) return null;
  return r.stdout;
}

const pythonAvailable = spawnSync("python", ["--version"], { encoding: "utf8" }).status === 0;

test("JS output is byte-identical to Python converter", { skip: !pythonAvailable && "python not on PATH" }, async (t) => {
  assert.ok(FIXTURES.length > 0, "no fixtures found");
  for (const file of FIXTURES) {
    for (const immTags of [true, false]) {
      await t.test(`${path.basename(file)} immTags=${immTags}`, () => {
        const expected = pythonConvert(file, immTags);
        assert.ok(expected !== null, "python converter failed");
        const actual = convertFile(file, { immTags });
        assert.equal(actual, expected);
      });
    }
  }
});

const PY_SCHEMA = `
import sys, json
sys.path.insert(0, sys.argv[1])
from t2a_sysml import load_model, validate_schema
sys.stdout.reconfigure(encoding="utf-8")
issues = validate_schema(load_model(sys.argv[2]))
print(json.dumps(sorted([i.code, i.severity] for i in issues)))
`;

function pythonSchemaIssues(file) {
  const r = spawnSync("python", ["-c", PY_SCHEMA, path.join(ROOT, "src"), file], {
    encoding: "utf8",
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
  });
  if (r.error || r.status !== 0) return null;
  return JSON.parse(r.stdout);
}

const PY_STATE = `
import sys
sys.path.insert(0, sys.argv[1])
from t2a_sysml import convert_state_file
sys.stdout.reconfigure(encoding="utf-8", newline="")
sys.stdout.write(convert_state_file(sys.argv[2]))
`;

function pythonStateConvert(file) {
  const r = spawnSync("python", ["-c", PY_STATE, path.join(ROOT, "src"), file], {
    encoding: "utf8",
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
  });
  if (r.error || r.status !== 0) return null;
  return r.stdout;
}

test(
  "state view: JS output is byte-identical to Python converter",
  { skip: !pythonAvailable && "python not on PATH" },
  async (t) => {
    for (const file of [...GOLD_JSONS, COFFEE].filter(existsSync)) {
      await t.test(path.basename(file), () => {
        const expected = pythonStateConvert(file);
        assert.ok(expected !== null, "python state converter failed");
        assert.equal(convertStateFile(file), expected);
      });
    }
  },
);

test(
  "validate_schema parity: JS and Python emit the same (code, severity) list",
  { skip: !pythonAvailable && "python not on PATH" },
  async (t) => {
    for (const file of GOLD_JSONS.filter(existsSync)) {
      await t.test(path.basename(file), () => {
        const expected = pythonSchemaIssues(file);
        assert.ok(expected !== null, "python validate_schema failed");
        const actual = validateSchema(loadModel(file))
          .map((i) => [i.code, i.severity])
          .sort();
        assert.deepEqual(actual, expected);
      });
    }
  },
);
