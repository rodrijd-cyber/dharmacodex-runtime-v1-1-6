from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.asset_manager import AssetManager, REQUIRED_RELATIVE_PATHS, sha256_file
from app.master_adapter import generate_complete_internal_reading
from app.master_loader import MASTER_PATH, MASTER_SHA256
from app.schemas import ReadingInput


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUTS = {
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


@pytest.fixture(scope="session")
def assets():
    return AssetManager().prepare()


@pytest.fixture(scope="session", params=["veronica", "josue"])
def calculated(request, assets):
    name = request.param
    return name, generate_complete_internal_reading(ReadingInput(**FIXTURE_INPUTS[name]), assets)


def parity_projection(bundle: dict) -> dict:
    systems = bundle["systems"]
    astro = systems["astrology"]["normalized"]
    hd = systems["human_design"]["normalized"]
    num = systems["numerology"]["normalized"]
    dm = systems["destiny_matrix"]["normalized"]
    projection = {
        "input": bundle["input_context"],
        "astrology": {"points": astro["points"], "angles": astro["angles"], "houses": astro["houses"], "aspects": astro["aspects"], "balance": astro["balance"]},
        "human_design": {"personality": hd["personality"], "design": hd["design"], "gate_states": hd["gate_states"], "active_channels": hd["active_channels"], "defined_centers": hd["defined_centers"], "open_centers": hd["open_centers"], "type": hd["type"], "strategy": hd["strategy"], "authority": hd["authority"], "profile": hd["profile"], "incarnation_cross": hd["internal_readings"]["incarnation_cross"]},
        "numerology": {"core": num["core"], "markers": num["markers"], "life_stages": num["life_stages"], "natal_grid": num["natal_grid"], "digit_counts": num["digit_counts"], "arrows": num["arrows"]},
        "destiny_matrix": {"values": dm["matrix"]["values"], "channels": dm["matrix"]["channels"], "karmic_tail_governance": dm["matrix"]["karmic_tail_governance"], "life_cycle": dm["life_cycle"]},
        "geometry": {"human_design": systems["human_design"]["visual"]["geometry"], "destiny_matrix": systems["destiny_matrix"]["visual"]["geometry"]},
    }
    return json.loads(json.dumps(projection, ensure_ascii=False))


def test_canonical_master_is_exact():
    assert sha256_file(MASTER_PATH) == MASTER_SHA256


def test_all_assets_verified_and_sqlite_readonly(assets):
    manifest = json.loads(assets.manifest.read_text(encoding="utf-8"))
    entries = {item["path"]: item["sha256"] for item in manifest["files"]}
    assert set(entries) == set(REQUIRED_RELATIVE_PATHS)
    for relative, expected in entries.items():
        assert sha256_file(assets.path(relative)) == expected
    for filename in ("Astro_Readings_V2.0.db", "HD_DB_v2.0.db", "NUM_DB_v2.0.db", "DM_DB_v2.0.db"):
        connection = sqlite3.connect(f"file:{assets.db(filename).resolve()}?mode=ro&immutable=1", uri=True)
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        connection.close()


def test_field_by_field_parity(calculated):
    name, bundle = calculated
    expected = json.loads((ROOT / "fixtures" / f"{name}.parity.json").read_text(encoding="utf-8"))
    assert parity_projection(bundle) == expected


def test_four_real_renderers_and_clean_ui(calculated):
    _name, bundle = calculated
    assert set(bundle["systems"]) == {"astrology", "human_design", "numerology", "destiny_matrix"}
    forbidden = re.compile(r"/content|PASS_WITH_IMPROVEMENTS|No synthesis|No PDF|Synthesis Gate|\.db(?:<|\s)", re.I)
    for system in bundle["systems"].values():
        html = system["visual"]["html"]
        assert "<html" in html.lower()
        assert not forbidden.search(html)
    assert bundle["systems"]["human_design"]["visual"]["geometry"]["gates"] == 64
    assert bundle["systems"]["human_design"]["visual"]["geometry"]["centers"] == 9
    assert bundle["systems"]["human_design"]["visual"]["geometry"]["channels"] == 36
    assert bundle["systems"]["destiny_matrix"]["visual"]["geometry"]["nodes"] == 32


def test_no_fixture_only_runtime(assets):
    third = ReadingInput(full_name="Prueba Dinámica", birth_date="1991-06-12", birth_time="07:14", city="Monterrey", country="Mexico", latitude=25.6866, longitude=-100.3161, timezone="America/Monterrey", focus="Trabajo", experience="Avanzado")
    result = generate_complete_internal_reading(third, assets)
    assert result["systems"]["astrology"]["normalized"]["points"]["Sol"]["longitude"] != 129.70005881717933
    assert len(result["systems"]["destiny_matrix"]["normalized"]["matrix"]["values"]) == 32


def test_fastapi_health_and_post():
    from app.service import app
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        response = client.post("/internal/reading", json=FIXTURE_INPUTS["veronica"])
        assert response.status_code == 200
        assert len(response.json()["systems"]) == 4
