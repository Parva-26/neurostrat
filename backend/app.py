"""
app.py
──────
NeuroStrat FastAPI Backend

Serves two primary routes consumed by the NeuroStrat frontend:
  POST /api/strategy   →  Runs ML pipeline, returns strategy card
  GET  /api/history    →  Returns recent outreach decisions

Additional utility routes:
  GET  /api/health     →  Liveness check
  GET  /api/stats      →  Aggregate stats (Profile page)
  GET  /api/decision/{id}  →  Full detail for one record

Architecture
────────────
  Frontend (Vite / React)
       │
       │  HTTP  (CORS allowed on localhost:5173 / 3000 / 8080)
       ▼
  FastAPI  (this file)
       │
       ├── signal_extractor.py   free-text → ML features
       ├── response_builder.py   ML output → frontend JSON
       ├── history_store.py      SQLite persistence
       │
       └── ../outreach_engine/   ML model (inference.py)
               └── models/       serialised .joblib artefacts

Run
───
  pip install -r requirements.txt
  uvicorn app:app --reload --port 8000

Or with auto-reload watching both backend + engine:
  uvicorn app:app --reload --reload-dir . --reload-dir ../outreach_engine --port 8000
"""

import sys
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── Path setup: allow importing from ../outreach_engine ───────────────────────
ENGINE_DIR = Path(__file__).resolve().parent.parent / "ml"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from inference       import OutreachDecisionEngine     # noqa: E402
from signal_extractor import extract_signals           # noqa: E402
from response_builder import build_strategy_response   # noqa: E402
from history_store    import init_db, save_decision, get_history, \
                             get_decision_by_id, get_stats  # noqa: E402

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("neurostrat")

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="NeuroStrat API",
    description="AI Outreach Decision Engine — backend for the NeuroStrat frontend",
    version="1.0.0",
    docs_url="/docs",       # Swagger UI at http://localhost:8000/docs
    redoc_url="/redoc",
)

# CORS — allow the Vite dev server and common local ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite default
        "http://localhost:3000",   # CRA / older setups
        "http://localhost:8080",   # alternative
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ML engine: load once at startup ──────────────────────────────────────────
engine: Optional[OutreachDecisionEngine] = None


@app.on_event("startup")
def startup() -> None:
    global engine
    log.info("Initialising database ...")
    init_db()
    log.info("Loading ML models ...")
    try:
        engine = OutreachDecisionEngine()
        log.info("ML models loaded ✓")
    except Exception as exc:
        log.error(f"Failed to load ML models: {exc}")
        log.error("Make sure models/ exist inside outreach_engine/. Run train_evaluate.py first.")
        raise RuntimeError("Model load failed") from exc


# ── Request / Response schemas ────────────────────────────────────────────────

class StrategyRequest(BaseModel):
    """
    Mirrors the form payload sent by ScenarioForm.tsx:
      onGenerate({ name, role, context })
    """
    name:    str = Field(..., min_length=1, max_length=200,
                         description="Contact's full name")
    role:    str = Field(..., min_length=1, max_length=200,
                         description="Contact's job title or role")
    context: str = Field(default="", max_length=2000,
                         description="Scenario context, prior interactions, goals")


class StrategyResponse(BaseModel):
    """
    Mirrors what StrategyCard.tsx expects:
      { channel, confidence, contactName, factors[] }
    The _meta field is bonus data the frontend safely ignores.
    """
    channel:     str
    confidence:  int
    contactName: str
    factors:     list[str]
    _meta:       dict = {}      # raw ML scores — useful for debugging


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["Utility"])
def health():
    """Liveness check — returns 200 when the server and models are ready."""
    model_ok = engine is not None
    return {
        "status":   "ok" if model_ok else "degraded",
        "model_loaded": model_ok,
    }


@app.post("/api/strategy", response_model=StrategyResponse, tags=["Core"])
def generate_strategy(body: StrategyRequest):
    """
    Main endpoint consumed by Index.tsx → handleGenerate().

    Pipeline:
      1. Extract ML features from free-text {name, role, context}
      2. Run OutreachDecisionEngine.predict()
      3. Translate ML output → frontend JSON shape
      4. Persist to SQLite history
    """
    if engine is None:
        raise HTTPException(503, "ML model not loaded — check server logs")

    log.info(f"Strategy request: name='{body.name}' role='{body.role}'")

    # ── Step 1: Signal extraction ─────────────────────────────────────────────
    extracted  = extract_signals(body.name, body.role, body.context)
    features   = extracted["features"]
    signal_log = extracted["signal_log"]

    log.info(
        f"  Extracted → role={features['role']} industry={features['industry']} "
        f"company={features['company_size']} eng={features['engagement_score']:.2f} "
        f"li={features['linkedin_active']:.2f} sentiment={features['news_sentiment']:+.2f}"
    )

    # ── Step 2: ML prediction ─────────────────────────────────────────────────
    try:
        ml_card = engine.predict(features)
    except Exception as exc:
        log.error(f"ML prediction failed: {exc}")
        raise HTTPException(500, f"Prediction error: {exc}")

    log.info(
        f"  Predicted → channel='{ml_card['channel']}' ({ml_card['channel_confidence']:.0%}) "
        f"tone='{ml_card['tone']}' ({ml_card['tone_confidence']:.0%})"
    )

    # ── Step 3: Build response ────────────────────────────────────────────────
    response = build_strategy_response(
        contact_name=body.name,
        ml_card=ml_card,
        signal_log=signal_log,
    )

    # ── Step 4: Persist ───────────────────────────────────────────────────────
    try:
        record_id = save_decision(body.name, body.role, body.context, response)
        log.info(f"  Saved to history (id={record_id})")
    except Exception as exc:
        log.warning(f"  History save failed (non-fatal): {exc}")

    return response


@app.get("/api/history", tags=["History"])
def list_history(
    limit:  int = Query(default=50,  ge=1,  le=200, description="Max records to return"),
    offset: int = Query(default=0,   ge=0,           description="Pagination offset"),
):
    """
    Consumed by History.tsx.
    Returns HistoryItem[] matching the frontend interface exactly.
    """
    items = get_history(limit=limit, offset=offset)
    log.info(f"History requested — returning {len(items)} items")
    return items


@app.get("/api/decision/{decision_id}", tags=["History"])
def get_decision(decision_id: int):
    """
    Full detail view for a single past decision.
    (Useful for a future detail/expand interaction on history cards.)
    """
    record = get_decision_by_id(decision_id)
    if not record:
        raise HTTPException(404, f"Decision {decision_id} not found")
    return record


@app.get("/api/stats", tags=["Utility"])
def get_summary_stats():
    """
    Aggregate statistics — suitable for the Profile or Settings pages.
    Returns total decisions, average confidence, and channel distribution.
    """
    return get_stats()
