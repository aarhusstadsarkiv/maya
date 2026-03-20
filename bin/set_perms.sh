#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <user> <group> <app_root>"
    exit 1
fi

OWNER="$1"
GROUP="$2"
APP_ROOT="$3"
DATA_DIR="$APP_ROOT/local/data"
BIN_DIR="$APP_ROOT/bin"

find "$APP_ROOT" \
  \( -type d \( -name .git -o -name .venv \) -o -path "$DATA_DIR" -o -path "$BIN_DIR" \) -prune \
  -o -exec chown "$OWNER:$GROUP" {} +

chown -R "$OWNER:$GROUP" "$DATA_DIR" "$BIN_DIR"

find "$APP_ROOT" \
  \( -type d \( -name .git -o -name .venv \) -o -path "$DATA_DIR" -o -path "$BIN_DIR" \) -prune \
  -o -type d -exec chmod 2750 {} +

find "$APP_ROOT" \
  \( -type d \( -name .git -o -name .venv \) -o -path "$DATA_DIR" -o -path "$BIN_DIR" \) -prune \
  -o -type f -exec chmod 0640 {} +

find "$DATA_DIR" -type d -exec chmod 2770 {} +
find "$DATA_DIR" -type f -exec chmod 0660 {} +

find "$BIN_DIR" -type d -exec chmod 2750 {} +
find "$BIN_DIR" -type f -exec chmod 0750 {} +