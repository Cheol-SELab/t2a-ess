/**
 * Round-trip every synthetic case and fixture through the selab-rust-lsp server and
 * check diagnostics + diagram graph (see tools/lsp_check.js). Skipped when the LSP
 * binary is not present (set SELAB_LSP_BIN to point at one).
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { LSP_BIN, lspAvailable, runAll } from "../tools/lsp_check.js";

test("selab-rust-lsp accepts converter output", { skip: !lspAvailable() && `sysml-lsp not found at ${LSP_BIN}` }, async (t) => {
  const results = await runAll();
  assert.ok(results.length > 0);
  for (const r of results) {
    await t.test(`${r.kind}: ${r.id}`, () => {
      assert.ok(r.ok, r.problems.join("\n"));
    });
  }
});
