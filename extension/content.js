// Inline banner (stretch). Runs inside the Gmail tab. It watches for the open message,
// asks the service worker to analyze it, and injects a colored verdict banner above it.
// The banner shows the score plus an "Explain" button; clicking it (and only then) fetches
// a fresh plain-English AI explanation of the score into an expandable panel.
//
// Best-effort: Gmail's DOM is obfuscated and changes, so if the selector misses, the
// banner simply doesn't appear (the reliable path is the toolbar popup).
//
// Auth note: analysis uses a SILENT token (interactive:false), so open the popup and sign
// in once first — after that the cached token lets the banner work without prompting.
// (The Explain call needs no Gmail token — it hits our own backend.)
(function () {
  let lastId = null;
  let inflight = false;

  function openMessage() {
    const nodes = document.querySelectorAll("[data-legacy-message-id]");
    if (!nodes.length) return null;
    const node = nodes[nodes.length - 1]; // last = most-recently-opened message
    return { id: node.getAttribute("data-legacy-message-id"), node };
  }

  function bucket(l) {
    return ["legitimate", "suspicious", "phishing"].includes((l || "").toLowerCase())
      ? l.toLowerCase()
      : "suspicious";
  }

  function makeBanner(v) {
    const el = document.createElement("div");
    el.className = "pd-wrap pd-" + bucket(v.risk_label);
    el.dataset.verdictId = v.verdict_id != null ? String(v.verdict_id) : "";
    el.innerHTML =
      `<div class="pd-banner">` +
      `<span class="pd-dot"></span>` +
      `<b>${(v.risk_label || "").toUpperCase()}</b>` +
      `<span class="pd-score">${Math.round(v.risk_score)}/100</span>` +
      `<button class="pd-explain-btn" type="button">Explain ▾</button>` +
      `<span class="pd-tag">Phishing Detector</span>` +
      `</div>` +
      `<div class="pd-panel" hidden></div>`;
    return el;
  }

  function toggleExplain(el) {
    const btn = el.querySelector(".pd-explain-btn");
    const panel = el.querySelector(".pd-panel");
    if (!panel.hidden) {
      panel.hidden = true;
      btn.textContent = "Explain ▾";
      return;
    }
    panel.hidden = false;
    btn.textContent = "Hide ▴";
    if (panel.dataset.loaded === "1") return; // fetched once, keep it

    const vid = el.dataset.verdictId;
    if (!vid) {
      panel.textContent = "No verdict id available to explain.";
      return;
    }
    panel.textContent = "Asking the model…";
    chrome.runtime.sendMessage({ type: "explain", verdictId: Number(vid) }, (resp) => {
      if (resp && resp.ok && resp.result) {
        const r = resp.result;
        panel.textContent =
          r.available && r.explanation
            ? r.explanation
            : "The AI explanation is unavailable (the model didn't run for this verdict).";
        panel.dataset.loaded = "1";
      } else {
        panel.textContent = "Couldn't get an explanation: " + ((resp && resp.error) || "unknown error");
      }
    });
  }

  function inject(node, verdict) {
    document.querySelectorAll(".pd-wrap").forEach((e) => e.remove());
    const el = makeBanner(verdict);
    const parent = node.parentElement;
    if (!parent) return;
    parent.insertBefore(el, node);
    el.querySelector(".pd-explain-btn").addEventListener("click", () => toggleExplain(el));
  }

  function tick() {
    const cur = openMessage();
    if (!cur || !cur.id || cur.id === lastId || inflight) return;
    lastId = cur.id;
    inflight = true;
    chrome.runtime.sendMessage(
      { type: "analyze", id: cur.id, interactive: false, useLlm: true },
      (resp) => {
        inflight = false;
        if (resp && resp.ok) inject(cur.node, resp.verdict);
      }
    );
  }

  setInterval(tick, 1500);
})();
