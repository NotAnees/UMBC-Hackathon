interface Segment {
  band: string;
  label: string;
  count: number;
}

const RADIUS = 62;
const STROKE = 30;
const CIRC = 2 * Math.PI * RADIUS;
const GAP = 2; // surface gap between fills, per the viz mark spec

/**
 * Part-to-whole at a glance. A pie is only safe here because there are three
 * segments and every value is directly labelled — angle comparison is the weak
 * channel, so the numbers do the reading and the slices do the glance.
 */
export default function CompositionPie({
  segments,
  total,
}: {
  segments: Segment[];
  total: number;
}) {
  const present = segments.filter((s) => s.count > 0);
  let offset = 0;

  return (
    <div className="pie-wrap">
      <svg
        className="pie"
        viewBox="0 0 160 160"
        role="img"
        aria-label={`Inbox composition of ${total} scanned messages: ${segments
          .map((s) => `${s.label} ${s.count}`)
          .join(", ")}`}
      >
        <circle className="pie-track" cx="80" cy="80" r={RADIUS} strokeWidth={STROKE} />
        {present.map((segment) => {
          const length = (segment.count / total) * CIRC;
          const dash = Math.max(length - GAP, 1);
          const circle = (
            <circle
              key={segment.band}
              className={`pie-seg s-${segment.band}`}
              cx="80"
              cy="80"
              r={RADIUS}
              strokeWidth={STROKE}
              strokeDasharray={`${dash} ${CIRC - dash}`}
              strokeDashoffset={-offset}
            >
              <title>{`${segment.label}: ${segment.count} of ${total}`}</title>
            </circle>
          );
          offset += length;
          return circle;
        })}
        <text className="pie-total" x="80" y="76">
          {total}
        </text>
        <text className="pie-total-label" x="80" y="94">
          scanned
        </text>
      </svg>

      {/* Direct labels: the reader never has to judge an angle. */}
      <ul className="pie-legend">
        {segments.map((segment) => (
          <li key={segment.band}>
            <span className={`key k-${segment.band}`} aria-hidden="true" />
            <span className="pie-legend-label">{segment.label}</span>
            <strong className="pie-legend-value">{segment.count}</strong>
            <span className="pie-legend-share">
              {total > 0 ? `${Math.round((segment.count / total) * 100)}%` : "—"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
