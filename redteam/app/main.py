"""Red-team FastAPI service.

Self-contained sibling to the blue-team `api` service. Generates synthetic phishing
samples from an in-house template bank (see samples.py) and delivers them ONLY into
the local Mailhog sandbox, where the blue-team detector picks them up through its
normal pipeline. Also serves a red-team dashboard at `/`. Runs on port 8001.

Endpoints:
  POST /redteam/generate         one phishing sample (attack type + difficulty)
  POST /redteam/generate-benign  one legitimate-but-phishy sample (false-positive test)
  POST /redteam/batch            a mixed campaign of N phishing + benign samples
  GET  /redteam/inbox            read-only view of the Mailhog sandbox
  GET  /redteam/stats            session activity aggregates (powers the dashboard)
"""
import random
from collections import Counter
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import db, generator, inbox, sender, store
from .crafting import CraftedAttack
from .schemas import (
    AttackType,
    BatchItem,
    BatchRequest,
    BatchResponse,
    BenignCategory,
    BenignRequest,
    BenignResponse,
    Difficulty,
    GeneratedEmail,
    GenerateRequest,
    GenerateResponse,
    InboxResponse,
    ScorecardResponse,
    StatsResponse,
)

_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Phishing Red-Team Service", version="0.2.0")

# Frontend (Vite dev server) may call this directly; allow it in local dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _email_of(a: CraftedAttack) -> GeneratedEmail:
    return GeneratedEmail(
        subject=a.subject, body=a.body_text, from_name=a.from_name, from_address=a.from_address
    )


def _record(kind: str, variant: str, difficulty: str | None, a: CraftedAttack, delivered: bool):
    store.record(
        {
            "kind": kind,
            "label": a.ground_truth,
            "variant": variant,
            "difficulty": difficulty,
            "tells": a.planted_tells,
            "from_address": a.from_address,
            "subject": a.subject,
            "delivered": delivered,
        }
    )


def _persist(kind: str, variant: str, brand: str | None, difficulty: str | None, a: CraftedAttack):
    """Record the answer key, keyed by the sample's X-Redteam-Id. No-ops if DB is down.

    We no longer insert the `emails` row — the blue team's Mailhog poller is the single
    path that inserts + analyzes the delivered message. Ground truth is joined back to
    that email via the X-Redteam-Id header (found in emails.raw_headers).
    """
    db.save_ground_truth(
        a.redteam_id,
        run_row={
            "kind": kind,
            "ground_truth": a.ground_truth,
            "attack_type": variant,
            "target_brand": brand,
            "difficulty": difficulty,
            "planted_tells": a.planted_tells,
        },
    )


@app.on_event("startup")
def _startup():
    """Create the shared tables if they don't exist yet (best-effort)."""
    db.ensure_schema()


# --- UI + health -----------------------------------------------------------


@app.get("/", include_in_schema=False)
def console():
    """Serve the red-team dashboard (same-origin, so its API calls need no CORS)."""
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "sandbox_destination": sender.SANDBOX_DESTINATION,
        "db_available": db.is_available(),
    }


# --- generation ------------------------------------------------------------


@app.post("/redteam/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    """Generate a synthetic phishing sample and (optionally) deliver it to the sandbox."""
    attack = generator.generate_email(req.attack_type, req.target_brand, req.difficulty)
    delivered = False
    if req.send:
        sender.send_to_sandbox(attack)
        delivered = True
        _persist("attack", req.attack_type.value, req.target_brand, req.difficulty.value, attack)
    _record("attack", req.attack_type.value, req.difficulty.value, attack, delivered)
    return GenerateResponse(
        attack_type=req.attack_type,
        difficulty=req.difficulty,
        target_brand=req.target_brand,
        ground_truth=attack.ground_truth,
        email=_email_of(attack),
        planted_tells=attack.planted_tells,
        delivered_to_sandbox=delivered,
        sandbox_destination=sender.SANDBOX_DESTINATION,
    )


@app.post("/redteam/generate-benign", response_model=BenignResponse)
def generate_benign(req: BenignRequest):
    """Generate a legitimate-but-phishy sample to test the detector's false-positive rate."""
    sample = generator.generate_benign(req.category, req.target_brand)
    delivered = False
    if req.send:
        sender.send_to_sandbox(sample)
        delivered = True
        _persist("benign", req.category.value, req.target_brand, None, sample)
    _record("benign", req.category.value, None, sample, delivered)
    return BenignResponse(
        category=req.category,
        target_brand=req.target_brand,
        email=_email_of(sample),
        surface_traps=sample.planted_tells,
        clean_signals=sample.clean_signals,
        delivered_to_sandbox=delivered,
        sandbox_destination=sender.SANDBOX_DESTINATION,
    )


@app.post("/redteam/batch", response_model=BatchResponse)
def batch(req: BatchRequest):
    """Run a mixed campaign of N samples (phishing + benign) into the sandbox."""
    rng = random.Random()
    attack_types = list(AttackType)
    difficulties = list(Difficulty)
    categories = list(BenignCategory)

    items: list[BatchItem] = []
    delivered_count = 0

    for _ in range(req.count):
        if rng.random() < req.benign_ratio:
            category = rng.choice(categories)
            sample = generator.generate_benign(category, None)
            if req.send:
                sender.send_to_sandbox(sample)
                _persist("benign", category.value, None, None, sample)
            _record("benign", category.value, None, sample, req.send)
            items.append(
                BatchItem(
                    kind="benign", label=sample.ground_truth, variant=category.value,
                    difficulty=None, from_address=sample.from_address, subject=sample.subject,
                    tell_count=len(sample.planted_tells), delivered=req.send,
                )
            )
        else:
            atype = rng.choice(attack_types)
            diff = rng.choice(difficulties)
            attack = generator.generate_email(atype, None, diff)
            if req.send:
                sender.send_to_sandbox(attack)
                _persist("attack", atype.value, None, diff.value, attack)
            _record("attack", atype.value, diff.value, attack, req.send)
            items.append(
                BatchItem(
                    kind="attack", label=attack.ground_truth, variant=atype.value,
                    difficulty=diff.value, from_address=attack.from_address, subject=attack.subject,
                    tell_count=len(attack.planted_tells), delivered=req.send,
                )
            )
        if req.send:
            delivered_count += 1

    counts = Counter(i.label for i in items)
    return BatchResponse(
        total=len(items), delivered=delivered_count, counts=dict(counts), items=items
    )


# --- inbox + stats ---------------------------------------------------------


@app.get("/redteam/inbox", response_model=InboxResponse)
def get_inbox(limit: int = 50):
    """Read-only view of the Mailhog sandbox (proxied server-side to avoid CORS)."""
    return InboxResponse(**inbox.fetch_inbox(limit))


def _flagged(verdict: str | None) -> bool:
    """The detector 'caught' something if it called it anything other than legitimate."""
    return (verdict or "").lower() in ("phishing", "suspicious")


@app.get("/redteam/scorecard", response_model=ScorecardResponse)
def get_scorecard():
    """Catch-rate + false-positive rate, scoring our ground truth against blue-team verdicts."""
    data = db.scorecard_data() or {"total_ground_truth": 0, "rows": []}
    rows = data["rows"]

    phishing = [r for r in rows if r["truth"] == "phishing"]
    benign = [r for r in rows if r["truth"] == "legitimate"]
    caught = [r for r in phishing if _flagged(r["verdict"])]
    fps = [r for r in benign if _flagged(r["verdict"])]

    by_diff: dict[str, dict] = {}
    for d in ("easy", "medium", "hard"):
        grp = [r for r in phishing if r["difficulty"] == d]
        got = [r for r in grp if _flagged(r["verdict"])]
        if grp:
            by_diff[d] = {
                "total": len(grp),
                "caught": len(got),
                "catch_rate": round(len(got) / len(grp) * 100, 1),
            }

    return ScorecardResponse(
        scored=len(rows),
        pending=max(0, data["total_ground_truth"] - len(rows)),
        phishing_total=len(phishing),
        benign_total=len(benign),
        caught=len(caught),
        missed=len(phishing) - len(caught),
        catch_rate=round(len(caught) / len(phishing) * 100, 1) if phishing else 0.0,
        false_positives=len(fps),
        fp_rate=round(len(fps) / len(benign) * 100, 1) if benign else 0.0,
        by_difficulty=by_diff,
    )


@app.get("/redteam/stats", response_model=StatsResponse)
def get_stats():
    """Aggregate activity for everything generated this session."""
    records = store.all_records()
    tell_counter: Counter = Counter()
    for r in records:
        tell_counter.update(r.get("tells") or [])
    return StatsResponse(
        total_generated=len(records),
        delivered=sum(1 for r in records if r.get("delivered")),
        by_label=dict(Counter(r["label"] for r in records)),
        by_attack_type=dict(Counter(r["variant"] for r in records if r["kind"] == "attack")),
        by_difficulty=dict(Counter(r["difficulty"] for r in records if r.get("difficulty"))),
        top_tells=[[t, c] for t, c in tell_counter.most_common(12)],
    )
