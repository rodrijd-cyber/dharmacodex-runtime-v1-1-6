#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "DHARMACODEX_ORG_COMPLETE_RUNTIME_V1_1_6_CONTAINER_DELTA.zip"
MANIFEST = ROOT / "DHARMACODEX_ORG_COMPLETE_RUNTIME_V1_1_6_CONTAINER_MANIFEST.json"
INCLUDE_ROOTS = [ROOT / "cloudflare_public", ROOT / "container_runtime"]
INCLUDE_FILES = [ROOT / "COMPLETE_RUNTIME_QA_REPORT.md"]
EXCLUDED_PARTS = {"node_modules", "dist", ".pages-functions-dist", "__pycache__", ".pytest_cache", ".fixture-runtime", ".test-runtime", "local_assets"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def candidates() -> list[Path]:
    files = list(INCLUDE_FILES)
    for base in INCLUDE_ROOTS:
        for path in base.rglob("*"):
            parts = path.relative_to(ROOT).parts
            if not path.is_file() or any(
                part in EXCLUDED_PARTS or part.startswith(".pages-functions-dist") or part.startswith("dist")
                for part in parts
            ):
                continue
            files.append(path)
    return sorted(set(files), key=lambda item: item.as_posix())


def main() -> None:
    files = candidates()
    manifest = {
        "release": "DHARMACODEX_ORG_COMPLETE_RUNTIME_V1_1_6_CONTAINER_DELTA",
        "status": "READY_FOR_AUTHENTICATED_DEPLOY",
        "canonical_master_sha256": "c615231ae6aebaff13097d89fc87a7bfe576eddccc637f060684634050fee27f",
        "deployment_command": "bash container_runtime/scripts/deploy.sh",
        "files": [{"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "size_bytes": path.stat().st_size} for path in files],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files.append(MANIFEST)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(files, key=lambda item: item.as_posix()):
            archive.write(path, path.relative_to(ROOT))
    print(json.dumps({"output": str(OUTPUT), "sha256": sha256(OUTPUT), "size_bytes": OUTPUT.stat().st_size, "files": len(files)}, indent=2))


if __name__ == "__main__":
    main()
