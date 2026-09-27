import { useCallback, useEffect, useState } from "react";

import { fetchCounts, type BandCounts } from "../api";
import CompositionPie from "./CompositionPie";

const BANDS = [
  { band: "phishing", label: "Phishing", tone: "t-bad" },
  { band: "suspicious", label: "Suspicious", tone: "t-warn" },
  { band: "legitimate", label: "Legitimate", tone: "t-good" },
] as const;

function share(count: number, total: number): string {
  if (total === 0) return "—";
  return `${Math.round((count / total) * 100)}% of scanned`;
}

/**
 * KPI row plus one part-to-whole bar. A count is a headline number, so it is a stat
 * tile rather than a one-bar chart, and the split across bands is part-to-whole, so
 * it is a single stacked bar rather than three gauges.
 */
export default function StatTiles({ reloadKey }: { reloadKey?: number }) {
  const [counts, setCounts] = useState<BandCounts | null>(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(() => {
    fetchCounts()
      .then((next) => {
        setCounts(next);
        setFailed(false);
      })
      .catch(() => setFailed(true));
  }, []);

  useEffect(load, [load, reloadKey]);

  if (failed) {
    return (
      <p className="note" role="alert">
        Could not load inbox totals.
      </p>
    );
  }

  const total = counts?.total ?? 0;
  const segments = BANDS.map((entry) => ({
    ...entry,
    count: counts?.[entry.band] ?? 0,
  }));

  return (
    <>
      <div className="kpi-row">
        <div className="tile">
          <div className="tile-label">Scanned</div>
          <div className="tile-value">{counts ? total : "—"}</div>
          <div className="tile-share">messages analysed</div>
        </div>

        {segments.map((entry) => (
          <div className={`tile ${entry.tone}`} key={entry.band}>
            <div className="tile-label">
              <span className={`key k-${entry.band}`} aria-hidden="true" />
              {entry.label}
            </div>
            <div className="tile-value">{counts ? entry.count : "—"}</div>
            <div className="tile-share">{counts ? share(entry.count, total) : " "}</div>
          </div>
        ))}
      </div>

      {total > 0 && (
        <section className="panel" aria-label="Inbox composition">
          <h2>Inbox composition</h2>
          <CompositionPie segments={segments} total={total} />
        </section>
      )}

    </>
  );
}
