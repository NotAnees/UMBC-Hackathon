from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EmailSource = Literal["paste", "upload", "mailhog", "redteam", "gmail"]
MailboxSource = Literal["mailhog", "gmail"]


class AnalyzeRequest(BaseModel):
    raw_email: str = Field(min_length=1, description="Raw .eml text, or just a pasted body")
    source: EmailSource = "paste"
    use_llm: bool = Field(
        default=True,
        description="Run the Claude AI deep scan. False scores on deterministic signals only.",
    )
    domain_age_days: int | None = Field(
        default=None,
        ge=0,
        description="Age of the sender domain. Omitted means unmeasured, which drops "
        "the domain_age term from the risk score rather than scoring it as safe.",
    )


class SignalOut(BaseModel):
    name: str
    weight: int
    triggered: bool
    evidence: str | None = None


class RiskComponentOut(BaseModel):
    subscore: float
    weight: float
    contribution: float


class ParsedEmailOut(BaseModel):
    subject: str | None = None
    sender: str | None = None
    reply_to: str | None = None
    received_at: datetime | None = None
    auth_results: str | None = None
    has_html: bool
    # The parsed body, which is the exact string the semantic pass quotes its risky
    # spans from — highlighting them against the raw paste would not line up.
    body_text: str | None = None


class RiskySpanOut(BaseModel):
    text: str
    reason: str


class LlmOut(BaseModel):
    verdict: str
    confidence: int
    rationale: str
    risky_spans: list[RiskySpanOut] = []
    signals_confirmed: list[str] = []


class AnalyzeResponse(BaseModel):
    email_id: int
    verdict_id: int
    email: ParsedEmailOut
    # None when the semantic pass did not run (no API key, or the call failed) —
    # the risk score renormalizes rather than treating the message as safe.
    llm: LlmOut | None = None

    heuristic_score: int
    heuristic_label: str

    risk_score: float
    risk_label: str
    risk_components: dict[str, RiskComponentOut]
    risk_weight_covered: float
    risk_unavailable: list[str]

    link_mismatch: bool
    unfamiliar_link: bool
    typosquat: bool

    signals: list[SignalOut]


class VerdictSummary(BaseModel):
    """Row shape for the history list — no findings blobs, so the list stays cheap."""

    verdict_id: int
    email_id: int
    source: str
    subject: str | None = None
    sender: str | None = None
    heuristic_score: float | None = None
    heuristic_label: str | None = None
    risk_score: float | None = None
    risk_label: str | None = None
    llm_verdict: str | None = None
    created_at: datetime


class VerdictList(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[VerdictSummary]


class ExplainResponse(BaseModel):
    verdict_id: int
    # On-demand plain-English explanation of the score; null if the LLM couldn't run.
    explanation: str | None = None
    available: bool


class FeedbackOut(BaseModel):
    id: int
    verdict_id: int
    marked_by: str | None = None
    is_correct: bool
    note: str | None = None
    created_at: datetime


class VerdictDetail(VerdictSummary):
    reply_to: str | None = None
    received_at: datetime | None = None
    raw_headers: str | None = None
    body_text: str | None = None
    body_html: str | None = None

    heuristic_findings: dict | None = None
    risk_components: dict | None = None
    domain_age_days: int | None = None
    link_mismatch: bool | None = None
    unfamiliar_link: bool | None = None
    typosquat: bool | None = None

    llm_confidence: float | None = None
    llm_rationale: str | None = None
    llm_risky_spans: list[RiskySpanOut] = []

    feedback: list[FeedbackOut] = []


class FeedbackRequest(BaseModel):
    is_correct: bool = Field(description="Was the stored verdict correct?")
    marked_by: str | None = Field(default=None, max_length=120)
    note: str | None = None


class MailboxMessage(BaseModel):
    external_id: str
    subject: str | None = None
    sender: str | None = None
    status: Literal["analyzed", "already_analyzed", "unparseable"]
    verdict_id: int | None = None
    risk_score: float | None = None
    risk_label: str | None = None


class MailboxPollResponse(BaseModel):
    source: MailboxSource
    fetched: int
    analyzed: int
    already_analyzed: int
    unparseable: int
    used_llm: bool
    messages: list[MailboxMessage]
