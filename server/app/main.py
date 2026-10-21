import os
import sqlite3
from datetime import datetime
import json
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

DB_PATH = os.environ.get("DB_PATH", "telemetry.db")

app = FastAPI()


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            value REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            action TEXT NOT NULL,
            params TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_telemetry_device_id "
        "ON telemetry (device_id, id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_telemetry_device_time "
        "ON telemetry (device_id, timestamp, id)"
    )
    conn.commit()
    conn.close()


init_db()


class TelemetryIn(BaseModel):
    device_id: str
    value: float


class CommandIn(BaseModel):
    action: str
    params: Optional[Dict[str, Any]] = None


@app.post("/api/devices/{device_id}/command")
def create_command(device_id: str, data: CommandIn):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO commands (device_id, action, params, status, created_at) "
        "VALUES (?, ?, ?, 'pending', ?)",
        (
            device_id,
            data.action,
            json.dumps(data.params) if data.params is not None else None,
            datetime.now().isoformat(),
        ),
    )
    command_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"command_id": command_id, "status": "pending"}


@app.get("/api/devices/{device_id}/commands")
def list_pending_commands(device_id: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, action, params, created_at FROM commands "
        "WHERE device_id = ? AND status = 'pending' ORDER BY id ASC",
        (device_id,),
    ).fetchall()
    conn.close()
    return {
        "device_id": device_id,
        "commands": [
            {
                "id": r[0],
                "action": r[1],
                "params": json.loads(r[2]) if r[2] else None,
                "created_at": r[3],
            }
            for r in rows
        ],
    }


@app.post("/api/commands/{command_id}/ack")
def ack_command(command_id: int):
    conn = get_conn()
    cur = conn.execute(
        "UPDATE commands SET status = 'done', completed_at = ? "
        "WHERE id = ? AND status = 'pending'",
        (datetime.now().isoformat(), command_id),
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        return {"status": "not_found_or_already_done"}
    return {"status": "ok"}


@app.post("/api/telemetry")
def receive_telemetry(data: TelemetryIn):
    conn = get_conn()
    conn.execute(
        "INSERT INTO telemetry (device_id, value, timestamp) VALUES (?, ?, ?)",
        (data.device_id, data.value, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/api/devices/{device_id}/latest")
def get_latest(device_id: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT value, timestamp FROM telemetry "
        "WHERE device_id = ? ORDER BY id DESC LIMIT 1",
        (device_id,),
    ).fetchone()
    conn.close()
    if row:
        return {"device_id": device_id, "value": row[0], "timestamp": row[1]}
    return {"error": "no data"}

@app.get("/api/devices")
def list_devices():
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT device_id FROM telemetry GROUP BY device_id ORDER BY device_id"
        ).fetchall()
        return {"devices": [row[0] for row in rows]}
    finally:
        conn.close()


@app.get("/api/devices/{device_id}/history")
def get_history(device_id: str, limit: int = Query(100, ge=1, le=500),
                offset: int = Query(0, ge=0)):
    conn = get_conn()
    try:
        # Read count and page from the same snapshot while new readings arrive.
        conn.execute("BEGIN")
        total = conn.execute(
            "SELECT COUNT(*) FROM telemetry WHERE device_id = ?", (device_id,)
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT id, value, timestamp FROM telemetry WHERE device_id = ? "
            "ORDER BY id DESC LIMIT ? OFFSET ?", (device_id, limit, offset)
        ).fetchall()
        return {"device_id": device_id, "total": total, "limit": limit,
                "offset": offset, "readings": [
                    {"id": row[0], "value": row[1], "timestamp": row[2]}
                    for row in rows]}
    finally:
        conn.close()


@app.get("/api/devices/{device_id}/history/plot")
def get_history_plot(device_id: str, start: datetime = Query(..., alias="from"),
                     end: datetime = Query(..., alias="to")):
    # Existing timestamps are local server time without a UTC offset.
    if start.tzinfo is not None or end.tzinfo is not None:
        raise HTTPException(422, "Use local server time without a timezone offset")
    if start > end:
        raise HTTPException(422, "Period start must not be after period end")
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, value, timestamp FROM telemetry "
            "WHERE device_id = ? AND timestamp >= ? AND timestamp <= ? "
            "ORDER BY timestamp, id LIMIT 50001",
            (device_id, start.isoformat(), end.isoformat()),
        ).fetchall()
        if len(rows) > 50000:
            raise HTTPException(413, "More than 50000 readings; choose a shorter period")
        return {"device_id": device_id, "readings": [
            {"id": row[0], "value": row[1], "timestamp": row[2]} for row in rows]}
    finally:
        conn.close()
