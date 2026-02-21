from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta

from .database import SessionLocal
from .models import Pond, SensorReading, Alert
from .schemas import (
    PondOut, ReadingCreate, ReadingOut,
    AlertOut, HealthOut, TimeseriesOut, TimeseriesPoint
)
from .risk_engine import calculate_risk, status_from_health

router = APIRouter(prefix="/api/v1")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _ensure_pond(db: Session, pond_id: int) -> Pond:
    pond = db.query(Pond).filter(Pond.id == pond_id).first()
    if not pond:
        raise HTTPException(status_code=404, detail="Pond not found")
    return pond

@router.get("/ponds", response_model=list[PondOut])
def list_ponds(db: Session = Depends(get_db)):
    return db.query(Pond).order_by(Pond.id.asc()).all()

@router.post("/ingest/reading")
def ingest_reading(payload: ReadingCreate, db: Session = Depends(get_db)):
    _ensure_pond(db, payload.pond_id)

    risk = calculate_risk(
        do=payload.dissolved_oxygen,
        temp=payload.temperature,
        ammonia=payload.ammonia,
        ph=payload.ph,
    )

    reading = SensorReading(
        pond_id=payload.pond_id,
        dissolved_oxygen=payload.dissolved_oxygen,
        temperature=payload.temperature,
        ammonia=payload.ammonia,
        ph=payload.ph,
        turbidity=payload.turbidity,
        health_score=risk.health_score,
        do_risk=risk.do_risk,
        nh3_risk=risk.nh3_risk,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    # Create alerts (avoid spamming: only create if same unresolved message not present recently)
    recent_window = datetime.utcnow() - timedelta(minutes=10)
    for severity, msg in risk.messages:
        exists = (
            db.query(Alert)
            .filter(
                Alert.pond_id == payload.pond_id,
                Alert.message == msg,
                Alert.resolved == False,  # noqa: E712
                Alert.created_at >= recent_window,
            )
            .first()
        )
        if not exists:
            db.add(Alert(pond_id=payload.pond_id, message=msg, severity=severity))
            db.commit()

    return {"ok": True, "reading_id": reading.id, "health_score": reading.health_score}

@router.get("/ponds/{pond_id}/latest", response_model=ReadingOut)
def latest_reading(pond_id: int, db: Session = Depends(get_db)):
    _ensure_pond(db, pond_id)
    r = (
        db.query(SensorReading)
        .filter(SensorReading.pond_id == pond_id)
        .order_by(desc(SensorReading.created_at))
        .first()
    )
    if not r:
        raise HTTPException(status_code=404, detail="No readings yet")
    return r

@router.get("/ponds/{pond_id}/health", response_model=HealthOut)
def pond_health(pond_id: int, db: Session = Depends(get_db)):
    latest = latest_reading(pond_id, db)
    return HealthOut(
        pond_id=pond_id,
        health_score=latest.health_score,
        do_risk=latest.do_risk,
        nh3_risk=latest.nh3_risk,
        status=status_from_health(latest.health_score),
    )

@router.get("/ponds/{pond_id}/timeseries", response_model=TimeseriesOut)
def pond_timeseries(
    pond_id: int,
    range_hours: int = Query(24, ge=1, le=168),
    limit: int = Query(720, ge=10, le=2000),
    db: Session = Depends(get_db),
):
    _ensure_pond(db, pond_id)
    since = datetime.utcnow() - timedelta(hours=range_hours)

    rows = (
        db.query(SensorReading)
        .filter(SensorReading.pond_id == pond_id, SensorReading.created_at >= since)
        .order_by(SensorReading.created_at.asc())
        .limit(limit)
        .all()
    )
    points = [
        TimeseriesPoint(
            t=r.created_at,
            dissolved_oxygen=r.dissolved_oxygen,
            ammonia=r.ammonia,
            temperature=r.temperature,
            ph=r.ph,
            health_score=r.health_score,
        )
        for r in rows
    ]
    return TimeseriesOut(pond_id=pond_id, points=points)

@router.get("/ponds/{pond_id}/alerts", response_model=list[AlertOut])
def pond_alerts(
    pond_id: int,
    include_resolved: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    _ensure_pond(db, pond_id)
    q = db.query(Alert).filter(Alert.pond_id == pond_id)
    if not include_resolved:
        q = q.filter(Alert.resolved == False)  # noqa: E712
    return q.order_by(desc(Alert.created_at)).limit(limit).all()

@router.post("/alerts/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if not alert.resolved:
        alert.resolved = True
        alert.resolved_at = datetime.utcnow()
        db.commit()
        db.refresh(alert)
    return alert
