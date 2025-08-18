FROM python:3.11-slim
LABEL maintainer="yooooonira"

ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /tmp/requirements.txt
COPY ./requirements.dev.txt /tmp/requirements.dev.txt
COPY ./scripts /scripts
COPY . /app
WORKDIR /app
EXPOSE 8000


ARG DEV=true

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev \
    && python -m venv /py \
    && /py/bin/pip install --upgrade pip \
    && /py/bin/pip install -r /tmp/requirements.txt \
    && if [ "$DEV" = "true" ]; then /py/bin/pip install -r /tmp/requirements.dev.txt ; fi \
    && apt-get purge -y --auto-remove build-essential libpq-dev libjpeg62-turbo-dev zlib1g-dev \
    && apt-get install -y --no-install-recommends libpq5 libjpeg62-turbo zlib1g \
    && rm -rf /var/lib/apt/lists/* /tmp

ENV PATH="/scripts:/py/bin:$PATH"

RUN adduser --disabled-password --gecos "" django-user && \
    mkdir -p /vol/web/media /vol/web/static && \
    chown -R django-user:django-user /vol /scripts && \
    chmod -R 755 /vol && \
    chmod -R +x /scripts

USER django-user

CMD ["run.sh"]
