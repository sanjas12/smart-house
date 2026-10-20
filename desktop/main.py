import os
import random
import time
from datetime import datetime

import requests

os.environ['NO_PROXY'] = '127.0.0.1,localhost'

SERVER_URL = os.environ.get("SERVER_URL", "http://127.0.0.1:3000")
DEVICE_ID = os.environ.get("DEVICE_ID", "demo-sensor-01")
INTERVAL_SEC = float(os.environ.get("INTERVAL_SEC", "2"))

def read_sensor():
    """Заглушка вместо реального опроса устройства."""
    return round(random.uniform(20.0, 30.0), 2)

def send_telemetry(value: float) -> None:
    url = f"{SERVER_URL}/api/telemetry"
    payload = {"device_id": DEVICE_ID, "value": value}
    try:
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
        print(f"[{datetime.now():%H:%M:%S}] sent {value} -> {resp.status_code}")
    except requests.RequestException as exc:
        print(f"[{datetime.now():%H:%M:%S}] ERROR: {exc}")

def main():
    print(f"Collector started. Server={SERVER_URL}, device={DEVICE_ID}")
    while True:
        value = read_sensor()
        send_telemetry(value)
        time.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    main()