def test_post_telemetry_returns_ok(client):
    resp = client.post(
        "/api/telemetry",
        json={"device_id": "sensor-1", "value": 42.5},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_latest_returns_last_value(client):
    client.post("/api/telemetry", json={"device_id": "sensor-1", "value": 10.0})
    client.post("/api/telemetry", json={"device_id": "sensor-1", "value": 20.0})
    client.post("/api/telemetry", json={"device_id": "sensor-2", "value": 99.9})

    resp = client.get("/api/devices/sensor-1/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["device_id"] == "sensor-1"
    assert body["value"] == 20.0          # последнее значение, не 10.0
    assert "timestamp" in body


def test_latest_unknown_device_returns_error(client):
    resp = client.get("/api/devices/unknown/latest")
    assert resp.status_code == 200
    assert resp.json() == {"error": "no data"}