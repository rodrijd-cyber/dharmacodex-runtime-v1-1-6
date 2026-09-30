#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
Rollback is release-based and does not modify R2 assets:
1. Cloudflare dashboard → Workers & Pages → dharmacodex-org → Deployments → Rollback.
2. Workers & Pages → dharmacodex-runtime-internal → Deployments → Rollback.
3. Keep Cloudflare Access protecting /internal/* throughout rollback.
EOF

