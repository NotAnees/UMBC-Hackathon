from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EmailSource = Literal["paste", "upload", "mailhog", "redteam"]


class AnalyzeRequest(BaseModel):
    raw_email: str = Field(min_length=1, description="Raw .eml text, or just a pasted body")
    source: EmailSource = "paste"
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


class AnalyzeResponse(BaseModel):
    email_id: int
    verdict_id: int
    email: ParsedEmailOut

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
