import requests
import random
import time

API_URL = "http://localhost:8000/ingest"

while True:
    data = {
        "pond_id": 1,
        "dissolved_oxygen": random.uniform(3, 8),
        "temperature": random.uniform(25, 35),
        "ammonia": random.uniform(0.1, 1.0),
        "ph": random.uniform(6.5, 8.5)
    }

    r = requests.post(API_URL, json=data)
    print(r.json())
    time.sleep(5)
