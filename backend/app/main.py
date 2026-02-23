# backend/app/main.py
import os
import threading
import time
import random
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import engine, Base, SessionLocal
from .models import Pond, SensorReading, Alert
from .routes import router
from .risk_engine import calculate_risk, status_from_health

app = FastAPI(title="AquaHealthOS Demo", version="1.0.0")


def _parse_origins(raw: str) -> list[str]:
    if not raw:
        return ["*"]
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts or ["*"]


origins = _parse_origins(os.getenv("CORS_ORIGINS", ""))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Simulation controller (multi-pond)
# -----------------------------
_sim_running: dict[int, bool] = {}
_sim_threads: dict[int, threading.Thread] = {}
_sim_lock = threading.Lock()


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _ensure_pond(db: Session, pond_id: int) -> Pond:
    pond = db.query(Pond).filter(Pond.id == pond_id).first()
    if not pond:
        raise HTTPException(status_code=404, detail="Pond not found")
    return pond


def _create_reading_and_alerts(db: Session, pond_id: int, do: float, temp: float, ammonia: float, ph: float, turb: float):
    risk = calculate_risk(do=do, temp=temp, ammonia=ammonia, ph=ph)

    reading = SensorReading(
        pond_id=pond_id,
        dissolved_oxygen=do,
        temperature=temp,
        ammonia=ammonia,
        ph=ph,
        turbidity=turb,
        health_score=risk.health_score,
        do_risk=risk.do_risk,
        nh3_risk=risk.nh3_risk,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    # de-spam: same unresolved message within last 10 minutes
    recent_window = datetime.utcnow() - timedelta(minutes=10)
    for severity, msg in risk.messages:
        exists = (
            db.query(Alert)
            .filter(
                Alert.pond_id == pond_id,
                Alert.message == msg,
                Alert.resolved == False,  # noqa: E712
                Alert.created_at >= recent_window,
            )
            .first()
        )
        if not exists:
            db.add(Alert(pond_id=pond_id, message=msg, severity=severity))
            db.commit()

    return reading.id


def _sim_loop(pond_id: int, interval_sec: int, incident_mode: bool):
    """
    incident_mode:
      - gradually drops DO
      - slowly rises ammonia
    """
    t = 0
    do_base = 6.8
    am_base = 0.15

    while True:
        with _sim_lock:
            if not _sim_running.get(pond_id, False):
                break

        t += 1

        if incident_mode:
            do = do_base - (t * 0.03) + random.uniform(-0.15, 0.15)
            ammonia = am_base + (t * 0.003) + random.uniform(-0.02, 0.02)
        else:
            do = do_base + random.uniform(-0.4, 0.4)
            ammonia = am_base + random.uniform(-0.05, 0.05)

        temp = 29.0 + random.uniform(-1.2, 1.2)
        ph = 7.6 + random.uniform(-0.25, 0.25)
        turb = 12.0 + random.uniform(-3.0, 3.0)

        do = _clamp(do, 0.5, 12.0)
        ammonia = _clamp(ammonia, 0.0, 2.0)
        temp = _clamp(temp, 10.0, 40.0)
        ph = _clamp(ph, 6.0, 9.5)
        turb = _clamp(turb, 0.0, 200.0)

        db = SessionLocal()
        try:
            _ensure_pond(db, pond_id)
            _create_reading_and_alerts(db, pond_id, do, temp, ammonia, ph, turb)
        finally:
            db.close()

        time.sleep(max(1, int(interval_sec)))


def _start_sim(pond_id: int, interval_sec: int, incident_mode: bool) -> bool:
    with _sim_lock:
        if _sim_running.get(pond_id, False):
            return False
        _sim_running[pond_id] = True

        th = threading.Thread(target=_sim_loop, args=(pond_id, interval_sec, incident_mode), daemon=True)
        _sim_threads[pond_id] = th
        th.start()
        return True


def _stop_sim(pond_id: int) -> bool:
    with _sim_lock:
        if not _sim_running.get(pond_id, False):
            return False
        _sim_running[pond_id] = False
        return True


def _sim_status(pond_id: int) -> bool:
    with _sim_lock:
        return bool(_sim_running.get(pond_id, False))


# -----------------------------
# App lifecycle
# -----------------------------
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

    # Seed ponds if empty
    db = SessionLocal()
    try:
        if db.query(Pond).count() == 0:
            db.add_all([
                Pond(name="Pond A", species="fish"),
                Pond(name="Pond B", species="shrimp"),
                Pond(name="Pond C", species="tilapia"),
            ])
            db.commit()
    finally:
        db.close()


@app.get("/healthz")
def healthz():
    return {"ok": True}


# -----------------------------
# Simulation API (frontend toggle)
# -----------------------------
@app.get("/api/v1/sim/status/{pond_id}")
def sim_status(pond_id: int):
    return {"pond_id": pond_id, "running": _sim_status(pond_id)}


@app.post("/api/v1/sim/start/{pond_id}")
def sim_start(pond_id: int, interval_sec: int = 5, incident_mode: bool = True):
    db = SessionLocal()
    try:
        _ensure_pond(db, pond_id)
    finally:
        db.close()

    started = _start_sim(pond_id, interval_sec=interval_sec, incident_mode=incident_mode)
    return {"pond_id": pond_id, "running": _sim_status(pond_id), "started": started}


@app.post("/api/v1/sim/stop/{pond_id}")
def sim_stop(pond_id: int):
    stopped = _stop_sim(pond_id)
    return {"pond_id": pond_id, "running": _sim_status(pond_id), "stopped": stopped}


# Main API
app.include_router(router)
