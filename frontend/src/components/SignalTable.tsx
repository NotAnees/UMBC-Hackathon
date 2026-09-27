import type { Signal } from "../api";

export default function SignalTable({ signals }: { signals: Signal[] }) {
  const triggered = signals.filter((s) => s.triggered).length;

  return (
    <div className="panel">
      <h2>
        Signals{" "}
        <span className="placeholder">
          ({triggered} of {signals.length} triggered)
        </span>
      </h2>
      <table className="signals">
        <tbody>
          {/* Triggered first: the reader wants what fired, not the full checklist. */}
          {[...signals]
            .sort((a, b) => Number(b.triggered) - Number(a.triggered) || b.weight - a.weight)
            .map((signal) => (
              <tr key={signal.name} className={signal.triggered ? "on" : "off"}>
                <td className="sig-state">{signal.triggered ? "●" : "○"}</td>
                <td className="sig-name mono">{signal.name}</td>
                <td className="sig-weight mono">{signal.weight}</td>
                <td className="sig-evidence">{signal.evidence || ""}</td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}
