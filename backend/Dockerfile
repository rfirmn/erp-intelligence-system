# ==============================================================================
# Production / Internal Server Dockerfile for ERP Intelligence Dashboard Backend
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final stage
FROM python:3.12-slim AS runner

WORKDIR /app

# Install curl for container health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python dependencies from builder
COPY --from=builder /install /usr/local

# Security: Create and use non-root system user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy application source code and scripts
COPY --chown=appuser:appgroup ./app /app/app
COPY --chown=appuser:appgroup ./scripts /app/scripts

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

EXPOSE 8000

# Docker Healthcheck targeting the living API health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:${APP_PORT}/api/v1/health || exit 1

# Auto-initialize database schemas/tables if needed, then start FastAPI with uvicorn
CMD ["sh", "-c", "python scripts/init_db.py && exec uvicorn app.main:app --host ${APP_HOST} --port ${APP_PORT}"]
