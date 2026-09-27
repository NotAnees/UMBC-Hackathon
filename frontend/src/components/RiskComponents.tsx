import type { RiskComponent } from "../api";

const LABELS: Record<string, string> = {
  llm_confidence: "AI deep scan",
  auth_failure: "SPF / DKIM / DMARC",
  url_mismatch: "link target mismatch",
  domain_age: "domain age",
  typosquat: "lookalike domain",
  identity_mismatch: "From vs Reply-To",
  urgency_language: "urgency language",
};

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
  const rows = Object.entries(components).sort(
    (a, b) => b[1].contribution - a[1].contribution,
  );

  return (
    <div className="panel">
      <h2>
        Why this score <span className="placeholder">{riskScore} = sum of contributions</span>
      </h2>

      <table className="components">
        <thead>
          <tr>
            <th>component</th>
            <th>subscore</th>
            <th>weight</th>
            <th>contributes</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map(([name, component]) => (
            <tr key={name}>
              <td>
                {LABELS[name] ?? name}
                <div className="placeholder mono">{name}</div>
              </td>
              <td className="mono num-cell">{component.subscore}</td>
              <td className="mono num-cell">{component.weight}</td>
              <td className="mono num-cell strong">{component.contribution}</td>
              <td className="bar-cell">
                <div className="bar" style={{ width: `${Math.min(component.contribution, 100)}%` }} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {unavailable.length > 0 && (
        <p className="placeholder">
          {unavailable.map((name) => LABELS[name] ?? name).join(", ")} could not be measured, so{" "}
          {Math.round(weightCovered * 100)}% of the formula ran and the remaining weights were
          rebalanced. An unmeasured component is not scored as safe.
        </p>
      )}
    </div>
  );
}
