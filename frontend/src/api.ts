// Cross-origin calls to the API are fine: the backend sets allow_origins=["*"].
// docker-compose supplies VITE_API_URL; the fallback covers `npm run dev` on the host.
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type RiskLabel = "legitimate" | "suspicious" | "phishing";
export type EmailSource = "paste" | "upload" | "mailhog" | "redteam";

export interface Signal {
  name: string;
  weight: number;
  triggered: boolean;
  evidence: string | null;
}

export interface RiskComponent {
  subscore: number;
  weight: number;
  contribution: number;
}

export interface RiskySpan {
  text: string;
  reason: string;
}

export interface LlmOut {
  verdict: string;
  confidence: number;
  rationale: string;
  risky_spans: RiskySpan[];
  signals_confirmed: string[];
}

export interface ParsedEmailOut {
  subject: string | null;
  sender: string | null;
  reply_to: string | null;
  received_at: string | null;
  auth_results: string | null;
  has_html: boolean;
  body_text: string | null;
}

export interface AnalyzeResponse {
  email_id: number;
  verdict_id: number;
  email: ParsedEmailOut;
  llm: LlmOut | null;
  heuristic_score: number;
  heuristic_label: string;
  risk_score: number;
  risk_label: RiskLabel;
  risk_components: Record<string, RiskComponent>;
  risk_weight_covered: number;
  risk_unavailable: string[];
  link_mismatch: boolean;
  unfamiliar_link: boolean;
  typosquat: boolean;
  signals: Signal[];
}

export interface DbHealth {
  database: string;
}

export interface VerdictSummary {
  verdict_id: number;
  email_id: number;
  source: string;
  subject: string | null;
  sender: string | null;
  heuristic_score: number | null;
  heuristic_label: string | null;
  risk_score: number | null;
  risk_label: string | null;
  llm_verdict: string | null;
  created_at: string;
}

export interface VerdictList {
  total: number;
  limit: number;
  offset: number;
  items: VerdictSummary[];
}

export interface FeedbackOut {
  id: number;
  verdict_id: number;
  marked_by: string | null;
  is_correct: boolean;
  note: string | null;
  created_at: string;
}

/** Stored shape of a signal: keyed by name, unlike the array /analyze returns. */
export interface StoredFinding {
  triggered: boolean;
  weight: number;
  evidence: string | null;
}

export interface VerdictDetail extends VerdictSummary {
  reply_to: string | null;
  received_at: string | null;
  raw_headers: string | null;
  body_text: string | null;
  body_html: string | null;
  heuristic_findings: Record<string, StoredFinding> | null;
  risk_components: Record<string, RiskComponent> | null;
  domain_age_days: number | null;
  link_mismatch: boolean | null;
  unfamiliar_link: boolean | null;
  typosquat: boolean | null;
  llm_confidence: number | null;
  llm_rationale: string | null;
  llm_risky_spans: RiskySpan[];
  feedback: FeedbackOut[];
}

export interface MailboxMessage {
  external_id: string;
  subject: string | null;
  sender: string | null;
  status: "analyzed" | "already_analyzed" | "unparseable";
  verdict_id: number | null;
  risk_score: number | null;
  risk_label: string | null;
}

export interface MailboxPollResponse {
  fetched: number;
  analyzed: number;
  already_analyzed: number;
  unparseable: number;
  used_llm: boolean;
  messages: MailboxMessage[];
}

/** Every term in the risk formula, so the UI can name the ones that went unmeasured. */
export const RISK_TERMS = [
  "llm_confidence",
  "auth_failure",
  "url_mismatch",
  "domain_age",
  "typosquat",
  "identity_mismatch",
  "urgency_language",
] as const;

export function findingsToSignals(findings: Record<string, StoredFinding> | null): Signal[] {
  return Object.entries(findings ?? {}).map(([name, finding]) => ({
    name,
    weight: finding.weight,
    triggered: finding.triggered,
    evidence: finding.evidence,
  }));
}

/**
 * The stored verdict keeps the components but not the coverage summary, so both are
 * derived from what is present rather than adding fields to the detail response.
 */
export function coverageOf(components: Record<string, RiskComponent> | null) {
  const present = Object.keys(components ?? {});
  const weightCovered = Object.values(components ?? {}).reduce((sum, c) => sum + c.weight, 0);
  return {
    weightCovered: Math.round(weightCovered * 10000) / 10000,
    unavailable: RISK_TERMS.filter((term) => !present.includes(term)),
  };
}

/** FastAPI reports problems in `detail`; surface that instead of a bare status code. */
async function unwrap<T>(response: Response, label: string): Promise<T> {
  if (response.ok) {
    return response.json() as Promise<T>;
  }
  let detail = `${response.status} ${response.statusText}`;
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      detail = body.detail;
    } else if (Array.isArray(body?.detail) && body.detail[0]?.msg) {
      detail = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    }
  } catch {
    // Non-JSON error body; the status line is all we have.
  }
  throw new Error(`${label}: ${detail}`);
}

export async function apiGet<T>(path: string): Promise<T> {
  return unwrap<T>(await fetch(`${API_URL}${path}`), `GET ${path}`);
}

export interface AnalyzeOptions {
  useLlm: boolean;
  domainAgeDays: number | null;
}

export async function analyzeText(
  rawEmail: string,
  options: AnalyzeOptions,
): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      raw_email: rawEmail,
      source: "paste" satisfies EmailSource,
      use_llm: options.useLlm,
      domain_age_days: options.domainAgeDays,
    }),
  });
  return unwrap<AnalyzeResponse>(response, "Analyze");
}

/**
 * Uploaded .eml goes up as raw bytes rather than through a form, which is what the
 * /analyze/eml endpoint expects — reading the file as text first would corrupt any
 * message whose charset is not UTF-8.
 */
export async function analyzeEml(file: File, options: AnalyzeOptions): Promise<AnalyzeResponse> {
  const params = new URLSearchParams({ source: "upload", use_llm: String(options.useLlm) });
  if (options.domainAgeDays !== null) {
    params.set("domain_age_days", String(options.domainAgeDays));
  }
  const response = await fetch(`${API_URL}/analyze/eml?${params}`, {
    method: "POST",
    headers: { "Content-Type": "message/rfc822" },
    body: await file.arrayBuffer(),
  });
  return unwrap<AnalyzeResponse>(response, "Analyze .eml");
}

export interface VerdictQuery {
  limit: number;
  offset: number;
  source?: string;
  label?: string;
}

export async function fetchVerdicts(query: VerdictQuery): Promise<VerdictList> {
  const params = new URLSearchParams({
    limit: String(query.limit),
    offset: String(query.offset),
  });
  if (query.source) params.set("source", query.source);
  if (query.label) params.set("label", query.label);
  return apiGet<VerdictList>(`/verdicts?${params}`);
}

export async function fetchVerdict(verdictId: number | string): Promise<VerdictDetail> {
  return apiGet<VerdictDetail>(`/verdicts/${verdictId}`);
}

export async function pollMailbox(
  source: string,
  useLlm: boolean,
): Promise<MailboxPollResponse> {
  return apiGet<MailboxPollResponse>(`/mailbox/poll?source=${source}&use_llm=${useLlm}`);
}

export async function sendFeedback(
  verdictId: number,
  body: { is_correct: boolean; marked_by?: string | null; note?: string | null },
): Promise<FeedbackOut> {
  const response = await fetch(`${API_URL}/verdicts/${verdictId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return unwrap<FeedbackOut>(response, "Feedback");
}

export interface MailboxSourceInfo {
  available: boolean;
  label: string;
  hint?: string;
}

export async function fetchMailboxSources(): Promise<Record<string, MailboxSourceInfo>> {
  return apiGet<Record<string, MailboxSourceInfo>>("/mailbox/sources");
}
