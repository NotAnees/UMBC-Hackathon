/** Internal names never reach the screen: one map, used by every table. */
export const TERM_LABELS: Record<string, string> = {
  llm_confidence: "AI deep scan",
  auth_failure: "SPF / DKIM / DMARC",
  url_mismatch: "Link target mismatch",
  domain_age: "Domain age",
  typosquat: "Lookalike domain",
  identity_mismatch: "From vs Reply-To",
  urgency_language: "Urgency language",
};

export const SIGNAL_LABELS: Record<string, string> = {
  spf_fail: "SPF failed",
  dkim_fail: "DKIM failed",
  dmarc_fail: "DMARC failed",
  sender_reply_to_mismatch: "Replies go elsewhere",
  link_mismatch: "Link target mismatch",
  typosquat: "Lookalike domain",
  unfamiliar_link: "Unfamiliar link domain",
  urgency_language: "Urgency language",
};

/** Plain-English "what does this check actually look at", for the help column. */
export const SIGNAL_HINTS: Record<string, string> = {
  spf_fail: "The sending server is not authorised to send for this domain.",
  dkim_fail: "The message signature does not verify, so the content may be altered.",
  dmarc_fail: "The domain's own anti-spoofing policy rejected this message.",
  sender_reply_to_mismatch:
    "A reply would go to a different domain than the one the mail claims to be from.",
  link_mismatch: "A link's visible text names one destination while it points at another.",
  typosquat: "A domain imitates a known brand without being it.",
  unfamiliar_link: "The message links to a domain unrelated to the sender.",
  urgency_language: "Pressure phrasing that pushes the reader to act without checking.",
};

export function labelFor(name: string): string {
  return SIGNAL_LABELS[name] ?? TERM_LABELS[name] ?? name;
}

export type Band = "legitimate" | "suspicious" | "phishing";

/** Mirrors scorer.py: LEGITIMATE_MAX 33, SUSPICIOUS_MAX 66. */
export const BANDS: { band: Band; from: number; to: number }[] = [
  { band: "legitimate", from: 0, to: 33 },
  { band: "suspicious", from: 34, to: 66 },
  { band: "phishing", from: 67, to: 100 },
];

export function bandOf(label: string | null | undefined): Band | null {
  return label === "legitimate" || label === "suspicious" || label === "phishing" ? label : null;
}

/**
 * The band the number alone would land in. Mirrors `label_for` in scorer.py, which
 * compares with <=, so 33.0 is legitimate and 33.5 is suspicious.
 *
 * When this disagrees with the stored label, a floor in the scorer raised the verdict
 * above its arithmetic — the AI read intent the structural signals could not measure.
 */
export function bandForScore(score: number): Band {
  return BANDS.find((entry) => score <= entry.to)?.band ?? "phishing";
}
