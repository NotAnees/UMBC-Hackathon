import type { AnalyzeResponse } from "../api";
import RiskBadge from "./RiskBadge";
import RiskComponents from "./RiskComponents";
import SignalTable from "./SignalTable";
import SpanHighlighter from "./SpanHighlighter";

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      <span className="field-value mono">{value || "—"}</span>
    </div>
  );
}

export default function VerdictCard({ result }: { result: AnalyzeResponse }) {
  const body = result.email.body_text ?? "";
  const spans = result.llm?.risky_spans ?? [];

  return (
    <>
      <div className="panel verdict-head">
        <div>
          <div className="score-row">
            <span className="score">{result.risk_score}</span>
            <RiskBadge label={result.risk_label} />
          </div>
          <div className="placeholder">
            heuristic view: {result.heuristic_score} · {result.heuristic_label}
          </div>
        </div>
        <div className="coverage">
          <div className="mono">scored on {Math.round(result.risk_weight_covered * 100)}% of signals</div>
          <div className="placeholder mono">verdict #{result.verdict_id}</div>
        </div>
      </div>

      <RiskComponents
        components={result.risk_components}
        unavailable={result.risk_unavailable}
        weightCovered={result.risk_weight_covered}
        riskScore={result.risk_score}
      />

      {result.llm ? (
        <div className="panel">
          <h2>
            AI deep scan <RiskBadge label={result.llm.verdict} score={result.llm.confidence} />
          </h2>
          <p className="rationale">{result.llm.rationale}</p>
          {result.llm.signals_confirmed.length > 0 && (
            <div className="placeholder mono">
              confirmed: {result.llm.signals_confirmed.join(", ")}
            </div>
          )}
        </div>
      ) : (
        <div className="panel">
          <h2>AI deep scan</h2>
          <p className="placeholder">
            Did not run — no API key, or the request failed. The score above comes from the
            deterministic signals only.
          </p>
        </div>
      )}

      <SignalTable signals={result.signals} />

      <div className="panel">
        <h2>
          Message body
          {spans.length > 0 && <span className="placeholder">risky spans highlighted</span>}
        </h2>
        {body ? (
          <SpanHighlighter text={body} spans={spans} />
        ) : (
          <p className="placeholder">No text body was parsed from this message.</p>
        )}
        {result.email.has_html && (
          <p className="placeholder">
            This message had an HTML part. Its links were analysed, but the markup is never
            rendered here.
          </p>
        )}
      </div>

      <div className="panel">
        <h2>Headers</h2>
        <Field label="Subject" value={result.email.subject} />
        <Field label="From" value={result.email.sender} />
        <Field label="Reply-To" value={result.email.reply_to} />
        <Field label="Auth" value={result.email.auth_results} />
      </div>
    </>
  );
}
