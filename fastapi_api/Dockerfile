FROM python:3.11-slim

# 시스템 의존성 (psycopg2, uvicorn 등 빌드 최소화)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY run.sh ./run.sh
EXPOSE 8001
CMD ["./run.sh"]
