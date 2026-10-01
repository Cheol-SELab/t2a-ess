/** Shared fixture paths + helpers for the JS converter tests. */
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(HERE, "..", "..", ".."); // text2activity/
const GOLD = path.join(ROOT, "data", "gold");
export const MUMT = path.join(GOLD, "mumt", "mumt.gold.json");
export const GOLD_JSONS = [
  MUMT,
  path.join(GOLD, "nghe", "nghe.gold.json"),
  path.join(GOLD, "av", "av.gold.json"),
];
export const COFFEE = path.join(ROOT, "src", "examples", "coffee_order_T2A-ESS.json");
export const NON_GOLD = path.join(ROOT, "data", "diagnostic", "mumt", "mumt.nongold.json");

export function balanced(text) {
  let depth = 0;
  for (const ch of text) {
    if (ch === "{") depth += 1;
    else if (ch === "}") {
      depth -= 1;
      if (depth < 0) return false;
    }
  }
  return depth === 0;
}

/** Returns true (and marks the test skipped) when the fixture file is absent. */
export const skipUnless = (t, file) =>
  existsSync(file) ? false : (t.skip(`fixture missing: ${path.basename(file)}`), true);
