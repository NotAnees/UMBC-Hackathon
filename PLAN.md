# AI Phishing Detection & Red-Team Tool — Project Plan

Shared context for everyone on the team. If you're picking up a task, read this first.

## 1. What we're building

A two-sided AI phishing tool:

- **Blue team (defense)**: paste/upload an email, get back a verdict (Legitimate / Suspicious / Phishing) with an explanation, backed by two layers of analysis — fast deterministic heuristics and an LLM semantic pass.
- **Red team (offense)**: an LLM-driven generator that produces synthetic phishing emails (credential-harvesting, BEC/urgency, brand-impersonation templates) and fires them into our own sandboxed Mailhog inbox to stress-test the detector — a closed-loop "can our detector catch what our own generator makes" demo.

**Guardrail (non-negotiable)**: the generator only ever sends to our own Mailhog container (never a real SMTP server or a real address) and only ever produces content used to test/train our own detector or the seed corpus. No real targets, no external delivery, ever.

## 2. Stack

- **Backend**: Python + FastAPI
- **Frontend**: React (Vite)
- **Database**: Postgres
- **Fake inbox for demo**: Mailhog
- **LLM**: Google AI Studio (Gemini) via the `google-genai` Python SDK

Why: Python has the best libraries for email/header parsing (SPF/DKIM/DMARC) and a first-class Gemini SDK; React gives us a real interactive dashboard instead of server-rendered pages. The team is already comfortable with React + Python, which matters more than raw setup speed in a 24-hour window.

## 3. High-Level Architecture

```
┌─────────────┐      ┌──────────────┐      ┌───────────────────┐
│  Frontend    │ HTTP │  API Backend  │◄────►│  Mailhog/Maildev  │
│  (React/Vite)│◄────►│  (FastAPI)    │      │  (sandboxed SMTP) │
└─────────────┘      └──────┬───────┘      └─────────▲─────────┘
                             │                          │
                 ┌───────────┼─────────┐                │ generated emails
                 ▼           ▼         ▼                │ (sandbox only)
           ┌──────────┐ ┌───────────┐ ┌──────────────┐
           │ Postgres │ │  Gemini   │◄┤ Red-Team     │
           │ (emails, │ │   API     │ │ Generator    │
           │ verdicts,│ │ (Google   │ │ (detection/  │
           │ feedback)│ │ AI Studio)│ │  redteam.py) │
           └──────────┘ └───────────┘ └──────────────┘
                 ▲
                 │ one-time seed job
           ┌───────────┐
           │ seed data │ (Nazario/PhishTank/Enron samples)
           └───────────┘
```

The Red-Team Generator calls the same Gemini API as the detection layer, but with a "write a phishing email" prompt instead of a "classify this email" prompt. Its only output destinations are Mailhog (sandbox SMTP) and the seed/training corpus — it never has a code path to any real mail server or external address.

Containers: `frontend`, `api`, `postgres`, `mailhog`, plus a one-shot `seed` job — and a standalone `redteam` service (see [Section 7](#7-red-team--offensive-module)) that owns the offensive side end-to-end and only ever talks to Mailhog. LLM calls run synchronously inside the API request — no queue/worker infra needed for a 24-hour demo. (If the Mailhog live-polling stretch goal gets built, it runs as a simple `asyncio` background loop inside the `api` process, not a separate queue service.)

## 4. Repo Structure (target)

```
.
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── PLAN.md                        # this file
├── Makefile                       # make up / make seed / make logs
├── backend/
│   ├── Dockerfile.dev
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                # FastAPI app, routes
│   │   ├── routers/
│   │   │   ├── analyze.py         # POST /analyze (paste text / upload .eml)
│   │   │   ├── mailbox.py         # GET /mailbox/poll (mailhog integration)
│   │   │   ├── history.py         # GET /verdicts, GET /verdicts/{id}
│   │   │   ├── feedback.py        # POST /verdicts/{id}/feedback
│   │   │   └── redteam.py         # POST /redteam/generate (sandbox-only)
│   │   ├── detection/
│   │   │   ├── heuristics.py      # auth headers, domain mismatch, URL checks
│   │   │   ├── url_analysis.py    # typosquat/lookalike/redirect logic
│   │   │   ├── llm_pass.py        # Gemini call + structured prompt
│   │   │   └── scorer.py          # combine heuristic + LLM -> final verdict
│   │   ├── redteam/
│   │   │   ├── generator.py       # Gemini call: generate synthetic phishing email
│   │   │   ├── templates.py       # attack-type prompt templates (BEC, credential, urgency, brand-impersonation)
│   │   │   └── sender.py          # sends generated email ONLY to Mailhog SMTP
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── schemas.py             # pydantic request/response models
│   │   └── db.py
│   └── tests/
├── frontend/
│   ├── Dockerfile.dev
│   ├── package.json
│   └── src/
│       ├── pages/Upload.tsx
│       ├── pages/History.tsx
│       ├── pages/VerdictDetail.tsx
│       └── components/RiskBadge.tsx, SpanHighlighter.tsx
├── seed/
│   ├── seed.py                    # loads sample corpora into Postgres on first boot
│   └── data/
│       ├── phishing/              # curated phishing sample subset
│       └── ham/                   # curated legitimate sample subset
└── infra/
    └── postgres/init.sql          # schema bootstrap
```

Status as of 2026-09-26: `docker-compose.yml` and `.env.example` exist. Everything else above is still to be scaffolded.

## 5. docker-compose Services

| Service | Image/Base | Purpose | Notes |
|---|---|---|---|
| `frontend` | Node 20 (Vite/React dev server) | Dashboard UI | Bind-mounted source, hot reload, proxies `/api` to backend |
| `api` | Python 3.12 + FastAPI + Uvicorn | Ingestion, heuristics, LLM orchestration, scoring, CRUD | `--reload` for hot reload; depends on postgres |
| `postgres` | `postgres:16-alpine` | Stores emails, header parse results, verdicts, feedback | Named volume `pgdata`; schema via `infra/postgres/init.sql` |
| `mailhog` | `mailhog/mailhog` | Fake SMTP + web UI + API mailbox for the "live inbox" demo | Web UI :8025, SMTP :1025 |
| `seed` | one-shot, built from `backend` image | Loads sample phishing/ham emails into Postgres on first boot | `restart: "no"`, runs after postgres healthcheck |
| `redteam` | Python 3.12 + FastAPI (own image in `redteam/`) | Standalone offensive service: generates synthetic phishing via Gemini, delivers only to Mailhog | Port :8001; owned by Anees; depends on mailhog; no DB access |

## 6. Detection Pipeline

### Layer 1 — Heuristics (deterministic, cheap, always runs)

1. **Auth headers**: parse `Authentication-Results` / `Received-SPF` for SPF/DKIM/DMARC pass/fail/none.
2. **Sender identity**: From vs Reply-To vs Return-Path domain mismatch; display-name spoofing.
3. **URL analysis**: typosquat/lookalike domains, homoglyphs, raw IP links, punycode, mismatched anchor text vs href, shortened/redirect URLs.
4. **Keyword/pattern pass**: urgency language, credential-harvesting phrasing, generic-greeting + sensitive-action requests.
5. Each check emits `(signal_name, weight, evidence_snippet)` → summed into `heuristic_score (0–100)`.

Pure Python, no external calls — reliable fallback if the network/API is flaky during the demo.

### Layer 2 — LLM Semantic Pass (Gemini)

Send sanitized headers + body (truncated) + heuristic findings as context. Ask for **strict JSON**:

```json
{
  "verdict": "phishing | suspicious | legitimate",
  "confidence": 0-100,
  "rationale": "short explanation",
  "risky_spans": [{"text": "...", "reason": "..."}],
  "signals_confirmed": ["urgency_language", "brand_impersonation"]
}
```

Notes:
- `backend/app/detection/llm_pass.py` reads `GEMINI_API_KEY` from the environment (set once in `.env`, injected into the `api` container by `docker-compose.yml`) and passes it to the `google-genai` client — e.g. `genai.Client(api_key=os.environ["GEMINI_API_KEY"])` — to actually make this scanning call. This is the one env var in `.env.example` you must replace with a real value; every other default works as-is.
- Check current model IDs/params before hardcoding.
- Cap email body length sent to the API (cost/latency control).
- Strip/neutralize any `<script>`/active HTML before sending anywhere or rendering in the frontend — render as sanitized text/highlighted spans, never live HTML in an unsandboxed iframe.

### Scoring

- `final_score = 0.4 * heuristic_score + 0.6 * llm_confidence_score` (tune live)
- Override: SPF/DKIM/DMARC all fail + domain mismatch → floor at "suspicious" regardless of LLM.
- Override: LLM says "phishing" with confidence >85 → floor at "phishing" regardless of heuristics (catches BEC-style social engineering with no bad URLs/headers).
- Wide disagreement between layers → surface both as "mixed signal" in the UI rather than silently averaging (good demo talking point).
- Buckets: **Legitimate (0–33) / Suspicious (34–66) / Phishing (67–100)**.
- Store raw heuristic findings + raw LLM JSON in Postgres so the UI can show a "why" breakdown — this is the core judging differentiator.

## 7. Red Team / Offensive Module

Goal: prove the detector actually generalizes by attacking it with our own generator, and give the demo a "we built both sides" story.

> **Implementation note (2026-09-26):** the red team is built as a **standalone FastAPI service** in the top-level `redteam/` folder (owned by Anees), not inside `backend/app/`. This keeps it decoupled from the blue-team backend (no shared code, no merge conflicts) and reinforces the safety story — the attacker is its own container whose only outbound path is Mailhog. It runs on port 8001, has no Postgres access and no external network dependency, and exposes `POST /redteam/generate`. Files: `redteam/app/{main,generator,samples,sender,schemas}.py`. The frontend "Generate Attack" button calls `:8001` for generation; the resulting email still flows through the blue-team pipeline via Mailhog exactly as described below. Catch-rate (`redteam_runs`) is wired up last, once the blue-team `/verdicts` endpoint exists.
>
> **Near-miss / false-positive corpus (2026-09-26):** `POST /redteam/generate-benign` produces *legitimate* emails that share phishing's surface features (urgency, deadlines, calls to action, generic greetings) but are clean underneath (aligned From/Reply-To/Return-Path, SPF/DKIM/DMARC pass, link on the sender's own domain). Categories: `marketing_promo`, `account_notification`, `password_reset_requested` (the trickiest — looks just like a credential lure), `shipping_update`. The response carries `ground_truth: "legitimate"`, the `surface_traps` that could fool a naive detector, and the `clean_signals` that make it truly benign. Paired with the phishing generator's `planted_tells`, this gives a labeled ham+phish corpus so the detector can be scored on precision (false-positive rate), not just recall. Templates in `redteam/app/benign_samples.py`.
>
> **Difficulty dial + ground-truth tells (2026-09-26):** `POST /redteam/generate` takes a `difficulty` (`easy | medium | hard`) meaning difficulty *for the detector*. Easy = loud (verbose lookalike domain, raw-IP link, SPF/DKIM/DMARC all fail, Reply-To/Return-Path mismatch); medium = typosquat domain, URL shortener, softfail auth; hard = homoglyph/punycode domain, mismatched HTML anchor, and SPF/DKIM/DMARC that *pass* (the attacker authenticated their own lookalike domain — so header checks alone can't catch it, exercising the URL/content layers). Every response also returns `planted_tells` — the exact ground-truth list of signals we injected — so the loop can later measure the detector's hits/misses signal-by-signal, not just a binary caught/missed. Crafting logic lives in `redteam/app/crafting.py`.
>
> **Generation is template-driven, not live-LLM (2026-09-26):** we tried live Gemini generation first, but the model refuses to produce phishing/BEC content (a policy refusal, not a bug), and deliberately disabling the provider's safety settings to force it is off the table. Instead the generator fills an in-house bank of clearly-synthetic sample templates (`redteam/app/samples.py`) — the offensive analogue of the seed spam corpus (Nazario/PhishTank). This is more demo-robust anyway: no refusals, no network flakiness, deterministic (seedable) output, and we control the "tells" directly. `sender.py` then stamps each sample with realistic header tells (mismatched Reply-To + Return-Path, failing SPF/DKIM/DMARC) so the blue-team Layer-1 heuristics actually fire — without those, a sample would only exercise the LLM pass. The output shape matches what a live-LLM path would return, so a compliant generation backend could be swapped in later without touching callers.

### How it works

1. `POST /redteam/generate` takes an `attack_type` (`credential_harvest | bec_urgency | brand_impersonation | generic`) and optional `target_brand` (e.g. "PayPal", "IT Helpdesk").
2. `redteam/templates.py` holds a prompt template per attack type, describing the tactic (not a real target) — e.g. "write a short urgency-driven email impersonating {brand} IT support asking the recipient to reset their password via a link, using typical phishing tells (generic greeting, threat of account suspension, mismatched sender domain)."
3. `redteam/generator.py` calls Gemini with that prompt, gets back the synthetic email (subject, body, a plausible-but-fake sender address/domain).
4. `redteam/sender.py` delivers the generated email **only** to the local Mailhog SMTP container (`mailhog:1025`) — this is the single, hardcoded destination; there is no code path that accepts an arbitrary recipient or external SMTP host.
5. From there it flows through the normal pipeline like any other inbound message: Mailhog → `/mailbox/poll` → heuristics → LLM verdict → stored in `verdicts` with `emails.source = 'redteam'`.

### Why this is safe to build

- **No real delivery path**: the sender module has Mailhog's hostname hardcoded, not a configurable SMTP target — there's no parameter that could redirect it to a real mail server.
- **No real target data**: prompts describe generic tactics/brand names for realism, never a real person's name, email, or organization.
- **Self-contained loop**: every generated email is both created and evaluated inside our own stack, purely to test/improve/demo our detector.
- Treat this exactly like a fuzzer testing our own service — same safety posture, same reason it's fine to build.

### Demo value

- Live "attack our own detector" moment: generate a fresh phishing email in front of judges, watch it land in Mailhog, watch the detector flag it seconds later with a rationale — much stronger than only showing pre-canned samples.
- Optional score: run N generated attacks, report detector catch-rate, as a concrete "how good is our detector" metric backed by data instead of a claim.

## 8. Data Model (Postgres, minimal)

- `emails(id, source [paste|upload|mailhog|redteam], raw_headers, subject, sender, reply_to, body_text, received_at, created_at)`
- `verdicts(id, email_id FK, heuristic_score, heuristic_findings JSONB, llm_verdict, llm_confidence, llm_rationale, llm_risky_spans JSONB, final_score, final_label, created_at)`
- `feedback(id, verdict_id FK, marked_by, is_correct BOOLEAN, note, created_at)` — cheap to add now even though it's a stretch feature
- `redteam_runs(id, attack_type, target_brand, generated_email_id FK -> emails.id, detector_caught BOOLEAN, created_at)` — powers the catch-rate metric

## 9. MVP Feature List (build in this order)

1. `docker-compose up` brings up frontend + api + postgres, seeded with ~15–20 sample emails — **do this first**, everything else depends on the team being unblocked.
2. Backend: `.eml` upload + raw-paste endpoint → parse headers/body (Python `email` stdlib).
3. Heuristic layer: SPF/DKIM/DMARC parse, sender/reply-to mismatch, URL/lookalike-domain check, urgency keywords.
4. LLM layer: single Gemini call with structured JSON output, rationale + risky spans.
5. Scorer: combine into final label + score, persist to Postgres.
6. Frontend "Analyze" page: paste box + file upload, verdict card (label, score, risk badge, triggered signals, highlighted risky spans, LLM rationale).
7. Frontend "History" page: past analyzed emails, click into detail view.
8. Seed script: sample corpus loaded on first boot so there's demo data instantly.
9. README with one-command onboarding.
10. Red-team MVP: `POST /redteam/generate` (one attack type is enough for MVP) → Mailhog → auto-flows through the existing pipeline. A "Generate Attack" button on the frontend that triggers it and jumps to the resulting verdict.

## 10. Stretch Goals (only after MVP is demo-solid)

1. **Mailhog live mailbox demo** — poll Mailhog API for new messages, auto-analyze, "Live Inbox" view.
2. **Feedback loop** — thumbs up/down on a verdict, stored in `feedback`, dashboard tile showing agreement rate.
3. **Async background loop for Mailhog polling** — an `asyncio` task inside the `api` process (no Redis needed) so new Mailhog messages get picked up and analyzed without a manual trigger.
4. **Simple shared-API auth** — static bearer token (`API_SHARED_SECRET`) on write endpoints.
5. **URL/attachment sandbox stub** — resolve redirect chains (HTTP HEAD/GET, capped hops), report final destination + hop count.
6. **"Training set export" stub** — `GET /export/feedback.jsonl` logging heuristic-vs-LLM disagreements + feedback, as a narrative stretch (not real fine-tuning).
7. **Slack slash-command** — only if MVP + a couple stretch items are already solid; more realistic than a browser extension in remaining time.
8. **Full red-team attack-type coverage** — implement all four attack types, add a "batch generate N attacks, report catch-rate" dashboard tile.
9. **Adaptive red-team loop** — feed the detector's own rationale back into the generator prompt ("the last attempt was caught because X, try to avoid that") for a few rounds; demo talking point on adversarial robustness. Still Mailhog-only, still our own detector — no new safety surface, just more prompt iterations.

## 11. Team Onboarding

1. `git clone <repo>` → `cd UMBC-Hackathon`
2. `cp .env.example .env` → replace `GEMINI_API_KEY` with a real key (share via team password manager/DM, never commit). Every other value in `.env.example` is a working default for local dev — nothing else needs to change.
3. `docker compose up --build` — spins up all services; `seed` runs once and exits after loading sample data
4. Open `http://localhost:5173` (frontend), `http://localhost:8025` (Mailhog UI), `http://localhost:8000/docs` (FastAPI Swagger)
5. Source directories are bind-mounted — local edits hot-reload in both frontend (Vite) and backend (uvicorn `--reload`). Only rebuild (`docker compose up --build`) when dependencies change.
6. `Makefile` shortcuts (once added): `make up`, `make down`, `make seed`, `make logs service=api`.
7. Git workflow: feature branches per teammate (e.g. `feature/Anees-Red-Team`) → PR into the shared `UAT` branch → once tested on `UAT`, PR from `UAT` into `main`. `.env` is never committed (only `.env.example`). Postgres data persists in a named volume — `docker compose down -v` only if you want a clean reseed.

## 12. Demo Script (for judging)

1. Open dashboard, show the "Analyze" page.
2. Paste/upload a known phishing sample (e.g. a PayPal-lookalike) → verdict card: "Phishing, 91/100" — SPF fail, domain mismatch, urgency language highlighted, LLM rationale.
3. Paste/upload a legitimate email → "Legitimate, 12/100" — auth headers pass, no manipulation language found. Shows it's not just keyword-matching.
4. Show a "mixed signal" example (legit marketing email with urgency language but clean headers) — sells the "two-layer, not naive" story.
5. **Red-team moment**: click "Generate Attack," watch a fresh synthetic phishing email land in Mailhog and get auto-analyzed seconds later — this is the "we built the attacker too, and our own defense catches it" beat. Explicitly call out that generation stays inside our own sandbox.
6. (Stretch) Show a batch catch-rate metric from several generated attacks.
7. Show History dashboard, click into a detail view, show feedback thumbs (stretch).
8. Close with the export/feedback-loop narrative if built.

## 13. Open Decisions / Notes

- LLM provider is **Gemini (Google AI Studio)**, not Anthropic — use `google-genai`, not the `anthropic` package, when implementing `llm_pass.py`.
- One shared API key for the whole team, kept only in `.env`, only the backend container needs it. Set a quota/budget limit before the event.
- Red-team generator is scoped strictly to our own Mailhog sandbox — see [Section 7](#7-red-team--offensive-module) for the guardrails. Anyone extending `redteam/sender.py` must keep the destination hardcoded to the Mailhog service, never a configurable host.
