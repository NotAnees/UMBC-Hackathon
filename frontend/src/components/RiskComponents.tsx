import type { CSSProperties } from "react";

import type { RiskComponent } from "../api";
import { TERM_LABELS } from "../labels";

// The backend stores each factor's designed weight and a contribution computed as
// weight * subscore / weight_covered. So whenever coverage is partial the two do not
// reproduce on screen — 40 x 0.05 reads as 2 next to an "adds 5". The effective
// weight is what actually multiplied the level, and it is what the reader needs.
function effectiveWeight(weight: number, weightCovered: number): number {
  return weightCovered > 0 ? weight / weightCovered : 0;
}

export default function RiskComponents({
  components,
  unavailable,
  weightCovered,
  riskScore,
}: {
  components: Record<string, RiskComponent>;
  unavailable: string[];
  weightCovered: number;
  riskScore: number;
}) {
  // Highest contributor first — that is the answer to "why this score".
  const rows = Object.entries(components).sort((a, b) => b[1].contribution - a[1].contribution);

  const partial = weightCovered > 0 && weightCovered < 1;
  const inflation = weightCovered > 0 ? 1 / weightCovered : 0;
  const aiOff = unavailable.includes("llm_confidence");
  const [topName, topComponent] = rows[0] ?? [];

  return (
    <section className="panel">
      <h2>
        Why this score
        <span className="muted-note">contributions add up to {riskScore}</span>
      </h2>

      <table className="components">
        <thead>
          <tr>
            <th scope="col">Factor</th>
            <th scope="col" className="num-cell">
              Level
            </th>
            <th scope="col" className="num-cell">
              {partial ? "Designed" : "Weight"}
            </th>
            {partial && (
              <th scope="col" className="num-cell">
                Rebalanced
              </th>
            )}
            <th scope="col" className="num-cell">
              Adds
            </th>
            <th scope="col" className="sr-only">
              Relative size
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([name, component], index) => (
            <tr key={name}>
              <td>{TERM_LABELS[name] ?? name}</td>
              <td className="num-cell num">{component.subscore}</td>
              <td className={`num-cell num${partial ? " superseded" : ""}`}>{component.weight}</td>
              {partial && (
                <td className="num-cell num">
                  {effectiveWeight(component.weight, weightCovered).toFixed(3)}
                </td>
              )}
              <td className="num-cell num strong">{component.contribution}</td>
              <td className="bar-cell">
                <div
                  className="bar"
                  style={
                    {
                      width: `${Math.min(component.contribution, 100)}%`,
                      "--row": index,
                    } as CSSProperties
                  }
                  role="img"
                  aria-label={`${component.contribution} of ${riskScore} points`}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {partial && (
        <p className="note">
          Not measured: {unavailable.map((name) => TERM_LABELS[name] ?? name).join(", ")}. Only{" "}
          {Math.round(weightCovered * 100)}% of the formula ran. <strong>Designed</strong> is each
          factor's intended share of the full formula; <strong>rebalanced</strong> is what it
          actually carried here, after the unmeasured weight was spread across the factors that
          did run — {inflation.toFixed(2)}× each. That is why Level × Rebalanced reproduces Adds
          and Level × Designed does not. An unmeasured factor is never treated as safe.
        </p>
      )}

      {aiOff && (
        <p className="note note-strong">
          <strong>AI deep scan is off, and it is the largest factor in the formula at 0.30.</strong>{" "}
          With it unmeasured, every remaining factor is inflated to {inflation.toFixed(2)}× its
          designed weight
          {topName && topComponent
            ? ` — ${(TERM_LABELS[topName] ?? topName).toLowerCase()} is designed to carry ${
                topComponent.weight
              } but decided this score at ${effectiveWeight(
                topComponent.weight,
                weightCovered,
              ).toFixed(3)}`
            : ""}
          . It is also the only factor that reads <em>intent</em> rather than structure: a message
          with no links, no headers and no lookalike domain gives the other six factors nothing to
          measure, so it scores low however hostile it reads. Re-run this message with AI deep scan
          enabled to see the difference.
        </p>
      )}
    </section>
  );
}
