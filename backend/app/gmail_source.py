"""Read a real Gmail mailbox the same way the Chrome extension does.

Same API and the same `format=raw` call, so the detector receives the complete RFC
822 message — every Received hop, the DKIM signature and Google's own
Authentication-Results — rather than scraped body text. That is what keeps the
SPF/DKIM/DMARC term measurable on live mail.

Auth is deliberately split. The interactive consent runs once on the host
(`backend/scripts/gmail_authorize.py`), because a container has no browser to open.
It writes a token file holding the refresh token; this module then exchanges that for
access tokens over plain httpx, so the API image needs no Google client libraries.

READ-ONLY: the token is minted with gmail.readonly, and nothing here sends, modifies
or deletes mail.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
DEFAULT_TOKEN_PATH = "/app/secrets/token_readonly.json"
DEFAULT_QUERY = "in:inbox"
REQUEST_TIMEOUT = 20.0

# Access tokens last an hour; refresh a little early rather than racing expiry.
_EXPIRY_MARGIN_SECONDS = 120
_cached_access: tuple[str, float] | None = None


class GmailUnavailable(RuntimeError):
    """Gmail cannot be read — no token, or Google rejected the request."""


def token_path() -> Path:
    return Path(os.environ.get("GMAIL_TOKEN_PATH", DEFAULT_TOKEN_PATH))


def is_configured() -> bool:
    return token_path().exists()


def _stored_token() -> dict:
    path = token_path()
    if not path.exists():
        raise GmailUnavailable(
            f"No Gmail token at {path}. Run backend/scripts/gmail_authorize.py on the host first."
        )
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise GmailUnavailable(f"Gmail token at {path} is unreadable: {exc}") from exc

    missing = [k for k in ("client_id", "client_secret", "refresh_token") if not data.get(k)]
    if missing:
        raise GmailUnavailable(f"Gmail token is missing {', '.join(missing)}; re-authorize.")
    return data


def _access_token() -> str:
    global _cached_access
    if _cached_access and _cached_access[1] > time.time():
        return _cached_access[0]

    stored = _stored_token()
    try:
        response = httpx.post(
            TOKEN_ENDPOINT,
            data={
                "client_id": stored["client_id"],
                "client_secret": stored["client_secret"],
                "refresh_token": stored["refresh_token"],
                "grant_type": "refresh_token",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise GmailUnavailable(f"Could not refresh the Gmail access token: {exc}") from exc

    token = payload.get("access_token")
    if not token:
        raise GmailUnavailable("Google returned no access token; re-authorize.")

    _cached_access = (token, time.time() + payload.get("expires_in", 3600) - _EXPIRY_MARGIN_SECONDS)
    return token


def _get(path: str, params: dict | None = None) -> dict:
    try:
        response = httpx.get(
            f"{GMAIL_API}{path}",
            params=params,
            headers={"Authorization": f"Bearer {_access_token()}"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except GmailUnavailable:
        raise
    except Exception as exc:
        raise GmailUnavailable(f"Gmail request {path} failed: {exc}") from exc


def list_message_ids(limit: int) -> list[str]:
    query = os.environ.get("GMAIL_QUERY", DEFAULT_QUERY)
    payload = _get("/messages", {"maxResults": limit, "q": query})
    return [m["id"] for m in payload.get("messages", []) if m.get("id")]


def fetch_raw(message_id: str) -> str | None:
    """The full RFC 822 message, or None when Gmail returns something unusable."""
    raw = _get(f"/messages/{message_id}", {"format": "raw"}).get("raw")
    if not raw:
        return None
    # base64url, and Google omits the padding.
    padded = raw + "=" * (-len(raw) % 4)
    try:
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Could not decode Gmail message %s: %s", message_id, exc)
        return None
