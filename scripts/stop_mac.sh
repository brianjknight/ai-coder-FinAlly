#!/usr/bin/env bash
<<<<<<< HEAD
# Stop and remove the FinAlly container (macOS/Linux). Idempotent.
# The 'finally-data' volume is NOT removed, so your data persists.
set -euo pipefail

CONTAINER="finally"

if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  docker rm -f "$CONTAINER" >/dev/null
  echo "FinAlly container stopped and removed. Data volume 'finally-data' preserved."
else
  echo "FinAlly container is not running."
fi
=======
set -euo pipefail

CONTAINER_NAME="finally"

docker stop "$CONTAINER_NAME" 2>/dev/null && echo "FinAlly stopped." || echo "FinAlly is not running."
docker rm "$CONTAINER_NAME" 2>/dev/null || true
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
