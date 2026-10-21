"""GUI lifecycle checks using Qt's offscreen backend."""
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from PyQt5.QtWidgets import QApplication
from gui import CollectorWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def wait_for(app, condition):
    deadline = time.monotonic() + 3
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert condition()


def test_start_stop_and_restart(app):
    def collect(settings, stop, emit):
        emit("telemetry", 24.75)
        emit("command", 7)
        stop.wait(3)

    window = CollectorWindow()
    try:
        with patch("gui.run_collector", side_effect=collect):
            window.start_button.click()
            assert not window.entries[0].isEnabled()
            wait_for(app, lambda: window.sent == 1)
            assert window.value.text() == "24.75"
            assert window.commands == 1
            window.stop_button.click()
            wait_for(app, lambda: window.worker is None)
            assert window.start_button.isEnabled()
            assert window.entries[0].isEnabled()
            window.start_button.click()
            wait_for(app, lambda: window.sent == 2)
            window.stop_button.click()
            wait_for(app, lambda: window.worker is None)
    finally:
        window.stop()
        if window.worker is not None:
            window.worker.join(4)
            window.drain_events()
        window.close()


def test_close_waits_for_worker(app):
    def collect(settings, stop, emit):
        stop.wait(3)

    window = CollectorWindow()
    with patch("gui.run_collector", side_effect=collect):
        window.show()
        window.start()
        window.close()
        assert window.closing
        wait_for(app, lambda: window.worker is None and not window.isVisible())
        assert not window.timer.isActive()


def test_invalid_settings_do_not_start_worker(app):
    window = CollectorWindow()
    try:
        window.entries[2].setText("nan")
        with patch("gui.QMessageBox.warning") as warning:
            window.start()
        warning.assert_called_once()
        assert window.worker is None
        assert window.entries[0].isEnabled()
    finally:
        window.close()
