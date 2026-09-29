// Checks the per-currency budget helpers in bundle/app.js: node anna_app/check_budget.mjs
// app.js needs the Anna SDK and a DOM, so load it without its import line and
// its main() call, and export the pure helpers.
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const src = readFileSync(new URL("./bundle/app.js", import.meta.url), "utf8");
const body = src
  .replace(/^import .*\n/m, "")
  .replace(/\nmain\(\)\.catch[\s\S]*$/, "\n");
assert.notEqual(body, src);
const tmp = join(mkdtempSync(join(tmpdir(), "wefinance-")), "app.mjs");
writeFileSync(tmp, `${body}\nexport { budgetFor, migrateBudgets, overviewCurrencyOf };\n`);
const { budgetFor, migrateBudgets, overviewCurrencyOf } = await import(tmp);

// A USD budget must not be reused as a CNY budget.
assert.equal(budgetFor({ USD: 1000 }, "USD"), 1000);
assert.equal(budgetFor({ USD: 1000 }, "CNY"), 5000);

// The old single number moves to the currency the overview opens in.
assert.deepEqual(migrateBudgets(null, 1000, "USD"), { USD: 1000 });
assert.deepEqual(migrateBudgets({ CNY: 3000 }, 1000, "USD"), { CNY: 3000 });
assert.deepEqual(migrateBudgets(null, null, "USD"), {});

const txns = [
  { date: "2026-08-03", amount: 10, currency: "USD" },
  { date: "2026-08-04", amount: 10, currency: "USD" },
  { date: "2026-09-01", amount: 45, currency: "CNY" },
];
assert.equal(overviewCurrencyOf(txns), "CNY");
assert.equal(overviewCurrencyOf([]), "USD");

console.log("budget checks passed");
