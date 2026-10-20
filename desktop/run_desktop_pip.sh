#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

export PYTHONIOENCODING=utf-8

source .venv/Scripts/activate

python main.py
