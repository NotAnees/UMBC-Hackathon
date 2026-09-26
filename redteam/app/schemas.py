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


class GenerateRequest(BaseModel):
    attack_type: AttackType = AttackType.credential_harvest
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
    target_brand: Optional[str]
    email: GeneratedEmail
    delivered_to_sandbox: bool
    # Static, non-configurable sandbox destination — surfaced so the UI can prove containment.
    sandbox_destination: str
