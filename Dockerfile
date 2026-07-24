FROM node:22-slim AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1 \
    STATIC_EXPORT=true \
    NEXT_PUBLIC_API_URL=""
RUN npm run build


FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    STORAGE_DIR=/app/storage \
    CHROMA_PERSIST_DIR=/app/storage/chroma_db \
    SQLITE_CHECKPOINT_PATH=/app/storage/checkpoints.db \
    OUTPUT_DIR=/app/storage/output \
    FRONTEND_STATIC_DIR=/app/frontend/out \
    HF_HOME=/app/.cache/huggingface \
    EMBEDDING_MODEL_REVISION=1110a243fdf4706b3f48f1d95db1a4f5529b4d41 \
    AUTO_INGEST=true

RUN apt-get update && apt-get install -y --no-install-recommends \
        libharfbuzz0b \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        gosu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY --from=frontend-builder /build/frontend/out ./frontend/out

# Bake the small knowledge base and embedding model into the image. The
# application repeats this check at startup for deployments using an empty
# persistent volume.
RUN python -c "from src.rag.ingest import ensure_documents_ingested; assert ensure_documents_ingested() > 0"

RUN useradd --create-home --uid 10001 appuser \
    && chmod +x /app/scripts/docker-entrypoint.sh \
    && mkdir -p /app/storage /app/.cache \
    && chown -R appuser:appuser /app/storage /app/.cache

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/health/live', timeout=3)" || exit 1

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["python", "scripts/run_api.py", "--host", "0.0.0.0", "--no-reload"]
