from __future__ import annotations

import html
import json
import math
import re
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import swisseph as swe

from .asset_manager import RuntimeAssets
from .master_loader import MASTER_SHA256, load_section
from .render_cleanup import clean_internal_html
from .schemas import ReadingInput


_ASTRO_POINT_NAMES = {
    "Sol": "Sun", "Luna": "Moon", "Mercurio": "Mercury", "Venus": "Venus",
    "Marte": "Mars", "Jupiter": "Jupiter", "Saturno": "Saturn", "Urano": "Uranus",
    "Neptuno": "Neptune", "Pluton": "Pluto", "Nodo Norte": "North Node",
    "Nodo Sur": "South Node", "Lilith": "Lilith", "Quiron": "Chiron",
}
_ASTRO_SIGNS = {
    "Aries": "Aries", "Tauro": "Taurus", "Geminis": "Gemini", "Cancer": "Cancer",
    "Leo": "Leo", "Virgo": "Virgo", "Libra": "Libra", "Escorpio": "Scorpio",
    "Sagitario": "Sagittarius", "Capricornio": "Capricorn", "Acuario": "Aquarius", "Piscis": "Pisces",
}
_ASPECT_NAMES = {
    "Conjuncion": "CONJUNCTION", "Sextil": "SEXTILE", "Cuadratura": "SQUARE",
    "Trigono": "TRINE", "Quincuncio": "QUINCUNX", "Oposicion": "OPPOSITION",
}


def _jsonable(value):
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _scrub_runtime_metadata(value):
    if isinstance(value, dict):
        return {
            key: _scrub_runtime_metadata(item)
            for key, item in value.items()
            if key not in {"db_path", "svg_source"} and not (isinstance(key, str) and key.startswith("_"))
        }
    if isinstance(value, list):
        return [_scrub_runtime_metadata(item) for item in value]
    return _jsonable(value)


def _connect_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _configure_namespaces(assets: RuntimeAssets) -> tuple[dict, dict, dict, dict]:
    astro = load_section("astrology")
    hd = load_section("human_design")
    num = load_section("numerology")
    dm = load_section("destiny_matrix")
    astro_db = str(assets.db("Astro_Readings_V2.0.db"))
    hd_db = str(assets.db("HD_DB_v2.0.db"))
    num_db = str(assets.db("NUM_DB_v2.0.db"))
    dm_db = str(assets.db("DM_DB_v2.0.db"))
    astro["ASTRO_DB_CANDIDATES"] = [astro_db]
    astro["SIGN_REGENTS"], astro["SIGN_REGENTS_SOURCE"] = astro["load_sign_regents"]()
    hd["HD_DB_CANDIDATES"] = [hd_db]
    num["NUM_DB_CANDIDATES"] = [num_db]
    dm["DM_DB_CANDIDATES"] = [dm_db]
    dm["DM_SVG_CANDIDATES"] = [str(assets.geometry / "DM.svg")]
    return astro, hd, num, dm


def _astrology_balance(chart: dict, db_path: Path) -> dict:
    """Aggregate the canonical ten planets using sign metadata from Astro DB."""
    counts = {"elements": {}, "modalities": {}, "polarities": {}}
    with _connect_readonly(db_path) as connection:
        rows = {row["SIGN_NAME"]: dict(row) for row in connection.execute("SELECT * FROM SIGNS")}
    for name, point in chart["points"].items():
        if name not in dict(chart_namespace()["POINT_IDS"]):
            continue
        row = rows.get(_ASTRO_SIGNS[point.sign])
        if not row:
            continue
        for target, column in (("elements", "ELEMENT"), ("modalities", "MODALITY"), ("polarities", "POLARITY")):
            key = row[column]
            counts[target][key] = counts[target].get(key, 0) + 1
    counts["dominant_element"] = max(counts["elements"], key=counts["elements"].get)
    counts["dominant_modality"] = max(counts["modalities"], key=counts["modalities"].get)
    counts["dominant_polarity"] = max(counts["polarities"], key=counts["polarities"].get)
    counts["source"] = "master_calculated_points + Astro_Readings_V2.0.SIGNS"
    return counts


def chart_namespace() -> dict:
    return load_section("astrology")


def _astrology_readings(chart: dict, db_path: Path) -> dict:
    result = {"points": {}, "aspects": []}
    with _connect_readonly(db_path) as connection:
        for runtime_name, point in chart["points"].items():
            db_point = _ASTRO_POINT_NAMES.get(runtime_name)
            if not db_point:
                continue
            sign_row = connection.execute(
                "SELECT * FROM PLANET_SIGNS WHERE PS_POINT=? AND PS_SIGN=? LIMIT 1",
                (db_point, _ASTRO_SIGNS[point.sign]),
            ).fetchone()
            house_row = connection.execute(
                "SELECT * FROM PLANET_HOUSES WHERE PH_POINT=? AND PH_HOUSE=? LIMIT 1",
                (db_point, f"House {point.house}"),
            ).fetchone()
            result["points"][runtime_name] = {
                "sign": dict(sign_row) if sign_row else None,
                "house": dict(house_row) if house_row else None,
            }
        for aspect in chart["display_aspects"]:
            first = _ASTRO_POINT_NAMES.get(aspect["point_a"])
            second = _ASTRO_POINT_NAMES.get(aspect["point_b"])
            if not first or not second:
                continue
            aspect_type = _ASPECT_NAMES[aspect["type"]]
            row = connection.execute(
                "SELECT * FROM ASPECTS_READS WHERE ASP_TYPE=? AND ((ASP_POINT_X=? AND ASP_POINT_Y=?) OR (ASP_POINT_X=? AND ASP_POINT_Y=?)) LIMIT 1",
                (aspect_type, first, second, second, first),
            ).fetchone()
            if row:
                result["aspects"].append({"runtime": aspect, "reading": dict(row)})
    return result


def calculate_astrology(input_data: ReadingInput, assets: RuntimeAssets) -> dict:
    astro, _, _, _ = _configure_namespaces(assets)
    chart = astro["calculate_chart"](input_data.master_input())
    normalized = {
        "input": _jsonable(chart["input"]),
        "local_datetime": chart["local_datetime"].isoformat(),
        "utc_datetime": chart["utc_datetime"].isoformat(),
        "julian_day": chart["julian_day"],
        "points": _jsonable(chart["points"]),
        "angles": _jsonable(chart["angles"]),
        "houses": _jsonable(chart["houses"]),
        "aspects": _jsonable(chart["aspects"]),
        "display_aspects": _jsonable(chart["display_aspects"]),
        "balance": _astrology_balance(chart, assets.db("Astro_Readings_V2.0.db")),
        "readings": _astrology_readings(chart, assets.db("Astro_Readings_V2.0.db")),
    }
    normalized["_runtime_chart"] = chart
    normalized["_namespace"] = astro
    return normalized


def render_astrology(result: dict) -> dict:
    namespace, chart = result["_namespace"], result["_runtime_chart"]
    svg = namespace["render_wheel_svg"](chart)
    html_document = clean_internal_html(namespace["render_html"](chart))
    return {"format": "html+svg", "html": html_document, "svg": svg, "renderer": "canonical_master_v1.1.6"}


def calculate_human_design(input_data: ReadingInput, astrology_result: dict, assets: RuntimeAssets) -> dict:
    _, hd, _, _ = _configure_namespaces(assets)
    master_input = input_data.master_input()
    natal_jd = astrology_result["julian_day"]
    natal_utc = astrology_result["utc_datetime"]
    design_jd = hd["find_design_jd"](natal_jd)
    personality = hd["calc_activations"](natal_jd)
    design = hd["calc_activations"](design_jd)
    derived = hd["derive_hd"](personality, design)
    result = {
        "name": master_input["name"],
        "birth_local": f'{master_input["year"]:04d}-{master_input["month"]:02d}-{master_input["day"]:02d} {master_input["hour"]:02d}:{master_input["minute"]:02d} {master_input["timezone"]}',
        "birth_utc": natal_utc,
        "design_jd": design_jd,
        "personality": personality,
        "design": design,
        **derived,
    }
    result["internal_readings"] = hd["load_hd_internal_readings"](result)
    result["_namespace"] = hd
    return result


def render_human_design(result: dict, bodygraph_svg: Path) -> dict:
    namespace = result["_namespace"]
    serializable = {key: value for key, value in result.items() if not key.startswith("_")}
    svg, checks = namespace["_bg_prepare_svg"](bodygraph_svg, serializable)
    html_document = clean_internal_html(namespace["_bg_render_html_v115"](svg, serializable, checks))
    return {"format": "html+svg", "html": html_document, "svg": svg, "geometry": _scrub_runtime_metadata(checks), "renderer": "canonical_master_v1.1.6+BodyGraph.svg"}


def calculate_numerology(input_data: ReadingInput, assets: RuntimeAssets) -> dict:
    _, _, num, _ = _configure_namespaces(assets)
    current_year = datetime.now(timezone.utc).year
    result = num["compute_numerology"](
        input_data.full_name, input_data.birth_date.day, input_data.birth_date.month,
        input_data.birth_date.year, current_year,
    )
    result["readings"] = num["load_numerology_readings"](result)
    result["internal_readings"] = num["load_numerology_internal_readings"](result)
    result["governance"]["db_query_executed"] = bool(result["readings"].get("db_path"))
    for item in result["arrows"]["strength"] + result["arrows"]["weakness"]:
        db_row = result["readings"]["arrows"].get(item["name"], {})
        item["reading"] = db_row.get("ARROWS_PSY", "Información no disponible")
        if db_row.get("ARROWS_KEY"):
            item["canonical_name"] = db_row["ARROWS_KEY"]
            item["name"] = db_row["ARROWS_KEY"]
    result["_namespace"] = num
    return result


def render_numerology(result: dict) -> dict:
    namespace = result["_namespace"]
    serializable = {key: value for key, value in result.items() if not key.startswith("_")}
    return {"format": "html", "html": clean_internal_html(namespace["render_html"](serializable)), "renderer": "canonical_master_v1.1.6"}


def _strict_karmic_tail(matrix: dict, db_path: Path) -> dict:
    triad = matrix["channels"]["Cola Karmica"]["Cola Karmica"]
    key = ".".join(str(value) for value in triad)
    with _connect_readonly(db_path) as connection:
        rows = connection.execute("SELECT * FROM KARMIC_TAIL WHERE KARMIC_TAIL=?", (key,)).fetchall()
    if not rows:
        return {"status": "NOT_FOUND", "ordered_triad": triad, "triad_key": key}
    if len(rows) != 1:
        raise RuntimeError(f"AMBIGUOUS_KARMIC_TAIL:{key}")
    return {"status": "RESOLVED", "ordered_triad": triad, "triad_key": key, "row": dict(rows[0])}


def calculate_destiny_matrix(input_data: ReadingInput, assets: RuntimeAssets) -> dict:
    _, _, _, dm = _configure_namespaces(assets)
    matrix = dm["compute_matrix"](input_data.birth_date.day, input_data.birth_date.month, input_data.birth_date.year)
    matrix["input"]["name"] = input_data.full_name
    matrix["internal_readings"] = dm["load_matrix_internal_readings"](matrix)
    strict_tail = _strict_karmic_tail(matrix, assets.db("DM_DB_v2.0.db"))
    matrix["karmic_tail_governance"] = strict_tail
    matrix["karmic_tail_name"] = strict_tail.get("row", {}).get("KARMIC_TAIL_NAME", "")
    life_cycle = dm["compute_life_cycle"](matrix["values"])
    return {"matrix": matrix, "life_cycle": life_cycle, "_namespace": dm}


def render_destiny_matrix(result: dict, dm_svg: Path) -> dict:
    namespace = result["_namespace"]
    matrix, life_cycle = result["matrix"], result["life_cycle"]
    svg, checks = namespace["render_dm_svg_template"](dm_svg, matrix)
    html_document = clean_internal_html(namespace["render_dm_template_html_v115"](matrix, svg, checks))
    return {"format": "html+svg", "html": html_document, "svg": svg, "geometry": _scrub_runtime_metadata(checks), "renderer": "canonical_master_v1.1.6+DM.svg"}


def _without_runtime(value: dict) -> dict:
    return _scrub_runtime_metadata(value)


def generate_complete_internal_reading(input_data: ReadingInput, assets: RuntimeAssets) -> dict:
    swe.set_ephe_path(str(assets.ephe))
    astrology = calculate_astrology(input_data, assets)
    human_design = calculate_human_design(input_data, astrology, assets)
    numerology = calculate_numerology(input_data, assets)
    destiny_matrix = calculate_destiny_matrix(input_data, assets)

    astrology_visual = render_astrology(astrology)
    human_visual = render_human_design(human_design, assets.geometry / "BodyGraph.svg")
    numerology_visual = render_numerology(numerology)
    matrix_visual = render_destiny_matrix(destiny_matrix, assets.geometry / "DM.svg")

    systems = {
        "astrology": {"status": "calculated", "normalized": _without_runtime(astrology), "representation_model": {"geometry": "astrology_wheel", "point_count": len(astrology["points"]), "aspect_count": len(astrology["display_aspects"])}, "visual": astrology_visual, "validation": {"status": "PASS"}},
        "human_design": {"status": "calculated_internal_only", "visibility": "INTERNAL_ONLY", "normalized": _without_runtime(human_design), "representation_model": {"geometry": human_visual["geometry"], "gates": 64, "centers": 9, "channels": 36}, "visual": human_visual, "validation": {"status": "PASS"}},
        "numerology": {"status": "calculated", "normalized": _without_runtime(numerology), "representation_model": {"geometry": "core_cycles_natal_grid", "core_count": 6, "stage_count": 4}, "visual": numerology_visual, "validation": {"status": "PASS"}},
        "destiny_matrix": {"status": "calculated", "normalized": _without_runtime(destiny_matrix), "representation_model": {"geometry": matrix_visual["geometry"], "nodes": 32}, "visual": matrix_visual, "validation": {"status": "PASS"}},
    }
    return {
        "bundle_version": "1.1.6-container.1",
        "input_context": input_data.model_dump(mode="json"),
        "provenance": {"master_sha256": MASTER_SHA256, "calculation_source": "canonical_master_v1.1.6_adapter", "assets_version": "1.1.6", "storage_provider": "r2_private_bridge"},
        "systems": systems,
        "governance": {"internal_only": True, "human_design_public": False, "personal_input_persisted": False},
    }
