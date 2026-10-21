"""PyQt5 interface. Widget updates are confined to the GUI thread."""
import os
import queue
import threading
from datetime import datetime

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QVBoxLayout, QWidget, QTabWidget,
)

from collector import Settings, run_collector
from history import HistoryWidget
from chart import ChartWidget


class CollectorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.stop_event = threading.Event()
        self.events = queue.Queue(maxsize=500)
        self.closing = False
        self.sent = 0
        self.commands = 0
        self.setWindowTitle("Automation Hub — сборщик данных")
        self.resize(820, 650)
        self.setMinimumSize(640, 530)
        panel = QWidget()
        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        tabs.addTab(panel, "Сборщик")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        title = QLabel("Automation Hub")
        title.setFont(QFont("Arial", 22, QFont.Bold))
        layout.addWidget(title)
        layout.addWidget(QLabel("Демонстрационный сборщик • оборудование не подключено"))
        group = QGroupBox("Подключение")
        form = QFormLayout(group)
        self.entries = []
        for label, env, default in [
            ("Адрес сервера", "SERVER_URL", "http://127.0.0.1:3000"),
            ("Устройство", "DEVICE_ID", "demo-sensor-01"),
            ("Интервал, сек.", "INTERVAL_SEC", "2"),
        ]:
            entry = QLineEdit(os.environ.get(env, default))
            form.addRow(label, entry)
            self.entries.append(entry)
        layout.addWidget(group)
        controls = QHBoxLayout()
        self.start_button = QPushButton("Запустить")
        self.start_button.clicked.connect(self.start)
        controls.addWidget(self.start_button)
        self.stop_button = QPushButton("Остановить")
        self.stop_button.clicked.connect(self.stop)
        self.stop_button.setEnabled(False)
        controls.addWidget(self.stop_button)
        controls.addStretch()
        self.status = QLabel("Остановлен")
        controls.addWidget(self.status)
        layout.addLayout(controls)
        layout.addWidget(QLabel("Последнее отправленное показание"))
        self.value = QLabel("—")
        self.value.setFont(QFont("Arial", 30, QFont.Bold))
        layout.addWidget(self.value)
        self.stats = QLabel("Отправлено: 0   •   Команд подтверждено: 0")
        layout.addWidget(self.stats)
        layout.addWidget(QLabel("Журнал событий"))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        layout.addWidget(self.log, 1)
        self.history = HistoryWidget(
            lambda: self.entries[0].text(), lambda: self.entries[1].text())
        tabs.addTab(self.history, "История из базы")
        self.chart = ChartWidget(
            lambda: self.entries[0].text(),
            lambda: self.history.devices.currentText() or self.entries[1].text())
        tabs.addTab(self.chart, "График истории")
        self.history.devices.currentTextChanged.connect(self.chart.sync_device)
        self.entries[0].textChanged.connect(self.chart.invalidate)
        self.entries[1].textChanged.connect(self.chart.sync_device)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.drain_events)
        self.timer.start(100)

    def append_log(self, message):
        self.log.appendPlainText("[{}] {}".format(datetime.now().strftime("%H:%M:%S"), message))
        bar = self.log.verticalScrollBar()
        bar.setValue(bar.maximum())

    def start(self):
        if self.worker is not None:
            return
        try:
            url, device, interval = [entry.text().strip() for entry in self.entries]
            settings = Settings(url, device, float(interval.replace(",", ".")))
        except ValueError as exc:
            QMessageBox.warning(self, "Проверьте настройки", str(exc))
            return
        self.stop_event.clear()
        for entry in self.entries:
            entry.setEnabled(False)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status.setText("Запуск…")
        self.append_log("Запуск: {} → {}".format(device, url))
        self.worker = threading.Thread(target=self.collect, args=(settings,), daemon=True)
        self.worker.start()

    def emit(self, kind, value):
        # Keep memory bounded even if the window is temporarily busy.
        try:
            self.events.put_nowait((kind, value))
        except queue.Full:
            pass

    def collect(self, settings):
        try:
            run_collector(settings, self.stop_event, self.emit)
        except Exception as exc:
            self.emit("error", "Сборщик завершился: {}".format(exc))

    def stop(self):
        if self.worker is not None:
            self.stop_event.set()
            self.status.setText("Остановка…")
            self.stop_button.setEnabled(False)

    def drain_events(self):
        for _ in range(500):
            try:
                kind, data = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "telemetry":
                self.sent += 1
                self.value.setText("{:.2f}".format(data))
                if not self.stop_event.is_set():
                    self.status.setText("Телеметрия отправлена")
                self.append_log("Отправлено показание: {:.2f}".format(data))
            elif kind == "command":
                self.commands += 1
                self.append_log("Подтверждена демо-команда №{}".format(data))
            else:
                if kind == "error" and not self.stop_event.is_set():
                    self.status.setText("Ошибка связи — повтор в следующем цикле")
                self.append_log(str(data))
            self.stats.setText("Отправлено: {}   •   Команд подтверждено: {}".format(self.sent, self.commands))
        if self.worker is not None and not self.worker.is_alive():
            self.worker = None
            self.status.setText("Остановлен")
            self.append_log("Сборщик остановлен")
            for entry in self.entries:
                entry.setEnabled(True)
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
        if self.closing and self.worker is None:
            self.close()
            return

    def closeEvent(self, event):
        if self.worker is None:
            self.timer.stop()
            event.accept()
            return
        self.closing = True
        self.start_button.setEnabled(False)
        self.stop()
        event.ignore()


def launch():
    app = QApplication([])
    window = CollectorWindow()
    window.show()
    return app.exec_()
