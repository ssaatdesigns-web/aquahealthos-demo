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
from .risk_engine import calculate_risk

app = FastAPI(title="AquaHealthOS Demo", version="1.0.0")


# =============================
# 🔥 FIXED CORS (IMPORTANT)
# =============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://aquahealthos-demo.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# =============================
# Simulation controller
# =============================
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


def _create_reading_and_alerts(db: Session, pond_id: int, do, temp, ammonia, ph, turb):
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

    return reading.id


def _sim_loop(pond_id: int, interval_sec: int, incident_mode: bool):
    while _sim_running.get(pond_id, False):

        do = 6 + random.uniform(-1, 1)
        temp = 28 + random.uniform(-2, 2)
        ammonia = 0.1 + random.uniform(0, 0.2)
        ph = 7.5 + random.uniform(-0.3, 0.3)
        turb = 10 + random.uniform(-3, 3)

        db = SessionLocal()
        try:
            _ensure_pond(db, pond_id)
            _create_reading_and_alerts(db, pond_id, do, temp, ammonia, ph, turb)
        except Exception as e:
            print("SIM ERROR:", e)
        finally:
            db.close()

        time.sleep(interval_sec)


def _start_sim(pond_id: int, interval_sec: int, incident_mode: bool):
    if _sim_running.get(pond_id):
        return False

    _sim_running[pond_id] = True
    t = threading.Thread(
        target=_sim_loop,
        args=(pond_id, interval_sec, incident_mode),
        daemon=True
    )
    t.start()
    _sim_threads[pond_id] = t
    return True


def _stop_sim(pond_id: int):
    _sim_running[pond_id] = False
    return True


def _sim_status(pond_id: int):
    return _sim_running.get(pond_id, False)


# =============================
# Startup (DB + Seed)
# =============================
@app.on_event("startup")
def startup():
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ DB connected")

        db = SessionLocal()
        try:
            if db.query(Pond).count() == 0:
                db.add_all([
                    Pond(name="Pond A", species="fish"),
                    Pond(name="Pond B", species="shrimp"),
                    Pond(name="Pond C", species="tilapia"),
                ])
                db.commit()
                print("✅ Seeded ponds")
        finally:
            db.close()

    except Exception as e:
        print("❌ DB FAILED BUT APP CONTINUES:", e)


# =============================
# Health
# =============================
@app.get("/healthz")
def healthz():
    return {"ok": True}


# =============================
# Simulation API
# =============================
@app.get("/api/v1/sim/status/{pond_id}")
def sim_status(pond_id: int):
    return {
        "pond_id": pond_id,
        "running": _sim_status(pond_id)
    }


@app.post("/api/v1/sim/start/{pond_id}")
def sim_start(pond_id: int, interval_sec: int = 5, incident_mode: bool = True):
    started = _start_sim(pond_id, interval_sec, incident_mode)
    return {
        "pond_id": pond_id,
        "running": _sim_status(pond_id),
        "started": started
    }


@app.post("/api/v1/sim/stop/{pond_id}")
def sim_stop(pond_id: int):
    stopped = _stop_sim(pond_id)
    return {
        "pond_id": pond_id,
        "running": _sim_status(pond_id),
        "stopped": stopped
    }


# =============================
# Main API routes
# =============================
app.include_router(router)
