<<<<<<< HEAD
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
=======
# Stage 1: Build frontend static export
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime with backend + frontend static files
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for cache layering
COPY backend/pyproject.toml backend/uv.lock ./

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies (without the project itself)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev --no-editable

# Copy backend source
COPY backend/ ./

# Install project with dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# Copy frontend build output
COPY --from=frontend-builder /app/frontend/out ./static

# Create db directory for SQLite volume mount
RUN mkdir -p /app/db

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
