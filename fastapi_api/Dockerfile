# FROM python:3.11-slim

# WORKDIR /fastapp
# COPY requirements.txt ./requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt

# COPY ./app ./app

# ENV PYTHONUNBUFFERED=1
# ENV LOG_LEVEL=INFO

# EXPOSE 8001
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--log-level", "info"]

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120

# 빌드/런타임에 필요한 기본 패키지 추가
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc git \
    libffi-dev libssl-dev \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /fastapp

# 먼저 requirements.txt만 복사 (캐시 활용)
COPY requirements.txt .

# 최신 빌드 도구 설치 후 requirements 설치
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# 앱 소스 복사
COPY ./app ./app

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--log-level", "info"]
