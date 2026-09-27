import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchVerdicts, rescanVerdicts, type VerdictList } from "../api";
import MailboxPoll from "../components/MailboxPoll";
import Arrow from "../components/Arrow";
import RiskBadge from "../components/RiskBadge";

const SCORE_TONE: Record<string, string> = {
  legitimate: "score-good",
  suspicious: "score-warn",
  phishing: "score-bad",
};

const PAGE_SIZE = 25;
const LABELS = ["", "phishing", "suspicious", "legitimate"];
// No "redteam": its samples are ingested by the Mailhog poller, so they land as
// source=mailhog. The enum still allows it, but nothing writes it today.
const SOURCES = ["", "paste", "upload", "mailhog"];

export default function History() {
  const [label, setLabel] = useState("");
  const [source, setSource] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<VerdictList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rescanning, setRescanning] = useState(false);
  // Bumping this remounts MailboxPoll, wiping its on-screen results too.
  const [viewKey, setViewKey] = useState(0);

  const load = useCallback(() => {
    setError(null);
    fetchVerdicts({
      limit: PAGE_SIZE,
      offset,
      label: label || undefined,
      source: source || undefined,
    })
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [label, source, offset]);

  useEffect(load, [load]);

  // A poll adds rows, and filters change what page 0 means, so both reset paging.
  const refresh = useCallback(() => {
    setOffset(0);
    load();
  }, [load]);

  // Re-run Claude on only the verdicts currently on screen (this page) and update
  // their scores in place, then reload so the new numbers show.
  async function deepScanPage() {
    if (!data || data.items.length === 0) return;
    setRescanning(true);
    setError(null);
    try {
      await rescanVerdicts(data.items.map((row) => row.verdict_id), true);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRescanning(false);
    }
  }

  // Demo aid: clear what's on screen only. Does NOT delete any verdict from the
  // database or touch Gmail/Mailhog — "refresh" (or a poll) brings the rows back.
  function clearView() {
    setData({ total: 0, limit: PAGE_SIZE, offset: 0, items: [] });
    setError(null);
    setViewKey((key) => key + 1);
  }

  const total = data?.total ?? 0;

  return (
    <>
      <h1>History</h1>
      <p className="subtitle">Everything the detector has scored, newest first.</p>

      <MailboxPoll key={viewKey} onDone={refresh} />

      <div className="panel">
        <div className="controls" style={{ marginTop: 0 }}>
          <label className="check">
            verdict
            <select
              value={label}
              onChange={(event) => {
                setLabel(event.target.value);
                setOffset(0);
              }}
            >
              {LABELS.map((value) => (
                <option key={value} value={value}>
                  {value || "all"}
                </option>
              ))}
            </select>
          </label>

          <label className="check">
            source
            <select
              value={source}
              onChange={(event) => {
                setSource(event.target.value);
                setOffset(0);
              }}
            >
              {SOURCES.map((value) => (
                <option key={value} value={value}>
                  {value || "all"}
                </option>
              ))}
            </select>
          </label>

          <button onClick={load}>refresh</button>
          <button
            onClick={() => void deepScanPage()}
            disabled={rescanning || !data || data.items.length === 0}
            title="Re-run Claude on the emails shown on this page and update their scores"
          >
            {rescanning ? "AI deep scanning…" : "AI deep scan this page"}
          </button>
          <button
            onClick={clearView}
            title="Demo only: clears the list from the screen. Nothing is deleted — click refresh to bring it back."
          >
            clear view
          </button>
          <span className="placeholder mono">
            {total} verdict{total === 1 ? "" : "s"}
          </span>
        </div>
      </div>

      {error && (
        <div className="panel error" role="alert">
          {error}
        </div>
      )}

      <div className="panel">
        {!data ? (
          <p className="note" aria-live="polite">Loading…</p>
        ) : data.items.length === 0 ? (
          <p className="note">
            Nothing matches. Analyze an email, or poll the sandbox inbox above.
          </p>
        ) : (
          <>
            <table className="verdicts">
              <thead>
                <tr>
                  <th scope="col">Risk</th>
                  <th scope="col">Verdict</th>
                  <th scope="col">Subject</th>
                  <th scope="col">From</th>
                  <th scope="col">Source</th>
                  <th scope="col">AI</th>
                  <th scope="col" className="sr-only">Open</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((row) => (
                  <tr key={row.verdict_id}>
                    <td className={`num-cell num ${SCORE_TONE[row.risk_label ?? ""] ?? ""}`}>
                      {row.risk_score ?? "—"}
                    </td>
                    <td style={{ width: 110 }}>
                      <RiskBadge label={row.risk_label ?? "unknown"} />
                    </td>
                    <td>{row.subject || "(no subject)"}</td>
                    <td className="mono placeholder">{row.sender}</td>
                    <td className="mono placeholder" style={{ width: 70 }}>
                      {row.source}
                    </td>
                    <td className="mono placeholder" style={{ width: 80 }}>
                      {row.llm_verdict ?? "—"}
                    </td>
                    <td style={{ width: 60 }}>
                      <Link to={`/verdicts/${row.verdict_id}`}>open</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="controls">
              <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                <Arrow dir="left" />
                Newer
              </button>
              <button
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Older
                <Arrow dir="right" />
              </button>
              <span className="placeholder mono">
                {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
              </span>
            </div>
          </>
        )}
      </div>
    </>
  );
}
