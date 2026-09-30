#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_DIR="$(cd "${RUNTIME_DIR}/.." && pwd)"
ASSET_DIR="${RUNTIME_DIR}/r2_upload/v1.1.6"
BUCKET="dharmacodex-runtime-private"

python3 "${SCRIPT_DIR}/build_manifest.py"

while IFS= read -r relative; do
  npx --yes wrangler@4.141.0 r2 object put "${BUCKET}/v1.1.6/${relative}" --file "${ASSET_DIR}/${relative}" --remote
done <<'EOF'
manifest.sha256.json
databases/Astro_Readings_V2.0.db
databases/DM_DB_v2.0.db
databases/HD_DB_v2.0.db
databases/NUM_DB_v2.0.db
geometry/BodyGraph.svg
geometry/DM.svg
ephe/sepl_18.se1
ephe/seas_18.se1
ephe/semoon_18.se1
EOF

npm --prefix "${RUNTIME_DIR}/worker" ci
npm --prefix "${RUNTIME_DIR}/worker" run deploy
npx --yes wrangler@4.141.0 pages deploy "${PROJECT_DIR}/cloudflare_public" --project-name dharmacodex-org
