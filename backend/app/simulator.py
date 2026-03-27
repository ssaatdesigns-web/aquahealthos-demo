# backend/app/simulator.py
# NOTE: This legacy file is NOT used by main.py.
# Simulation is handled directly in main.py via _sim_loop / _start_sim / _stop_sim.
# Kept here only as reference; fixed the broken import so it doesn't cause
# any future import-time crashes.

import random
import threading
import time
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import SensorReading   # ← was wrongly "Reading" (model doesn't exist)
from datetime import datetime

running_simulations = {}
lock = threading.Lock()


def generate_reading(pond_id: int):
    return {
        "pond_id": pond_id,
        "temperature": round(random.uniform(24, 34), 2),
        "ph": round(random.uniform(6.5, 9.0), 2),
        "dissolved_oxygen": round(random.uniform(3.0, 8.0), 2),
        "ammonia": round(random.uniform(0.05, 0.5), 3),
        "turbidity": round(random.uniform(5.0, 20.0), 2),
    }


def simulation_loop(pond_id: int):
    db: Session = SessionLocal()
    while running_simulations.get(pond_id, False):
        data = generate_reading(pond_id)
        reading = SensorReading(**data)
        db.add(reading)
        db.commit()
        time.sleep(5)
    db.close()


def start_simulation(pond_id: int):
    with lock:
        if running_simulations.get(pond_id):
            return False
        running_simulations[pond_id] = True
        thread = threading.Thread(target=simulation_loop, args=(pond_id,))
        thread.daemon = True
        thread.start()
        return True


def stop_simulation(pond_id: int):
    with lock:
        running_simulations[pond_id] = False
        return True


def is_running(pond_id: int):
    return running_simulations.get(pond_id, False)
