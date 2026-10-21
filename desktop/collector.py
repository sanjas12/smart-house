"""Collector shared by the graphical and console interfaces."""
import math
import random
from dataclasses import dataclass
from threading import Event
from typing import Callable
from urllib.parse import quote, urlsplit

import requests


@dataclass(frozen=True)
class Settings:
    server_url: str
    device_id: str
    interval: float

    def __post_init__(self):
        parsed = urlsplit(self.server_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Укажите адрес сервера с http:// или https://")
        if parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError("Адрес сервера не должен содержать параметры или пароль")
        if not self.device_id.strip():
            raise ValueError("Укажите идентификатор устройства")
        if not math.isfinite(self.interval) or self.interval < 0.1:
            raise ValueError("Интервал должен быть числом не меньше 0,1 секунды")


def run_collector(settings: Settings, stop: Event, emit: Callable):
    """Run until stopped; report events without accessing UI objects."""
    base = settings.server_url.rstrip("/")
    device = quote(settings.device_id, safe="")
    with requests.Session() as session:
        # Local requests must bypass corporate proxies.
        if urlsplit(base).hostname in ("localhost", "127.0.0.1", "::1"):
            session.trust_env = False
        while not stop.is_set():
            value = round(random.uniform(20.0, 30.0), 2)
            try:
                response = session.post(
                    base + "/api/telemetry",
                    json={"device_id": settings.device_id, "value": value}, timeout=5,
                )
                response.raise_for_status()
                emit("telemetry", value)
            except requests.RequestException as exc:
                emit("error", "Телеметрия: {}".format(exc))
            if stop.is_set():
                break
            try:
                response = session.get(
                    base + "/api/devices/" + device + "/commands", timeout=5,
                )
                response.raise_for_status()
                commands = response.json()["commands"]
                if not isinstance(commands, list):
                    raise ValueError("commands должен быть списком")
                for command in commands:
                    if stop.is_set():
                        break
                    command_id = command["id"]
                    emit("log", "Демо-команда: {} {}".format(
                        command["action"], command.get("params")))
                    response = session.post(
                        base + "/api/commands/" + quote(str(command_id), safe="") + "/ack",
                        timeout=5,
                    )
                    response.raise_for_status()
                    if response.json().get("status") != "ok":
                        raise ValueError("Сервер не подтвердил выполнение команды")
                    emit("command", command_id)
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                emit("error", "Команды: {}".format(exc))
            stop.wait(settings.interval)
