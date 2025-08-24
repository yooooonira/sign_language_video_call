#!/bin/sh
set -e

mkdir -p /vol/web/media/uploads
chmod -R 755 /vol/web/media/uploads

python manage.py wait_for_db
python manage.py collectstatic --noinput
python manage.py migrate

if [ "$ENV" = "production" ]; then
    gunicorn drf_api.asgi:application \
        -k uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:8000 \
        --workers 4 \
        --log-level info
else
    uvicorn drf_api.asgi:application --host 0.0.0.0 --port 8000 --reload
fi
