// Service worker: the only context with OAuth + host permissions. The popup and the
// in-page content script both message it to do the privileged work (get a token, read
// Gmail via the API, call the detector's /analyze). Keeping it here avoids cross-origin
// and CORS problems that would hit a content script running in the mail.google.com page.

const BACKEND = "http://localhost:8000"; // the blue-team detector API
const GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me";

function getToken(interactive) {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ interactive }, (token) => {
      if (chrome.runtime.lastError || !token) {
        reject(new Error(chrome.runtime.lastError?.message || "No auth token"));
      } else {
        resolve(token);
      }
    });
  });
}

async function gfetch(path, token) {
  const r = await fetch(GMAIL + path, { headers: { Authorization: "Bearer " + token } });
  if (!r.ok) throw new Error("Gmail API " + r.status);
  return r.json();
}

async function listRecent(token, max = 12) {
  const list = await gfetch(`/messages?maxResults=${max}&q=in:inbox`, token);
  const ids = (list.messages || []).map((m) => m.id);
  const items = [];
  for (const id of ids) {
    const m = await gfetch(
      `/messages/${id}?format=metadata&metadataHeaders=Subject&metadataHeaders=From`,
      token
    );
    const headers = m.payload?.headers || [];
    const h = (name) => (headers.find((x) => x.name.toLowerCase() === name) || {}).value || "";
    items.push({ id, subject: h("subject"), from: h("from"), snippet: m.snippet || "" });
  }
  return items;
}

function b64urlToText(b64url) {
  const b64 = (b64url || "").replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64);
  const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
  return new TextDecoder("utf-8").decode(bytes);
}

async function analyze(token, id, useLlm) {
  // format=raw gives the full RFC822 message (headers included), so the detector's
  // header heuristics (SPF/DKIM/DMARC, domain mismatch) can fire.
  const m = await gfetch(`/messages/${id}?format=raw`, token);
  const raw = b64urlToText(m.raw);
  const r = await fetch(BACKEND + "/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_email: raw, source: "upload", use_llm: useLlm !== false }),
  });
  if (!r.ok) throw new Error("analyze " + r.status + " — " + (await r.text()).slice(0, 140));
  return r.json();
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    try {
      const token = await getToken(msg.interactive !== false);
      if (msg.type === "listRecent") {
        sendResponse({ ok: true, items: await listRecent(token) });
      } else if (msg.type === "analyze") {
        sendResponse({ ok: true, verdict: await analyze(token, msg.id, msg.useLlm) });
      } else {
        sendResponse({ ok: false, error: "unknown message type" });
      }
    } catch (e) {
      sendResponse({ ok: false, error: e.message });
    }
  })();
  return true; // keep the message channel open for the async response
});
