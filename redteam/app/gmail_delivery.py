"""Insert synthetic samples into the operator's OWN Gmail inbox (self-only).

SAFETY BOUNDARY: `userId` is hardcoded to "me" and the Gmail `messages.insert` call has
NO recipient parameter, so this can only ever add a message to the *authenticated
account's own* mailbox — it physically cannot send to, or target, any other address.
This is the web-button equivalent of `redteam/gmail_insert.py`, kept to the same
self-only invariant.

It reuses the `gmail.insert` refresh token that `gmail_insert.py --auth` already minted
(`secrets/token.json`), refreshing access tokens over stdlib urllib so the container
needs no Google client libraries. The token is mounted read-only into the container.
"""
import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
# userId=me is hardcoded here — there is deliberately no way to address another mailbox.
GMAIL_INSERT_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
DEFAULT_TOKEN_PATH = "/app/secrets/token.json"
_REQUEST_TIMEOUT = 20
_cached_access: tuple[str, float] | None = None


class GmailInsertUnavailable(RuntimeError):
    """Gmail insert can't run — no token, or Google rejected the request."""


def token_path() -> str:
    return os.environ.get("GMAIL_INSERT_TOKEN_PATH", DEFAULT_TOKEN_PATH)


def is_configured() -> bool:
    return os.path.exists(token_path())


def _stored() -> dict:
    path = token_path()
    if not os.path.exists(path):
        raise GmailInsertUnavailable(
            f"No Gmail token at {path}. Run `python redteam/gmail_insert.py --auth` on the host first."
        )
    data = json.loads(open(path, encoding="utf-8").read())
    for key in ("client_id", "client_secret", "refresh_token"):
        if not data.get(key):
            raise GmailInsertUnavailable(f"Gmail token is missing {key}; re-authorize.")
    return data


def _access_token() -> str:
    global _cached_access
    if _cached_access and _cached_access[1] > time.time():
        return _cached_access[0]
    stored = _stored()
    body = urllib.parse.urlencode(
        {
            "client_id": stored["client_id"],
            "client_secret": stored["client_secret"],
            "refresh_token": stored["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode()
    try:
        req = urllib.request.Request(TOKEN_ENDPOINT, data=body, method="POST")
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            payload = json.load(resp)
    except Exception as exc:
        raise GmailInsertUnavailable(f"Could not refresh the Gmail access token: {exc}") from exc
    token = payload.get("access_token")
    if not token:
        raise GmailInsertUnavailable("Google returned no access token; re-authorize.")
    _cached_access = (token, time.time() + payload.get("expires_in", 3600) - 120)
    return token


def insert_raw(raw_bytes: bytes) -> str:
    """Insert one raw RFC 822 message into the operator's own inbox. Returns the message id."""
    body = json.dumps(
        {"raw": base64.urlsafe_b64encode(raw_bytes).decode(), "labelIds": ["INBOX", "UNREAD"]}
    ).encode()
    req = urllib.request.Request(
        GMAIL_INSERT_URL,
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {_access_token()}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            return json.load(resp).get("id", "?")
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:200].decode(errors="replace")
        raise GmailInsertUnavailable(f"Gmail insert failed: {exc.code} {detail}") from exc
    except Exception as exc:
        raise GmailInsertUnavailable(f"Gmail insert failed: {exc}") from exc
