#!/bin/sh
set -eu

# Persistent mounts commonly replace the image-owned directory with a
# root-owned path. Prepare all writable locations, then drop privileges.
if [ "$(id -u)" = "0" ]; then
    mkdir -p \
        "$STORAGE_DIR" \
        "$CHROMA_PERSIST_DIR" \
        "$(dirname "$SQLITE_CHECKPOINT_PATH")" \
        "$OUTPUT_DIR" \
        "$HF_HOME"

    chown -R appuser:appuser \
        "$STORAGE_DIR" \
        "$CHROMA_PERSIST_DIR" \
        "$(dirname "$SQLITE_CHECKPOINT_PATH")" \
        "$OUTPUT_DIR" \
        "$HF_HOME"

    exec gosu appuser "$@"
fi

exec "$@"
