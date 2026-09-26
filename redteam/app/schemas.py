"""Request/response models for the red-team service."""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AttackType(str, Enum):
    """Supported synthetic-phishing tactics used to stress-test our own detector."""

    credential_harvest = "credential_harvest"
    bec_urgency = "bec_urgency"
    brand_impersonation = "brand_impersonation"
    generic = "generic"


class Difficulty(str, Enum):
    """Difficulty *for the detector*: easy = loud/obvious, hard = stealthy/header-clean."""

    easy = "easy"
    medium = "medium"
    hard = "hard"


class BenignCategory(str, Enum):
    """Legitimate-but-phishy email types used to test the detector's false-positive rate."""

    marketing_promo = "marketing_promo"
    account_notification = "account_notification"
    password_reset_requested = "password_reset_requested"
    shipping_update = "shipping_update"


class GenerateRequest(BaseModel):
    attack_type: AttackType = AttackType.credential_harvest
    difficulty: Difficulty = Difficulty.easy
    # A generic brand/role for realism (e.g. "IT Helpdesk"). Never a real person or org contact.
    target_brand: Optional[str] = Field(default=None, max_length=80)
    # If false, the email is generated but NOT delivered to the Mailhog sandbox.
    send: bool = True


class GeneratedEmail(BaseModel):
    subject: str
    body: str
    from_name: str
    from_address: str


class GenerateResponse(BaseModel):
    attack_type: AttackType
    difficulty: Difficulty
    target_brand: Optional[str]
    # Ground-truth label so phishing and benign samples can be scored together.
    ground_truth: str = "phishing"
    email: GeneratedEmail
    # Ground truth: the tells we deliberately planted, so the detector's hits/misses
    # can be measured signal-by-signal later.
    planted_tells: list[str]
    delivered_to_sandbox: bool
    # Static, non-configurable sandbox destination — surfaced so the UI can prove containment.
    sandbox_destination: str


class BenignRequest(BaseModel):
    category: BenignCategory = BenignCategory.marketing_promo
    target_brand: Optional[str] = Field(default=None, max_length=80)
    send: bool = True


class BenignResponse(BaseModel):
    category: BenignCategory
    target_brand: Optional[str]
    ground_truth: str = "legitimate"
    email: GeneratedEmail
    # Surface features that could fool a naive detector into a false positive...
    surface_traps: list[str]
    # ...but these clean signals are why it is actually legitimate.
    clean_signals: list[str]
    delivered_to_sandbox: bool
    sandbox_destination: str
