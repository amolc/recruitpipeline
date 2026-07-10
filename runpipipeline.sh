#!/usr/bin/env bash
set -e

PORT=8500

echo "==> Killing any process on port $PORT..."
lsof -ti :$PORT | xargs kill -9 2>/dev/null || true

echo "==> Starting Django on port $PORT..."
source venv/bin/activate
python manage.py runserver "$PORT"
