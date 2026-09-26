"""Insert synthetic phishing samples directly into YOUR OWN Gmail inbox for testing.

This is the real-inbox analogue of the Mailhog sandbox loop. It uses the Gmail API's
`users.messages.insert`, which places a message you construct directly into your own
mailbox — it never sends over SMTP and there is no recipient parameter, so it can only
ever affect the authenticated account (`userId="me"`). Same containment posture as
sender.py: it cannot target anyone else.

Run this on your HOST machine (not in the container) so the OAuth browser flow can open:

    # one-time: install deps into a venv
    pip install -r redteam/requirements-gmail.txt

    # first run opens a browser to authorize (writes secrets/token.json), then inserts
    python redteam/gmail_insert.py --auth              # just authenticate
    python redteam/gmail_insert.py --count 5           # insert a mixed batch
    python redteam/gmail_insert.py --type brand_impersonation --difficulty hard --brand PayPal

Credentials: place your Desktop-app OAuth client JSON at secrets/credentials.json
(git-ignored). token.json is created automatically on first login.
"""
from __future__ import annotations

import argparse
import base64
import random
import sys
from pathlib import Path

# Make the `app` package importable whether run from repo root or the redteam/ dir.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.generator import generate_email, generate_benign  # noqa: E402
from app.schemas import AttackType, BenignCategory, Difficulty  # noqa: E402
from app.sender import build_message  # noqa: E402

# gmail.insert only adds messages to your own mailbox; it cannot send or read others'.
SCOPES = ["https://www.googleapis.com/auth/gmail.insert"]

_ROOT = Path(__file__).resolve().parent.parent
_CREDS = _ROOT / "secrets" / "credentials.json"
_TOKEN = _ROOT / "secrets" / "token.json"


def get_service():
    """Authenticate (cached) and return a Gmail API service. Opens a browser on first run."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    if not _CREDS.exists():
        sys.exit(f"Missing {_CREDS}. Download your Desktop-app OAuth client JSON there first.")

    creds = None
    if _TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(_CREDS), SCOPES)
            creds = flow.run_local_server(port=0)
        _TOKEN.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def _address(service) -> str:
    """The authenticated user's own email address (used only as the cosmetic To header)."""
    try:
        return service.users().getProfile(userId="me").execute().get("emailAddress", "me")
    except Exception:
        return "me"


def insert_sample(service, attack, to_address: str) -> str:
    """Insert one crafted sample into the user's own inbox. Returns the new message id."""
    msg = build_message(attack)
    # Retarget the cosmetic To header to the user's own address (insert has no recipient).
    del msg["To"]
    msg["To"] = to_address
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().insert(
        userId="me",
        body={"raw": raw, "labelIds": ["INBOX", "UNREAD"]},
    ).execute()
    return result.get("id", "?")


def _build_samples(args) -> list:
    """Return a list of CraftedAttacks per the CLI args."""
    rng = random.Random()
    if args.type == "benign":
        cat = BenignCategory(args.category) if args.category else rng.choice(list(BenignCategory))
        return [generate_benign(cat, args.brand)]
    if args.type and args.type != "mix":
        diff = Difficulty(args.difficulty)
        return [generate_email(AttackType(args.type), args.brand, diff)]

    # mix: a spread of attack types/difficulties plus one benign near-miss
    samples = []
    for _ in range(max(1, args.count - 1)):
        samples.append(
            generate_email(rng.choice(list(AttackType)), args.brand, rng.choice(list(Difficulty)))
        )
    samples.append(generate_benign(rng.choice(list(BenignCategory)), None))
    return samples


def main():
    ap = argparse.ArgumentParser(description="Insert synthetic phishing samples into your own Gmail inbox.")
    ap.add_argument("--auth", action="store_true", help="only authenticate, then exit")
    ap.add_argument("--count", type=int, default=5, help="how many to insert (mix mode)")
    ap.add_argument("--type", default="mix",
                    help="attack type, 'benign', or 'mix' (default)")
    ap.add_argument("--category", help="benign category (with --type benign)")
    ap.add_argument("--difficulty", default="easy", choices=[d.value for d in Difficulty])
    ap.add_argument("--brand", help="optional brand/role, e.g. PayPal")
    args = ap.parse_args()

    service = get_service()
    addr = _address(service)
    if args.auth:
        print(f"Authenticated as {addr}. Token saved to {_TOKEN}.")
        return

    samples = _build_samples(args)
    print(f"Inserting {len(samples)} sample(s) into {addr}'s inbox...")
    for s in samples:
        label = getattr(s, "ground_truth", "?")
        mid = insert_sample(service, s, addr)
        print(f"  [{label:10}] {s.from_address:42}  {s.subject[:45]}  -> id {mid}")
    print("Done. Check your Gmail inbox.")


if __name__ == "__main__":
    main()
