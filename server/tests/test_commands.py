def test_create_and_list_pending_command(client):
    resp = client.post(
        "/api/devices/sensor-1/command",
        json={"action": "pump_on", "params": {"speed": 50}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert isinstance(body["command_id"], int)

    listing = client.get("/api/devices/sensor-1/commands").json()
    assert listing["device_id"] == "sensor-1"
    assert len(listing["commands"]) == 1
    cmd = listing["commands"][0]
    assert cmd["action"] == "pump_on"
    assert cmd["params"] == {"speed": 50}


def test_ack_removes_from_pending(client):
    cmd_id = client.post(
        "/api/devices/sensor-1/command", json={"action": "fan_off"}
    ).json()["command_id"]

    ack = client.post(f"/api/commands/{cmd_id}/ack")
    assert ack.status_code == 200
    assert ack.json() == {"status": "ok"}

    listing = client.get("/api/devices/sensor-1/commands").json()
    assert listing["commands"] == []


def test_ack_unknown_command(client):
    resp = client.post("/api/commands/99999/ack")
    assert resp.status_code == 200
    assert resp.json() == {"status": "not_found_or_already_done"}


def test_commands_isolated_by_device(client):
    client.post("/api/devices/a/command", json={"action": "x"})
    client.post("/api/devices/b/command", json={"action": "y"})

    a = client.get("/api/devices/a/commands").json()["commands"]
    b = client.get("/api/devices/b/commands").json()["commands"]
    assert [c["action"] for c in a] == ["x"]
    assert [c["action"] for c in b] == ["y"]