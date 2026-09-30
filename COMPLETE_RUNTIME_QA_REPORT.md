# DharmaCodex Complete Runtime v1.1.6-container.1 — QA

Status: `READY_FOR_AUTHENTICATED_DEPLOY`

## Runtime verification

- Canonical master SHA-256: `c615231ae6aebaff13097d89fc87a7bfe576eddccc637f060684634050fee27f` — PASS.
- Canonical master is copied read-only and loaded without executing Colab top-level cells — PASS.
- Python 3.12 dependency wheel resolution, including `pyswisseph==2.10.3.2` — PASS.
- FastAPI health and reading endpoints through in-process HTTP client — PASS.
- Four SQLite databases open with `mode=ro&immutable=1`; `PRAGMA integrity_check=ok` — PASS.
- Nine R2 asset hashes verified against `manifest.sha256.json` — PASS.
- No geocoding, dynamic package installation, `/content`, browser calculation, or personal-data persistence — PASS.

## Calculation and parity

- Veronica: Astrology points/angles/houses/aspects, Human Design activations/mechanics, Numerology, and Destiny Matrix equal the frozen Colab output field by field — PASS.
- Josué 12:50: complete normalized snapshot repeatability across all four systems — PASS.
- Josué legacy checkpoints: Sun Aquarius/House 10, Moon Aries/House 12, Mercury Aquarius/House 11, Projector, Karmic Tail `15.18.6`, Life Path 33 and Expression 33 — PASS.
- Third arbitrary input produces a distinct calculated reading — PASS; runtime is not fixture-only.
- Astrology balance derives from canonical calculated points joined to `Astro_Readings_V2.0.SIGNS` — PASS.
- Karmic Tail uses the exact ordered triad; `NOT_FOUND` omits and duplicates fail closed as `AMBIGUOUS_KARMIC_TAIL` — PASS.

## Renderer verification

- Astrology wheel: real calculated SVG and HTML — PASS.
- Human Design: real `BodyGraph.svg`, 64 gates, 9 centers, 36 channels — PASS; INTERNAL ONLY.
- Numerology: core, cycles, challenges, natal grid, arrows, DB readings — PASS.
- Destiny Matrix: real `DM.svg`, 32 injected nodes and DB readings — PASS.
- Visible HTML excludes `/content`, DB paths, QA labels, `PASS_WITH_IMPROVEMENTS`, `No synthesis`, `No PDF`, and runtime diagnostics — PASS.

## Cloudflare integration

- Pages Function compiles — PASS.
- Worker bundles with `RUNTIME_BUCKET`, Container Durable Object and no public Worker route — PASS.
- R2 egress is limited to the `runtime-assets` outbound handler and ten exact keys (manifest plus nine assets) — PASS.
- Pages Function requires a Cloudflare Access assertion and forwards through `RUNTIME_SERVICE` — PASS.
- Wrangler dry-run resolves the Worker, R2 binding, Durable Object and Dockerfile — PASS with `--containers-rollout=none`.
- Image build was not executable in this managed session because its kernel prohibits Docker daemon sockets/mount propagation. The Python runtime and exact image dependency set were executed locally; authenticated Cloudflare deployment remains the release boundary.

## Automated tests

`pytest`: 8 passed.

1. Canonical master hash.
2. Asset hashes and SQLite integrity/read-only access.
3. Veronica field-by-field parity.
4. Josué field-by-field parity.
5. Four real renderers and clean visual output.
6. Dynamic third input.
7. Health endpoint.
8. Reading API endpoint.

## Public regression

Unchanged hashes:

- `cloudflare_public/index.html`: `e795669dd0a59244030010d19aeb3f86423a33d6015ea23570a8ce3580b1040f`
- `cloudflare_public/assets/styles.css`: `723d7560fd1de6d3292ecbac3eaab576627711541805ddaaa5127c910fb582eb`
- `cloudflare_public/brujula/app.js`: `a905a97bf85ec89b3e24f4642f20f5ca1110019444443b5904d47830ba02bec0`
- `cloudflare_public/camino-1/app.js`: `21eaeb5649dd8e7ebe7d939590977895e5bf3faede947bd43f6a7827afc22695`

No public page links to `/internal/reading/`.

## Deployment

After `wrangler login`, run exactly:

```bash
bash container_runtime/scripts/deploy.sh
```

