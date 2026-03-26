FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend:/app/worker

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-ita \
    && rm -rf /var/lib/apt/lists/*

COPY modules/catasto/worker/requirements.txt /app/worker/requirements.txt
RUN pip install --no-cache-dir -r /app/worker/requirements.txt

COPY modules/catasto/worker /app/worker
COPY backend /app/backend

CMD ["python", "/app/worker/worker.py"]
