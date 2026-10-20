import os
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """
    Создаёт TestClient с временной БД.

    Важно: DB_PATH выставляется ДО импорта app.main,
    потому что init_db() вызывается на уровне модуля.
    """
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_file))

    # сбрасываем кэш импорта, чтобы app.main перечитал DB_PATH
    for mod in list(sys.modules):
        if mod == "app.main" or mod.startswith("app."):
            del sys.modules[mod]

    # добавляем корень server/ в sys.path, чтобы `import app` работал
    server_root = Path(__file__).resolve().parents[1]
    if str(server_root) not in sys.path:
        sys.path.insert(0, str(server_root))

    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c

    # после теста удаляем временную БД (tmp_path сам чистится pytest'ом)