from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc

from .models import SensorReading
from .risk_engine import calculate_risk, status_from_health


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _linreg_slope(xs: List[float], ys: List[float]) -> float:
    """
    Simple linear regression slope (y = a + b*x) => returns b.
    No external deps.
    """
    n = len(xs)
    if n < 2:
        return 0.0
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    den = sum((x - x_mean) ** 2 for x in xs)
    if den == 0:
        return 0.0
    return num / den


def build_forecast(
    db: Session,
    pond_id: int,
    hours: int = 24,
    step_minutes: int = 60,
    lookback_hours: int = 6,
    max_points: int = 360,
) -> Dict[str, Any]:
    """
    Forecast next N hours based on recent trend.
    - Uses last lookback_hours readings (or max_points) to estimate slopes
    - Projects DO and ammonia; keeps temp/pH near recent mean with small drift
    - Converts forecasted values to health_score using your existing risk engine
    """
    now = datetime.utcnow()
    since = now - timedelta(hours=lookback_hours)

    rows = (
        db.query(SensorReading)
        .filter(SensorReading.pond_id == pond_id, SensorReading.created_at >= since)
        .order_by(desc(SensorReading.created_at))
        .limit(max_points)
        .all()
    )

    if not rows:
        return {
            "pond_id": pond_id,
            "generated_at": now.isoformat(),
            "hours": hours,
            "step_minutes": step_minutes,
            "points": [],
            "summary": {
                "message": "No readings available yet. Start simulation to generate forecast.",
                "critical_hours": 0,
                "watch_hours": 0,
                "good_hours": 0,
            },
        }

    # Reverse to oldest->newest
    rows = list(reversed(rows))

    # Build x in minutes from first timestamp
    t0 = rows[0].created_at
    xs = [(r.created_at - t0).total_seconds() / 60.0 for r in rows]

    do_ys = [r.dissolved_oxygen for r in rows]
    nh3_ys = [r.ammonia for r in rows]
    temp_ys = [r.temperature for r in rows]
    ph_ys = [r.ph for r in rows]

    # Estimate slopes per minute
    do_slope = _linreg_slope(xs, do_ys)          # mg/L per minute
    nh3_slope = _linreg_slope(xs, nh3_ys)        # mg/L per minute
    temp_slope = _linreg_slope(xs, temp_ys)      # °C per minute
    ph_slope = _linreg_slope(xs, ph_ys)          # per minute

    # Use last known value as baseline
    last = rows[-1]
    base_do = float(last.dissolved_oxygen)
    base_nh3 = float(last.ammonia)
    base_temp = float(last.temperature)
    base_ph = float(last.ph)

    # Slightly dampen slopes for stability (demo-friendly)
    do_slope *= 0.7
    nh3_slope *= 0.7
    temp_slope *= 0.3
    ph_slope *= 0.2

    # Forecast points
    steps = int((hours * 60) / step_minutes)
    points: List[Dict[str, Any]] = []

    critical_hours = 0
    watch_hours = 0
    good_hours = 0

    for i in range(1, steps + 1):
        minutes_ahead = i * step_minutes
        t = now + timedelta(minutes=minutes_ahead)

        pred_do = base_do + do_slope * minutes_ahead
        pred_nh3 = base_nh3 + nh3_slope * minutes_ahead
        pred_temp = base_temp + temp_slope * minutes_ahead
        pred_ph = base_ph + ph_slope * minutes_ahead

        # Plausibility clamps
        pred_do = _clamp(pred_do, 0.2, 12.0)
        pred_nh3 = _clamp(pred_nh3, 0.0, 3.0)
        pred_temp = _clamp(pred_temp, 10.0, 40.0)
        pred_ph = _clamp(pred_ph, 6.0, 9.5)

        risk = calculate_risk(do=pred_do, temp=pred_temp, ammonia=pred_nh3, ph=pred_ph)
        status = status_from_health(risk.health_score)

        if status == "CRITICAL":
            critical_hours += step_minutes / 60
        elif status == "WATCH":
            watch_hours += step_minutes / 60
        else:
            good_hours += step_minutes / 60

        points.append(
            {
                "t": t.isoformat(),
                "dissolved_oxygen": round(pred_do, 3),
                "ammonia": round(pred_nh3, 4),
                "temperature": round(pred_temp, 2),
                "ph": round(pred_ph, 2),
                "health_score": round(risk.health_score, 2),
                "do_risk": round(risk.do_risk, 2),
                "nh3_risk": round(risk.nh3_risk, 2),
                "status": status,
            }
        )

    # Round summary hours to 1 decimal
    summary = {
        "critical_hours": round(critical_hours, 1),
        "watch_hours": round(watch_hours, 1),
        "good_hours": round(good_hours, 1),
        "do_slope_per_hour": round(do_slope * 60.0, 4),
        "nh3_slope_per_hour": round(nh3_slope * 60.0, 5),
        "temp_slope_per_hour": round(temp_slope * 60.0, 4),
        "ph_slope_per_hour": round(ph_slope * 60.0, 5),
    }

    return {
        "pond_id": pond_id,
        "generated_at": now.isoformat(),
        "hours": hours,
        "step_minutes": step_minutes,
        "points": points,
        "summary": summary,
    }
