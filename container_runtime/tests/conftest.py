from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DCX_LOCAL_ASSET_ROOT", str(ROOT / "r2_upload/v1.1.6"))
os.environ.setdefault("DCX_RUNTIME_ROOT", str(ROOT / ".test-runtime"))
