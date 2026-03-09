# ══════════════════════════════════════════════════════════════════════════════
# StockAI v2.0 Dockerfile — FastAPI + static HTML frontend
# ══════════════════════════════════════════════════════════════════════════════
# Build:  docker build -t stockai .
# Run:    docker run -p 8000:8000 --env-file .env stockai
# Browse: http://localhost:8000/app
# ══════════════════════════════════════════════════════════════════════════════

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (layer-cached when only code changes)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy only the source that the app needs
COPY backend/ backend/
COPY frontend/ frontend/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

CMD ["python", "backend/run.py"]
