FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY serial_bridge.py .
CMD ["python", "serial_bridge.py"]
