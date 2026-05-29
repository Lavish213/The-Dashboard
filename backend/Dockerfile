# ---- base ----
FROM python:3.12-slim AS base
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for runtime
RUN useradd --no-create-home --shell /bin/false app

# ---- deps ----
FROM base AS deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- dev ----
FROM deps AS dev
COPY . .
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---- production ----
FROM deps AS production
COPY . .
RUN chown -R app:app /app
USER app
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000
# Single worker: ConnectionManager is in-process (not redis-backed).
# Scale horizontally only after migrating broadcasts to redis pub/sub.
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/ready || exit 1
CMD ["python", "-c", "import api.main; print('import ok')"]
