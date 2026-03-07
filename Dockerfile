FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libreoffice-calc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Directorio para datos persistentes (DB, archivos)
RUN mkdir -p /app/data

VOLUME ["/app/data"]

EXPOSE 8000

CMD ["python", "main.py"]
