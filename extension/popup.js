const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const bucket = (l) => (["legitimate", "suspicious", "phishing"].includes((l || "").toLowerCase()) ? l.toLowerCase() : "suspicious");

function send(msg) {
  return new Promise((resolve) => chrome.runtime.sendMessage(msg, resolve));
}

let items = [];

$("load").addEventListener("click", async () => {
  $("load").disabled = true;
  $("status").textContent = "Signing in & loading…";
  const resp = await send({ type: "listRecent", interactive: true });
  $("load").disabled = false;
  if (!resp || !resp.ok) {
    $("list").innerHTML = `<div class="err">Couldn't load Gmail: ${esc(resp?.error || "unknown error")}</div>`;
    $("status").textContent = "";
    return;
  }
  items = resp.items;
  $("status").textContent = `${items.length} recent email(s)`;
  $("all").disabled = items.length === 0;
  render();
});

$("all").addEventListener("click", async () => {
  $("all").disabled = true;
  for (const it of items) await analyzeRow(it.id);
  $("all").disabled = false;
});

function render() {
  $("list").innerHTML = items
    .map(
      (it) => `
      <div class="row" data-id="${esc(it.id)}">
        <div class="from">${esc(it.from)}</div>
        <div class="subj">${esc(it.subject) || "(no subject)"}</div>
        <div class="foot">
          <span class="badge pending" data-badge>not analyzed</span>
          <button class="ghost mini" data-analyze>Analyze</button>
          <button class="ghost mini" data-explain hidden>Explain</button>
        </div>
        <div class="rat" data-rat></div>
      </div>`
    )
    .join("");
  document.querySelectorAll("[data-analyze]").forEach((btn) =>
    btn.addEventListener("click", () => analyzeRow(btn.closest(".row").dataset.id))
  );
  document.querySelectorAll("[data-explain]").forEach((btn) =>
    btn.addEventListener("click", () => explainRow(btn.closest(".row").dataset.id))
  );
}

async function analyzeRow(id) {
  const row = document.querySelector(`.row[data-id="${CSS.escape(id)}"]`);
  if (!row) return;
  const badge = row.querySelector("[data-badge]");
  const rat = row.querySelector("[data-rat]");
  const explainBtn = row.querySelector("[data-explain]");
  badge.className = "badge pending";
  badge.textContent = "analyzing…";
  const resp = await send({ type: "analyze", id, interactive: false, useLlm: true });
  if (!resp || !resp.ok) {
    badge.className = "badge pending";
    badge.textContent = "error";
    rat.textContent = resp?.error || "";
    return;
  }
  const v = resp.verdict;
  const b = bucket(v.risk_label);
  badge.className = "badge " + b;
  badge.textContent = `${v.risk_label} · ${Math.round(v.risk_score)}`;
  rat.textContent = v.llm ? v.llm.rationale : "Scored on deterministic signals (Claude pass didn't run).";
  if (v.verdict_id != null) {
    row.dataset.verdictId = String(v.verdict_id);
    explainBtn.hidden = false;
  }
}

async function explainRow(id) {
  const row = document.querySelector(`.row[data-id="${CSS.escape(id)}"]`);
  if (!row) return;
  const rat = row.querySelector("[data-rat]");
  const btn = row.querySelector("[data-explain]");
  const vid = row.dataset.verdictId;
  if (!vid) return;
  btn.disabled = true;
  rat.textContent = "Asking the model…";
  const resp = await send({ type: "explain", verdictId: Number(vid) });
  btn.disabled = false;
  if (resp && resp.ok && resp.result && resp.result.available && resp.result.explanation) {
    rat.textContent = resp.result.explanation;
  } else if (resp && resp.ok && resp.result) {
    rat.textContent = "AI explanation unavailable (the model didn't run for this verdict).";
  } else {
    rat.textContent = "Couldn't get an explanation: " + ((resp && resp.error) || "unknown error");
  }
}
