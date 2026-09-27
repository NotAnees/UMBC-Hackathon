import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  coverageOf,
  fetchVerdict,
  findingsToSignals,
  sendFeedback,
  type VerdictDetail as Detail,
} from "../api";
import Arrow from "../components/Arrow";
import RiskBadge from "../components/RiskBadge";
import VerdictBanner from "../components/VerdictBanner";
import RiskComponents from "../components/RiskComponents";
import SignalTable from "../components/SignalTable";
import SpanHighlighter from "../components/SpanHighlighter";

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      <span className="field-value">{value || "—"}</span>
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

  if (error)
    return (
      <div className="panel error" role="alert">
        {error}
      </div>
    );
  if (!detail)
    return (
      <p className="note" aria-live="polite">
        Loading…
      </p>
    );

  const coverage = coverageOf(detail.risk_components);

  return (
    <>
      <p className="backlink">
        <Link to="/history">
          <Arrow dir="left" />
          Back to history
        </Link>
      </p>

      <h1>{detail.subject || "(no subject)"}</h1>
      <p className="subtitle">
        From {detail.sender || "unknown sender"} · arrived via {detail.source} ·{" "}
        {new Date(detail.created_at).toLocaleString()}
      </p>

      <VerdictBanner
        label={detail.risk_label}
        score={detail.risk_score}
        heuristicScore={detail.heuristic_score}
        heuristicLabel={detail.heuristic_label}
        weightCovered={coverage.weightCovered}
        meta={`verdict #${detail.verdict_id}`}
      />

      {detail.risk_components && (
        <RiskComponents
          components={detail.risk_components}
          unavailable={[...coverage.unavailable]}
          weightCovered={coverage.weightCovered}
          riskScore={detail.risk_score ?? 0}
        />
      )}

      <section className="panel">
        <h2>
          AI deep scan
          {detail.llm_verdict && (
            <RiskBadge label={detail.llm_verdict} score={detail.llm_confidence ?? undefined} />
          )}
        </h2>
        {detail.llm_rationale ? (
          <p className="rationale">{detail.llm_rationale}</p>
        ) : (
          <p className="note">Did not run for this message.</p>
        )}
      </section>

      <SignalTable signals={findingsToSignals(detail.heuristic_findings)} />

      <section className="panel">
        <h2>
          Message body
          {detail.llm_risky_spans.length > 0 && (
            <span className="muted-note">risky phrases highlighted</span>
          )}
        </h2>
        {detail.body_text ? (
          <SpanHighlighter text={detail.body_text} spans={detail.llm_risky_spans} />
        ) : (
          <p className="note">No text body stored for this message.</p>
        )}
      </section>

      <section className="panel">
        <h2>Headers</h2>
        <Field label="Subject" value={detail.subject} />
        <Field label="From" value={detail.sender} />
        <Field label="Reply-To" value={detail.reply_to} />
        <Field
          label="Domain age"
          value={detail.domain_age_days === null ? "not measured" : `${detail.domain_age_days} days`}
        />
      </section>

      <section className="panel">
        <h2>
          Was this right? <span className="muted-note">real mail has no ground truth</span>
        </h2>
        <div className="controls" style={{ marginTop: 0 }}>
          <button className="primary" disabled={saving} onClick={() => void mark(true)}>
            Correct
          </button>
          <button disabled={saving} onClick={() => void mark(false)}>
            Wrong
          </button>
          <input
            className="note-input"
            value={note}
            placeholder="Optional note"
            aria-label="Optional note about this verdict"
            onChange={(event) => setNote(event.target.value)}
          />
        </div>
        {detail.feedback.length > 0 && (
          <ul className="span-reasons">
            {detail.feedback.map((entry) => (
              <li key={entry.id}>
                {entry.is_correct ? "correct" : "wrong"}
                {entry.note ? ` — ${entry.note}` : ""}{" "}
                <span className="muted-note">{new Date(entry.created_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
