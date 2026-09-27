// Inline banner (stretch). Runs inside the Gmail tab. It watches for the open message,
// asks the service worker to analyze it, and injects a colored verdict banner above it.
// Best-effort: Gmail's DOM is obfuscated and changes, so if the selector misses, the
// banner simply doesn't appear (the reliable path is the toolbar popup).
//
// Auth note: this uses a SILENT token (interactive:false), so open the popup and sign in
// once first — after that the cached token lets the banner work without prompting.
(function () {
  let lastId = null;
  let inflight = false;

  function openMessage() {
    // Gmail tags each message div with the API's message id here.
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
    el.className = "pd-banner pd-" + bucket(v.risk_label);
    const rationale = v.llm ? v.llm.rationale : "Scored on deterministic signals (Claude pass didn't run).";
    el.innerHTML =
      `<span class="pd-dot"></span><b>${(v.risk_label || "").toUpperCase()}</b>` +
      `<span class="pd-score">${Math.round(v.risk_score)}/100</span>` +
      `<span class="pd-rat"></span><span class="pd-tag">Phishing Detector</span>`;
    el.querySelector(".pd-rat").textContent = rationale; // textContent = safe, no injection
    return el;
  }

  function inject(node, verdict) {
    document.querySelectorAll(".pd-banner").forEach((e) => e.remove());
    const parent = node.parentElement;
    if (parent) parent.insertBefore(makeBanner(verdict), node);
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
