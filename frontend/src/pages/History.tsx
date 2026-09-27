import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchVerdicts, type VerdictList } from "../api";
import MailboxPoll from "../components/MailboxPoll";
import RiskBadge from "../components/RiskBadge";

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

  const total = data?.total ?? 0;

  return (
    <>
      <h1>History</h1>
      <p className="subtitle">Everything the detector has scored, newest first.</p>

      <MailboxPoll onDone={refresh} />

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
          <span className="placeholder mono">
            {total} verdict{total === 1 ? "" : "s"}
          </span>
        </div>
      </div>

      {error && <div className="panel error">{error}</div>}

      <div className="panel">
        {!data ? (
          <p className="placeholder">Loading…</p>
        ) : data.items.length === 0 ? (
          <p className="placeholder">
            Nothing matches. Analyze an email, or poll the sandbox inbox above.
          </p>
        ) : (
          <>
            <table className="verdicts">
              <thead>
                <tr>
                  <th>risk</th>
                  <th>verdict</th>
                  <th>subject</th>
                  <th>from</th>
                  <th>source</th>
                  <th>llm</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.items.map((row) => (
                  <tr key={row.verdict_id}>
                    <td className="num-cell mono strong">{row.risk_score ?? "—"}</td>
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
                ← newer
              </button>
              <button
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                older →
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
