"""Curated bank of benign-but-phishy sample templates (the "ham" / near-miss corpus).

These are LEGITIMATE emails that happen to share surface features with phishing
(urgency, deadlines, calls to action, generic greetings) — the classic false-positive
trap. Crucially, they are *clean* underneath: aligned From/Reply-To/Return-Path, passing
SPF/DKIM/DMARC, and links on the same domain as the sender. They exist to test whether
the detector over-flags, i.e. its precision — not just its recall on real attacks.
"""
from dataclasses import dataclass

from .schemas import BenignCategory


@dataclass(frozen=True)
class BenignTemplate:
    subject: str
    from_name: str
    from_local: str
    body: str
    # Surface features a naive detector might over-weight into a false positive.
    surface_traps: list[str]


BENIGN_BANK: dict[BenignCategory, list[BenignTemplate]] = {
    BenignCategory.marketing_promo: [
        BenignTemplate(
            subject="Last chance: your 40% off ends tonight",
            from_name="{brand} Offers",
            from_local="offers",
            body=(
                "Hi there,\n\n"
                "Just a reminder that your 40% off promo code expires at midnight tonight! "
                "Don't miss out — shop the sale now:\n\n"
                "{link}\n\n"
                "Happy shopping,\nThe {brand} Team\n\n"
                "You are receiving this because you subscribed to {brand} emails. Unsubscribe anytime."
            ),
            surface_traps=["urgency_language", "deadline_pressure", "call_to_action_link"],
        ),
    ],
    BenignCategory.account_notification: [
        BenignTemplate(
            subject="Your {brand} statement is ready to view",
            from_name="{brand} Account Services",
            from_local="no-reply",
            body=(
                "Hello,\n\n"
                "Your monthly {brand} statement is now available. You can view it securely "
                "by signing in to your account:\n\n"
                "{link}\n\n"
                "For your security, we will never ask for your password by email.\n\n"
                "Thank you,\n{brand} Account Services"
            ),
            surface_traps=["generic_greeting", "account_action_link"],
        ),
    ],
    BenignCategory.password_reset_requested: [
        BenignTemplate(
            subject="Reset your {brand} password",
            from_name="{brand} Security",
            from_local="security",
            body=(
                "Hi,\n\n"
                "We received a request to reset the password for your {brand} account. "
                "Click the link below within 30 minutes to choose a new password:\n\n"
                "{link}\n\n"
                "If you didn't request this, you can safely ignore this email — your password "
                "will not change.\n\n"
                "{brand} Security"
            ),
            # Deliberately the trickiest: looks exactly like a credential-harvest lure,
            # but it is the real, user-initiated reset flow with clean infrastructure.
            surface_traps=["urgency_language", "deadline_pressure", "credential_action_link"],
        ),
    ],
    BenignCategory.shipping_update: [
        BenignTemplate(
            subject="Your {brand} order has shipped",
            from_name="{brand} Shipping",
            from_local="orders",
            body=(
                "Hi,\n\n"
                "Good news — your order is on its way! Track your package here:\n\n"
                "{link}\n\n"
                "Estimated delivery: 2-3 business days.\n\n"
                "Thanks for shopping with {brand}."
            ),
            surface_traps=["call_to_action_link"],
        ),
    ],
}

DEFAULT_BENIGN_BRANDS = {
    BenignCategory.marketing_promo: "ShopMart",
    BenignCategory.account_notification: "Northwind Bank",
    BenignCategory.password_reset_requested: "Workspace",
    BenignCategory.shipping_update: "Parcelly",
}
