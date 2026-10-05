#!/bin/sh
# One-shot init job (compose service `qdrant_init`):
# if the Qdrant collection does not exist yet, restore it from the newest
# snapshot in /snapshots (= retrieval_service/artifacts/qdrant_snapshots).
# Safe to run on every `docker compose up`: it does nothing when the collection exists.
set -eu

QDRANT_URL="${QDRANT_URL:-http://qdrant:6333}"
COLLECTION="${DB_COLLECTION_NAME:-nmk_chatbot_collection}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-/snapshots}"

echo "[qdrant-init] Waiting for Qdrant at ${QDRANT_URL} ..."
i=0
until curl -fsS "${QDRANT_URL}/readyz" >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -ge 60 ]; then
    echo "[qdrant-init] Qdrant did not become ready in time" >&2
    exit 1
  fi
  sleep 2
done

if curl -fsS "${QDRANT_URL}/collections/${COLLECTION}/exists" | grep -q '"exists":true'; then
  echo "[qdrant-init] Collection '${COLLECTION}' already exists, nothing to do."
  exit 0
fi

# Newest snapshot file (names end with a timestamp).
SNAPSHOT="$(ls -1 "${SNAPSHOT_DIR}"/*.snapshot 2>/dev/null | sort | tail -n 1 || true)"
if [ -z "${SNAPSHOT}" ]; then
  echo "[qdrant-init] WARNING: collection '${COLLECTION}' is missing and no snapshot was found in ${SNAPSHOT_DIR}."
  echo "[qdrant-init] Run the ingestion from the host instead: cd retrieval_service && python scripts/ingest.py (with DB_URL=http://localhost:6333)"
  exit 0
fi

echo "[qdrant-init] Restoring '${COLLECTION}' from $(basename "${SNAPSHOT}") ..."
curl -fsS -X POST \
  "${QDRANT_URL}/collections/${COLLECTION}/snapshots/upload?priority=snapshot&wait=true" \
  -H "Content-Type: multipart/form-data" \
  -F "snapshot=@${SNAPSHOT}"
echo
echo "[qdrant-init] Restore finished."
