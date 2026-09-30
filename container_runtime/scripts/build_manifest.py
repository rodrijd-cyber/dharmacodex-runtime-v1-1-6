#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "r2_upload" / "v1.1.6"
REQUIRED = [
    "databases/Astro_Readings_V2.0.db",
    "databases/DM_DB_v2.0.db",
    "databases/HD_DB_v2.0.db",
    "databases/NUM_DB_v2.0.db",
    "geometry/BodyGraph.svg",
    "geometry/DM.svg",
    "ephe/sepl_18.se1",
    "ephe/seas_18.se1",
    "ephe/semoon_18.se1",
]


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> None:
    files = []
    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"missing: {relative}")
        files.append({"path": relative, "sha256": digest(path), "size_bytes": path.stat().st_size})
    payload = {
        "manifest_version": "1.1.6-container.1",
        "asset_prefix": "v1.1.6",
        "files": files,
    }
    output = ROOT / "manifest.sha256.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

