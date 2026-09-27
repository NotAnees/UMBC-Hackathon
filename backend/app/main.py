from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text

from app import models  # noqa: F401 - registers models on Base before create_all
from app.db import Base, engine
from app.routers import analyze, feedback, history, mailbox

_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="AI Phishing Detector API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(analyze.router)
app.include_router(history.router)
app.include_router(mailbox.router)
app.include_router(feedback.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/", include_in_schema=False)
def dashboard():
    """Serve the blue-team dashboard (same-origin, so its API calls need no CORS)."""
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "ok"}
