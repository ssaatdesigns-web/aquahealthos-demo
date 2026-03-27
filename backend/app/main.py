# backend/app/main.py

import os
import threading
import time
import random
import traceback

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import engine, Base, SessionLocal
from .models import Pond, SensorReading, Alert
from .routes import router
from .risk_engine import calculate_risk


# =============================
# CORS (stable)
# =============================
def _get_allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    defaults = [
        "https://aquahealthos-demo.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    if not raw:
        return defaults
    extra = [x.strip() for x in raw.split(",") if x.strip()]
    return list(dict.fromkeys(defaults + extra))


# =============================
# Simulation controller
# =============================
_sim_running: dict[int, bool] = {}
_sim_threads: dict[int, threading.Thread] = {}
_sim_lock = threading.Lock()


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _ensure_pond(db: Session, pond_id: int) -> Pond:
    """Raises ValueError (not HTTPException) — safe to call from background threads."""
    pond = db.query(Pond).filter(Pond.id == pond_id).first()
    if not pond:
        raise ValueError(f"Pond {pond_id} not found")
    return pond


def _create_reading_and_alerts(
    db: Session,
    pond_id: int,
    do: float,
    temp: float,
    ammonia: float,
    ph: float,
    turb: float,
) -> int:
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

    for severity, msg in getattr(risk, "messages", []):
        db.add(Alert(pond_id=pond_id, message=msg, severity=severity))
    db.commit()

    return reading.id


def _sim_loop(pond_id: int, interval_sec: int, incident_mode: bool) -> None:
    print(f"🚀 Simulator started for pond {pond_id}")

    while True:
        with _sim_lock:
            if not _sim_running.get(pond_id, False):
                print(f"🛑 Simulator stopped for pond {pond_id}")
                break

        if incident_mode:
            do = _clamp(5.5 + random.uniform(-1.5, 0.4), 0.5, 12.0)
            temp = _clamp(29.0 + random.uniform(-2.0, 2.5), 10.0, 40.0)
            ammonia = _clamp(0.25 + random.uniform(0.0, 0.35), 0.0, 2.0)
            ph = _clamp(7.6 + random.uniform(-0.5, 0.5), 6.0, 9.5)
            turb = _clamp(14.0 + random.uniform(-4.0, 8.0), 0.0, 200.0)
        else:
            do = _clamp(6.5 + random.uniform(-1.0, 1.0), 0.5, 12.0)
            temp = _clamp(28.0 + random.uniform(-2.0, 2.0), 10.0, 40.0)
            ammonia = _clamp(0.1 + random.uniform(0.0, 0.2), 0.0, 2.0)
            ph = _clamp(7.5 + random.uniform(-0.3, 0.3), 6.0, 9.5)
            turb = _clamp(10.0 + random.uniform(-3.0, 3.0), 0.0, 200.0)

        print(f"📊 Simulating pond {pond_id}")
        print("➡️ Values:", do, temp, ammonia, ph, turb)

        db = SessionLocal()
        try:
            _ensure_pond(db, pond_id)
            print("💾 Inserting reading...")
            _create_reading_and_alerts(db, pond_id, do, temp, ammonia, ph, turb)
            print("✅ Insert success")
        except Exception as e:
            print("❌ SIM ERROR:", e)
            traceback.print_exc()
        finally:
            db.close()

        time.sleep(max(1, interval_sec))


def _start_sim(pond_id: int, interval_sec: int, incident_mode: bool) -> bool:
    with _sim_lock:
        if _sim_running.get(pond_id, False):
            return False

        _sim_running[pond_id] = True
        t = threading.Thread(
            target=_sim_loop,
            args=(pond_id, interval_sec, incident_mode),
            daemon=True,
        )
        _sim_threads[pond_id] = t
        t.start()
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


# =============================
# Lifespan (replaces deprecated @app.on_event)
# =============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting AquaHealthOS backend...")
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
            else:
                print("✅ Ponds already exist")
        finally:
            db.close()

    except Exception as e:
        print("❌ DB ERROR:", e)
        print("⚠️ App will continue without DB seeding")

    yield  # App runs here


app = FastAPI(title="AquaHealthOS Demo", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================
# Basic routes
# =============================
@app.get("/")
def root():
    return {"status": "running"}


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
        "running": _sim_status(pond_id),
    }


@app.post("/api/v1/sim/start/{pond_id}")
def sim_start(pond_id: int, interval_sec: int = 5, incident_mode: bool = True):
    started = _start_sim(pond_id, interval_sec, incident_mode)
    return {
        "pond_id": pond_id,
        "running": _sim_status(pond_id),
        "started": started,
    }


@app.post("/api/v1/sim/stop/{pond_id}")
def sim_stop(pond_id: int):
    stopped = _stop_sim(pond_id)
    return {
        "pond_id": pond_id,
        "running": _sim_status(pond_id),
        "stopped": stopped,
    }


# =============================
# Main API routes
# =============================
app.include_router(router)
