from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .database import get_db
from .models import Pond, SensorReading, Alert
from .risk_engine import calculate_risk, status_from_health
from .forecast import build_forecast

router = APIRouter(prefix="/api/v1", tags=["AquaHealth"])


# -----------------------------------
# Utility
# -----------------------------------

def _ensure_pond(db: Session, pond_id: int) -> Pond:
    pond = db.query(Pond).filter(Pond.id == pond_id).first()
    if not pond:
        raise HTTPException(status_code=404, detail="Pond not found")
    return pond


# -----------------------------------
# Ponds
# -----------------------------------

@router.get("/ponds", response_model=List[dict])
def list_ponds(db: Session = Depends(get_db)):
    ponds = db.query(Pond).all()
    return [
        {"id": p.id, "name": p.name, "species": p.species}
        for p in ponds
    ]


# -----------------------------------
# Latest Reading
# -----------------------------------

@router.get("/ponds/{pond_id}/latest")
def get_latest_reading(pond_id: int, db: Session = Depends(get_db)):
    _ensure_pond(db, pond_id)

    reading = (
        db.query(SensorReading)
        .filter(SensorReading.pond_id == pond_id)
        .order_by(desc(SensorReading.created_at))
        .first()
    )

    if not reading:
        return None

    return {
        "id": reading.id,
        "pond_id": reading.pond_id,
        "dissolved_oxygen": reading.dissolved_oxygen,
        "temperature": reading.temperature,
        "ammonia": reading.ammonia,
        "ph": reading.ph,
        "turbidity": reading.turbidity,
        "health_score": reading.health_score,
        "do_risk": reading.do_risk,
        "nh3_risk": reading.nh3_risk,
        "status": status_from_health(reading.health_score),
        "created_at": reading.created_at,
    }


# -----------------------------------
# Alerts
# -----------------------------------

@router.get("/ponds/{pond_id}/alerts")
def get_alerts(
    pond_id: int,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _ensure_pond(db, pond_id)

    alerts = (
        db.query(Alert)
        .filter(Alert.pond_id == pond_id)
        .order_by(desc(Alert.created_at))
        .limit(limit)
        .all()
    )

    return [
        {
            "id": a.id,
            "pond_id": a.pond_id,
            "message": a.message,
            "severity": a.severity,
            "resolved": a.resolved,
            "created_at": a.created_at,
        }
        for a in alerts
    ]


# -----------------------------------
# Ingest Sensor Reading (Simulator / Manual)
# -----------------------------------

@router.post("/ponds/{pond_id}/ingest")
def ingest_reading(
    pond_id: int,
    dissolved_oxygen: float,
    temperature: float,
    ammonia: float,
    ph: float,
    turbidity: float,
    db: Session = Depends(get_db),
):
    _ensure_pond(db, pond_id)

    risk = calculate_risk(
        do=dissolved_oxygen,
        temp=temperature,
        ammonia=ammonia,
        ph=ph,
    )

    reading = SensorReading(
        pond_id=pond_id,
        dissolved_oxygen=dissolved_oxygen,
        temperature=temperature,
        ammonia=ammonia,
        ph=ph,
        turbidity=turbidity,
        health_score=risk.health_score,
        do_risk=risk.do_risk,
        nh3_risk=risk.nh3_risk,
    )

    db.add(reading)
    db.commit()
    db.refresh(reading)

    # Create alerts if needed
    for severity, msg in risk.messages:
        alert = Alert(
            pond_id=pond_id,
            message=msg,
            severity=severity,
        )
        db.add(alert)
        db.commit()

    return {
        "message": "Reading ingested",
        "health_score": reading.health_score,
        "status": status_from_health(reading.health_score),
    }


# -----------------------------------
# AI Forecast (Next 24h Risk Prediction)
# -----------------------------------

@router.get("/ponds/{pond_id}/forecast")
def pond_forecast(
    pond_id: int,
    hours: int = Query(24, ge=1, le=72),
    step_minutes: int = Query(60, ge=5, le=240),
    db: Session = Depends(get_db),
):
    """
    Returns next N hours forecast based on recent trends.
    Uses linear regression slope from last readings.
    """
    _ensure_pond(db, pond_id)

    forecast_data = build_forecast(
        db=db,
        pond_id=pond_id,
        hours=hours,
        step_minutes=step_minutes,
    )

    return forecast_data
