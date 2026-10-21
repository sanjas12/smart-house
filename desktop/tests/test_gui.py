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


def test_history_pages_and_empty_result(app):
    window = CollectorWindow()
    history = window.history
    history.busy = True
    history.results.put(('http://127.0.0.1:3000', 'sensor', 0, ['sensor'], 101,
                         [('101', '2026-10-21T12:00:00', '25.5')], None))
    history.drain()
    assert history.table.rowCount() == 1
    assert history.table.item(0, 2).text() == '25.5'
    assert history.next.isEnabled()
    assert not history.previous.isEnabled()
    history.devices.setEditText('unknown')
    assert history.table.rowCount() == 0
    assert not history.next.isEnabled()
    history.results.put(('http://127.0.0.1:3000', 'unknown', 0, ['sensor'], 0, [], None))
    history.drain()
    assert 'Показаний пока нет' in history.message.text()
    window.close()


def test_history_error_and_stale_server_result(app):
    window = CollectorWindow()
    history = window.history
    history.results.put(('http://127.0.0.1:3000', 'sensor', 0, [], 0, [], 'offline'))
    history.drain()
    assert 'offline' in history.message.text()
    assert history.refresh.isEnabled()
    window.entries[0].setText('http://localhost:4000')
    history.results.put(('http://127.0.0.1:3000', 'sensor', 0, [], 0, [], None))
    history.drain()
    assert 'Адрес сервера изменён' in history.message.text()
    window.close()


def test_history_fetch_uses_server_api(app):
    from unittest.mock import MagicMock

    window = CollectorWindow()
    devices = MagicMock()
    devices.json.return_value = {'devices': ['sensor']}
    readings = MagicMock()
    readings.json.return_value = {
        'total': 1, 'readings': [{'id': 1, 'timestamp': '2026-10-21', 'value': 23}]}
    session = MagicMock()
    session.get.side_effect = [devices, readings]
    with patch('history.requests.Session') as factory:
        factory.return_value.__enter__.return_value = session
        window.history.fetch('http://localhost:3000', '', 0, 'sensor')
    assert session.trust_env is False
    assert session.get.call_args_list[1].args[0].endswith('/api/devices/sensor/history')
    assert session.get.call_args_list[1].kwargs['params'] == {'limit': 100, 'offset': 0}
    window.entries[0].setText('http://localhost:3000')
    window.history.drain()
    assert window.history.devices.currentText() == 'sensor'
    assert window.history.table.item(0, 2).text() == '23'
    window.close()
