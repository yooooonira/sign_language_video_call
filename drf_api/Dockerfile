FROM python:3.12-slim
LABEL maintainer="yooooonira"
ENV PYTHONUNBUFFERED=1
COPY ./drf_api/requirements.txt /tmp/requirements.txt
COPY ./drf_api/requirements.dev.txt /tmp/requirements.dev.txt
COPY ./drf_api /app
WORKDIR /app
EXPOSE 8000
ARG DEV=false
RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    /py/bin/pip install -r /tmp/requirements.txt && \
    if [ "$DEV" = "true" ]; then /py/bin/pip install -r /tmp/requirements.dev.txt; fi && \
    rm -rf /tmp && \
    adduser --disabled-password --gecos "" django-user
ENV PATH="/py/bin:$PATH"
USER django-user

