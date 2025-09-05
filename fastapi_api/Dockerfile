FROM python:3.11-slim

WORKDIR /fastapp

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY ./AI_Language ./AI_Language

ENV PYTHONPATH="/fastapp:/fastapp/app:$PYTHONPATH"
ENV TFLITE_PATH="/fastapp/AI_Language/models/multi_hand_gesture_classifier.tflite"

ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--log-level", "info"]

