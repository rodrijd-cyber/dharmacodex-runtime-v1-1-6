# DharmaCodex container runtime deployment

This delta adds one private container-backed Worker to the existing `dharmacodex.org` Pages project. It does not create a second website or expose R2.

## Prerequisites

- Cloudflare account authenticated for Wrangler.
- Existing Pages project `dharmacodex-org` serving `dharmacodex.org`.
- Private R2 bucket `dharmacodex-runtime-private`.
- Cloudflare Access policy covering `dharmacodex.org/internal/*`.
- Containers enabled on the Cloudflare account.

## Deploy

From the delta root, run exactly:

```bash
bash container_runtime/scripts/deploy.sh
```

The command rebuilds the SHA-256 manifest, uploads the nine private runtime assets, deploys the container Worker, and deploys the existing Pages directory with its Service Binding.

## Access policy

Create a self-hosted Access application for `dharmacodex.org/internal/*`. Permit only Rocky, Pablo, Cae, and explicitly approved reviewers. Do not add `/internal/reading/` to public navigation.

## Runtime boundaries

- `RUNTIME_BUCKET` exists only on `dharmacodex-runtime-internal`.
- `RUNTIME_SERVICE` exists only on the Pages project.
- The Worker has `workers_dev = false` and no public route.
- The container can request only the allowlisted `runtime-assets` hostname handled by the Worker.
- Reading inputs are processed in memory and are not persisted.

## Rollback

Run `bash container_runtime/scripts/rollback.sh` for the rollback procedure. R2 objects are immutable versioned assets and do not need deletion.

