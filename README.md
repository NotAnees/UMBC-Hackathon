# UMBC-Hackathon — AI Phishing Detection & Red-Team Tool

A two-sided phishing tool: a **blue-team detector** (heuristics + Claude semantic pass)
and a **red-team generator** that attacks it, with a measured catch-rate loop between them.
Plus a Chrome extension that runs the detector on a real Gmail inbox.

## Start here
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — how everything actually works (read this first).
- **[PLAN.md](PLAN.md)** — the original planning doc (some parts are aspirational/older).

## Quick start
```bash
cp .env.example .env            # then set ANTHROPIC_API_KEY
docker compose up -d --build api redteam postgres mailhog
```
- Blue-team dashboard: http://localhost:8000
- Red-team dashboard:  http://localhost:8001
- Mailhog sandbox:     http://localhost:8025

Demo the loop: Red **Campaign** → Blue **Live Inbox → Poll & analyze** → Red **Scorecard**.
