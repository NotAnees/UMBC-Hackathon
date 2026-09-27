import type { RiskySpan } from "../api";

interface Located {
  start: number;
  end: number;
  reason: string;
}

/**
 * Where each quoted span sits in the body. Spans the model paraphrased instead of
 * quoting are reported back rather than approximated — guessing a position would
 * highlight text the model never actually flagged.
 */
export function locateSpans(text: string, spans: RiskySpan[]): { found: Located[]; missing: RiskySpan[] } {
  const haystack = text.toLowerCase();
  const found: Located[] = [];
  const missing: RiskySpan[] = [];

  for (const span of spans) {
    const needle = span.text.trim().toLowerCase();
    const start = needle ? haystack.indexOf(needle) : -1;
    if (start === -1) {
      missing.push(span);
      continue;
    }
    found.push({ start, end: start + needle.length, reason: span.reason });
  }

  // Overlaps would produce nested marks, so keep the earliest (longest on ties).
  found.sort((a, b) => a.start - b.start || b.end - a.end);
  const kept: Located[] = [];
  for (const candidate of found) {
    if (kept.length === 0 || candidate.start >= kept[kept.length - 1].end) {
      kept.push(candidate);
    }
  }
  return { found: kept, missing };
}

export default function SpanHighlighter({ text, spans }: { text: string; spans: RiskySpan[] }) {
  const { found, missing } = locateSpans(text, spans);

  const pieces: React.ReactNode[] = [];
  let cursor = 0;
  found.forEach((span, index) => {
    if (span.start > cursor) {
      pieces.push(text.slice(cursor, span.start));
    }
    pieces.push(
      <mark key={index} title={span.reason}>
        {text.slice(span.start, span.end)}
      </mark>,
    );
    cursor = span.end;
  });
  if (cursor < text.length) {
    pieces.push(text.slice(cursor));
  }

  return (
    <>
      <pre className="body-text">{pieces}</pre>
      {found.length > 0 && (
        <ul className="span-reasons">
          {found.map((span, index) => (
            <li key={index}>
              <code>{text.slice(span.start, span.end)}</code> — {span.reason}
            </li>
          ))}
        </ul>
      )}
      {missing.length > 0 && (
        <p className="placeholder">
          {missing.length} span{missing.length > 1 ? "s" : ""} could not be located verbatim in the
          body and {missing.length > 1 ? "are" : "is"} not highlighted.
        </p>
      )}
    </>
  );
}
