import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  fetchMailboxSources,
  pollMailbox,
  type MailboxPollResponse,
  type MailboxSourceInfo,
} from "../api";
import RiskBadge from "./RiskBadge";

export default function MailboxPoll({ onDone }: { onDone: () => void }) {
  const [source, setSource] = useState("mailhog");
  const [sources, setSources] = useState<Record<string, MailboxSourceInfo>>({});
  const [useLlm, setUseLlm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MailboxPollResponse | null>(null);

  useEffect(() => {
    fetchMailboxSources().then(setSources).catch(() => setSources({}));
  }, []);

  async function poll() {
    setBusy(true);
    setError(null);
    try {
      setResult(await pollMailbox(source, useLlm));
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const fresh = result?.messages.filter((m) => m.status === "analyzed") ?? [];

  return (
    <div className="panel">
      <h2>
        Sandbox inbox <span className="placeholder">pull delivered mail and score it</span>
      </h2>

      <div className="controls" style={{ marginTop: 0 }}>
        <button className="primary" onClick={() => void poll()} disabled={busy}>
          {busy ? "Polling…" : "Poll inbox"}
        </button>
        <label className="check">
          source
          <select value={source} onChange={(event) => setSource(event.target.value)}>
            {Object.entries(sources).map(([key, info]) => (
              <option key={key} value={key} disabled={!info.available}>
                {info.label}
                {info.available ? "" : " — not set up"}
              </option>
            ))}
          </select>
        </label>

        <label className="check">
          <input
            type="checkbox"
            checked={useLlm}
            onChange={(event) => setUseLlm(event.target.checked)}
          />
          AI deep scan
        </label>
        <span className="placeholder">
          off by default — scans the whole batch, one Claude call per email
        </span>
      </div>

      {error && <p className="error-text">{error}</p>}

      {result && (
        <>
          <p className="mono" style={{ marginBottom: 6 }}>
            fetched {result.fetched} · newly analyzed {result.analyzed} · already seen{" "}
            {result.already_analyzed}
            {result.unparseable > 0 && ` · unparseable ${result.unparseable}`}
          </p>
          {fresh.length === 0 ? (
            <p className="placeholder">
              {source === "gmail"
                ? "No unseen mail in the inbox."
                : "Nothing new. Generate a batch from the red-team console, then poll again."}
            </p>
          ) : (
            <table className="verdicts">
              <tbody>
                {fresh.map((message) => (
                  <tr key={message.external_id}>
                    <td className="num-cell mono">{message.risk_score}</td>
                    <td style={{ width: 110 }}>
                      <RiskBadge label={message.risk_label ?? "unknown"} />
                    </td>
                    <td>{message.subject || "(no subject)"}</td>
                    <td className="mono placeholder">{message.sender}</td>
                    <td style={{ width: 60 }}>
                      {message.verdict_id && (
                        <Link to={`/verdicts/${message.verdict_id}`}>open</Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}
