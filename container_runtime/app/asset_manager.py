from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path
from threading import Lock


VERSION = os.getenv("DCX_RUNTIME_VERSION", "1.1.6")
REQUIRED_RELATIVE_PATHS = (
    "databases/Astro_Readings_V2.0.db",
    "databases/DM_DB_v2.0.db",
    "databases/HD_DB_v2.0.db",
    "databases/NUM_DB_v2.0.db",
    "geometry/BodyGraph.svg",
    "geometry/DM.svg",
    "ephe/sepl_18.se1",
    "ephe/seas_18.se1",
    "ephe/semoon_18.se1",
)


class AssetVerificationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_entries(payload: dict) -> dict[str, str]:
    raw = payload.get("files", payload)
    if isinstance(raw, list):
        return {
            str(item.get("path") or item.get("key")): str(item.get("sha256", "")).lower()
            for item in raw
            if isinstance(item, dict)
        }
    if isinstance(raw, dict):
        return {
            str(key): str(value.get("sha256") if isinstance(value, dict) else value).lower()
            for key, value in raw.items()
        }
    raise AssetVerificationError("RUNTIME_MANIFEST_INVALID")


class RuntimeAssets:
    def __init__(self, root: Path):
        self.root = root
        self.databases = root / "databases"
        self.geometry = root / "geometry"
        self.ephe = root / "ephe"
        self.manifest = root / "manifest.sha256.json"

    def path(self, relative: str) -> Path:
        return self.root / relative

    def db(self, filename: str) -> Path:
        return self.databases / filename


class AssetManager:
    def __init__(self) -> None:
        self.runtime_root = Path(os.getenv("DCX_RUNTIME_ROOT", "/app/runtime")) / VERSION
        self.base_url = os.getenv("DCX_ASSET_BASE_URL", f"http://runtime-assets/v{VERSION}").rstrip("/")
        local = os.getenv("DCX_LOCAL_ASSET_ROOT")
        self.local_root = Path(local).resolve() if local else None
        self._lock = Lock()
        self._ready: RuntimeAssets | None = None

    def prepare(self) -> RuntimeAssets:
        with self._lock:
            if self._ready is not None:
                return self._ready
            self.runtime_root.parent.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix=f"dcx-{VERSION}-", dir=self.runtime_root.parent))
            try:
                manifest_bytes = self._read("manifest.sha256.json")
                payload = json.loads(manifest_bytes)
                entries = _manifest_entries(payload)
                for relative in REQUIRED_RELATIVE_PATHS:
                    expected = entries.get(relative) or entries.get(f"v{VERSION}/{relative}")
                    if not expected or len(expected) != 64:
                        raise AssetVerificationError(f"RUNTIME_MANIFEST_ENTRY_MISSING:{relative}")
                    target = stage / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(self._read(relative))
                    actual = sha256_file(target)
                    if actual != expected:
                        raise AssetVerificationError(f"RUNTIME_ASSET_HASH_MISMATCH:{relative}")
                (stage / "manifest.sha256.json").write_bytes(manifest_bytes)
                # Preserve the canonical master asset names byte-for-byte. The
                # adapter must not silently rename an ephemeris and change parity.
                if self.runtime_root.exists():
                    shutil.rmtree(self.runtime_root)
                stage.rename(self.runtime_root)
            except Exception:
                shutil.rmtree(stage, ignore_errors=True)
                raise
            self._ready = RuntimeAssets(self.runtime_root)
            return self._ready

    def _read(self, relative: str) -> bytes:
        if self.local_root is not None:
            candidate = self.local_root / relative
            if not candidate.is_file():
                raise AssetVerificationError(f"RUNTIME_ASSET_MISSING:{relative}")
            return candidate.read_bytes()
        url = f"{self.base_url}/{relative}"
        request = urllib.request.Request(url, headers={"accept": "application/octet-stream"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except Exception as exc:
            raise AssetVerificationError(f"RUNTIME_ASSET_BRIDGE_FAILED:{relative}") from exc
