#!/usr/bin/env bash
<<<<<<< HEAD
# Start the FinAlly container (macOS/Linux). Idempotent.
# Usage: scripts/start_mac.sh [--build] [--no-open]
set -euo pipefail

IMAGE="finally"
CONTAINER="finally"
VOLUME="finally-data"
PORT="${PORT:-8000}"
URL="http://localhost:${PORT}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BUILD=0
OPEN=1
for arg in "$@"; do
  case "$arg" in
    --build|-b) BUILD=1 ;;
    --no-open)  OPEN=0 ;;
    -h|--help)
      echo "Usage: $0 [--build] [--no-open]"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is not installed or not on PATH." >&2
  exit 1
fi

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    echo "No .env found - creating one from .env.example (add your OPENROUTER_API_KEY)."
    cp .env.example .env
  else
    echo "Error: .env file is missing." >&2
    exit 1
  fi
fi

if [ "$BUILD" -eq 1 ] || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Building Docker image '$IMAGE'..."
  docker build -t "$IMAGE" .
fi

# Remove any existing container (running or stopped) so this is safe to re-run
if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "Replacing existing container '$CONTAINER'..."
  docker rm -f "$CONTAINER" >/dev/null
fi

docker run -d \
  --name "$CONTAINER" \
  -v "$VOLUME":/app/db \
  -p "$PORT":8000 \
  --env-file .env \
  "$IMAGE" >/dev/null

echo "Waiting for FinAlly to become healthy..."
for _ in $(seq 1 30); do
  if curl -fsS "$URL/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "FinAlly is running at $URL"

if [ "$OPEN" -eq 1 ]; then
  if command -v open >/dev/null 2>&1; then
    open "$URL" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 || true
  fi
fi
=======
set -euo pipefail

CONTAINER_NAME="finally-gsd"
IMAGE_NAME="finally-gsd"

# Stop existing container if running
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Build if --build flag passed or image doesn't exist
if [[ "${1:-}" == "--build" ]] || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    echo "Building FinAlly Docker image..."
    docker build -t "$IMAGE_NAME" .
fi

# Run container
docker run -d \
    --name "$CONTAINER_NAME" \
    -p 8000:8000 \
    -v finally-data-gsd:/app/db \
    --env-file .env \
    "$IMAGE_NAME"

echo ""
echo "FinAlly is running at http://localhost:8008"
echo "Stop with: ./scripts/stop_mac.sh"
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
