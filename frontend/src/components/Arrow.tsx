export default function Arrow({ dir }: { dir: "left" | "right" }) {
  return (
    <svg
      viewBox="0 0 16 16"
      className="arrow"
      aria-hidden="true"
      style={dir === "left" ? { transform: "scaleX(-1)" } : undefined}
    >
      <path d="M2.5 8h11" />
      <path d="M9 3.5L13.5 8 9 12.5" />
    </svg>
  );
}
