"""
main.py — the inference service that runs inside the container.

Endpoints:
  GET  /health   -> liveness probe (Container Apps / load balancers hit this)
  GET  /         -> tiny info page
  POST /predict  -> one customer  -> churn probability + risk band
  POST /predict/batch -> list of customers

Design notes:
  - The model is loaded ONCE at startup, not per request (cold start pays the
    load cost; warm requests are fast).
  - It calls the SAME engineer() used in training -> no train/serve skew.
  - No MLflow dependency at serve time: the container just loads the joblib
    artifact, keeping the image lean and cold starts shorter.
"""

from __future__ import annotations
import json
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from app.schema import Customer, Prediction
from src.features import engineer

MODEL_PATH = Path("models/churn_pipeline.joblib")
META_PATH = Path("models/model_meta.json")
INDEX_HTML = Path(__file__).parent / "templates" / "index.html"

app = FastAPI(
    title="Bank Churn Prediction API",
    description="Serverless churn scoring — XGBoost pipeline served via FastAPI.",
    version="1.0.0",
)

_model = None
_version = "unknown"


@app.on_event("startup")
def load_model() -> None:
    global _model, _version
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Model artifact missing at {MODEL_PATH}. Train first.")
    _model = joblib.load(MODEL_PATH)
    if META_PATH.exists():
        _version = json.loads(META_PATH.read_text()).get("trained_at", "unknown")


def _risk_band(p: float) -> str:
    if p >= 0.66:
        return "high"
    if p >= 0.33:
        return "medium"
    return "low"


def _score(customers: list[Customer]) -> list[Prediction]:
    raw = pd.DataFrame([c.model_dump() for c in customers])
    feats = engineer(raw)                       # identical to training
    proba = _model.predict_proba(feats)[:, 1]
    return [
        Prediction(
            churn_probability=round(float(p), 4),
            churn_prediction=int(p >= 0.5),
            risk_band=_risk_band(float(p)),
            model_version=_version,
        )
        for p in proba
    ]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": _model is not None}


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))


@app.get("/info")
def info() -> dict:
    return {
        "service": "bank-churn-api",
        "model_version": _version,
        "docs": "/docs",
    }


@app.post("/predict", response_model=Prediction)
def predict(customer: Customer) -> Prediction:
    if _model is None:
        raise HTTPException(503, "Model not loaded")
    return _score([customer])[0]


@app.post("/predict/batch", response_model=list[Prediction])
def predict_batch(customers: list[Customer]) -> list[Prediction]:
    if _model is None:
        raise HTTPException(503, "Model not loaded")
    if not customers:
        raise HTTPException(400, "Empty list")
    return _score(customers)
