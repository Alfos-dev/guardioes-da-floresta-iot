FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# SQLite device registry lives on a mounted volume.
VOLUME ["/data"]

CMD ["python", "-u", "ingest_service.py"]
