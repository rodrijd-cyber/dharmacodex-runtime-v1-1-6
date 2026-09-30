#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DCX_LOCAL_ASSET_ROOT"] = str(ROOT / "r2_upload/v1.1.6")
os.environ["DCX_RUNTIME_ROOT"] = str(ROOT / ".fixture-runtime")

from app.asset_manager import AssetManager  # noqa: E402
from app.master_adapter import generate_complete_internal_reading  # noqa: E402
from app.schemas import ReadingInput  # noqa: E402


FIXTURES = {
    "veronica": {
        "full_name": "Veronica Idali Cazares Diaz", "birth_date": "1988-08-01", "birth_time": "12:30",
        "city": "Juárez, Chihuahua", "country": "Mexico", "latitude": 31.7389744,
        "longitude": -106.4832065, "timezone": "America/Ciudad_Juarez",
        "focus": "Propósito y Misión", "experience": "Ninguna (Desde Cero)",
    },
    "josue": {
        "full_name": "Josué Daniel Rodríguez Prieto", "birth_date": "1988-01-24", "birth_time": "12:50",
        "city": "Chihuahua, Chihuahua", "country": "Mexico", "latitude": 28.6353,
        "longitude": -106.0889, "timezone": "America/Chihuahua",
        "focus": "Propósito y dirección", "experience": "Avanzado",
    },
}


def snapshot(bundle: dict) -> dict:
    systems = bundle["systems"]
    astro = systems["astrology"]["normalized"]
    hd = systems["human_design"]["normalized"]
    num = systems["numerology"]["normalized"]
    dm = systems["destiny_matrix"]["normalized"]
    return {
        "input": bundle["input_context"],
        "astrology": {
            "points": astro["points"], "angles": astro["angles"], "houses": astro["houses"],
            "aspects": astro["aspects"], "balance": astro["balance"],
        },
        "human_design": {
            "personality": hd["personality"], "design": hd["design"], "gate_states": hd["gate_states"],
            "active_channels": hd["active_channels"], "defined_centers": hd["defined_centers"],
            "open_centers": hd["open_centers"], "type": hd["type"], "strategy": hd["strategy"],
            "authority": hd["authority"], "profile": hd["profile"],
            "incarnation_cross": hd["internal_readings"]["incarnation_cross"],
        },
        "numerology": {
            "core": num["core"], "markers": num["markers"], "life_stages": num["life_stages"],
            "natal_grid": num["natal_grid"], "digit_counts": num["digit_counts"], "arrows": num["arrows"],
        },
        "destiny_matrix": {
            "values": dm["matrix"]["values"], "channels": dm["matrix"]["channels"],
            "karmic_tail_governance": dm["matrix"]["karmic_tail_governance"],
            "life_cycle": dm["life_cycle"],
        },
        "geometry": {
            "human_design": systems["human_design"]["visual"]["geometry"],
            "destiny_matrix": systems["destiny_matrix"]["visual"]["geometry"],
        },
    }


def main() -> None:
    assets = AssetManager().prepare()
    for name, values in FIXTURES.items():
        bundle = generate_complete_internal_reading(ReadingInput(**values), assets)
        output = ROOT / "fixtures" / f"{name}.parity.json"
        output.write_text(json.dumps(snapshot(bundle), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(output)


if __name__ == "__main__":
    main()

