#!/usr/bin/env bash
set -e

if [ -d "/workspace/backend" ]; then
  cd /workspace/backend
elif [ -d "backend" ]; then
  cd backend
else
  echo "Error: Backend directory not found." >&2
  exit 1
fi

PORT="${PORT:-8080}"

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT}"
