from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20))  # paste | upload | mailhog | redteam
    # Upstream id (e.g. a Mailhog message ID) so repeated polling stays idempotent.
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    raw_headers: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(998), nullable=True)
    sender: Mapped[str | None] = mapped_column(String(320), nullable=True)
    reply_to: Mapped[str | None] = mapped_column(String(320), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    verdicts: Mapped[list["Verdict"]] = relationship(back_populates="email")


class Verdict(Base):
    __tablename__ = "verdicts"

    id: Mapped[int] = mapped_column(primary_key=True)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id"))
    heuristic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    heuristic_findings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    llm_verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    llm_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_risky_spans: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    link_mismatch: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    unfamiliar_link: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    typosquat: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    domain_age_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    risk_components: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    email: Mapped["Email"] = relationship(back_populates="verdicts")
    feedback: Mapped[list["Feedback"]] = relationship(back_populates="verdict")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    verdict_id: Mapped[int] = mapped_column(ForeignKey("verdicts.id"))
    marked_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    verdict: Mapped["Verdict"] = relationship(back_populates="feedback")


class RedteamRun(Base):
    __tablename__ = "redteam_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    attack_type: Mapped[str] = mapped_column(String(30))  # credential_harvest | bec_urgency | brand_impersonation | generic
    target_brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    generated_email_id: Mapped[int] = mapped_column(ForeignKey("emails.id"))
    detector_caught: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    generated_email: Mapped["Email"] = relationship()
