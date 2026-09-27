import { BANDS, bandOf, bandForScore } from "../labels";

/**
 * The verdict, as the loudest thing on screen.
 *
 * Inherits the band treatment from the incumbent dashboard
 * (backend/app/static/index.html `.b-legitimate/.b-suspicious/.b-phishing`) so the two
 * UIs read as one product — the flooded tint and the colored score, but not its 10px
 * labels, which sit under the type floor this app keeps.
 */
export default function VerdictBanner({
  label,
  score,
  heuristicScore,
  heuristicLabel,
  weightCovered,
  meta,
}: {
  label: string | null;
  score: number | null;
  heuristicScore: number | null;
  heuristicLabel: string | null;
  weightCovered: number;
  meta?: string;
}) {
  const band = bandOf(label);
  const shown = score ?? 0;

  // A floor in the scorer can raise the label above the band its own number sits in.
  // Unexplained, that reads as a bug — a red "Phishing" beside 41, next to a legend
  // saying phishing is 67-100. Named, it is the clearest evidence on the page that
  // the AI pass is load-bearing.
  const scoreBand = score !== null ? bandForScore(score) : null;
  const raised = band !== null && scoreBand !== null && band !== scoreBand;

  return (
    <section className={`panel banner${band ? ` b-${band}` : ""}`} aria-label="Verdict">
      <div className="banner-verdict">
        <strong className="banner-score">{shown}</strong>
        <div>
          <div className="banner-label">{label ?? "not scored"}</div>
          <div className="banner-sub">
            out of 100 · {Math.round(weightCovered * 100)}% of signals measured
          </div>
        </div>
      </div>

      <div className="banner-side">
        <ul className="legend">
          {BANDS.map((entry) => (
            <li key={entry.band} className={entry.band === band ? "on" : undefined}>
              <span className={`legend-key k-${entry.band}`} aria-hidden="true" />
              {entry.band}
              <span className="legend-range">
                {entry.from}–{entry.to}
              </span>
            </li>
          ))}
        </ul>
        <p className="banner-meta">
          Deterministic signals alone: {heuristicScore ?? "—"} · {heuristicLabel ?? "—"}
          {meta ? ` · ${meta}` : ""}
        </p>
      </div>

      {raised && (
        <p className="banner-override">
          <strong>Raised to {label} by the AI deep scan.</strong> The weighted score is {shown},
          which on its own is {scoreBand}. A confident reading of intent stands even when the
          structural signals are quiet — this message had little for the other factors to measure,
          which is what a business-email-compromise attempt looks like: no bad links, no failed
          authentication, just the request itself.
        </p>
      )}
    </section>
  );
}
