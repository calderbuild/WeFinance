import { AnnaAppRuntime } from "/static/anna-apps/_sdk/latest/index.js";

// Real tool_ids minted on the Executa Hub -- must stay in sync with
// anna_app/manifest.json's required_executas and each executa.json.
const TOOL_IDS = {
  ocr: "tool-calderbuild-wefinance-bill-scanner-swymwa2w",
  chat: "tool-calderbuild-wefinance-advisor-chat-zm45qs9z",
  recommend: "tool-calderbuild-wefinance-investment-recommendations-r2q5jdey",
};

const DEFAULT_BUDGET = 5000;

const state = {
  transactions: [],
  // One budget per currency, e.g. {USD: 5000, CNY: 3000}. A single untyped
  // number would get relabeled whenever the overview switches currency.
  budgets: {},
  overviewCurrency: "USD",
};

let anna;

async function callTool(toolId, method, args) {
  // anna.tools.invoke() resolves directly to the executa's own `data` payload
  // on success (host already unwraps the {success, data} envelope) and
  // throws a real Error (with .code/.details) on failure -- see the SDK's
  // own usage example and error-shape note in _sdk/latest/index.js.
  try {
    return await anna.tools.invoke({ tool_id: toolId, method, args });
  } catch (err) {
    throw new Error(err?.message || err?.code || `${method} failed`);
  }
}

function stripDataUriPrefix(base64) {
  const comma = base64.indexOf(",");
  return base64.startsWith("data:") && comma !== -1 ? base64.slice(comma + 1) : base64;
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(stripDataUriPrefix(reader.result));
    reader.onerror = () => reject(reader.error || new Error("failed to read file"));
    reader.readAsDataURL(file);
  });
}

function formatTransactionsSummary(transactions) {
  if (!transactions.length) return "(no transactions scanned yet)";
  return transactions
    .map((t) => `${t.date} | ${t.merchant} | ${t.category} | ${t.amount} ${t.currency}`)
    .join("\n");
}

// Transaction and recommendation text comes from an LLM reading whatever a user
// uploads or types, so it's untrusted -- escape before it ever hits innerHTML.
function esc(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

function setStatus(el, message, isError) {
  el.textContent = message || "";
  el.classList.toggle("is-error", Boolean(isError));
}

function renderTransactionTable(transactions) {
  const table = document.getElementById("scan-table");
  const tbody = table.querySelector("tbody");
  tbody.innerHTML = "";
  for (const t of transactions) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${esc(t.date)}</td>
      <td>${esc(t.merchant)}</td>
      <td>${esc(t.category)}</td>
      <td>${esc(t.amount)}</td>
      <td>${esc(t.currency)}</td>
    `;
    tbody.appendChild(row);
  }
  table.hidden = transactions.length === 0;
}

function refreshTransactionCounts() {
  document.getElementById("ask-txn-count").textContent = state.transactions.length;
  document.getElementById("rec-txn-count").textContent = state.transactions.length;
}

async function persistTransactions() {
  await anna.storage.set({ key: "transactions", value: state.transactions });
}

async function persistBudget() {
  await anna.storage.set({ key: "budgets", value: state.budgets });
}

function budgetFor(budgets, currency) {
  const value = budgets[currency];
  return typeof value === "number" && value >= 0 ? value : DEFAULT_BUDGET;
}

// Older versions stored one number under "budget". It belongs to whatever
// currency the overview was showing, which is the currency it opens in now.
function migrateBudgets(storedBudgets, legacyBudget, currency) {
  if (storedBudgets && typeof storedBudgets === "object" && !Array.isArray(storedBudgets)) {
    return storedBudgets;
  }
  if (typeof legacyBudget === "number" && legacyBudget >= 0) {
    return { [currency]: legacyBudget };
  }
  return {};
}

function monthKey(dateStr) {
  return typeof dateStr === "string" ? dateStr.slice(0, 7) : "";
}

function formatMoney(amount, currency) {
  const value = Number(amount || 0);
  try {
    return value.toLocaleString(undefined, {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    });
  } catch {
    // Not an ISO 4217 code this browser knows: show the code, don't guess a symbol.
    return `${Math.round(value).toLocaleString()} ${currency}`;
  }
}

function currencySymbol(currency) {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency })
      .formatToParts(0)
      .find((p) => p.type === "currency").value;
  } catch {
    return currency;
  }
}

function mostCommon(values) {
  const counts = new Map();
  for (const v of values) counts.set(v, (counts.get(v) || 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
}

const currencyOf = (t) => t.currency || "USD";

function latestMonthOf(transactions) {
  return transactions
    .map((t) => monthKey(t.date))
    .filter(Boolean)
    .sort()
    .at(-1);
}

// The currency most of the latest month's rows are in (USD when there are none).
function overviewCurrencyOf(transactions) {
  const latestMonth = latestMonthOf(transactions);
  const latestMonthTxns = transactions.filter((t) => monthKey(t.date) === latestMonth);
  return (
    mostCommon((latestMonthTxns.length ? latestMonthTxns : transactions).map(currencyOf)) || "USD"
  );
}

function formatMonthLabel(key) {
  const [year, month] = key.split("-");
  if (!year || !month) return key;
  const date = new Date(Number(year), Number(month) - 1, 1);
  return date.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

function renderBarList(container, rows, currency) {
  container.innerHTML = "";
  if (!rows.length) {
    container.innerHTML = `<p class="hint">No spending recorded yet.</p>`;
    return;
  }
  const max = Math.max(...rows.map((r) => r.amount), 1);
  for (const row of rows) {
    const el = document.createElement("div");
    el.className = "bar-row";
    const pct = Math.max(2, Math.round((row.amount / max) * 100));
    el.innerHTML = `
      <div class="bar-row-label">${esc(row.label)}</div>
      <div class="bar-track"><div class="bar-fill" style="width: ${pct}%"></div></div>
      <div class="bar-row-value">${esc(formatMoney(row.amount, currency))}</div>
    `;
    container.appendChild(el);
  }
}

function renderOverview() {
  const empty = document.getElementById("overview-empty");
  const content = document.getElementById("overview-content");

  if (!state.transactions.length) {
    empty.hidden = false;
    content.hidden = true;
    return;
  }
  empty.hidden = true;
  content.hidden = false;

  // "This month" tracks the app's own data (latest scanned transaction),
  // not the device clock -- a personal ledger's current period is defined
  // by what's actually been scanned, not by wall-clock date.
  const latestMonth = latestMonthOf(state.transactions);

  // Amounts only add up within one currency. The overview follows the
  // currency most of this month's rows are in and says how many rows it left
  // out, rather than summing yuan into dollars under a "$".
  const currency = overviewCurrencyOf(state.transactions);
  const inCurrency = state.transactions.filter((t) => currencyOf(t) === currency);
  const otherCount = state.transactions.length - inCurrency.length;
  const note = document.getElementById("overview-currency-note");
  note.hidden = otherCount === 0;
  note.textContent = `Totals are in ${currency}. ${otherCount} transaction(s) in other currencies aren't included.`;
  document.getElementById("budget-currency").textContent = currencySymbol(currency);
  state.overviewCurrency = currency;
  const budget = budgetFor(state.budgets, currency);

  const thisMonthTxns = inCurrency.filter((t) => monthKey(t.date) === latestMonth);
  const totalSpent = thisMonthTxns.reduce((sum, t) => sum + (Number(t.amount) || 0), 0);
  const remaining = budget - totalSpent;
  const usageRate = budget > 0 ? (totalSpent / budget) * 100 : 0;

  let statusLabel = "Healthy";
  let statusType = "healthy";
  if (usageRate >= 100) {
    statusLabel = "Overspent";
    statusType = "danger";
  } else if (usageRate >= 85) {
    statusLabel = "Caution";
    statusType = "warning";
  } else if (usageRate >= 60) {
    statusLabel = "Good";
    statusType = "healthy";
  }

  const budgetInput = document.getElementById("budget-input");
  if (document.activeElement !== budgetInput) {
    budgetInput.value = budget;
  }
  document.getElementById("health-spent").textContent = formatMoney(totalSpent, currency);
  const remainingEl = document.getElementById("health-remaining");
  remainingEl.textContent = formatMoney(remaining, currency);
  remainingEl.classList.toggle("is-negative", remaining < 0);
  const badge = document.getElementById("health-badge");
  badge.textContent = statusLabel;
  badge.className = `badge ${statusType}`;
  const fill = document.getElementById("usage-bar-fill");
  fill.style.width = `${Math.min(usageRate, 100)}%`;
  fill.className = `usage-bar-fill ${statusType === "healthy" ? "" : statusType}`.trim();

  const monthTotals = new Map();
  for (const t of inCurrency) {
    const key = monthKey(t.date);
    if (!key) continue;
    monthTotals.set(key, (monthTotals.get(key) || 0) + (Number(t.amount) || 0));
  }
  const monthRows = [...monthTotals.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .slice(-6)
    .map(([key, amount]) => ({ label: formatMonthLabel(key), amount }));
  renderBarList(document.getElementById("trend-months"), monthRows, currency);

  const categoryTotals = new Map();
  for (const t of thisMonthTxns) {
    const key = t.category || "Other";
    categoryTotals.set(key, (categoryTotals.get(key) || 0) + (Number(t.amount) || 0));
  }
  const categoryRows = [...categoryTotals.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([label, amount]) => ({ label, amount }));
  renderBarList(document.getElementById("trend-categories"), categoryRows, currency);
}

function setupOverviewPanel() {
  const budgetInput = document.getElementById("budget-input");
  budgetInput.addEventListener("change", async () => {
    const value = Number(budgetInput.value);
    state.budgets[state.overviewCurrency] =
      Number.isFinite(value) && value >= 0 ? value : DEFAULT_BUDGET;
    await persistBudget();
    renderOverview();
  });

  document.getElementById("overview-empty-cta").addEventListener("click", () => {
    document.querySelector('.tab-btn[data-tab="scan"]').click();
  });
}

function setupTabs() {
  const buttons = document.querySelectorAll(".tab-btn");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      document.querySelectorAll(".panel").forEach((p) => {
        p.hidden = p.id !== `panel-${btn.dataset.tab}`;
      });
    });
  });
}

async function clearTransactions() {
  state.transactions = [];
  renderTransactionTable(state.transactions);
  refreshTransactionCounts();
  renderOverview();
  await persistTransactions();
}

function setupScanPanel() {
  const fileInput = document.getElementById("scan-file");
  const statusEl = document.getElementById("scan-status");
  const clearBtn = document.getElementById("clear-transactions");

  clearBtn.addEventListener("click", async () => {
    await clearTransactions();
    setStatus(statusEl, "Cleared all scanned transactions.");
  });

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files?.[0];
    if (!file) return;

    setStatus(statusEl, "Scanning...");
    try {
      const imageBase64 = await readFileAsBase64(file);
      const data = await callTool(TOOL_IDS.ocr, "extract_transactions", {
        image_base64: imageBase64,
        image_type: file.type || "image/jpeg",
      });
      const newTxns = data.transactions || [];
      state.transactions = state.transactions.concat(newTxns);
      renderTransactionTable(state.transactions);
      refreshTransactionCounts();
      renderOverview();
      await persistTransactions();
      setStatus(
        statusEl,
        newTxns.length
          ? `Found ${newTxns.length} transaction(s).`
          : "No transactions found in that image."
      );
    } catch (err) {
      setStatus(statusEl, err.message || String(err), true);
    } finally {
      fileInput.value = "";
    }
  });
}

function setupAskPanel() {
  const questionEl = document.getElementById("ask-question");
  const submitBtn = document.getElementById("ask-submit");
  const statusEl = document.getElementById("ask-status");
  const answerEl = document.getElementById("ask-answer");

  submitBtn.addEventListener("click", async () => {
    const question = questionEl.value.trim();
    if (!question) {
      setStatus(statusEl, "Type a question first.", true);
      return;
    }
    submitBtn.disabled = true;
    setStatus(statusEl, "Asking...");
    answerEl.hidden = true;
    try {
      const data = await callTool(TOOL_IDS.chat, "ask_advisor", {
        question,
        transactions_summary: formatTransactionsSummary(state.transactions),
      });
      answerEl.textContent = data.advice || "(no answer)";
      answerEl.hidden = false;
      setStatus(statusEl, "");
    } catch (err) {
      setStatus(statusEl, err.message || String(err), true);
    } finally {
      submitBtn.disabled = false;
    }
  });
}

function renderRecommendations(recommendations) {
  const container = document.getElementById("rec-cards");
  container.innerHTML = "";
  for (const rec of recommendations) {
    const card = document.createElement("div");
    card.className = "rec-card";
    const steps = (rec.rationale_steps || []).map((s) => `<li>${esc(s)}</li>`).join("");
    card.innerHTML = `
      <h3>${esc(rec.title)}</h3>
      <span class="risk-level">${esc(rec.risk_level)}</span>
      <p>${esc(rec.summary)}</p>
      <ul>${steps}</ul>
    `;
    container.appendChild(card);
  }
}

function setupRecommendPanel() {
  const submitBtn = document.getElementById("rec-submit");
  const statusEl = document.getElementById("rec-status");

  submitBtn.addEventListener("click", async () => {
    if (!state.transactions.length) {
      setStatus(statusEl, "Scan at least one bill first.", true);
      return;
    }
    const riskProfile = document.getElementById("rec-risk").value;
    const incomeRaw = document.getElementById("rec-income").value;
    const goal = document.getElementById("rec-goal").value.trim();
    const horizon = document.getElementById("rec-horizon").value.trim();

    submitBtn.disabled = true;
    setStatus(statusEl, "Generating recommendations...");
    document.getElementById("rec-cards").innerHTML = "";
    try {
      const args = {
        transactions: state.transactions,
        risk_profile: riskProfile,
        investment_goal: goal,
        investment_horizon: horizon,
      };
      if (incomeRaw !== "") {
        args.monthly_income = Number(incomeRaw);
      }
      const data = await callTool(TOOL_IDS.recommend, "generate_recommendations", args);
      renderRecommendations(data.recommendations || []);
      setStatus(statusEl, "");
    } catch (err) {
      setStatus(statusEl, err.message || String(err), true);
    } finally {
      submitBtn.disabled = false;
    }
  });
}

async function main() {
  anna = await AnnaAppRuntime.connect();

  // Read back through anna.storage.get() -- NOT anna.runtimeState, which is
  // a one-time snapshot from the window "hello" handshake and is never
  // updated by anna.storage.set(). Those are two separate backends; writing
  // to one and reading from the other is why data looked persisted within
  // a session but reset to empty on every reopen.
  const [storedTransactions, storedBudgets, legacyBudget] = await Promise.all([
    anna.storage.get({ key: "transactions" }),
    anna.storage.get({ key: "budgets" }),
    anna.storage.get({ key: "budget" }),
  ]);
  if (storedTransactions?.exists && Array.isArray(storedTransactions.value)) {
    state.transactions = storedTransactions.value;
    renderTransactionTable(state.transactions);
  }
  state.budgets = migrateBudgets(
    storedBudgets?.exists ? storedBudgets.value : null,
    legacyBudget?.exists ? legacyBudget.value : null,
    overviewCurrencyOf(state.transactions)
  );
  refreshTransactionCounts();
  renderOverview();

  setupTabs();
  setupOverviewPanel();
  setupScanPanel();
  setupAskPanel();
  setupRecommendPanel();
}

main().catch((err) => {
  document.getElementById("root").textContent = `Failed to start: ${err.message || err}`;
});
