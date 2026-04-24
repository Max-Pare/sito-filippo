#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$ROOT_DIR/flask-server"

cd "$APP_DIR"
exec "$ROOT_DIR/.venv/bin/gunicorn" --config "$APP_DIR/gunicorn.conf.py" wsgi:app
