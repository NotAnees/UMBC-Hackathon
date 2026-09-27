import type { Signal } from "../api";
import { SIGNAL_HINTS, labelFor } from "../labels";

export default function SignalTable({ signals }: { signals: Signal[] }) {
  const triggered = signals.filter((s) => s.triggered).length;

  return (
    <section className="panel">
      <h2>
        Checks
        <span className="muted-note">
          {triggered} of {signals.length} fired
        </span>
      </h2>

      <table className="signals">
        <caption className="sr-only">
          Detection checks, those that fired first. Weight is the points each contributes to the
          deterministic score out of 100.
        </caption>
        <thead>
          <tr>
            <th scope="col" className="sr-only">
              Result
            </th>
            <th scope="col">Check</th>
            <th scope="col" className="col-weight">
              Weight
            </th>
            <th scope="col">What it found</th>
          </tr>
        </thead>
        <tbody>
          {/* Fired first: the reader wants what happened, not the whole checklist. */}
          {[...signals]
            .sort((a, b) => Number(b.triggered) - Number(a.triggered) || b.weight - a.weight)
            .map((signal) => (
              <tr key={signal.name} className={signal.triggered ? "on" : "off"}>
                <td>
                  <span className="dot-state" aria-hidden="true" />
                  <span className="sr-only">{signal.triggered ? "Fired" : "Did not fire"}</span>
                </td>
                <td>
                  <span title={SIGNAL_HINTS[signal.name] ?? undefined}>
                    {labelFor(signal.name)}
                  </span>
                </td>
                <td className="col-weight num">{signal.weight}</td>
                <td className="sig-evidence">{signal.evidence || ""}</td>
              </tr>
            ))}
        </tbody>
      </table>
    </section>
  );
}
