FROM python:3.11-slim

WORKDIR /app

# Install system deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY skill.md .

ENV PORT=8080
EXPOSE 8080

# Railway sets PORT env var - use shell form to expand it
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8080}
