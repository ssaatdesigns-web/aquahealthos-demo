from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import SensorReading, Alert
from .schemas import ReadingCreate
from .risk_engine import calculate_risk

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/ingest")
def ingest_reading(reading: ReadingCreate, db: Session = Depends(get_db)):
    db_reading = SensorReading(**reading.dict())
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)

    health_score, messages = calculate_risk(db_reading)

    for msg in messages:
        alert = Alert(
            pond_id=reading.pond_id,
            message=msg,
            severity="HIGH"
        )
        db.add(alert)
        db.commit()

    return {"health_score": health_score}

@router.get("/alerts/{pond_id}")
def get_alerts(pond_id: int, db: Session = Depends(get_db)):
    return db.query(Alert).filter(Alert.pond_id == pond_id).all()
