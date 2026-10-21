"""Read server telemetry without blocking the Qt event loop."""
import queue
import threading
from urllib.parse import quote, urlsplit

import requests
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from collector import Settings


class HistoryWidget(QWidget):
    PAGE_SIZE = 100

    def __init__(self, server_url, default_device):
        super().__init__()
        self.server_url = server_url
        self.default_device = default_device
        self.results = queue.Queue()
        self.busy = False
        self.offset = 0
        self.total = 0
        self.loaded_url = None
        self.loaded_device = None
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Устройство"))
        self.devices = QComboBox()
        self.devices.setEditable(True)
        controls.addWidget(self.devices, 1)
        self.refresh = QPushButton("Обновить из базы")
        self.refresh.clicked.connect(lambda: self.load(0))
        controls.addWidget(self.refresh)
        layout.addLayout(controls)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Время записи", "Значение"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        navigation = QHBoxLayout()
        self.previous = QPushButton("Назад")
        self.previous.clicked.connect(lambda: self.load(max(0, self.offset - self.PAGE_SIZE)))
        self.next = QPushButton("Далее")
        self.next.clicked.connect(lambda: self.load(self.offset + self.PAGE_SIZE))
        navigation.addWidget(self.previous)
        navigation.addWidget(self.next)
        self.message = QLabel("Нажмите «Обновить из базы». Сервер должен быть запущен.")
        self.message.setWordWrap(True)
        layout.addLayout(navigation)
        layout.addWidget(self.message)
        self.previous.setEnabled(False)
        self.next.setEnabled(False)
        self.devices.currentTextChanged.connect(self.selection_changed)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.drain)
        self.timer.start(100)

    def selection_changed(self):
        self.previous.setEnabled(False)
        self.next.setEnabled(False)
        self.table.setRowCount(0)
        self.message.setText("Нажмите «Обновить из базы» для выбранного устройства.")

    def load(self, offset=0):
        if self.busy:
            return
        url = self.server_url().strip().rstrip("/")
        device = self.devices.currentText().strip()
        try:
            Settings(url, device or "history", 1)
        except ValueError as exc:
            self.message.setText(str(exc))
            return
        if url != self.loaded_url or device != self.loaded_device:
            offset = 0
        self.busy = True
        for control in (self.refresh, self.devices, self.previous, self.next):
            control.setEnabled(False)
        self.table.setRowCount(0)
        self.message.setText("Загрузка…")
        threading.Thread(target=self.fetch, args=(url, device, offset, self.default_device().strip()), daemon=True).start()

    def fetch(self, url, device, offset, default):
        try:
            with requests.Session() as session:
                if urlsplit(url).hostname in ("localhost", "127.0.0.1", "::1"):
                    session.trust_env = False
                response = session.get(url + "/api/devices", timeout=5)
                response.raise_for_status()
                devices = response.json()["devices"]
                if not isinstance(devices, list) or not all(isinstance(d, str) for d in devices):
                    raise ValueError("Некорректный список устройств")
                if not device:
                    device = default if default in devices else (devices[0] if devices else default)
                response = session.get(
                    url + "/api/devices/" + quote(device, safe="") + "/history",
                    params={"limit": self.PAGE_SIZE, "offset": offset}, timeout=5,
                )
                response.raise_for_status()
                body = response.json()
                rows = body["readings"]
                if not isinstance(rows, list) or not isinstance(body["total"], int):
                    raise ValueError("Некорректная история показаний")
                # Validate before handing the result to the UI.
                rows = [(str(r["id"]), str(r["timestamp"]), str(r["value"])) for r in rows]
                self.results.put((url, device, offset, devices, body["total"], rows, None))
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            self.results.put((url, device, offset, [], 0, [], str(exc)))

    def drain(self):
        try:
            url, device, offset, devices, total, rows, error = self.results.get_nowait()
        except queue.Empty:
            return
        self.busy = False
        self.refresh.setEnabled(True)
        self.devices.setEnabled(True)
        if url != self.server_url().strip().rstrip("/"):
            self.message.setText("Адрес сервера изменён. Обновите данные.")
            return
        if error:
            self.message.setText("Не удалось прочитать базу через сервер: " + error)
            return
        self.loaded_url, self.loaded_device = url, device
        self.offset, self.total = offset, total
        self.devices.blockSignals(True)
        self.devices.clear()
        self.devices.addItems(devices)
        self.devices.setEditText(device)
        self.devices.blockSignals(False)
        self.table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.previous.setEnabled(offset > 0)
        self.next.setEnabled(offset + len(rows) < total)
        self.message.setText(
            "{} • {} • Записи {}–{} из {} (новые сверху)".format(
                url, device, offset + 1 if rows else 0, offset + len(rows), total)
            if rows else "{} • {} • Показаний пока нет".format(url, device))
