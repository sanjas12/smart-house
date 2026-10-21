import sys
from pathlib import Path
from threading import Event
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collector import Settings, run_collector


@pytest.mark.parametrize("url,device,interval", [
    ("localhost:3000", "demo", 2),
    ("http://localhost", "", 2),
    ("http://localhost", "demo", float("nan")),
    ("http://localhost", "demo", float("inf")),
    ("http://localhost", "demo", 0),
    ("http://localhost?x=1", "demo", 2),
])
def test_invalid_settings(url, device, interval):
    with pytest.raises(ValueError):
        Settings(url, device, interval)


def test_telemetry_and_demo_command_ack():
    stop = Event()
    session = MagicMock()
    response = session.post.return_value
    response.json.return_value = {"status": "ok"}
    session.get.return_value.json.return_value = {
        "commands": [{"id": 7, "action": "pump_on", "params": None}]}
    events = []

    def emit(kind, value):
        events.append((kind, value))
        if kind == "command":
            stop.set()

    with patch("collector.requests.Session") as factory:
        factory.return_value.__enter__.return_value = session
        run_collector(Settings("http://localhost:3000/", "demo", 2), stop, emit)
    assert [kind for kind, _ in events] == ["telemetry", "log", "command"]
    assert session.post.call_args_list[0].args[0] == "http://localhost:3000/api/telemetry"
    assert session.post.call_args_list[0].kwargs["json"]["device_id"] == "demo"
    assert session.post.call_args_list[1].args[0].endswith("/api/commands/7/ack")
    assert session.trust_env is False


def test_network_error_can_stop_without_polling():
    stop = Event()
    session = MagicMock()
    session.post.side_effect = requests.ConnectionError("offline")
    events = []

    def emit(kind, value):
        events.append((kind, value))
        stop.set()

    with patch("collector.requests.Session") as factory:
        factory.return_value.__enter__.return_value = session
        run_collector(Settings("http://localhost", "demo", 2), stop, emit)
    assert events[0][0] == "error"
    session.get.assert_not_called()


def test_malformed_commands_reported():
    stop = Event()
    session = MagicMock()
    session.get.return_value.json.return_value = {"commands": None}

    def emit(kind, value):
        if kind == "error":
            stop.set()

    with patch("collector.requests.Session") as factory:
        factory.return_value.__enter__.return_value = session
        run_collector(Settings("http://localhost", "demo", 2), stop, emit)
    assert session.post.call_count == 1
