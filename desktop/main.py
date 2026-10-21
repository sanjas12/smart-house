"""Desktop entry point: GUI by default, console with --cli."""
import argparse
import os
from datetime import datetime
from threading import Event

from collector import Settings, run_collector


def main():
    parser = argparse.ArgumentParser(description="Automation Hub — сборщик данных")
    parser.add_argument("--cli", action="store_true", help="запустить без графического окна")
    args = parser.parse_args()
    if not args.cli:
        try:
            from gui import launch
        except ImportError as exc:
            if not (exc.name or "").startswith("PyQt5"):
                raise
            parser.exit(1, "PyQt5 не установлен. Установите зависимости desktop/requirements.txt. "
                        "Для консольного режима используйте --cli.\n")
        launch()
        return
    try:
        settings = Settings(
            os.environ.get("SERVER_URL", "http://127.0.0.1:3000"),
            os.environ.get("DEVICE_ID", "demo-sensor-01"),
            float(os.environ.get("INTERVAL_SEC", "2")),
        )
    except ValueError as exc:
        parser.error(str(exc))
    stop = Event()
    print("Демонстрационный сборщик: {} → {}".format(settings.device_id, settings.server_url))
    try:
        run_collector(settings, stop, lambda kind, value: print(
            "[{}] {}: {}".format(datetime.now().strftime("%H:%M:%S"), kind, value)))
    except KeyboardInterrupt:
        stop.set()


if __name__ == "__main__":
    main()
