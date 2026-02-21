import os
import time
import random
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
POND_ID = int(os.getenv("POND_ID", "1"))
INTERVAL = int(os.getenv("INTERVAL_SEC", "5"))
INCIDENT_MODE = os.getenv("INCIDENT_MODE", "1") == "1"

INGEST_URL = f"{API_BASE}/api/v1/ingest/reading"

do_base = 6.8
am_base = 0.15

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

t = 0
while True:
    t += 1

    # Scripted incident: DO gradually drops, ammonia slowly rises
    if INCIDENT_MODE:
        do = do_base - (t * 0.03) + random.uniform(-0.15, 0.15)
        ammonia = am_base + (t * 0.003) + random.uniform(-0.02, 0.02)
    else:
        do = do_base + random.uniform(-0.4, 0.4)
        ammonia = am_base + random.uniform(-0.05, 0.05)

    temp = 29.0 + random.uniform(-1.2, 1.2)
    ph = 7.6 + random.uniform(-0.25, 0.25)
    turbidity = 12.0 + random.uniform(-3.0, 3.0)

    payload = {
        "pond_id": POND_ID,
        "dissolved_oxygen": clamp(do, 0.5, 12.0),
        "temperature": clamp(temp, 10.0, 40.0),
        "ammonia": clamp(ammonia, 0.0, 2.0),
        "ph": clamp(ph, 6.0, 9.5),
        "turbidity": clamp(turbidity, 0.0, 200.0),
    }

    try:
        r = requests.post(INGEST_URL, json=payload, timeout=10)
        print("ingest:", r.status_code, r.json())
    except Exception as e:
        print("ingest error:", e)

    time.sleep(INTERVAL)
