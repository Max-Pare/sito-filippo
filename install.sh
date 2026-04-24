#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -m venv "$ROOT_DIR/.venv"
"$ROOT_DIR/.venv/bin/python" -m pip install --upgrade pip wheel
"$ROOT_DIR/.venv/bin/pip" install -r "$ROOT_DIR/flask-server/requirements.txt"
mkdir -p "$ROOT_DIR/flask-server/data"
