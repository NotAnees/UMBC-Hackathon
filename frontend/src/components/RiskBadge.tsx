import { bandOf } from "../labels";

export default function RiskBadge({ label, score }: { label: string; score?: number }) {
  const band = bandOf(label);
  return (
    <span className={`badge${band ? ` ${band}` : " unknown"}`}>
      {band ?? "not scored"}
      {score !== undefined && <b className="num">{score}</b>}
    </span>
  );
}
