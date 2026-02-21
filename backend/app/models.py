from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Pond(Base):
    __tablename__ = "ponds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    species = Column(String, nullable=False, default="fish")

    readings = relationship("SensorReading", back_populates="pond", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="pond", cascade="all, delete-orphan")

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True)
    pond_id = Column(Integer, ForeignKey("ponds.id"), nullable=False, index=True)

    dissolved_oxygen = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    ammonia = Column(Float, nullable=False)
    ph = Column(Float, nullable=False)
    turbidity = Column(Float, nullable=False, default=0.0)

    health_score = Column(Float, nullable=False, default=100.0)
    do_risk = Column(Float, nullable=False, default=0.0)
    nh3_risk = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    pond = relationship("Pond", back_populates="readings")

Index("idx_sensor_readings_pond_time", SensorReading.pond_id, SensorReading.created_at)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    pond_id = Column(Integer, ForeignKey("ponds.id"), nullable=False, index=True)

    message = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # LOW | MEDIUM | HIGH
    resolved = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)

    pond = relationship("Pond", back_populates="alerts")
