from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from email import message_from_bytes, message_from_string, policy
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

AUTH_RESULT_HEADERS = ("Authentication-Results", "ARC-Authentication-Results")

# Headers that mark a payload as a real RFC 822 message rather than pasted prose.
_KNOWN_HEADER_RE = re.compile(
    r"^(?:from|to|cc|bcc|subject|date|sender|reply-to|return-path|received|"
    r"authentication-results|arc-authentication-results|received-spf|message-id|"
    r"in-reply-to|references|mime-version|content-type|content-transfer-encoding|"
    r"dkim-signature|list-id|list-unsubscribe|x-[a-z0-9-]+)[ \t]*:",
    re.IGNORECASE | re.MULTILINE,
)
_HTML_HINT_RE = re.compile(r"<(?:a\s|/?(?:html|body|div|p|table|span|br)\b)", re.IGNORECASE)
SPF_RESULTS = frozenset(
    {"pass", "fail", "softfail", "neutral", "none", "temperror", "permerror"}
)
_NON_TEXT_TAGS = {"script", "style", "head", "title"}


@dataclass
class ParsedEmail:
    raw_headers: str | None
    subject: str | None
    sender: str | None
    reply_to: str | None
    auth_results: str | None
    body_text: str | None
    body_html: str | None
    received_at: datetime | None


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _NON_TEXT_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _NON_TEXT_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and data.strip():
            self._chunks.append(data.strip())

    def text(self) -> str:
        return " ".join(self._chunks)


def html_to_text(body_html: str) -> str:
    parser = _TextExtractor()
    parser.feed(body_html or "")
    return parser.text()


def _decoded(value: object) -> str | None:
    """Header value as text, decoding RFC 2047 encoded-words when present."""
    if value is None:
        return None
    text = str(value)
    if "=?" in text:
        try:
            text = str(make_header(decode_header(text)))
        except Exception:
            pass
    return " ".join(text.split()) or None


def _header(msg: EmailMessage, name: str) -> str | None:
    try:
        return _decoded(msg[name])
    except Exception:
        return None


def _headers_all(msg: EmailMessage, name: str) -> list[str]:
    try:
        values = msg.get_all(name) or []
    except Exception:
        return []
    return [text for text in (_decoded(v) for v in values) if text]


def _normalized_spf(received_spf: str) -> str | None:
    """`Received-SPF: fail (example.com: domain of ...)` carries the same verdict as
    `spf=fail` in an Authentication-Results header, but in a different shape. Emit
    the normalized form so callers only have to look for one spelling."""
    first = received_spf.strip().split(None, 1)[0].lower().rstrip(":;,") if received_spf.strip() else ""
    return f"spf={first}" if first in SPF_RESULTS else None


def _auth_results(msg: EmailMessage) -> str | None:
    parts: list[str] = []
    for name in AUTH_RESULT_HEADERS:
        parts.extend(_headers_all(msg, name))
    combined = "; ".join(parts).lower()
    for value in _headers_all(msg, "Received-SPF"):
        normalized = _normalized_spf(value)
        if normalized and normalized not in combined:
            parts.append(normalized)
    return "; ".join(parts) or None


def _part_content(msg: EmailMessage, subtype: str) -> str | None:
    try:
        part = msg.get_body(preferencelist=(subtype,))
    except Exception:
        part = None
    if part is None:
        return None

    try:
        content = part.get_content()
    except Exception:
        payload = part.get_payload(decode=True)
        if payload is None:
            return None
        content = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    return str(content).strip() or None


def _received_at(msg: EmailMessage) -> datetime | None:
    raw_date = _header(msg, "Date")
    if not raw_date:
        return None
    try:
        return parsedate_to_datetime(raw_date)
    except (TypeError, ValueError):
        return None


def _raw_headers(msg: EmailMessage) -> str | None:
    try:
        lines = [f"{key}: {value}" for key, value in msg.items()]
    except Exception:
        return None
    return "\n".join(lines) or None


def looks_like_rfc822(raw: str) -> bool:
    """Whether the leading block carries a header a real message would have.

    Without this check the stdlib parser reads any leading `Word: value` line as a
    header, so a pasted body starting "URGENT: your account..." has its first line
    swallowed as a header named URGENT — and a one-line paste ends up with no body
    at all.
    """
    head = re.split(r"\r?\n\r?\n", raw.lstrip(), maxsplit=1)[0][:4000]
    return bool(_KNOWN_HEADER_RE.search(head))


def _body_only(text: str) -> ParsedEmail:
    body = text.strip()
    return ParsedEmail(
        raw_headers=None,
        subject=None,
        sender=None,
        reply_to=None,
        auth_results=None,
        body_text=body or None,
        # Pasted markup still gets its anchors analysed rather than read as prose.
        body_html=body if body and _HTML_HINT_RE.search(body) else None,
        received_at=None,
    )


def parse_email(raw: str | bytes) -> ParsedEmail:
    """Parse a raw RFC 822 message (an uploaded .eml or pasted text) into the
    fields the detection layer consumes.

    Pasted text with no headers at all still parses: it becomes the body, with
    the header-derived fields left as None.
    """
    sniff = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else (raw or "")
    if not looks_like_rfc822(sniff):
        return _body_only(sniff)

    if isinstance(raw, bytes):
        msg = message_from_bytes(raw, policy=policy.default)
    else:
        msg = message_from_string(raw or "", policy=policy.default)

    body_html = _part_content(msg, "html")
    body_text = _part_content(msg, "plain")
    if not body_text and body_html:
        # HTML-only mail is common, and the keyword heuristics read body_text —
        # without this they would silently never fire on those messages.
        body_text = html_to_text(body_html) or None

    return ParsedEmail(
        raw_headers=_raw_headers(msg),
        subject=_header(msg, "Subject"),
        sender=_header(msg, "From"),
        reply_to=_header(msg, "Reply-To"),
        auth_results=_auth_results(msg),
        body_text=body_text,
        body_html=body_html,
        received_at=_received_at(msg),
    )
