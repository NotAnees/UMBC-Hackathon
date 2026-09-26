from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlparse

SHORTENER_DOMAINS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly"}

# Domains we treat as familiar out of the box. A link to one of these is not by
# itself interesting; a link to anything outside this set (and outside the
# sender's own domain) is what `check_unfamiliar_links` reports.
FAMILIAR_DOMAINS = {
    "google.com",
    "gmail.com",
    "microsoft.com",
    "outlook.com",
    "office.com",
    "apple.com",
    "icloud.com",
    "amazon.com",
    "github.com",
    "gitlab.com",
    "linkedin.com",
    "slack.com",
    "zoom.us",
    "dropbox.com",
    "paypal.com",
    "stripe.com",
    "salesforce.com",
    "atlassian.com",
    "adobe.com",
    "docusign.net",
    "youtube.com",
    "facebook.com",
    "instagram.com",
    "wikipedia.org",
    "cloudflare.com",
    "umbc.edu",
}

# Suffixes where the registrable domain is the last three labels, not two.
_MULTI_PART_SUFFIXES = {
    "co.uk",
    "org.uk",
    "ac.uk",
    "gov.uk",
    "co.jp",
    "com.au",
    "net.au",
    "org.au",
    "co.nz",
    "com.br",
    "co.in",
    "com.mx",
    "co.za",
    "com.sg",
}

# Used to decide whether a dotted token is plausibly a hostname rather than a
# filename ("invoice.pdf") or prose ("etc.").
COMMON_TLDS = {
    "com", "net", "org", "io", "co", "gov", "edu", "mil", "int", "info", "biz",
    "app", "dev", "me", "us", "uk", "ca", "de", "fr", "nl", "es", "it", "se",
    "no", "fi", "pl", "ru", "ua", "cn", "jp", "kr", "in", "au", "nz", "br",
    "mx", "za", "sg", "xyz", "top", "site", "online", "live", "shop", "store",
    "click", "link", "support", "email", "cloud", "tech", "space", "website",
    "ly", "gl", "gd", "so", "sh", "ai", "tv", "cc", "to",
}

_URL_IN_TEXT_RE = re.compile(r"https?://[^\s\]\)>\"']+", re.IGNORECASE)
_TEXT_URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"'\]\),]+", re.IGNORECASE)
_BARE_DOMAIN_RE = re.compile(
    r"\b((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,})\b", re.IGNORECASE
)
_IP_HOST_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


@dataclass
class LinkFinding:
    anchor_text: str
    href: str
    reason: str
    kind: str = "other"


class _AnchorExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def _flush(self) -> None:
        if self._href is not None:
            self._links.append((" ".join(self._text).strip(), self._href))
        self._href = None
        self._text = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._flush()
            self._href = dict(attrs).get("href") or None
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._flush()

    def links(self) -> list[tuple[str, str]]:
        # Phishing HTML is often malformed, so an anchor left open at EOF still counts.
        self._flush()
        return self._links


def extract_links(body_html: str) -> list[tuple[str, str]]:
    parser = _AnchorExtractor()
    parser.feed(body_html or "")
    return parser.links()


def extract_text_urls(body_text: str) -> list[tuple[str, str]]:
    """URLs written directly in a plain-text body, as ("", url) pairs. There is no
    visible anchor text to disagree with the target, so the empty string makes the
    text-vs-href check skip them instead of needing a special case."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()

    for match in _TEXT_URL_RE.finditer(body_text or ""):
        url = match.group(0).rstrip(".,;:!?'\")")
        if url.lower() not in seen:
            seen.add(url.lower())
            found.append(("", url))
    return found


def collect_links(body_html: str | None, body_text: str | None = None) -> list[tuple[str, str]]:
    """Every link worth analysing. Anchors win when the HTML has them, because
    plain text derived from HTML repeats anchor *text* — treating a spoofed
    'paypal.com/login' label as a real destination would mask the spoof.
    """
    anchors = extract_links(body_html or "")
    if anchors:
        return anchors
    return extract_text_urls(body_text or "")


def registrable_domain(host: str) -> str:
    """Approximate eTLD+1 so 'www.paypal.com' and 'paypal.com' compare equal."""
    parts = (host or "").lower().strip(".").split(".")
    if len(parts) <= 2:
        return ".".join(parts)
    if ".".join(parts[-2:]) in _MULTI_PART_SUFFIXES:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _clean_host(netloc: str) -> str | None:
    return netloc.split("@")[-1].split(":")[0].lower() or None


def href_host(href: str) -> str | None:
    """Hostname an href actually resolves to, or None for non-navigating and
    same-origin-relative hrefs (mailto:, #anchor, /path)."""
    href = (href or "").strip()
    if not href or href.startswith(("#", "/", "mailto:", "tel:", "javascript:", "data:")):
        return None
    if "://" in href or href.startswith("//"):
        return _clean_host(urlparse(href).netloc)

    # Scheme-less but absolute, e.g. "www.evil.com/login".
    host = _clean_host(urlparse(f"//{href}").netloc)
    if host and host.rsplit(".", 1)[-1] in COMMON_TLDS:
        return host
    return None


def anchor_text_host(anchor_text: str) -> str | None:
    """Hostname the visible link text *claims*, whether written as a full URL
    ('https://paypal.com/x') or a bare domain ('paypal.com/x')."""
    url_match = _URL_IN_TEXT_RE.search(anchor_text or "")
    if url_match:
        return _clean_host(urlparse(url_match.group(0)).netloc)

    for match in _BARE_DOMAIN_RE.finditer(anchor_text or ""):
        host = match.group(1).lower().rstrip(".")
        if host.rsplit(".", 1)[-1] in COMMON_TLDS:
            return host
    return None


def check_link_mismatch(
    body_html: str, body_text: str | None = None
) -> tuple[bool, list[LinkFinding]]:
    """Flags anchors whose visible text names one domain while the href points
    elsewhere, plus raw-IP hrefs, punycode/homograph domains, and known shorteners.
    Returns (triggered, findings).
    """
    findings: list[LinkFinding] = []

    for anchor_text, href in collect_links(body_html, body_text):
        host = href_host(href)
        if not host:
            continue

        text_host = anchor_text_host(anchor_text)
        if text_host and registrable_domain(text_host) != registrable_domain(host):
            findings.append(
                LinkFinding(
                    anchor_text,
                    href,
                    f"link text shows '{text_host}' but points to '{host}'",
                    "text_spoof",
                )
            )
            continue

        if _IP_HOST_RE.match(host):
            findings.append(
                LinkFinding(anchor_text, href, f"raw IP address link ({host})", "raw_ip")
            )
            continue

        if "xn--" in host:
            findings.append(
                LinkFinding(anchor_text, href, f"punycode/homograph domain ({host})", "punycode")
            )
            continue

        if registrable_domain(host) in SHORTENER_DOMAINS:
            findings.append(
                LinkFinding(anchor_text, href, f"link shortener ({host})", "shortener")
            )

    return (len(findings) > 0, findings)


def link_hosts(body_html: str, body_text: str | None = None) -> list[str]:
    """Every distinct hostname the body actually links to."""
    hosts: list[str] = []
    for _, href in collect_links(body_html, body_text):
        host = href_host(href)
        if host and host not in hosts:
            hosts.append(host)
    return hosts


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a or not b:
        return len(a) or len(b)

    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (char_a != char_b))
            )
        previous = current
    return previous[-1]


# Below this length, edit distance stops being meaningful ('acme' is 1 edit from
# 'acne'), so short brand labels are only checked for containment.
MIN_BRAND_LABEL_LEN = 5
MIN_BRAND_CONTAINMENT_LEN = 4
MAX_TYPO_DISTANCE = 2


def _label(domain: str) -> str:
    return domain.split(".")[0]


def check_typosquat(
    domains: list[str],
    *,
    brand_domains: set[str] | None = None,
) -> tuple[bool, list[str]]:
    """Flags domains that imitate a known brand without being it — either a
    near-miss spelling ('paypa1.com', 'gogle.com') or the brand name pasted into
    an unrelated domain ('secure-paypal-login.com'). Returns (triggered, reasons).
    """
    brands = {registrable_domain(d) for d in (brand_domains or FAMILIAR_DOMAINS)}
    brand_labels = {
        _label(b): b for b in brands if len(_label(b)) >= MIN_BRAND_CONTAINMENT_LEN
    }

    reasons: list[str] = []
    seen: set[str] = set()

    for raw in domains:
        domain = registrable_domain(raw or "")
        if not domain or domain in brands or domain in seen or _IP_HOST_RE.match(domain):
            continue
        seen.add(domain)

        if "xn--" in domain:
            reasons.append(f"'{domain}' uses punycode/homograph encoding")
            continue

        label = _label(domain)
        tokens = [label, *(t for t in label.split("-") if t)]

        for brand_label, brand in sorted(brand_labels.items()):
            if brand_label in label:
                reasons.append(f"'{domain}' embeds '{brand_label}' but is not {brand}")
                break

            if len(brand_label) < MIN_BRAND_LABEL_LEN:
                continue

            near = next(
                (
                    _levenshtein(t, brand_label)
                    for t in tokens
                    if len(t) >= MIN_BRAND_LABEL_LEN
                    and _levenshtein(t, brand_label) <= MAX_TYPO_DISTANCE
                ),
                None,
            )
            if near is not None:
                reasons.append(f"'{domain}' is {near} edit(s) from '{brand}'")
                break

    return (len(reasons) > 0, reasons)


def check_unfamiliar_links(
    body_html: str,
    *,
    body_text: str | None = None,
    sender_domain: str | None = None,
    known_domains: set[str] | None = None,
) -> tuple[bool, list[LinkFinding]]:
    """Flags links pointing to domains we have no reason to trust.

    A domain is familiar when it is the sender's own registrable domain, a
    well-known domain (`FAMILIAR_DOMAINS`), or one the caller supplies via
    `known_domains` — that parameter is how the seed corpus / previously-seen
    senders get injected without making this layer touch the database.

    Raw-IP hosts are skipped here because `check_link_mismatch` already charges
    for them; double-counting one link would distort the weighted score.
    """
    familiar = {registrable_domain(d) for d in FAMILIAR_DOMAINS}
    if known_domains:
        familiar |= {registrable_domain(d) for d in known_domains if d}
    if sender_domain:
        familiar.add(registrable_domain(sender_domain))

    findings: list[LinkFinding] = []
    reported: set[str] = set()

    for anchor_text, href in collect_links(body_html, body_text):
        host = href_host(href)
        if not host or _IP_HOST_RE.match(host):
            continue

        domain = registrable_domain(host)
        if domain in familiar or domain in reported:
            continue

        reported.add(domain)
        findings.append(LinkFinding(anchor_text, href, f"link to unfamiliar domain '{domain}'"))

    return (len(findings) > 0, findings)
