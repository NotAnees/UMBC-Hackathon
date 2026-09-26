"""Red-team FastAPI service.

Self-contained sibling to the blue-team `api` service. Generates synthetic phishing
samples with Gemini and delivers them ONLY into the local Mailhog sandbox, where the
blue-team detector picks them up through its normal pipeline. Runs on port 8001.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import generator, sender
from .schemas import GenerateRequest, GenerateResponse

app = FastAPI(title="Phishing Red-Team Service", version="0.1.0")

# Frontend (Vite dev server) calls this directly; allow it in local dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "sandbox_destination": sender.SANDBOX_DESTINATION}


@app.post("/redteam/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    """Generate a synthetic phishing sample and (optionally) deliver it to the sandbox."""
    email = generator.generate_email(req.attack_type, req.target_brand)

    delivered = False
    if req.send:
        sender.send_to_sandbox(email)
        delivered = True

    return GenerateResponse(
        attack_type=req.attack_type,
        target_brand=req.target_brand,
        email=email,
        delivered_to_sandbox=delivered,
        sandbox_destination=sender.SANDBOX_DESTINATION,
    )
