#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

export PYTHONIOENCODING=utf-8

# rm faults.db

source .venv/Scripts/activate

# python init_db.py     - скрипт для инициализации БД

# python migrate_db.py     - скрипт для миграции БД

# python seed_data.py

uvicorn app.main:app --reload --port 3000
