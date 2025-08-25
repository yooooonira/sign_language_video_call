#!/usr/bin/env sh
set -e
# 마이그레이션 같은 건 여기서 필요 없지만
exec uvicorn app.main:app --host 0.0.0.0 --port 8001
