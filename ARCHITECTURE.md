# ARCHITECTURE — AI Phishing Detection & Red-Team Tool

> **Read this first if you are an LLM or a developer new to this repo.** It describes
> what the project actually is and how the pieces fit together *as currently built*.
> `PLAN.md` is the original planning doc (some of it is aspirational/older); **this file
> reflects the real, working state of the code.** Where they disagree, trust this file.

---

## 1. What this project is

A **two-sided phishing tool** built for a hackathon:

- **Blue team (defense):** an email phishing **detector**. You give it an email (paste, upload, a live Gmail message, or one pulled from a sandbox inbox) and it returns a verdict — **legitimate / suspicious / phishing** — with a score, a rationale, triggered signals, and highlighted risky spans.
- **Red team (offense):** a **synthetic phishing generator** that fabricates realistic-but-fake phishing emails at varying difficulty, delivers them into a local sandbox (Mailhog) or a real Gmail inbox, and then **scores how well the blue team's detector catches them** (catch rate, false-positive rate, per-difficulty).

The whole point is a **closed loop**: the red team attacks, the blue team defends, and we measure the outcome — "we built both the attacker and the defender, and here's proof the defender works."

**Safety posture (important):** the red-team generator produces *synthetic test fixtures only*. It delivers exclusively to (a) the local Mailhog sandbox (SMTP host hardcoded, no external path) or (b) the operator's **own** Gmail inbox via the Gmail API's `messages.insert` (`userId="me"`, no recipient parameter). There is no code path that targets another person or an external mail server. Treat it like a fuzzer testing our own classifier.

---

## 2. Services & ports (docker-compose.yml)

| Service | Port | Status | Role |
|---|---|---|---|
| `api` (blue backend) | 8000 | built | FastAPI detector: ingestion, heuristics, LLM pass, scoring, history, Mailhog poller. **Serves the blue-team dashboard at `/`.** |
| `redteam` | 8001 | built | Standalone FastAPI attacker: generation, delivery, campaign, stats, scorecard. **Serves the red-team dashboard at `/`.** |
| `postgres` | 5432 | built | Postgres 16. Stores emails, verdicts, feedback, and the red-team answer key. |
| `mailhog` | 1025 (SMTP), 8025 (UI/API) | built | Fake inbox — the sandbox seam between red and blue. |
| `frontend` | 5173 | **NOT built** | A Vite/React app is declared in compose but `frontend/` does not exist. The dashboards are instead served same-origin by `api` and `redteam` (no build step, no CORS). |
| `seed` | one-shot | **NOT built** | Declared in compose; `seed/` does not exist. |

Run everything: `docker compose up --build` (the `frontend`/`seed` services will fail to build — start the four that exist: `docker compose up -d --build api redteam postgres mailhog`).

There is also a **Chrome extension** (`extension/`) that runs in the operator's browser — not a container. And a **local Gmail seeder script** (`redteam/gmail_insert.py`) run on the host.

---

## 3. The three ways to use the detector

1. **Blue-team dashboard** — `http://localhost:8000/` (served by `api`). Views: Analyze (paste/upload → verdict), Live Inbox (poll Mailhog + analyze), History.
2. **Red-team dashboard** — `http://localhost:8001/` (served by `redteam`). Views: Generate, Campaign, Sandbox, Scorecard, Stats. Cross-links to the blue dashboard.
3. **Chrome extension** (`extension/`) — reads the operator's real Gmail via the Gmail API and scores messages with the blue team's `/analyze`. Popup + inline verdict banner.

Both dashboards are single static HTML files with a shared dark, animated-gradient theme (red accent = offense, cyan = defense).

---

## 4. The closed loop (how a sample flows)

```
RED (:8001)  POST /redteam/generate|/generate-benign|/batch
   │  builds a synthetic email (crafting.py) with a unique X-Redteam-Id header
   │  records the ANSWER KEY in redteam_ground_truth (keyed by that id)
   ▼
sender.py  → SMTP → MAILHOG (:1025)          [sandbox; hardcoded destination]
   ▼
BLUE (:8000)  GET /mailbox/poll[?use_llm=true]
   │  poller reads new Mailhog messages, inserts each into `emails`
   │  (source='mailhog'), runs the detection pipeline, writes a `verdicts` row
   ▼
RED (:8001)  GET /redteam/scorecard
   │  joins redteam_ground_truth ↔ emails (by X-Redteam-Id in raw_headers) ↔ verdicts
   ▼  → catch rate, false-positive rate, per-difficulty breakdown
```

**Single-channel ingestion (critical design point):** the red team **does NOT write the `emails` table.** Only the blue team's poller inserts emails (and analyzes them). This avoids duplicate rows and keeps the verdict and its answer key correlatable. The join key is the **`X-Redteam-Id`** header the red team stamps on every sample; the poller stores it inside `emails.raw_headers`, and the scorecard extracts it with a regex to join to `redteam_ground_truth.redteam_id`. See `redteam/app/db.py` and `redteam/app/main.py:get_scorecard`.

The extension is a **separate real-world path**: Gmail message → `/analyze` → verdict (it does not use Mailhog or the scorecard).

---

## 5. Blue team (`backend/`)

FastAPI app. Key modules:

- `app/main.py` — app setup, CORS (`*`), `create_all()` on startup, serves the dashboard at `/`, includes routers, `/health` + `/health/db`.
- `app/email_parser.py` — `parse_email(raw)` turns a raw `.eml`/pasted text into a `ParsedEmail` (subject, sender, reply_to, auth_results, body_text/html, received_at). Normalizes `Authentication-Results` + `Received-SPF` into a single `spf=<verdict>` form.
- `app/detection/heuristics.py` — deterministic signals (SPF/DKIM/DMARC, From/Reply-To/Return-Path mismatch, urgency/identity language). Emits weighted `signals`.
- `app/detection/url_analysis.py` — link extraction + typosquat / lookalike / anchor-mismatch / raw-IP / shortener checks.
- `app/detection/llm_pass.py` — **LLM semantic pass. Uses Anthropic Claude** (`anthropic` SDK, `client.messages.parse(..., output_format=LlmVerdict)`), **default model `claude-haiku-4-5`** (override `ANTHROPIC_MODEL`). Returns `None` on no key / failure / refusal so the deterministic layers stay authoritative. (History note: this was originally Gemini/`google-genai`; switched to Claude.)
- `app/detection/scorer.py` — combines heuristics + LLM into `final_score` / `final_label` and a separate `risk_score` / `risk_label`.
- `app/analysis.py` — shared analysis orchestration used by the routers.
- `app/models.py` — SQLAlchemy models (see schema below).
- `app/routers/` — `analyze.py` (`POST /analyze`, `POST /analyze/eml`), `mailbox.py` (`GET /mailbox/poll`), `history.py` (`GET /verdicts`, `GET /verdicts/{id}`), `feedback.py`.
- `app/static/index.html` — the blue-team dashboard.

### Blue endpoints
- `POST /analyze` — `{ raw_email, source, use_llm, domain_age_days }` → `AnalyzeResponse` (risk_label/score, heuristic_label/score, `llm` block, signals, link flags).
- `POST /analyze/eml` — same, body is raw `.eml` bytes.
- `GET /mailbox/poll?use_llm=bool` — pull + analyze new Mailhog messages (idempotent via `external_id`; skips already-analyzed). LLM off by default to conserve quota.
- `GET /verdicts?limit&offset` / `GET /verdicts/{id}` — history list + detail.
- `POST /verdicts/{id}/feedback` — thumbs up/down on a verdict.

---

## 6. Red team (`redteam/`)

Standalone FastAPI app, **no external network dependency** for generation (template-driven). Key modules:

- `app/samples.py` — bank of synthetic **phishing** templates per attack type.
- `app/benign_samples.py` — bank of **benign-but-phishy** templates (false-positive / near-miss tests), e.g. `password_reset_requested` looks like a credential lure but is clean.
- `app/crafting.py` — the difficulty engine. Produces a `CraftedAttack` with domains, links, auth headers, and a **`planted_tells`** ground-truth list. Difficulty is *for the detector*:
  - **easy** — verbose lookalike domain, raw-IP link, SPF/DKIM/DMARC all fail, Reply-To/Return-Path mismatch (loud).
  - **medium** — typosquat domain (`paypa1.com`), URL shortener, softfail auth.
  - **hard** — homoglyph/punycode domain (`xn--pypal-4ve.com`), mismatched HTML anchor, and SPF/DKIM/DMARC that **pass** (attacker authenticated their own lookalike — so header checks alone can't catch it).
- `app/generator.py` — fills a template + crafting into a `CraftedAttack`; stamps a unique `redteam_id`. (Originally attempted live Gemini generation; the model **refused** to write phishing, so generation is template-driven instead — see §9.)
- `app/sender.py` — delivers to Mailhog over SMTP (**hardcoded host**, no configurable destination). Stamps `X-Redteam-Id`. Also builds the header block persisted as ground-truth context.
- `app/db.py` — writes only `redteam_ground_truth` (keyed by `redteam_id`); computes the scorecard join.
- `app/store.py` — in-memory session log powering `/redteam/stats`.
- `app/inbox.py` — server-side proxy to the Mailhog API (so the dashboard reads the sandbox without CORS).
- `app/main.py` — endpoints + serves the red-team dashboard.
- `app/static/index.html` — the red-team dashboard.
- `gmail_insert.py` + `requirements-gmail.txt` — the **local host** Gmail seeder (see §8).

### Red endpoints
- `POST /redteam/generate` — `{ attack_type, difficulty, target_brand?, send }` → sample + `planted_tells`.
- `POST /redteam/generate-benign` — `{ category, target_brand?, send }` → sample + `surface_traps` + `clean_signals`.
- `POST /redteam/batch` — `{ count, benign_ratio, send }` → a mixed campaign.
- `GET /redteam/inbox` — read-only Mailhog view.
- `GET /redteam/scorecard` — catch rate / FP rate / per-difficulty (joins ground truth ↔ verdicts).
- `GET /redteam/stats` — session aggregates.

---

## 7. Database schema (Postgres)

Blue team owns the canonical schema (`backend/app/models.py`, created via `create_all()`); the red team creates only its own answer-key table (`CREATE TABLE IF NOT EXISTS` in `redteam/app/db.py`).

- **`emails`** — `id, source (paste|upload|mailhog|redteam), external_id, raw_headers, subject, sender, reply_to, body_text, body_html, received_at, created_at`. The sample *as if it arrived*. **Written only by the blue team's poller/analyze** — no ground truth here, so detection stays honest.
- **`verdicts`** — `id, email_id FK, heuristic_score, heuristic_findings, llm_verdict, llm_confidence, llm_rationale, llm_risky_spans, link_mismatch, unfamiliar_link, typosquat, domain_age_days, risk_score, risk_label, risk_components, final_score, final_label, created_at`.
- **`feedback`** — `id, verdict_id FK, marked_by, is_correct, note, created_at`.
- **`redteam_runs`** — blue team's model (`id, attack_type, target_brand, generated_email_id FK, detector_caught, created_at`). **Currently unused by the red team** (see §9 divergence note).
- **`redteam_ground_truth`** — red team's answer key: `id, redteam_id (unique), kind, ground_truth, attack_type, target_brand, difficulty, planted_tells (JSONB), created_at`. Joined to `emails` via the `X-Redteam-Id` header.

---

## 8. Gmail seeder (`redteam/gmail_insert.py`)

Run on the **host** (not in a container) so the OAuth browser flow can open. Uses the Gmail API `users.messages.insert` to place synthetic samples directly into the operator's **own** inbox (labeled INBOX/UNREAD) — the real-inbox analogue of the Mailhog loop, and the way to get test material for the extension. Credentials live in git-ignored `secrets/credentials.json` (+ `token.json`); scope `gmail.insert`. Examples:
```
python redteam/gmail_insert.py --auth                 # one-time browser sign-in
python redteam/gmail_insert.py --count 5              # mixed batch into your inbox
python redteam/gmail_insert.py --type brand_impersonation --difficulty hard --brand PayPal
```

---

## 9. Chrome extension (`extension/`)

Manifest V3 extension. Reads Gmail via the API and scores messages with `/analyze`.

- `manifest.json` — `gmail.readonly` OAuth (a **Chrome Extension** OAuth client, bound to the extension's ID), host perms for the Gmail API + `http://localhost:8000`.
- `background.js` — service worker; the only context with OAuth + host permissions. Gets the token, reads Gmail (`messages.get?format=raw` → full MIME so header heuristics fire), POSTs to `/analyze`. The popup and content script message it.
- `popup.html/js` — toolbar popup: Load inbox, Analyze (on demand or all), risk badges + rationale.
- `content.js/css` — best-effort inline verdict banner over the open Gmail message (fragile: depends on scraping Gmail's DOM for `data-legacy-message-id`).
- `README.md` — the OAuth "chicken-and-egg" setup (load unpacked → get extension ID → create Chrome-Extension OAuth client with that ID → paste client_id → reload).

The Chrome-Extension OAuth client ID is **not a secret** (no client secret exists for that client type), so it lives in `manifest.json`. It is bound to one extension ID, so each developer needs their own client for their own unpacked load.

---

## 10. Configuration & secrets

`.env` (git-ignored; copy from `.env.example`):
- `ANTHROPIC_API_KEY` — **the one value you must set** (from console.anthropic.com). The `api` container reads it; the `anthropic` client picks it up automatically. (Was `GEMINI_API_KEY` before the Claude switch.)
- `DATABASE_URL`, `MAILHOG_API_URL`, `API_SHARED_SECRET`, `FRONTEND_PORT`, `API_PORT`, `REDTEAM_PORT` — working defaults.

Secrets never committed: `.env`, and `secrets/` (Gmail `credentials.json` / `token.json`). Both are git-ignored.

---

## 11. Key design decisions & gotchas (for a future LLM)

1. **LLM provider is Claude, not Gemini.** Live Gemini generation was tried for the red team but the model refused to produce phishing content; disabling provider safety was off-limits. So **red-team generation is template-driven** (we author the fixtures), and the **blue-team detector's LLM pass uses Claude Haiku 4.5**. Do not reintroduce `google-genai`.
2. **Red team is template-driven on purpose** — no live LLM call in the generation path. This is more demo-robust (no refusals, no network) and gives exact `planted_tells` ground truth for free.
3. **Single-channel ingestion** — only the blue poller writes `emails`; the red team writes only `redteam_ground_truth`. Correlate via the `X-Redteam-Id` header. Do not re-add a direct `emails` insert on the red side (it caused duplicate rows).
4. **`redteam_runs` vs `redteam_ground_truth`** — the two teams modeled the results table differently and it was never unified. The scorecard uses `redteam_ground_truth`; `redteam_runs` is currently unused. Unifying them is an open task.
5. **Dashboards are served same-origin** by their own service (`api` at :8000, `redteam` at :8001) as static HTML — deliberately, to avoid a build step and CORS. The `frontend/` React service in compose was never built.
6. **Difficulty is difficulty *for the detector*** — `hard` means stealthy (passes SPF/DKIM/DMARC), which is *harder* to catch, not "a weak attack."
7. **Running DB schema drift:** because both services use `CREATE ... IF NOT EXISTS` / `create_all()` (neither ALTERs), if you add a column you must drop+recreate the tables on an existing volume (`docker compose down -v`, or `DROP TABLE ... CASCADE`) for it to take effect. Dev data is disposable.
8. **Git:** feature branches → `UAT` (integration) → `main`. Commits and PRs carry **no AI attribution** (per the repo owner's standing preference).

---

## 12. Quick start (fresh machine)

```bash
git clone <repo> && cd UMBC-Hackathon
cp .env.example .env            # then set ANTHROPIC_API_KEY
docker compose up -d --build api redteam postgres mailhog
# Blue dashboard:  http://localhost:8000
# Red dashboard:   http://localhost:8001
# Mailhog inbox:   http://localhost:8025
# API docs:        http://localhost:8000/docs  and  http://localhost:8001/docs
```
Demo the loop: Red dashboard → **Campaign** (fire a mixed batch) → Blue dashboard → **Live Inbox → Poll & analyze** (toggle "use Claude") → Red dashboard → **Scorecard** (catch rate).
