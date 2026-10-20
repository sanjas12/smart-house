import os
import random
import time
from datetime import datetime

import requests

# обход системного прокси Forefront TMG на Windows 7
os.environ["NO_PROXY"] = "127.0.0.1,localhost"

SERVER_URL = os.environ.get("SERVER_URL", "http://127.0.0.1:3000")
DEVICE_ID = os.environ.get("DEVICE_ID", "demo-sensor-01")
INTERVAL_SEC = float(os.environ.get("INTERVAL_SEC", "2"))


def read_sensor() -> float:
    return round(random.uniform(20.0, 30.0), 2)


def send_telemetry(value: float) -> None:
    url = f"{SERVER_URL}/api/telemetry"
    try:
        resp = requests.post(
            url, json={"device_id": DEVICE_ID, "value": value}, timeout=5
        )
        resp.raise_for_status()
        print(f"[{datetime.now():%H:%M:%S}] sent {value} -> {resp.status_code}")
    except requests.RequestException as exc:
        print(f"[{datetime.now():%H:%M:%S}] telemetry ERROR: {exc}")


def poll_commands() -> None:
    url = f"{SERVER_URL}/api/devices/{DEVICE_ID}/commands"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[{datetime.now():%H:%M:%S}] commands ERROR: {exc}")
        return

    for cmd in resp.json().get("commands", []):
        print(f"[{datetime.now():%H:%M:%S}] executing: {cmd['action']} {cmd.get('params')}")
        # Здесь в будущем — реальное управление устройством.
        # Пока просто подтверждаем выполнение.
        ack_url = f"{SERVER_URL}/api/commands/{cmd['id']}/ack"
        try:
            requests.post(ack_url, timeout=5).raise_for_status()
            print(f"[{datetime.now():%H:%M:%S}] ack command {cmd['id']}")
        except requests.RequestException as exc:
            print(f"[{datetime.now():%H:%M:%S}] ack ERROR: {exc}")


def main():
    print(f"Collector started. Server={SERVER_URL}, device={DEVICE_ID}")
    while True:
        send_telemetry(read_sensor())
        poll_commands()
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    main()