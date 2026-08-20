import { AnnaAppRuntime } from "/static/anna-apps/_sdk/latest/index.js";

// Real tool_ids minted on the Executa Hub -- must stay in sync with
// anna_app/manifest.json's required_executas and each executa.json.
const TOOL_IDS = {
  ocr: "tool-calderbuild-wefinance-bill-scanner-swymwa2w",
  chat: "tool-calderbuild-wefinance-advisor-chat-zm45qs9z",
  recommend: "tool-calderbuild-wefinance-investment-recommendations-r2q5jdey",
};

const state = {
  transactions: [],
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
      <td>${t.date ?? ""}</td>
      <td>${t.merchant ?? ""}</td>
      <td>${t.category ?? ""}</td>
      <td>${t.amount ?? ""}</td>
      <td>${t.currency ?? ""}</td>
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

function setupScanPanel() {
  const fileInput = document.getElementById("scan-file");
  const statusEl = document.getElementById("scan-status");

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files?.[0];
    if (!file) return;

    setStatus(statusEl, "Scanning...");
    try {
      const imageBase64 = await readFileAsBase64(file);
      const data = await callTool(TOOL_IDS.ocr, "extract_transactions", {
        image_base64: imageBase64,
        image_type: file.type || "image/jpeg",
        filename: file.name,
      });
      const newTxns = data.transactions || [];
      state.transactions = state.transactions.concat(newTxns);
      renderTransactionTable(state.transactions);
      refreshTransactionCounts();
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
    const steps = (rec.rationale_steps || []).map((s) => `<li>${s}</li>`).join("");
    card.innerHTML = `
      <h3>${rec.title ?? ""}</h3>
      <span class="risk-level">${rec.risk_level ?? ""}</span>
      <p>${rec.summary ?? ""}</p>
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

  const persisted = anna.runtimeState?.transactions;
  if (Array.isArray(persisted)) {
    state.transactions = persisted;
    renderTransactionTable(state.transactions);
  }
  refreshTransactionCounts();

  anna.on("runtime_state_synced", (syncedState) => {
    if (Array.isArray(syncedState?.transactions)) {
      state.transactions = syncedState.transactions;
      renderTransactionTable(state.transactions);
      refreshTransactionCounts();
    }
  });

  setupTabs();
  setupScanPanel();
  setupAskPanel();
  setupRecommendPanel();
}

main().catch((err) => {
  document.getElementById("root").textContent = `Failed to start: ${err.message || err}`;
});
