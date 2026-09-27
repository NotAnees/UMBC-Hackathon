"""One-time Gmail read consent, run on the HOST (a container has no browser to open).

It writes secrets/token_readonly.json, which the api container reads to refresh access
tokens by itself. Deliberately a separate file from secrets/token.json, which
redteam/gmail_insert.py owns with the gmail.insert scope — one file cannot hold two
different scope sets without whichever ran last breaking the other tool.

Usage (host, not the container):

    python3 -m venv /tmp/gmail-auth && /tmp/gmail-auth/bin/pip install google-auth-oauthlib
    /tmp/gmail-auth/bin/python backend/scripts/gmail_authorize.py

Prerequisite: a Desktop-app OAuth client JSON saved at secrets/credentials.json
(Google Cloud Console -> Credentials -> Create credentials -> OAuth client ID ->
Desktop app). secrets/ is git-ignored.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Read-only on purpose: this service never needs to send or modify mail.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_ROOT = Path(__file__).resolve().parent.parent.parent
_CREDENTIALS = _ROOT / "secrets" / "credentials.json"
_TOKEN = _ROOT / "secrets" / "token_readonly.json"


def main() -> int:
    if not _CREDENTIALS.exists():
        print(f"Missing {_CREDENTIALS}", file=sys.stderr)
        print(
            "Download a Desktop-app OAuth client JSON from Google Cloud Console and save it there.",
            file=sys.stderr,
        )
        return 1

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("google-auth-oauthlib is not installed. See this file's docstring.", file=sys.stderr)
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(str(_CREDENTIALS), SCOPES)
    # access_type=offline is what makes Google return a refresh token; without it the
    # container could not mint new access tokens after the first hour.
    credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    if not credentials.refresh_token:
        print("Google returned no refresh token. Revoke the app's access and retry.", file=sys.stderr)
        return 1

    _TOKEN.parent.mkdir(parents=True, exist_ok=True)
    _TOKEN.write_text(json.dumps(json.loads(credentials.to_json()), indent=2))
    _TOKEN.chmod(0o600)

    print(f"Wrote {_TOKEN}")
    print("Now restart the api container so it picks the token up:")
    print("  docker compose up -d --force-recreate api")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
