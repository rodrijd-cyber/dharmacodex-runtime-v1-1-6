from __future__ import annotations

import ast
import copy
import html
import json
import math
import os
import re
import sqlite3
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import swisseph as swe


MASTER_SHA256 = "c615231ae6aebaff13097d89fc87a7bfe576eddccc637f060684634050fee27f"
MASTER_PATH = Path(__file__).parent / "canonical" / "Master DharmaCodex V 1.1.6 Internal Reading Renderers Code.PY"

_SECTIONS = {
    "astrology": (212, 1432),
    "human_design": (1432, 2391),
    "numerology": (2391, 3659),
    "destiny_matrix": (3659, 4946),
}

_RUNTIME_ASSIGNMENTS = {
    "MASTER_INPUT", "TEST", "local_dt", "utc_dt", "SIGN_REGENTS", "SIGN_REGENTS_SOURCE",
    "chart", "qc", "html_document", "debug_payload", "qc_markdown",
    "_hd_input", "natal_jd", "natal_utc", "design_jd", "personality", "design", "derived", "result", "checks",
    "_bg_svg_candidates", "_bg_svg_path", "_bg_hd_result", "_bg_svg_markup", "_bg_checks", "_bg_html_out",
    "_num_input", "NOMBRE_COMPLETO", "DIA_NACIMIENTO", "MES_NACIMIENTO", "ANIO_NACIMIENTO", "ANIO_ACTUAL",
    "html", "report_md", "summary", "_dm_input", "NOMBRE_INTERNO", "matrix", "life_cycle", "karmic_triad", "debug",
}


def _names(node: ast.Assign | ast.AnnAssign) -> list[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    found: list[str] = []
    for target in targets:
        if isinstance(target, ast.Name):
            found.append(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            found.extend(item.id for item in target.elts if isinstance(item, ast.Name))
    return found


def _base_namespace() -> dict:
    return {
        "__builtins__": __builtins__, "os": os, "json": json, "math": math, "re": re,
        "sqlite3": sqlite3, "unicodedata": unicodedata, "datetime": datetime,
        "date": date, "timezone": timezone, "ZoneInfo": ZoneInfo, "dataclass": dataclass,
        "asdict": asdict, "Optional": Optional, "Path": Path, "swe": swe,
        "html_escape": html.escape, "copy": copy, "html": html, "ET": ET,
        "_bg_copy": copy, "_bg_html": html, "_bg_re": re, "_bg_ET": ET,
    }


@lru_cache(maxsize=1)
def canonical_source() -> str:
    import hashlib

    payload = MASTER_PATH.read_bytes()
    if hashlib.sha256(payload).hexdigest() != MASTER_SHA256:
        raise RuntimeError("CANONICAL_MASTER_HASH_MISMATCH")
    return payload.decode("utf-8")


@lru_cache(maxsize=4)
def load_section(name: str) -> dict:
    if name not in _SECTIONS:
        raise KeyError(name)
    source = canonical_source()
    tree = ast.parse(source, filename=str(MASTER_PATH))
    start, end = _SECTIONS[name]
    selected: list[ast.stmt] = []
    for node in tree.body:
        line = getattr(node, "lineno", 0)
        if not start <= line < end:
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            selected.append(node)
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = _names(node)
            if not targets or any(target in _RUNTIME_ASSIGNMENTS for target in targets):
                continue
            if all(target.isupper() or target.startswith("_BG_") or target.startswith("_DM_") for target in targets):
                selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = _base_namespace()
    exec(compile(module, str(MASTER_PATH), "exec"), namespace, namespace)
    return namespace

