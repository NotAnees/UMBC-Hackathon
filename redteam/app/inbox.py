"""Server-side proxy to the Mailhog sandbox inbox.

The dashboard is served same-origin from this service, but Mailhog (:8025) doesn't send
CORS headers, so the browser can't read it directly. This module fetches Mailhog's API
from the backend (same Docker network) and returns a simplified, safe view. Read-only —
it only lists what's already in the sandbox; it never sends.
"""
import json
import urllib.request

# Same hardcoded sandbox host as the sender — read side of the same box.
_MAILHOG_MESSAGES = "http://mailhog:8025/api/v2/messages"


def _first(headers: dict, key: str):
    values = headers.get(key) or []
    return values[0] if values else None


def _spf_verdict(auth_results: str) -> str | None:
    for state in ("pass", "softfail", "fail"):
        if f"spf={state}" in auth_results:
            return state
    return None


def fetch_inbox(limit: int = 50) -> dict:
    """Return a simplified list of sandbox messages, newest first. Never raises."""
    try:
        with urllib.request.urlopen(_MAILHOG_MESSAGES, timeout=5) as resp:
            data = json.load(resp)
    except Exception:
        return {"reachable": False, "total": 0, "items": []}

    items = []
    for m in (data.get("items") or [])[:limit]:
        headers = (m.get("Content") or {}).get("Headers") or {}
        auth = _first(headers, "Authentication-Results") or ""
        items.append(
            {
                "id": m.get("ID", ""),
                "from_addr": _first(headers, "From") or "",
                "to_addr": _first(headers, "To") or "",
                "subject": _first(headers, "Subject") or "",
                "created": m.get("Created"),
                "redteam": bool(_first(headers, "X-Redteam-Generated")),
                "spf": _spf_verdict(auth),
            }
        )
    return {"reachable": True, "total": data.get("total", len(items)), "items": items}
