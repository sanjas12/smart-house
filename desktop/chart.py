"""Interactive history chart with server-side period selection."""
import math
import queue
import threading
from datetime import datetime
from urllib.parse import quote, urlsplit

import requests
import pyqtgraph as pg
from PyQt5.QtCore import QDateTime, QTimer
from PyQt5.QtWidgets import (
    QDateTimeEdit, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from collector import Settings


class ChartWidget(QWidget):
    def __init__(self, server_url, device_id):
        super().__init__()
        self.server_url = server_url
        self.device_id = device_id
        self.results = queue.Queue()
        self.busy = False
        layout = QVBoxLayout(self)
        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Устройство"))
        self.device = QLineEdit(device_id())
        self.device.textChanged.connect(self.invalidate)
        device_row.addWidget(self.device)
        layout.addLayout(device_row)
        controls = QHBoxLayout()
        now = QDateTime.currentDateTime()
        self.start = QDateTimeEdit(now.addDays(-1))
        self.end = QDateTimeEdit(now)
        for label, field in (("С", self.start), ("По", self.end)):
            field.setCalendarPopup(True)
            field.setDisplayFormat("dd.MM.yyyy HH:mm:ss")
            controls.addWidget(QLabel(label))
            controls.addWidget(field)
        self.build = QPushButton("Построить график")
        self.build.clicked.connect(self.load)
        controls.addWidget(self.build)
        layout.addLayout(controls)
        layout.addWidget(QLabel("Период — в местном времени сервера. Границы включены."))
        self.plot = pg.PlotWidget(axisItems={"bottom": pg.DateAxisItem()})
        self.plot.setBackground("w")
        self.plot.setLabel("left", "Значение")
        self.plot.setLabel("bottom", "Время")
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.curve = self.plot.plot(pen=pg.mkPen("#2563eb", width=2),
                                    symbol="o", symbolSize=4, symbolBrush="#2563eb")
        self.curve.setDownsampling(auto=True, method="peak")
        self.curve.setClipToView(True)
        layout.addWidget(self.plot, 1)
        self.message = QLabel("Выберите устройство, период и нажмите «Построить график».")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.drain)
        self.timer.start(100)
        self.start.dateTimeChanged.connect(self.invalidate)
        self.end.dateTimeChanged.connect(self.invalidate)

    def sync_device(self):
        self.device.setText(self.device_id())

    def invalidate(self):
        self.curve.setData([], [])
        if not self.busy:
            self.message.setText("Параметры изменены. Постройте график заново.")

    def parameters(self):
        return (self.server_url().strip().rstrip("/"), self.device.text().strip(),
                self.start.dateTime().toString("yyyy-MM-ddTHH:mm:ss"),
                self.end.dateTime().toString("yyyy-MM-ddTHH:mm:ss") + ".999999")

    def load(self):
        if self.busy:
            return
        params = self.parameters()
        try:
            Settings(params[0], params[1], 1)
            if params[2] > params[3]:
                raise ValueError("Начало периода должно быть не позже окончания")
        except ValueError as exc:
            self.message.setText(str(exc))
            return
        self.busy = True
        self.build.setEnabled(False)
        self.start.setEnabled(False)
        self.end.setEnabled(False)
        self.curve.setData([], [])
        self.message.setText("Загрузка данных за выбранный период…")
        threading.Thread(target=self.fetch, args=(params,), daemon=True).start()

    def fetch(self, params):
        url, device, start, end = params
        try:
            with requests.Session() as session:
                if urlsplit(url).hostname in ("localhost", "127.0.0.1", "::1"):
                    session.trust_env = False
                response = session.get(
                    url + "/api/devices/" + quote(device, safe="") + "/history/plot",
                    params={"from": start, "to": end}, timeout=15)
                if response.status_code == 413:
                    raise ValueError("Более 50 000 показаний. Выберите меньший период.")
                response.raise_for_status()
                rows = response.json()["readings"]
                if not isinstance(rows, list):
                    raise ValueError("Некорректная история показаний")
                points = []
                for row in rows:
                    stamp = datetime.fromisoformat(row["timestamp"])
                    # Plot naive server wall-clock time on the local date axis.
                    value = float(row["value"])
                    if not math.isfinite(value):
                        raise ValueError("В истории есть нечисловое показание")
                    points.append((stamp.timestamp(), value))
                points.sort(key=lambda point: point[0])
                self.results.put((params, points, None))
        except (requests.RequestException, ValueError, KeyError, TypeError, OverflowError, OSError) as exc:
            self.results.put((params, [], str(exc)))

    def drain(self):
        try:
            params, points, error = self.results.get_nowait()
        except queue.Empty:
            return
        self.busy = False
        for control in (self.build, self.start, self.end):
            control.setEnabled(True)
        if params != self.parameters():
            self.message.setText("Параметры изменены. Постройте график заново.")
            return
        if error:
            self.message.setText("Не удалось построить график: " + error)
            return
        self.curve.setData([p[0] for p in points], [p[1] for p in points])
        self.plot.enableAutoRange()
        self.message.setText(
            "{} • {} • Точек: {}. Масштаб — колесом мыши, перемещение — перетаскиванием.".format(
                params[0], params[1], len(points)) if points
            else "За выбранный период показаний нет.")
