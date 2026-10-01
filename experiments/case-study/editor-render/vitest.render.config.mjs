// vitest config that runs the case-study render test with the EFFBD editor's own test setup,
// without placing any file in the editor repository.
import path from "node:path";
import { fileURLToPath } from "node:url";

const EDITOR = "G:/SW/SW-SELab/selab-ex-system-modeler/packages/selab-effbd-editor";
const HERE = path.dirname(fileURLToPath(import.meta.url));

export default {
  root: EDITOR,
  server: { fs: { strict: false } },
  test: {
    include: [path.join(HERE, "editor-render.test.mjs").replace(/\\/g, "/")],
    environment: "node",
    globals: false,
    testTimeout: 600_000,
    setupFiles: [path.join(EDITOR, "tests/setup.js")],
    alias: { vscode: path.join(EDITOR, "tests/mocks/vscode.js") },
  },
};
