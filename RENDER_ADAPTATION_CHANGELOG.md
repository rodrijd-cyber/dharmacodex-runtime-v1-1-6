# DharmaCodex — Render Adaptation v0.2

BASELINE:
DHARMACODEX_ORG_COMPLETE_RUNTIME_V1_1_6_CONTAINER_DELTA.zip

PREVIOUS ATTEMPT:
Render v0.1 — FAILED QA because PowerShell line-break escaping
produced literal escape text inside Dockerfile.

TARGET:
Render Web Service

DATE:
2026-09-28 14:14:01

CHANGES:
1. Enabled DCX_LOCAL_ASSET_ROOT=/app/runtime-assets.
2. Copied container_runtime/r2_upload/v1.1.6 into /app/runtime-assets.
3. Removed only the r2_upload exclusion from container_runtime/.dockerignore.
4. Canonical calculation/rendering source was not modified.
5. Canonical databases were not modified.
6. Ephemeris files were not modified.
7. Geometry files were not modified.
8. Existing Cloudflare/R2 deployment files were retained.
9. No credentials or secrets were added.
10. No user-input persistence was added.
11. Release generated directly from the original Container baseline.

INTENDED DEPLOYMENT:
Render Docker Web Service.

STATUS:
RENDER BUILD TEST — PENDING
