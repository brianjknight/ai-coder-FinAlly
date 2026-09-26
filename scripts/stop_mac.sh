#!/usr/bin/env bash
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
