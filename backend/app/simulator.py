import random
import threading
import time
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Reading
from datetime import datetime

running_simulations = {}
lock = threading.Lock()


def generate_reading(pond_id: int):
    return {
        "pond_id": pond_id,
        "temperature": round(random.uniform(24, 34), 2),
        "ph": round(random.uniform(6.5, 9.0), 2),
        "dissolved_oxygen": round(random.uniform(3.0, 8.0), 2),
        "timestamp": datetime.utcnow(),
    }


def simulation_loop(pond_id: int):
    db: Session = SessionLocal()
    while running_simulations.get(pond_id, False):
        data = generate_reading(pond_id)

        reading = Reading(**data)
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
