from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import sqlite3

app = FastAPI()

# Инициализация базы данных (только для демонстрации, в дальнейшем заменить на SQLAlchemy)
def init_db():
    conn = sqlite3.connect("telemetry.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            value REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

class TelemetryIn(BaseModel):
    device_id: str
    value: float

@app.post("/api/telemetry")
def receive_telemetry(data: TelemetryIn):
    conn = sqlite3.connect("telemetry.db")
    conn.execute(
        "INSERT INTO telemetry (device_id, value, timestamp) VALUES (?, ?, ?)",
        (data.device_id, data.value, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/devices/{device_id}/latest")
def get_latest(device_id: str):
    conn = sqlite3.connect("telemetry.db")
    row = conn.execute(
        "SELECT value, timestamp FROM telemetry WHERE device_id = ? ORDER BY id DESC LIMIT 1",
        (device_id,)
    ).fetchone()
    conn.close()
    if row:
        return {"device_id": device_id, "value": row[0], "timestamp": row[1]}
    return {"error": "no data"}