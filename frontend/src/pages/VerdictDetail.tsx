import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  coverageOf,
  fetchVerdict,
  findingsToSignals,
  sendFeedback,
  type VerdictDetail as Detail,
} from "../api";
import RiskBadge from "../components/RiskBadge";
import RiskComponents from "../components/RiskComponents";
import SignalTable from "../components/SignalTable";
import SpanHighlighter from "../components/SpanHighlighter";

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      <span className="field-value mono">{value || "—"}</span>
    </div>
  );
}

export default function VerdictDetail() {
  const { verdictId } = useParams();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    if (!verdictId) return;
    setError(null);
    fetchVerdict(verdictId)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [verdictId]);

  useEffect(load, [load]);

  async function mark(isCorrect: boolean) {
    if (!detail) return;
    setSaving(true);
    try {
      await sendFeedback(detail.verdict_id, {
        is_correct: isCorrect,
        note: note.trim() || null,
      });
      setNote("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  if (error) return <div className="panel error">{error}</div>;
  if (!detail) return <p className="placeholder">Loading…</p>;

  const coverage = coverageOf(detail.risk_components);

  return (
    <>
      <p className="subtitle">
        <Link to="/history">← history</Link>
      </p>

      <div className="panel verdict-head">
        <div>
          <div className="score-row">
            <span className="score">{detail.risk_score ?? "—"}</span>
            <RiskBadge label={detail.risk_label ?? "unknown"} />
          </div>
          <div className="placeholder">
            heuristic view: {detail.heuristic_score ?? "—"} · {detail.heuristic_label ?? "—"}
          </div>
        </div>
        <div className="coverage">
          <div className="mono">scored on {Math.round(coverage.weightCovered * 100)}% of signals</div>
          <div className="placeholder mono">
            verdict #{detail.verdict_id} · {detail.source}
          </div>
          <div className="placeholder mono">{new Date(detail.created_at).toLocaleString()}</div>
        </div>
      </div>

      {detail.risk_components && (
        <RiskComponents
          components={detail.risk_components}
          unavailable={[...coverage.unavailable]}
          weightCovered={coverage.weightCovered}
          riskScore={detail.risk_score ?? 0}
        />
      )}

      <div className="panel">
        <h2>
          AI deep scan
          {detail.llm_verdict && (
            <RiskBadge label={detail.llm_verdict} score={detail.llm_confidence ?? undefined} />
          )}
        </h2>
        {detail.llm_rationale ? (
          <p className="rationale">{detail.llm_rationale}</p>
        ) : (
          <p className="placeholder">Did not run for this message.</p>
        )}
      </div>

      <SignalTable signals={findingsToSignals(detail.heuristic_findings)} />

      <div className="panel">
        <h2>
          Message body
          {detail.llm_risky_spans.length > 0 && (
            <span className="placeholder">risky spans highlighted</span>
          )}
        </h2>
        {detail.body_text ? (
          <SpanHighlighter text={detail.body_text} spans={detail.llm_risky_spans} />
        ) : (
          <p className="placeholder">No text body stored for this message.</p>
        )}
      </div>

      <div className="panel">
        <h2>Headers</h2>
        <Field label="Subject" value={detail.subject} />
        <Field label="From" value={detail.sender} />
        <Field label="Reply-To" value={detail.reply_to} />
        <Field label="Domain age" value={detail.domain_age_days?.toString() ?? null} />
      </div>

      <div className="panel">
        <h2>
          Was this right? <span className="placeholder">real mail has no ground truth</span>
        </h2>
        <div className="controls" style={{ marginTop: 0 }}>
          <button className="primary" disabled={saving} onClick={() => void mark(true)}>
            Correct
          </button>
          <button disabled={saving} onClick={() => void mark(false)}>
            Wrong
          </button>
          <input
            className="note"
            value={note}
            placeholder="optional note"
            onChange={(event) => setNote(event.target.value)}
          />
        </div>
        {detail.feedback.length > 0 && (
          <ul className="span-reasons">
            {detail.feedback.map((entry) => (
              <li key={entry.id}>
                {entry.is_correct ? "correct" : "wrong"}
                {entry.note ? ` — ${entry.note}` : ""}{" "}
                <span className="placeholder">{new Date(entry.created_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
