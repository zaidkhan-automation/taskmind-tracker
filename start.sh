#!/usr/bin/env bash
set -e
exec uvicorn tracker_server:app --host 0.0.0.0 --port ${PORT:-8000}
