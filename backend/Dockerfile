FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gdal-bin libgdal-dev nmap iproute2 avahi-utils samba-common-bin postgresql-client libreoffice-writer fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN GDAL_VERSION="$(gdal-config --version)" \
    && pip install --no-cache-dir "GDAL==${GDAL_VERSION}"
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install-deps chromium \
    && python -m playwright install chromium

COPY . .
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
