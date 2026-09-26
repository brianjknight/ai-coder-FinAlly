# syntax=docker/dockerfile:1

# ---------- Stage 1: build the Next.js static export ----------
FROM node:20-slim AS frontend
WORKDIR /frontend

# Install deps first (cached unless package files change)
COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# Build the static export -> /frontend/out
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build


# ---------- Stage 2: Python runtime ----------
FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Install dependencies only (cached unless pyproject/uv.lock change)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy the backend source and install the project itself
COPY backend/ ./
RUN uv sync --frozen --no-dev

# Frontend static export
COPY --from=frontend /frontend/out /app/static

ENV PATH="/app/.venv/bin:$PATH" \
    DB_PATH=/app/db/finally.db \
    STATIC_DIR=/app/static

RUN mkdir -p /app/db
VOLUME ["/app/db"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
