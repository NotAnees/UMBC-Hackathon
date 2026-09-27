import type { AnalyzeResponse } from "../api";
import RiskBadge from "./RiskBadge";
import RiskComponents from "./RiskComponents";
import SignalTable from "./SignalTable";
import SpanHighlighter from "./SpanHighlighter";

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      <span className="field-value">{value || "—"}</span>
    </div>
  );
}

export default function VerdictCard({ result }: { result: AnalyzeResponse }) {
  const body = result.email.body_text ?? "";
  const spans = result.llm?.risky_spans ?? [];

  return (
    <>
      <RiskComponents
        components={result.risk_components}
        unavailable={result.risk_unavailable}
        weightCovered={result.risk_weight_covered}
        riskScore={result.risk_score}
      />

      {result.llm ? (
        <section className="panel">
          <h2>
            AI deep scan <RiskBadge label={result.llm.verdict} score={result.llm.confidence} />
          </h2>
          <p className="rationale">{result.llm.rationale}</p>
          {result.llm.signals_confirmed.length > 0 && (
            <p className="note">Confirmed: {result.llm.signals_confirmed.join(", ")}</p>
          )}
        </section>
      ) : (
        <section className="panel">
          <h2>AI deep scan</h2>
          <p className="note">
            Did not run — no API key, or the request failed. The score above comes from the
            deterministic checks only.
          </p>
        </section>
      )}

      <SignalTable signals={result.signals} />

      <section className="panel">
        <h2>
          Message body
          {spans.length > 0 && <span className="muted-note">risky phrases highlighted</span>}
        </h2>
        {body ? (
          <SpanHighlighter text={body} spans={spans} />
        ) : (
          <p className="note">No text body was parsed from this message.</p>
        )}
        {result.email.has_html && (
          <p className="note">
            This message had an HTML part. Its links were analysed, but the markup is never
            rendered here.
          </p>
        )}
      </section>

      <section className="panel">
        <h2>Headers</h2>
        <Field label="Subject" value={result.email.subject} />
        <Field label="From" value={result.email.sender} />
        <Field label="Reply-To" value={result.email.reply_to} />
        <Field label="Authentication" value={result.email.auth_results} />
      </section>
    </>
  );
}
