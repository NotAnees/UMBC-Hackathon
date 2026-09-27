const TONE: Record<string, string> = {
  legitimate: "badge green",
  suspicious: "badge amber",
  phishing: "badge red",
};

export default function RiskBadge({ label, score }: { label: string; score?: number }) {
  return (
    <span className={TONE[label] ?? "badge"}>
      {label}
      {score !== undefined && <b>{score}</b>}
    </span>
  );
}
