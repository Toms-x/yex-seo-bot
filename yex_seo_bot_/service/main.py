"""
YEX SEO Bot - Intelligence Microservice

Exposes the Claude interpretation layer and dedup state as HTTP endpoints
so n8n workflows can call them instead of running Python cron jobs directly.

n8n handles: scheduling, fetching (RSS/HTTP), Telegram delivery.
This service handles: dedup logic, Claude interpretation, digest synthesis.

Run with: uvicorn service.main:app --host 0.0.0.0 --port 8000
"""
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.state import (
    init_db, is_seen, mark_seen, log_alert, get_recent_alerts,
    record_price, get_price_baseline, cleanup_old_items,
)
from modules.intelligence import interpret_signal, synthesize_digest

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("service")

app = FastAPI(title="YEX SEO Bot Intelligence Service")


@app.on_event("startup")
def startup():
    init_db()
    log.info("Intelligence service started, DB initialized")


# ============================================================
# Schemas
# ============================================================

class DedupCheckRequest(BaseModel):
    source: str
    identifier: str


class DedupMarkRequest(BaseModel):
    source: str
    identifier: str
    title: str = ""
    url: str = ""


class InterpretRequest(BaseModel):
    signal_type: str
    raw_data: dict[str, Any]


class DigestRequest(BaseModel):
    alerts: list[dict]
    performance: Optional[dict] = None


class LogAlertRequest(BaseModel):
    module: str
    priority: str
    title: str


class PriceRecordRequest(BaseModel):
    coin_id: str
    price: float
    volume: float


class PriceBaselineRequest(BaseModel):
    coin_id: str
    days: int = 7


# ============================================================
# Dedup endpoints - n8n calls these before processing an item
# ============================================================

@app.post("/dedup/check")
def dedup_check(req: DedupCheckRequest):
    """Returns {"seen": true/false}. If seen=true, n8n's IF node should
    stop the workflow branch (skip this item, already alerted on)."""
    return {"seen": is_seen(req.source, req.identifier)}


@app.post("/dedup/mark")
def dedup_mark(req: DedupMarkRequest):
    """Call after deciding to process an item, so it's not re-alerted."""
    mark_seen(req.source, req.identifier, req.title, req.url)
    return {"status": "marked"}


# ============================================================
# Price history - for market anomaly baseline comparison
# ============================================================

@app.post("/price/record")
def price_record(req: PriceRecordRequest):
    record_price(req.coin_id, req.price, req.volume)
    return {"status": "recorded"}


@app.post("/price/baseline")
def price_baseline(req: PriceBaselineRequest):
    avg_price, avg_volume = get_price_baseline(req.coin_id, req.days)
    return {"avg_price": avg_price, "avg_volume": avg_volume}


# ============================================================
# Core intelligence - the whole reason this service exists
# ============================================================

@app.post("/interpret")
def interpret(req: InterpretRequest):
    """
    The main endpoint. n8n sends raw signal data, gets back a verdict:
    {
        "skip": bool,
        "priority": "URGENT|OPPORTUNITY|MONITOR|INSIGHT",
        "title": str,
        "summary": str,
        "angle": str
    }
    n8n's IF node checks "skip" to decide whether to send the Telegram alert.
    """
    try:
        verdict = interpret_signal(req.signal_type, req.raw_data)
        return verdict
    except Exception as e:
        log.error("Interpretation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/digest")
def digest(req: DigestRequest):
    """Called once daily by n8n's cron-triggered digest workflow."""
    try:
        text = synthesize_digest(req.alerts, req.performance)
        return {"text": text}
    except Exception as e:
        log.error("Digest synthesis failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Alert logging - so daily digest can pull history
# ============================================================

@app.post("/alerts/log")
def alerts_log(req: LogAlertRequest):
    log_alert(req.module, req.priority, req.title)
    return {"status": "logged"}


@app.get("/alerts/recent")
def alerts_recent(hours: int = 24):
    return {"alerts": get_recent_alerts(hours)}


# ============================================================
# Maintenance
# ============================================================

@app.post("/maintenance/cleanup")
def maintenance_cleanup(days: int = 30):
    cleanup_old_items(days)
    return {"status": "cleaned"}


@app.get("/health")
def health():
    return {"status": "ok"}
