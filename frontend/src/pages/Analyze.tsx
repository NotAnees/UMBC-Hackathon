import { useRef, useState } from "react";

import { analyzeEml, analyzeText, type AnalyzeResponse } from "../api";
import StatTiles from "../components/StatTiles";
import VerdictBanner from "../components/VerdictBanner";
import VerdictCard from "../components/VerdictCard";

const SAMPLE = `Authentication-Results: mx; spf=fail; dkim=fail; dmarc=fail
From: PayPal Support <support@paypa1-secure.com>
Reply-To: replies@totally-different.ru
Subject: URGENT: verify your account
Date: Tue, 15 Sep 2026 10:22:31 +0000
Content-Type: text/html

<html><body><p>URGENT: your account will be suspended. Act now to confirm your identity.</p>
<a href="http://192.168.1.5/login">paypal.com/login</a></body></html>`;

export default function Analyze() {
  const [raw, setRaw] = useState("");
  // Off until demo time: each analysis with this on is one paid Claude call.
  const [useLlm, setUseLlm] = useState(false);
  const [domainAge, setDomainAge] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [dragging, setDragging] = useState(false);
  const [analyzed, setAnalyzed] = useState(0);
  const fileInput = useRef<HTMLInputElement>(null);

  const options = () => ({
    useLlm,
    domainAgeDays: domainAge.trim() === "" ? null : Number(domainAge),
  });

  async function run(work: () => Promise<AnalyzeResponse>) {
    setBusy(true);
    setError(null);
    try {
      setResult(await work());
      setAnalyzed((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  function submitText() {
    if (raw.trim() === "" || busy) return;
    void run(() => analyzeText(raw, options()));
  }

  function submitFile(file: File) {
    void run(() => analyzeEml(file, options()));
  }

  return (
    <>
      <h1>Analyze</h1>
      <p className="subtitle">Paste a raw email or drop an .eml file to get a verdict.</p>

      <StatTiles reloadKey={analyzed} />

      <div
        className={`panel dropzone${dragging ? " dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          const file = event.dataTransfer.files[0];
          if (file) submitFile(file);
        }}
      >
        <textarea
          value={raw}
          onChange={(event) => setRaw(event.target.value)}
          onKeyDown={(event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === "Enter") submitText();
          }}
          aria-label="Raw email to analyze"
          placeholder="Paste full headers + body, or just the body…"
          rows={12}
          spellCheck={false}
        />

        <div className="controls">
          <button
            className="primary"
            onClick={submitText}
            disabled={busy || raw.trim() === ""}
            aria-busy={busy}
            title="Analyze this email (Cmd/Ctrl + Enter)"
          >
            {busy ? "Analyzing…" : "Analyze"}
          </button>

          <button onClick={() => fileInput.current?.click()} disabled={busy}>
            Upload .eml
          </button>
          <input
            ref={fileInput}
            type="file"
            accept=".eml,message/rfc822,text/plain"
            hidden
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) submitFile(file);
              event.target.value = "";
            }}
          />

          <label className="check">
            <input
              type="checkbox"
              checked={useLlm}
              onChange={(event) => setUseLlm(event.target.checked)}
            />
            AI deep scan
          </label>

          <label className="check">
            domain age
            <input
              className="num"
              type="number"
              min={0}
              value={domainAge}
              onChange={(event) => setDomainAge(event.target.value)}
              placeholder="days"
            />
          </label>

          <button className="ghost" onClick={() => setRaw(SAMPLE)} disabled={busy}>
            load sample
          </button>
        </div>
        <p className="placeholder">or drop an .eml anywhere on this panel</p>
      </div>

      <div aria-live="polite">
        {busy && <p className="note">Analyzing — running checks{useLlm ? " and the AI deep scan" : ""}…</p>}
      </div>

      {error && (
        <div className="panel error" role="alert">
          {error}
        </div>
      )}

      {result && (
        <>
          <VerdictBanner
            label={result.risk_label}
            score={result.risk_score}
            heuristicScore={result.heuristic_score}
            heuristicLabel={result.heuristic_label}
            weightCovered={result.risk_weight_covered}
            meta={`verdict #${result.verdict_id}`}
          />
          <VerdictCard result={result} />
        </>
      )}
    </>
  );
}
