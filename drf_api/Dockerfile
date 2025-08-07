FROM python:3.12-slim
LABEL maintainer="yooooonira"

ENV PYTHONUNBUFFERED=1
WORKDIR /app

#패키지 설치 및 Python deps 설치
COPY ./requirements.txt /tmp/requirements.txt
COPY ./requirements.dev.txt /tmp/requirements.dev.txt
COPY . /app

ARG DEV=false
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && pip install --upgrade pip \
    && pip install -r /tmp/requirements.txt \
    && if [ "$DEV" = "true" ]; then pip install -r /tmp/requirements.dev.txt; fi \
    && apt-get purge -y --auto-remove build-essential libpq-dev \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* /tmp


#유저 추가 및 권한 설정
RUN adduser --disabled-password --gecos "" django-user
USER django-user

EXPOSE 8000
