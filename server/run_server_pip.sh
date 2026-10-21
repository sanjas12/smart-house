#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8

if [[ -f .venv/Scripts/python.exe ]]; then
    VENV_PYTHON=".venv/Scripts/python.exe"
elif [[ -x .venv/bin/python ]]; then
    VENV_PYTHON=".venv/bin/python"
else
    echo "Окружение не найдено. Создайте .venv по инструкции в Readme.md." >&2
    exit 1
fi

exec "$VENV_PYTHON" -m uvicorn app.main:app --reload --port 3000
