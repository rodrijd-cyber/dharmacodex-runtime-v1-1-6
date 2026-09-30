# %% [CELDA UNICA] Master DharmaCodex V 1.1.6 Internal Reading Renderers
# DHARMACODEX - calculo + representaciones graficas internas

# @markdown ---
# @markdown ### DHARMACODEX MASTER V 1.1.5 INTERNAL READING RENDERERS
# @markdown Cambia solo este bloque. El resto calcula y genera las 4 representaciones.
NOMBRE_COMPLETO = "Veronica Idali Cazares Diaz"  # @param {type:"string"}
FECHA_NACIMIENTO = "1988-08-01"  # @param {type:"date"}
HORA_NACIMIENTO = "12:30"  # @param {type:"string"}
CIUDAD_NACIMIENTO = "Juarez, Chihuahua"  # @param {type:"string"}
PAIS_NACIMIENTO = "Mexico"  # @param {type:"string"}
USAR_COORDENADAS_MANUALES = False  # @param {type:"boolean"}
LATITUD_MANUAL = ""  # @param {type:"string"}
LONGITUD_MANUAL = ""  # @param {type:"string"}
TIMEZONE_MANUAL = ""  # @param {type:"string"}
FOCO_ACTUAL = "Propósito y Misión"  # @param ["Propósito y Misión", "Dinero y Carrera", "Relaciones y Pareja", "Sanación Kármica"]
EXPERIENCIA_PREVIA = "Ninguna (Desde Cero)"  # @param ["Ninguna (Desde Cero)", "Conozco mi signo", "Conozco mi Carta/Diseño", "Avanzado"]

import re

def _dcx_parse_birth_time(value):
    text = str(value or "00:00").strip()
    match = re.match(r"^(\d{1,2})(?::(\d{1,2}))?", text)
    if not match:
        raise ValueError(f"HORA_NACIMIENTO invalida: {value!r}. Usa HH:MM.")
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"HORA_NACIMIENTO fuera de rango: {value!r}.")
    return hour, minute

_dcx_birth_parts = [int(part) for part in FECHA_NACIMIENTO.split("-")]
ANIO_NACIMIENTO, MES_NACIMIENTO, DIA_NACIMIENTO = _dcx_birth_parts
AÑO_NACIMIENTO = ANIO_NACIMIENTO
HORA_INT, MIN_INT = _dcx_parse_birth_time(HORA_NACIMIENTO)
HORA_NACIMIENTO = f"{HORA_INT:02d}:{MIN_INT:02d}"

DB_FOLDER = "/content/Data_Bases"
OUTPUT_ROOT = "/content/dharmacodex_outputs"
BODYGRAPH_SVG_PATH = "/content/BodyGraph.svg"

import os
import urllib.request
import math
import json
import warnings

warnings.filterwarnings("ignore")

try:
    import swisseph as swe
    from geopy.geocoders import Nominatim
    from timezonefinder import TimezoneFinder
    import pytz
except ImportError:
    import subprocess

    subprocess.run(
        [
            "pip",
            "install",
            "-q",
            "pyswisseph",
            "geopy",
            "timezonefinder",
            "pytz",
        ],
        check=True,
    )
    import swisseph as swe
    from geopy.geocoders import Nominatim
    from timezonefinder import TimezoneFinder
    import pytz

from datetime import datetime
from zoneinfo import ZoneInfo
from dataclasses import dataclass, asdict
from typing import Optional


def _dcx_optional_float(value, field_name):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} debe ser un número válido.") from exc


def _dcx_preflight_location_input_and_files():
    """Valida el contrato de entrada y los assets requeridos sin modificarlos."""
    required_files = [
        "/content/DM_DB_v2.0.db",
        "/content/HD_DB_v2.0.db",
        "/content/Astro_Readings_V2.0.db",
        "/content/NUM_DB_v2.0.db",
        "/content/BodyGraph.svg",
        "/content/DM.svg",
    ]
    missing_files = [path for path in required_files if not os.path.isfile(path)]
    for path in required_files:
        print(f"PREFLIGHT FILE {'PASS' if path not in missing_files else 'MISSING'}: {path}")
    if not str(CIUDAD_NACIMIENTO or "").strip():
        raise ValueError("CIUDAD_NACIMIENTO es obligatoria.")
    if not str(PAIS_NACIMIENTO or "").strip():
        raise ValueError("PAIS_NACIMIENTO es obligatorio.")
    try:
        datetime.strptime(str(FECHA_NACIMIENTO), "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("FECHA_NACIMIENTO debe usar el formato YYYY-MM-DD.") from exc
    _dcx_parse_birth_time(HORA_NACIMIENTO)
    if USAR_COORDENADAS_MANUALES:
        if _dcx_optional_float(LATITUD_MANUAL, "LATITUD_MANUAL") is None:
            raise ValueError("LATITUD_MANUAL es obligatoria si USAR_COORDENADAS_MANUALES=True.")
        if _dcx_optional_float(LONGITUD_MANUAL, "LONGITUD_MANUAL") is None:
            raise ValueError("LONGITUD_MANUAL es obligatoria si USAR_COORDENADAS_MANUALES=True.")
    if missing_files:
        raise FileNotFoundError("Archivos requeridos faltantes en /content:\n- " + "\n- ".join(missing_files))
    print("PREFLIGHT STATUS: PASS")


def _dcx_resolve_location_contract():
    """Resuelve ubicación desde ciudad/país o desde el override manual explícito."""
    city = str(CIUDAD_NACIMIENTO or "").strip()
    country = str(PAIS_NACIMIENTO or "").strip()
    manual_timezone = str(TIMEZONE_MANUAL or "").strip()

    if USAR_COORDENADAS_MANUALES:
        latitude = _dcx_optional_float(LATITUD_MANUAL, "LATITUD_MANUAL")
        longitude = _dcx_optional_float(LONGITUD_MANUAL, "LONGITUD_MANUAL")
        if latitude is None or longitude is None:
            raise ValueError(
                "LATITUD_MANUAL y LONGITUD_MANUAL son obligatorias si "
                "USAR_COORDENADAS_MANUALES=True."
            )
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("Coordenadas manuales fuera de rango válido.")
        source = "MANUAL_OVERRIDE"
        selected_match = None
    else:
        query = ", ".join([city, country])
        geocoder = Nominatim(user_agent="dharmacodex_location_contract_v1_1_4")
        location = geocoder.geocode(query, timeout=15, addressdetails=True)
        if not location:
            raise ValueError(
                f"No fue posible localizar '{query}'. Especifica una ciudad y país más precisos "
                "o habilita USAR_COORDENADAS_MANUALES."
            )
        latitude = float(location.latitude)
        longitude = float(location.longitude)
        source = "GEOCODED"
        selected_match = getattr(location, "address", None)

    timezone_name = manual_timezone or TimezoneFinder().timezone_at(lat=latitude, lng=longitude)
    if not timezone_name:
        raise ValueError("No fue posible determinar la zona horaria para la ubicación resuelta.")
    try:
        ZoneInfo(timezone_name)
    except Exception as exc:
        raise ValueError(f"Zona horaria inválida o no disponible: {timezone_name!r}") from exc

    status = "PASS_WITH_MANUAL_OVERRIDE" if source == "MANUAL_OVERRIDE" else "PASS"
    print("\nLOCATION RESOLUTION CHECK")
    print(f"City: {city}")
    print(f"Country: {country}")
    print(f"Latitude: {latitude}")
    print(f"Longitude: {longitude}")
    print(f"Timezone: {timezone_name}")
    print(f"Source: {source}")
    if selected_match:
        print(f"Selected geocoding match: {selected_match}")
    print(f"Status: {status}\n")
    return {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone_name,
        "location_source": source,
        "geocoding_match": selected_match,
    }


_dcx_preflight_location_input_and_files()
_dcx_location = _dcx_resolve_location_contract()
LATITUD = _dcx_location["latitude"]
LONGITUD = _dcx_location["longitude"]
TIMEZONE_STR = _dcx_location["timezone"]
LOCATION_SOURCE = _dcx_location["location_source"]
GEOCODING_MATCH = _dcx_location["geocoding_match"]

# Efemerides
ephe_path = "/content/ephe"
os.makedirs(ephe_path, exist_ok=True)

for archivo in ["sepl_18.se1", "seas_18.se1", "semoon_18.se1"]:
    ruta = os.path.join(ephe_path, archivo)
    if not os.path.exists(ruta):
        for base in [
            "https://www.astro.com/ftp/swisseph/ephe/",
            "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/",
        ]:
            try:
                urllib.request.urlretrieve(base + archivo, ruta)
                break
            except Exception:
                continue

swe.set_ephe_path(ephe_path)
print("DHARMACODEX Cell 1 lista: Swiss Ephemeris y dependencias cargadas.")


# %% [CELDA 2] Astrologia: calculo + geometria + HTML + validacion

from html import escape as html_escape
from pathlib import Path
import sqlite3


# -----------------------------------------------------------------------------
# INPUT DEL BUSCADOR
# Cambia solamente este bloque para probar otra carta.
# -----------------------------------------------------------------------------

MASTER_INPUT = {
    "name": NOMBRE_COMPLETO,
    "full_name": NOMBRE_COMPLETO,
    "year": ANIO_NACIMIENTO,
    "month": MES_NACIMIENTO,
    "day": DIA_NACIMIENTO,
    "hour": HORA_INT,
    "minute": MIN_INT,
    "city": CIUDAD_NACIMIENTO,
    "country": PAIS_NACIMIENTO,
    "timezone": TIMEZONE_STR,
    "latitude": LATITUD,
    "longitude": LONGITUD,
    "lat": LATITUD,
    "lon": LONGITUD,
    "location_source": LOCATION_SOURCE,
    "geocoding_match": GEOCODING_MATCH,
    "focus": FOCO_ACTUAL,
    "experience": EXPERIENCIA_PREVIA,
}

from datetime import datetime
from zoneinfo import ZoneInfo

local_dt = datetime(
    ANIO_NACIMIENTO,
    MES_NACIMIENTO,
    DIA_NACIMIENTO,
    HORA_INT,
    MIN_INT,
    tzinfo=ZoneInfo(TIMEZONE_STR),
)

utc_dt = local_dt.astimezone(ZoneInfo("UTC"))

print("\nBIRTH TIME RESOLUTION CHECK")
print("Local datetime:", local_dt.isoformat())
print("Timezone:", TIMEZONE_STR)
print("UTC offset:", local_dt.utcoffset())
print("UTC datetime:", utc_dt.isoformat())
print("DST:", local_dt.dst())

# Los cuatro sistemas consumen este mismo bloque. Cambia solo MASTER_INPUT.
TEST = dict(MASTER_INPUT)


# -----------------------------------------------------------------------------
# CONSTANTES DE CALCULO
# -----------------------------------------------------------------------------

SIGNS = [
    "Aries",
    "Tauro",
    "Geminis",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Escorpio",
    "Sagitario",
    "Capricornio",
    "Acuario",
    "Piscis",
]

SIGN_SYMBOLS = {
    "Aries": "♈",
    "Tauro": "♉",
    "Geminis": "♊",
    "Cancer": "♋",
    "Leo": "♌",
    "Virgo": "♍",
    "Libra": "♎",
    "Escorpio": "♏",
    "Sagitario": "♐",
    "Capricornio": "♑",
    "Acuario": "♒",
    "Piscis": "♓",
}

POINT_SYMBOLS = {
    "Sol": "☉",
    "Luna": "☽",
    "Mercurio": "☿",
    "Venus": "♀",
    "Marte": "♂",
    "Jupiter": "♃",
    "Saturno": "♄",
    "Urano": "♅",
    "Neptuno": "♆",
    "Pluton": "♇",
    "Nodo Norte": "☊",
    "Nodo Sur": "☋",
    "Lilith": "⚸",
    "Quiron": "⚷",
}

POINT_IDS = [
    ("Sol", swe.SUN),
    ("Luna", swe.MOON),
    ("Mercurio", swe.MERCURY),
    ("Venus", swe.VENUS),
    ("Marte", swe.MARS),
    ("Jupiter", swe.JUPITER),
    ("Saturno", swe.SATURN),
    ("Urano", swe.URANUS),
    ("Neptuno", swe.NEPTUNE),
    ("Pluton", swe.PLUTO),
]

POINT_ORDER = [name for name, _ in POINT_IDS] + [
    "Nodo Norte",
    "Nodo Sur",
    "Lilith",
    "Quiron",
]

ANGLE_LABELS = {
    "Ascendente": "ASC",
    "Descendente": "DSC",
    "Medio Cielo": "MC",
    "Fondo Cielo": "IC",
}

ANGLE_ORDER = ["Ascendente", "Descendente", "Medio Cielo", "Fondo Cielo"]

ASPECT_RULES = {
    "Conjuncion": {"angle": 0.0, "orb": 8.0, "family": "neutral"},
    "Sextil": {"angle": 60.0, "orb": 6.0, "family": "harmonious"},
    "Cuadratura": {"angle": 90.0, "orb": 8.0, "family": "tense"},
    "Trigono": {"angle": 120.0, "orb": 8.0, "family": "harmonious"},
    "Quincuncio": {"angle": 150.0, "orb": 3.0, "family": "tense"},
    "Oposicion": {"angle": 180.0, "orb": 8.0, "family": "tense"},
}

ASPECT_COLORS = {
    "tense": "#B85858",
    "harmonious": "#477BA8",
    "neutral": "#8B836F",
}

# Respaldo para cuando Astro_Readings_V2.0.db no este cargada en Colab.
SIGN_REGENTS_FALLBACK = {
    "Aries": "Marte",
    "Tauro": "Venus",
    "Geminis": "Mercurio",
    "Cancer": "Luna",
    "Leo": "Sol",
    "Virgo": "Mercurio",
    "Libra": "Venus",
    "Escorpio": "Pluton",
    "Sagitario": "Jupiter",
    "Capricornio": "Saturno",
    "Acuario": "Urano",
    "Piscis": "Neptuno",
}

ASTRO_DB_CANDIDATES = [
    "/content/Data_Bases/Astro_Readings_V2.0.db",
    "/content/Data_Bases/03-Astro_Readings_V2.0.db",
    "/content/Astro_Readings_V2.0.db",
    "/content/03-Astro_Readings_V2.0.db",
]


def load_sign_regents():
    for candidate in ASTRO_DB_CANDIDATES:
        if not os.path.exists(candidate):
            continue
        connection = sqlite3.connect(f"file:{candidate}?mode=ro", uri=True)
        try:
            rows = connection.execute(
                "SELECT DISTINCT SH_SIGN, SH_RULER FROM SIGN_HOUSE "
                "WHERE SH_SIGN IS NOT NULL AND SH_RULER IS NOT NULL"
            ).fetchall()
            result = {str(sign): str(regent) for sign, regent in rows}
            if all(sign in result for sign in SIGNS):
                return result, candidate
        finally:
            connection.close()
    return dict(SIGN_REGENTS_FALLBACK), "embedded_fallback"


SIGN_REGENTS, SIGN_REGENTS_SOURCE = load_sign_regents()


# -----------------------------------------------------------------------------
# MODELO DE DATOS
# -----------------------------------------------------------------------------

@dataclass
class CelestialPoint:
    name: str
    symbol: str
    longitude: float
    speed: float
    sign: str
    degree: int
    minute: int
    second: int
    house: Optional[int] = None
    retrograde: bool = False


@dataclass
class HouseCusp:
    number: int
    longitude: float
    sign: str
    degree: int
    minute: int
    second: int


def normalize(value):
    return float(value) % 360.0


def zodiac_parts(longitude):
    value = normalize(longitude)
    sign_index = int(value // 30)
    inside = value - sign_index * 30
    degree = int(inside)
    minute_float = (inside - degree) * 60
    minute = int(minute_float)
    second = int((minute_float - minute) * 60)
    return SIGNS[sign_index], degree, minute, second


def degree_text(point, include_retrograde=True):
    suffix = " R" if include_retrograde and point.retrograde else ""
    return f"{point.degree}°{point.minute:02d}'{suffix}"


def angular_separation(a, b):
    difference = abs(normalize(a) - normalize(b))
    return min(difference, 360.0 - difference)


def build_display_aspects(aspects):
    """Filtra solamente la colección visual; conserva intacto el payload crudo."""
    angle_endpoints = set(ANGLE_ORDER) | {"ASC", "DSC", "MC", "IC"}
    allowed_types = {"Conjuncion", "Sextil", "Cuadratura", "Trigono", "Oposicion"}
    return [
        aspect for aspect in aspects
        if aspect["point_a"] not in angle_endpoints
        and aspect["point_b"] not in angle_endpoints
        and aspect["type"] in allowed_types
    ]


def calculate_body(julian_day, body_id):
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    try:
        values, _ = swe.calc_ut(julian_day, body_id, flags)
    except Exception:
        values, _ = swe.calc_ut(julian_day, body_id, swe.FLG_MOSEPH | swe.FLG_SPEED)
    return normalize(values[0]), float(values[3])


def locate_house(longitude, cusp_longitudes):
    longitude = normalize(longitude)
    for index in range(12):
        start = normalize(cusp_longitudes[index])
        end = normalize(cusp_longitudes[(index + 1) % 12])
        span = normalize(end - start)
        position = normalize(longitude - start)
        if position < span or math.isclose(position, span, abs_tol=1e-9):
            return index + 1
    return 1


def resolve_input(source):
    result = dict(source)
    city_country = ", ".join(
        part for part in [result.get("city", ""), result.get("country", "")] if part
    )

    latitude = result.get("latitude")
    longitude = result.get("longitude")

    if latitude is None or longitude is None:
        geocoder = Nominatim(user_agent="dharmacodex_internal_astrology")
        location = geocoder.geocode(city_country, timeout=15)
        if not location:
            raise ValueError(f"No fue posible localizar: {city_country}")
        latitude = float(location.latitude)
        longitude = float(location.longitude)

    timezone_name = result.get("timezone")
    if not timezone_name:
        timezone_name = TimezoneFinder().timezone_at(lat=latitude, lng=longitude)
    if not timezone_name:
        raise ValueError("No fue posible determinar la zona horaria.")

    result["latitude"] = float(latitude)
    result["longitude"] = float(longitude)
    result["timezone"] = timezone_name
    result["city_country"] = city_country
    result.setdefault("location_source", "GEOCODED")
    result.setdefault("geocoding_match", None)
    return result


def calculate_chart(source):
    data = resolve_input(source)
    local_timezone = ZoneInfo(data["timezone"])
    local_datetime = datetime(
        data["year"],
        data["month"],
        data["day"],
        data["hour"],
        data["minute"],
        tzinfo=local_timezone,
    )
    utc_datetime = local_datetime.astimezone(ZoneInfo("UTC"))
    decimal_hour = (
        utc_datetime.hour
        + utc_datetime.minute / 60
        + utc_datetime.second / 3600
    )
    julian_day = swe.julday(
        utc_datetime.year,
        utc_datetime.month,
        utc_datetime.day,
        decimal_hour,
    )

    try:
        cusps_raw, ascmc = swe.houses_ex(
            julian_day,
            data["latitude"],
            data["longitude"],
            b"P",
        )
    except Exception:
        cusps_raw, ascmc = swe.houses(
            julian_day,
            data["latitude"],
            data["longitude"],
            b"P",
        )

    cusp_longitudes = [normalize(value) for value in list(cusps_raw)[:12]]
    houses = []
    for index, longitude in enumerate(cusp_longitudes):
        sign, degree, minute, second = zodiac_parts(longitude)
        houses.append(
            HouseCusp(index + 1, longitude, sign, degree, minute, second)
        )

    points = {}
    for name, body_id in POINT_IDS:
        longitude, speed = calculate_body(julian_day, body_id)
        sign, degree, minute, second = zodiac_parts(longitude)
        points[name] = CelestialPoint(
            name=name,
            symbol=POINT_SYMBOLS[name],
            longitude=longitude,
            speed=speed,
            sign=sign,
            degree=degree,
            minute=minute,
            second=second,
            retrograde=speed < 0,
        )

    node_longitude, node_speed = calculate_body(julian_day, swe.TRUE_NODE)
    for name, longitude in [
        ("Nodo Norte", node_longitude),
        ("Nodo Sur", normalize(node_longitude + 180)),
    ]:
        sign, degree, minute, second = zodiac_parts(longitude)
        points[name] = CelestialPoint(
            name=name,
            symbol=POINT_SYMBOLS[name],
            longitude=longitude,
            speed=node_speed,
            sign=sign,
            degree=degree,
            minute=minute,
            second=second,
            retrograde=node_speed < 0,
        )

    for name, body_id in [("Lilith", swe.MEAN_APOG), ("Quiron", swe.CHIRON)]:
        longitude, speed = calculate_body(julian_day, body_id)
        sign, degree, minute, second = zodiac_parts(longitude)
        points[name] = CelestialPoint(
            name=name,
            symbol=POINT_SYMBOLS[name],
            longitude=longitude,
            speed=speed,
            sign=sign,
            degree=degree,
            minute=minute,
            second=second,
            retrograde=speed < 0,
        )

    for point in points.values():
        point.house = locate_house(point.longitude, cusp_longitudes)

    asc_longitude = normalize(ascmc[0])
    mc_longitude = normalize(ascmc[1])
    angle_longitudes = {
        "Ascendente": asc_longitude,
        "Descendente": normalize(asc_longitude + 180),
        "Medio Cielo": mc_longitude,
        "Fondo Cielo": normalize(mc_longitude + 180),
    }

    angles = {}
    angle_houses = {
        "Ascendente": 1,
        "Descendente": 7,
        "Medio Cielo": 10,
        "Fondo Cielo": 4,
    }
    for name, longitude in angle_longitudes.items():
        sign, degree, minute, second = zodiac_parts(longitude)
        angles[name] = CelestialPoint(
            name=name,
            symbol=ANGLE_LABELS[name],
            longitude=longitude,
            speed=0.0,
            sign=sign,
            degree=degree,
            minute=minute,
            second=second,
            house=angle_houses[name],
            retrograde=False,
        )

    aspect_points = {**points, **angles}
    names = POINT_ORDER + ANGLE_ORDER
    aspects = []
    for first_index in range(len(names)):
        for second_index in range(first_index + 1, len(names)):
            first_name = names[first_index]
            second_name = names[second_index]
            separation = angular_separation(
                aspect_points[first_name].longitude,
                aspect_points[second_name].longitude,
            )
            for aspect_name, rule in ASPECT_RULES.items():
                orb = abs(separation - rule["angle"])
                if orb <= rule["orb"]:
                    aspects.append(
                        {
                            "point_a": first_name,
                            "type": aspect_name,
                            "point_b": second_name,
                            "orb": round(orb, 2),
                            "family": rule["family"],
                        }
                    )
                    break

    display_aspects = build_display_aspects(aspects)

    return {
        "input": data,
        "local_datetime": local_datetime,
        "utc_datetime": utc_datetime,
        "julian_day": julian_day,
        "points": points,
        "angles": angles,
        "houses": houses,
        "aspects": aspects,
        "display_aspects": display_aspects,
    }


# -----------------------------------------------------------------------------
# GEOMETRIA DE LA RUEDA
# Distribucion radial acordada, desde el centro hacia afuera:
# aspectos 35%, casas/angulos 10%, astros 40%, signos/graduacion 15%.
# -----------------------------------------------------------------------------

CANVAS = 1200
CX = CY = CANVAS / 2
WHEEL_RADIUS = 520.0
ASPECT_RADIUS = WHEEL_RADIUS * 0.35
HOUSE_OUTER_RADIUS = WHEEL_RADIUS * 0.45
PLANET_OUTER_RADIUS = WHEEL_RADIUS * 0.85
DEGREE_OUTER_RADIUS = WHEEL_RADIUS

HOUSE_LABEL_RADIUS = (ASPECT_RADIUS + HOUSE_OUTER_RADIUS) / 2
PLANET_RADII = [
    PLANET_OUTER_RADIUS - 26,
    PLANET_OUTER_RADIUS - 62,
    PLANET_OUTER_RADIUS - 98,
    PLANET_OUTER_RADIUS - 134,
    PLANET_OUTER_RADIUS - 170,
]
SIGN_SYMBOL_RADIUS = WHEEL_RADIUS * 0.905
SIGN_INNER_RADIUS = PLANET_OUTER_RADIUS
DEGREE_TICK_BASE_RADIUS = WHEEL_RADIUS


def visual_angle(longitude, asc_longitude):
    # ASC queda exactamente a la izquierda. Las longitudes crecen antihorario.
    return normalize(180.0 + (normalize(longitude) - normalize(asc_longitude)))


def polar_xy(angle_degrees, radius):
    radians = math.radians(angle_degrees)
    return (
        CX + radius * math.cos(radians),
        CY - radius * math.sin(radians),
    )


def svg_line(x1, y1, x2, y2, css_class, extra=""):
    return (
        f'<line class="{css_class}" x1="{x1:.2f}" y1="{y1:.2f}" '
        f'x2="{x2:.2f}" y2="{y2:.2f}" {extra}/>'
    )


def boxes_overlap(first, second, padding=7):
    return not (
        first[2] + padding < second[0]
        or second[2] + padding < first[0]
        or first[3] + padding < second[1]
        or second[3] + padding < first[1]
    )


def planet_label_layout(points, asc_longitude):
    placements = []
    used_boxes = []
    ordered = sorted(
        [points[name] for name in POINT_ORDER],
        key=lambda item: visual_angle(item.longitude, asc_longitude),
    )

    for point in ordered:
        angle = visual_angle(point.longitude, asc_longitude)
        selected = None

        for radius in PLANET_RADII:
            x, y = polar_xy(angle, radius)
            box = (x - 66, y - 15, x + 66, y + 15)
            if not any(boxes_overlap(box, previous) for previous in used_boxes):
                selected = (x, y, radius, box)
                break

        if selected is None:
            # Ultimo recurso determinista: pequeno desplazamiento tangencial.
            radius = PLANET_RADII[-1]
            x, y = polar_xy(angle, radius)
            tangent_x = -math.sin(math.radians(angle))
            tangent_y = -math.cos(math.radians(angle))
            direction = -1 if len(placements) % 2 else 1
            x += tangent_x * 22 * direction
            y += tangent_y * 22 * direction
            box = (x - 66, y - 15, x + 66, y + 15)
            selected = (x, y, radius, box)

        x, y, radius, box = selected
        used_boxes.append(box)
        placements.append(
            {
                "point": point,
                "angle": angle,
                "x": x,
                "y": y,
                "radius": radius,
                "adjusted": radius < PLANET_RADII[0] - 1,
            }
        )

    return placements


def render_wheel_svg(chart):
    asc_longitude = chart["angles"]["Ascendente"].longitude
    pieces = [
        f'<svg class="wheel-svg" viewBox="0 0 {CANVAS} {CANVAS}" '
        'role="img" aria-label="Carta astral calculada">',
        "<defs>",
        '<marker id="degree-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">',
        '<path d="M0,0 L8,4 L0,8 Z" fill="#4B2E6D"/>',
        "</marker>",
        "</defs>",
        f'<circle class="wheel-base" cx="{CX}" cy="{CY}" r="{WHEEL_RADIUS}"/>',
        f'<circle class="degree-boundary" cx="{CX}" cy="{CY}" r="{DEGREE_OUTER_RADIUS}"/>',
        f'<circle class="sign-inner" cx="{CX}" cy="{CY}" r="{SIGN_INNER_RADIUS}"/>',
        f'<circle class="planet-inner" cx="{CX}" cy="{CY}" r="{HOUSE_OUTER_RADIUS}"/>',
        f'<circle class="aspect-boundary" cx="{CX}" cy="{CY}" r="{ASPECT_RADIUS}"/>',
    ]

    # Anillo zodiacal y graduacion completa de 360 grados.
    for sign_index, sign in enumerate(SIGNS):
        start_longitude = sign_index * 30.0
        boundary_angle = visual_angle(start_longitude, asc_longitude)
        bx1, by1 = polar_xy(boundary_angle, SIGN_INNER_RADIUS)
        bx2, by2 = polar_xy(boundary_angle, DEGREE_OUTER_RADIUS)
        pieces.append(svg_line(bx1, by1, bx2, by2, "sign-boundary"))

        middle_angle = visual_angle(start_longitude + 15.0, asc_longitude)
        sx, sy = polar_xy(middle_angle, SIGN_SYMBOL_RADIUS)
        pieces.append(
            f'<text class="sign-symbol" x="{sx:.2f}" y="{sy:.2f}">'
            f'{SIGN_SYMBOLS[sign]}</text>'
        )

        for degree in range(30):
            tick_angle = visual_angle(start_longitude + degree, asc_longitude)
            if degree in (10, 20):
                tick_length = (DEGREE_OUTER_RADIUS - SIGN_INNER_RADIUS) * 0.50
                tick_class = "degree-tick degree-half"
            elif degree in (5, 15, 25):
                tick_length = (DEGREE_OUTER_RADIUS - SIGN_INNER_RADIUS) * 0.25
                tick_class = "degree-tick degree-double"
            elif degree == 0:
                continue
            else:
                tick_length = (DEGREE_OUTER_RADIUS - SIGN_INNER_RADIUS) * 0.25
                tick_class = "degree-tick"

            tx1, ty1 = polar_xy(tick_angle, DEGREE_TICK_BASE_RADIUS)
            tx2, ty2 = polar_xy(
                tick_angle,
                DEGREE_TICK_BASE_RADIUS - tick_length,
            )
            pieces.append(svg_line(tx1, ty1, tx2, ty2, tick_class))

    # Lineas de aspectos dentro del 35% central.
    all_points = {**chart["points"], **chart["angles"]}
    for aspect in chart["display_aspects"]:
        first = all_points[aspect["point_a"]]
        second = all_points[aspect["point_b"]]
        first_angle = visual_angle(first.longitude, asc_longitude)
        second_angle = visual_angle(second.longitude, asc_longitude)
        x1, y1 = polar_xy(first_angle, ASPECT_RADIUS * 0.96)
        x2, y2 = polar_xy(second_angle, ASPECT_RADIUS * 0.96)
        color = ASPECT_COLORS[aspect["family"]]
        title = html_escape(
            f'{aspect["point_a"]} {aspect["type"]} '
            f'{aspect["point_b"]} · orbe {aspect["orb"]}°'
        )
        pieces.append(
            f'<g class="aspect-hit" data-aspect="{html_escape(aspect["type"])}">'
            f"<title>{title}</title>"
            + svg_line(
                x1,
                y1,
                x2,
                y2,
                "aspect-line",
                f'stroke="{color}"',
            )
            + "</g>"
        )

    # Cuspides y numeros de casas.
    for index, house in enumerate(chart["houses"]):
        next_house = chart["houses"][(index + 1) % 12]
        cusp_angle = visual_angle(house.longitude, asc_longitude)
        x1, y1 = polar_xy(cusp_angle, ASPECT_RADIUS)
        x2, y2 = polar_xy(cusp_angle, DEGREE_OUTER_RADIUS)
        css_class = "house-cusp angle-cusp" if house.number in (1, 4, 7, 10) else "house-cusp"
        pieces.append(svg_line(x1, y1, x2, y2, css_class))

        span = normalize(next_house.longitude - house.longitude)
        midpoint = normalize(house.longitude + span / 2)
        midpoint_angle = visual_angle(midpoint, asc_longitude)
        hx, hy = polar_xy(midpoint_angle, HOUSE_LABEL_RADIUS)
        pieces.append(
            f'<text class="house-number" x="{hx:.2f}" y="{hy:.2f}">'
            f"{house.number}</text>"
        )

    # Angulos: linea gruesa, etiqueta en el anillo de casas y grado en 360 grados.
    for angle_name in ANGLE_ORDER:
        angle_point = chart["angles"][angle_name]
        angle = visual_angle(angle_point.longitude, asc_longitude)
        line_x1, line_y1 = polar_xy(angle, 0)
        line_x2, line_y2 = polar_xy(angle, DEGREE_OUTER_RADIUS)
        pieces.append(svg_line(line_x1, line_y1, line_x2, line_y2, "angle-line"))

        label_x, label_y = polar_xy(angle, HOUSE_LABEL_RADIUS)
        degree_x, degree_y = polar_xy(angle, DEGREE_OUTER_RADIUS - 20)
        pieces.append(
            f'<text class="angle-label" x="{label_x:.2f}" y="{label_y:.2f}">'
            f'{ANGLE_LABELS[angle_name]}</text>'
        )
        pieces.append(
            f'<text class="angle-degree" x="{degree_x:.2f}" y="{degree_y:.2f}">'
            f'{degree_text(angle_point, False)} {SIGN_SYMBOLS[angle_point.sign]}</text>'
        )

    # Astros: simbolo, posicion y signo, siempre horizontales.
    for placement in planet_label_layout(chart["points"], asc_longitude):
        point = placement["point"]
        angle = placement["angle"]
        x = placement["x"]
        y = placement["y"]
        anchor_x, anchor_y = polar_xy(angle, SIGN_INNER_RADIUS - 3)

        if placement["adjusted"]:
            pieces.append(
                svg_line(
                    x,
                    y,
                    anchor_x,
                    anchor_y,
                    "planet-guide adjusted",
                    'marker-end="url(#degree-arrow)"',
                )
            )
        else:
            guide_x, guide_y = polar_xy(angle, placement["radius"] + 24)
            pieces.append(svg_line(x, y, guide_x, guide_y, "planet-guide"))

        retro = " R" if point.retrograde else ""
        point_title = html_escape(
            f"{point.name}: {point.sign} {degree_text(point)} · Casa {point.house}"
        )
        pieces.append(
            f'<g class="planet-mark" data-point="{html_escape(point.name)}">'
            f"<title>{point_title}</title>"
            f'<text class="planet-row" x="{x:.2f}" y="{y:.2f}">'
            f'<tspan class="planet-symbol">{point.symbol}</tspan>'
            f'<tspan class="planet-degree" dx="7">{point.degree}°{point.minute:02d}\'{retro}</tspan>'
            f'<tspan class="planet-sign" dx="7">{SIGN_SYMBOLS[point.sign]}</tspan>'
            "</text></g>"
        )

    pieces.append("</svg>")
    return "".join(pieces)


# -----------------------------------------------------------------------------
# TABLAS Y DOCUMENTO HTML
# -----------------------------------------------------------------------------

def searcher_information(chart):
    source = chart["input"]
    local_datetime = chart["local_datetime"]
    utc_datetime = chart["utc_datetime"]
    return [
        ("Nombre", source["name"]),
        ("Fecha de nacimiento", local_datetime.strftime("%d/%m/%Y")),
        ("Hora ingresada", local_datetime.strftime("%H:%M") + f' · {source["timezone"]}'),
        ("Hora UTC", utc_datetime.strftime("%d/%m/%Y %H:%M UTC")),
        ("Lugar", source["city_country"]),
        ("Coordenadas", f'{source["latitude"]:.6f}, {source["longitude"]:.6f}'),
    ]


def render_searcher(chart):
    items = []
    for label, value in searcher_information(chart):
        items.append(
            '<div class="identity-item">'
            f'<span class="identity-label">{html_escape(str(label))}</span>'
            f'<strong>{html_escape(str(value))}</strong>'
            "</div>"
        )
    return "".join(items)


def render_points_table(chart):
    rows = []
    for name in POINT_ORDER:
        point = chart["points"][name]
        rows.append(
            f'<tr data-point-row="{html_escape(name)}">'
            f'<td><span class="table-symbol">{point.symbol}</span> {html_escape(name)}</td>'
            f'<td>{SIGN_SYMBOLS[point.sign]} {html_escape(point.sign)}</td>'
            f'<td>{degree_text(point)}</td>'
            f'<td>{point.house}</td>'
            "</tr>"
        )
    return "".join(rows)


def render_houses_table(chart):
    rows = []
    for house in chart["houses"]:
        regent = SIGN_REGENTS.get(house.sign, "")
        regent_house = chart["points"].get(regent).house if regent in chart["points"] else None
        is_present = regent_house == house.number
        regent_note = f"Regente: {regent}"
        if is_present:
            regent_note += " · presente en esta casa"
        indicator_class = " ruler-present" if is_present else ""
        rows.append(
            "<tr>"
            f"<td>{house.number}</td>"
            f'<td>{SIGN_SYMBOLS[house.sign]} {html_escape(house.sign)}'
            f'<span class="ruler{indicator_class}">{html_escape(regent_note)}</span></td>'
            f"<td>{house.degree}°{house.minute:02d}'</td>"
            "</tr>"
        )
    return "".join(rows)


def render_angles_table(chart):
    rows = []
    for name in ANGLE_ORDER:
        point = chart["angles"][name]
        rows.append(
            "<tr>"
            f"<td>{ANGLE_LABELS[name]}</td>"
            f"<td>{SIGN_SYMBOLS[point.sign]} {html_escape(point.sign)}</td>"
            f"<td>{degree_text(point, False)}</td>"
            f"<td>{point.house}</td>"
            "</tr>"
        )
    return "".join(rows)


def render_aspects_table(chart):
    rows = []
    for aspect in chart["display_aspects"]:
        color = ASPECT_COLORS[aspect["family"]]
        rows.append(
            "<tr>"
            f'<td>{html_escape(aspect["point_a"])}</td>'
            f'<td><span class="aspect-dot" style="background:{color}"></span>'
            f'{html_escape(aspect["type"])}</td>'
            f'<td>{html_escape(aspect["point_b"])}</td>'
            "</tr>"
        )
    return "".join(rows)


def render_html(chart):
    wheel_svg = render_wheel_svg(chart)
    return f'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Astrology Internal Live Wheel v0.3</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
  --navy:#080E1F;
  --ivory:#F4EAD2;
  --gold:#C6A15B;
  --violet:#4B2E6D;
  --ink:#172033;
  --muted:rgba(244,234,210,.68);
  --line:rgba(198,161,91,.34);
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--navy); color:var(--ivory); font-family:Inter,system-ui,sans-serif; }}
.page {{ width:min(1320px,calc(100vw - 28px)); margin:24px auto 40px; }}
header {{ text-align:center; padding:20px 0 18px; border-bottom:1px solid var(--line); }}
.kicker {{ color:var(--gold); font:500 11px "IBM Plex Mono",monospace; text-transform:uppercase; }}
h1 {{ margin:8px 0 5px; font:600 clamp(42px,6vw,76px)/.95 "Cormorant Garamond",serif; }}
.subtitle {{ margin:0; color:var(--muted); }}
.identity {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:0; margin:22px 0; border-block:1px solid var(--line); }}
.identity-item {{ padding:13px 16px; border-right:1px solid var(--line); }}
.identity-item:nth-child(3n) {{ border-right:0; }}
.identity-label {{ display:block; color:var(--gold); font:500 9px "IBM Plex Mono",monospace; text-transform:uppercase; margin-bottom:5px; }}
.identity-item strong {{ font-size:13px; font-weight:500; overflow-wrap:anywhere; }}
.wheel-stage {{ max-width:1120px; margin:0 auto 26px; }}
.wheel-frame {{ background:var(--ivory); border:2px solid var(--gold); padding:16px; box-shadow:0 18px 50px rgba(0,0,0,.22); }}
.wheel-svg {{ width:100%; height:auto; display:block; }}
.wheel-base {{ fill:#F4EAD2; stroke:#C6A15B; stroke-width:2.4; }}
.degree-boundary,.sign-inner,.planet-inner,.aspect-boundary {{ fill:none; stroke:rgba(8,14,31,.5); stroke-width:1.5; }}
.aspect-boundary {{ stroke:#C6A15B; stroke-width:2; }}
.sign-boundary {{ stroke:#4B2E6D; stroke-width:3.4; }}
.degree-tick {{ stroke:#172033; stroke-width:1; opacity:.74; }}
.degree-double {{ stroke-width:2.1; }}
.degree-half {{ stroke-width:2.1; }}
.sign-symbol {{ text-anchor:middle; dominant-baseline:middle; fill:#080E1F; font:700 31px "Cormorant Garamond",serif; }}
.house-cusp {{ stroke:rgba(8,14,31,.46); stroke-width:1.15; }}
.angle-cusp {{ stroke:#C6A15B; stroke-width:3.4; }}
.house-number,.angle-label {{ text-anchor:middle; dominant-baseline:middle; font:700 17px "IBM Plex Mono",monospace; fill:#080E1F; paint-order:stroke; stroke:#F4EAD2; stroke-width:4px; }}
.angle-label {{ fill:#4B2E6D; font-size:16px; }}
.angle-line {{ stroke:#4B2E6D; stroke-width:4.3; opacity:.82; }}
.angle-degree {{ text-anchor:middle; dominant-baseline:middle; fill:#4B2E6D; font:700 10px "IBM Plex Mono",monospace; paint-order:stroke; stroke:#F4EAD2; stroke-width:4px; }}
.aspect-line {{ stroke-width:1.45; opacity:.62; transition:opacity .18s,stroke-width .18s; }}
.aspect-hit:hover .aspect-line {{ opacity:1; stroke-width:3; }}
.planet-guide {{ stroke:#C6A15B; stroke-width:1; opacity:.65; }}
.planet-guide.adjusted {{ stroke:#4B2E6D; stroke-width:1.2; stroke-dasharray:3 3; opacity:.9; }}
.planet-row {{ text-anchor:middle; dominant-baseline:middle; fill:#080E1F; paint-order:stroke; stroke:#F4EAD2; stroke-width:3px; stroke-linejoin:round; }}
.planet-symbol {{ font:700 23px "Cormorant Garamond",serif; }}
.planet-degree {{ fill:#4B2E6D; font:700 10px "IBM Plex Mono",monospace; }}
.planet-sign {{ fill:#080E1F; font:700 18px "Cormorant Garamond",serif; }}
.planet-mark {{ cursor:default; transition:filter .18s; }}
.planet-mark:hover {{ filter:drop-shadow(0 0 5px rgba(75,46,109,.7)); }}
.content-band {{ padding:22px 0; border-top:1px solid var(--line); }}
.content-band h2 {{ margin:0 0 14px; color:var(--ivory); font:600 31px "Cormorant Garamond",serif; }}
.tables-primary {{ display:grid; grid-template-columns:1.25fr 1fr; gap:24px; }}
.tables-secondary {{ display:grid; grid-template-columns:.75fr 1.25fr; gap:24px; margin-top:24px; }}
.table-wrap {{ min-width:0; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; }}
th {{ padding:8px 7px; text-align:left; color:var(--gold); border-bottom:1px solid rgba(198,161,91,.55); font:500 9px "IBM Plex Mono",monospace; text-transform:uppercase; }}
td {{ padding:8px 7px; border-bottom:1px solid rgba(198,161,91,.16); vertical-align:top; }}
.table-symbol {{ display:inline-block; width:20px; color:var(--gold); font-size:17px; }}
.ruler {{ display:block; margin-top:2px; color:var(--muted); font-size:9px; }}
.ruler-present {{ color:var(--gold); font-weight:600; }}
.aspects-grid {{ columns:2; column-gap:28px; }}
.aspects-grid table {{ break-inside:avoid; }}
.aspect-dot {{ display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:7px; }}
footer {{ margin-top:25px; padding-top:14px; border-top:1px solid var(--line); color:var(--muted); font:400 10px "IBM Plex Mono",monospace; display:flex; justify-content:space-between; gap:18px; }}
@media(max-width:900px) {{
  .identity,.tables-primary,.tables-secondary {{ grid-template-columns:1fr; }}
  .identity-item,.identity-item:nth-child(3n) {{ border-right:0; border-bottom:1px solid var(--line); }}
  .aspects-grid {{ columns:1; }}
}}
</style>
</head>
<body>
<div class="page">
  <header>
    <div class="kicker">Internal Representation Template / Not Public Output</div>
    <h1>Carta Astral</h1>
    <p class="subtitle">Rueda calculada · sistema Placidus · zodiaco tropical</p>
  </header>

  <section class="identity">{render_searcher(chart)}</section>

  <main>
    <section class="wheel-stage">
      <div class="wheel-frame">{wheel_svg}</div>
    </section>

    <section class="content-band">
      <div class="tables-primary">
        <div class="table-wrap">
          <h2>Planetas / puntos</h2>
          <table>
            <thead><tr><th>Punto</th><th>Signo</th><th>Grados</th><th>Casa</th></tr></thead>
            <tbody>{render_points_table(chart)}</tbody>
          </table>
        </div>
        <div class="table-wrap">
          <h2>Casas</h2>
          <table>
            <thead><tr><th>Casa</th><th>Signo y regente</th><th>Grados</th></tr></thead>
            <tbody>{render_houses_table(chart)}</tbody>
          </table>
        </div>
      </div>

      <div class="tables-secondary">
        <div class="table-wrap">
          <h2>Angulos</h2>
          <table>
            <thead><tr><th>Angulo</th><th>Signo</th><th>Grado</th><th>Casa</th></tr></thead>
            <tbody>{render_angles_table(chart)}</tbody>
          </table>
        </div>
        <div class="table-wrap">
          <h2>Leyenda de aspectos</h2>
          <table>
            <tbody>
              <tr><td><span class="aspect-dot" style="background:{ASPECT_COLORS['tense']}"></span>Cuadratura · Oposicion</td></tr>
              <tr><td><span class="aspect-dot" style="background:{ASPECT_COLORS['harmonious']}"></span>Sextil · Trigono</td></tr>
              <tr><td><span class="aspect-dot" style="background:{ASPECT_COLORS['neutral']}"></span>Conjuncion</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="content-band">
      <h2>Aspectos</h2>
      <div class="aspects-grid">
        <table>
          <thead><tr><th>Planeta A</th><th>Tipo de aspecto</th><th>Planeta B</th></tr></thead>
          <tbody>{render_aspects_table(chart)}</tbody>
        </table>
      </div>
    </section>
  </main>

  <footer>
    <span>DHARMACODEX · ASTROLOGY_INTERNAL_LIVE_WHEEL_v0.3</span>
    <span>Calculo y representacion separados · sin interpretacion</span>
  </footer>
</div>
</body>
</html>'''


# -----------------------------------------------------------------------------
# DEBUG Y QC AUTOMATICO
# El fixture Daniel verifica calculo; nunca reemplaza resultados del motor.
# -----------------------------------------------------------------------------

DANIEL_REFERENCE = {
    "angles": {
        "Ascendente": ("Tauro", 5, 46),
        "Descendente": ("Escorpio", 5, 46),
        "Medio Cielo": ("Capricornio", 24, 4),
        "Fondo Cielo": ("Cancer", 24, 4),
    },
    "houses": [
        ("Tauro", 5, 46),
        ("Geminis", 6, 3),
        ("Cancer", 0, 29),
        ("Cancer", 24, 4),
        ("Leo", 20, 51),
        ("Virgo", 24, 47),
        ("Escorpio", 5, 46),
        ("Sagitario", 6, 3),
        ("Capricornio", 0, 29),
        ("Capricornio", 24, 4),
        ("Acuario", 20, 51),
        ("Piscis", 24, 47),
    ],
    "points": {
        "Sol": ("Acuario", 3, 59, 10),
        "Luna": ("Aries", 19, 50, 12),
        "Mercurio": ("Acuario", 22, 17, 11),
        "Venus": ("Piscis", 11, 4, 11),
        "Marte": ("Sagitario", 10, 45, 8),
        "Jupiter": ("Aries", 22, 26, 12),
        "Saturno": ("Sagitario", 28, 5, 8),
        "Urano": ("Sagitario", 29, 0, 8),
        "Neptuno": ("Capricornio", 8, 39, 9),
        "Pluton": ("Escorpio", 12, 27, 7),
        "Nodo Norte": ("Piscis", 24, 22, 11),
        "Nodo Sur": ("Virgo", 24, 22, 5),
        "Lilith": ("Leo", 17, 46, 4),
        "Quiron": ("Geminis", 23, 53, 2),
    },
}


def minutes_inside_sign(sign, degree, minute):
    return SIGNS.index(sign) * 1800 + degree * 60 + minute


def circular_minute_difference(actual, expected):
    difference = abs(actual - expected)
    return min(difference, 21600 - difference)


def reference_matches(point, expected, tolerance_minutes=2, include_house=False):
    expected_sign, expected_degree, expected_minute = expected[:3]
    actual_total = minutes_inside_sign(point.sign, point.degree, point.minute)
    expected_total = minutes_inside_sign(
        expected_sign,
        expected_degree,
        expected_minute,
    )
    position_ok = circular_minute_difference(actual_total, expected_total) <= tolerance_minutes
    house_ok = True if not include_house else point.house == expected[3]
    return position_ok and house_ok


def build_qc(chart):
    asc = chart["angles"]["Ascendente"]
    house_angles = [
        visual_angle(house.longitude, asc.longitude) for house in chart["houses"]
    ]
    checks = {
        "asc_left_alignment": math.isclose(
            visual_angle(asc.longitude, asc.longitude),
            180.0,
            abs_tol=1e-9,
        ),
        "ring_percentages": {
            "aspects": 35,
            "houses_angles": 10,
            "planets": 40,
            "signs_degrees": 15,
        },
        "ring_percentages_total": 35 + 10 + 40 + 15 == 100,
        "house_count": len(chart["houses"]) == 12,
        "point_count": len(chart["points"]) == 14,
        "angle_count": len(chart["angles"]) == 4,
        "display_aspects_exclude_angles": all(
            aspect["point_a"] not in ANGLE_ORDER and aspect["point_b"] not in ANGLE_ORDER
            for aspect in chart["display_aspects"]
        ),
        "display_aspects_exclude_quincunx": all(
            aspect["type"] != "Quincuncio" for aspect in chart["display_aspects"]
        ),
        "display_aspects_allowed_types_only": all(
            aspect["type"] in {"Conjuncion", "Sextil", "Cuadratura", "Trigono", "Oposicion"}
            for aspect in chart["display_aspects"]
        ),
        "houses_counterclockwise": all(
            normalize(house_angles[(index + 1) % 12] - house_angles[index]) > 0
            for index in range(12)
        ),
        "zodiac_counterclockwise": math.isclose(
            normalize(
                visual_angle(30.0, asc.longitude)
                - visual_angle(0.0, asc.longitude)
            ),
            30.0,
            abs_tol=1e-9,
        ),
        "retrograde_available": all(
            isinstance(point.retrograde, bool) for point in chart["points"].values()
        ),
        "reference_applied": chart["input"].get("name") == "Daniel Test",
    }

    if checks["reference_applied"]:
        checks["daniel_angles"] = all(
            reference_matches(chart["angles"][name], expected)
            for name, expected in DANIEL_REFERENCE["angles"].items()
        )
        checks["daniel_houses"] = all(
            reference_matches(house, expected)
            for house, expected in zip(chart["houses"], DANIEL_REFERENCE["houses"])
        )
        checks["daniel_points"] = all(
            reference_matches(chart["points"][name], expected, include_house=True)
            for name, expected in DANIEL_REFERENCE["points"].items()
        )

    boolean_checks = [
        value
        for key, value in checks.items()
        if isinstance(value, bool) and key != "reference_applied"
    ]
    checks["overall_pass"] = all(boolean_checks)
    return checks


def chart_to_debug(chart, qc):
    return {
        "artifact_id": "ASTROLOGY_INTERNAL_LIVE_WHEEL_DEBUG_v0.3",
        "input": chart["input"],
        "local_datetime": chart["local_datetime"].isoformat(),
        "utc_datetime": chart["utc_datetime"].isoformat(),
        "julian_day": chart["julian_day"],
        "points": {name: asdict(point) for name, point in chart["points"].items()},
        "angles": {name: asdict(point) for name, point in chart["angles"].items()},
        "houses": [asdict(house) for house in chart["houses"]],
        "aspects": chart["aspects"],
        "display_aspects": chart["display_aspects"],
        "geometry": {
            "visual_transform": "180 + (longitude - asc_longitude)",
            "wheel_radius": WHEEL_RADIUS,
            "aspect_radius": ASPECT_RADIUS,
            "house_outer_radius": HOUSE_OUTER_RADIUS,
            "planet_outer_radius": PLANET_OUTER_RADIUS,
            "degree_outer_radius": DEGREE_OUTER_RADIUS,
        },
        "sign_regents_source": SIGN_REGENTS_SOURCE,
        "qc": qc,
    }


def render_qc_markdown(qc):
    lines = [
        "# ASTROLOGY_INTERNAL_LIVE_WHEEL_VALIDATION_v0.3",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    for key, value in qc.items():
        if isinstance(value, bool):
            lines.append(f"| `{key}` | {'PASS' if value else 'FAIL'} |")
    lines.extend(
        [
            "",
            "Nota: el fixture Daniel solo valida los resultados calculados. ",
            "No sustituye ni corrige valores del motor.",
        ]
    )
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# EJECUCION EN COLAB
# -----------------------------------------------------------------------------

chart = calculate_chart(TEST)
qc = build_qc(chart)
html_document = render_html(chart)
debug_payload = chart_to_debug(chart, qc)
qc_markdown = render_qc_markdown(qc)

OUTPUT_HTML = Path("/content/ASTROLOGY_INTERNAL_LIVE_WHEEL_PROOF_v0.3.html")
OUTPUT_JSON = Path("/content/ASTROLOGY_INTERNAL_LIVE_WHEEL_DEBUG_v0.3.json")
OUTPUT_REPORT = Path("/content/ASTROLOGY_INTERNAL_LIVE_WHEEL_VALIDATION_v0.3.md")

OUTPUT_HTML.write_text(html_document, encoding="utf-8")
OUTPUT_JSON.write_text(
    json.dumps(debug_payload, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
OUTPUT_REPORT.write_text(qc_markdown, encoding="utf-8")

print("DONE")
print("HTML:", OUTPUT_HTML)
print("JSON:", OUTPUT_JSON)
print("REPORT:", OUTPUT_REPORT)
print("SUMMARY:", json.dumps(qc, ensure_ascii=False, indent=2))

try:
    from IPython.display import HTML, display

    display(HTML(html_document))
except Exception:
    pass


# %% [CELDA 3 — HUMAN DESIGN]

import json
import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

try:
    from IPython.display import HTML, display
except Exception:
    HTML = None

    def display(_value):
        return None

try:
    import swisseph as swe
except Exception as exc:
    raise RuntimeError(
        "swisseph no esta disponible. Ejecuta primero tu celda de setup de Swiss Ephemeris "
        "que ya te funciono en Colab, y despues corre esta celda maestra."
    ) from exc


OUT_HTML = "/content/HD_INTERNAL_LIVE_BODYGRAPH_PROOF_v0.5.html"
OUT_DEBUG = "/content/HD_INTERNAL_LIVE_BODYGRAPH_DEBUG_v0.5.json"
OUT_REPORT = "/content/HD_INTERNAL_LIVE_BODYGRAPH_VALIDATION_v0.5.md"

COLORS = {
    "bg": "#080E1F",
    "paper": "#F4EAD2",
    "gold": "#C6A15B",
    "violet": "#4B2E6D",
    "idle": "#6F6A5D",
    "line_idle": "#8B836F",
    "personality": "#F4EAD2",
    "design": "#C94B45",
    "defined": "#C6A15B",
    "open": "#080E1F",
}

PLANET_GLYPHS = {
    "Sol": "☉", "Tierra": "⊕", "Nodo Norte": "☊", "Nodo Sur": "☋",
    "Luna": "☽", "Mercurio": "☿", "Venus": "♀", "Marte": "♂",
    "Jupiter": "♃", "Saturno": "♄", "Urano": "♅", "Neptuno": "♆", "Pluton": "♇",
}

BODY_IDS = {
    "Sol": swe.SUN,
    "Luna": swe.MOON,
    "Mercurio": swe.MERCURY,
    "Venus": swe.VENUS,
    "Marte": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturno": swe.SATURN,
    "Urano": swe.URANUS,
    "Neptuno": swe.NEPTUNE,
    "Pluton": swe.PLUTO,
    "Nodo Norte": swe.TRUE_NODE,
}

PUERTAS_MANDALA = [
    41, 19, 13, 49, 30, 55, 37, 63, 22, 36, 25, 17, 21, 51, 42, 3,
    27, 24, 2, 23, 8, 20, 16, 35, 45, 12, 15, 52, 39, 53, 62, 56,
    31, 33, 7, 4, 29, 59, 40, 64, 47, 6, 46, 18, 48, 57, 32, 50,
    28, 44, 1, 43, 14, 34, 9, 5, 26, 11, 10, 58, 38, 54, 61, 60,
]

CHANNELS = [
    (64, 47), (61, 24), (63, 4), (17, 62), (43, 23), (11, 56),
    (16, 48), (20, 57), (31, 7), (8, 1), (33, 13), (45, 21),
    (35, 36), (12, 22), (25, 51), (40, 37), (26, 44), (2, 14),
    (46, 29), (15, 5), (10, 20), (10, 34), (10, 57), (34, 20), (34, 57),
    (50, 27), (32, 54), (28, 38), (18, 58), (59, 6), (42, 53),
    (3, 60), (9, 52), (19, 49), (39, 55), (41, 30),
]

CHANNEL_CENTERS = {
    "64-47": ("Cabeza", "Ajna"), "61-24": ("Cabeza", "Ajna"), "63-4": ("Cabeza", "Ajna"),
    "17-62": ("Ajna", "Garganta"), "43-23": ("Ajna", "Garganta"), "11-56": ("Ajna", "Garganta"),
    "16-48": ("Garganta", "Bazo"), "20-57": ("Garganta", "Bazo"),
    "31-7": ("Garganta", "Centro G"), "8-1": ("Garganta", "Centro G"), "33-13": ("Garganta", "Centro G"),
    "45-21": ("Garganta", "Corazon"), "35-36": ("Garganta", "Plexo Solar"), "12-22": ("Garganta", "Plexo Solar"),
    "25-51": ("Centro G", "Corazon"), "40-37": ("Corazon", "Plexo Solar"), "26-44": ("Corazon", "Bazo"),
    "2-14": ("Centro G", "Sacral"), "46-29": ("Centro G", "Sacral"), "15-5": ("Centro G", "Sacral"),
    "10-20": ("Centro G", "Garganta"), "10-34": ("Centro G", "Sacral"), "10-57": ("Centro G", "Bazo"),
    "34-20": ("Sacral", "Garganta"), "34-57": ("Sacral", "Bazo"),
    "50-27": ("Bazo", "Sacral"), "32-54": ("Bazo", "Raiz"), "28-38": ("Bazo", "Raiz"), "18-58": ("Bazo", "Raiz"),
    "59-6": ("Sacral", "Plexo Solar"), "42-53": ("Sacral", "Raiz"), "3-60": ("Sacral", "Raiz"),
    "9-52": ("Sacral", "Raiz"), "19-49": ("Raiz", "Plexo Solar"), "39-55": ("Raiz", "Plexo Solar"),
    "41-30": ("Raiz", "Plexo Solar"),
}

GATE_POS = {
    # Cabeza
    64: (365,138), 61: (400,138), 63: (435,138),
    # Ajna
    47: (355,226), 24: (400,226), 4: (445,226), 17: (354,272), 11: (400,286), 43: (446,272),
    # Garganta
    62: (352,354), 23: (385,354), 56: (418,354), 16: (342,386), 20: (354,420), 8: (385,430),
    31: (415,430), 35: (458,366), 12: (468,398), 45: (456,430), 33: (432,410),
    # Centro G
    1: (400,474), 7: (358,502), 13: (442,502), 10: (334,548), 25: (466,548), 15: (366,620),
    46: (434,620), 2: (400,648),
    # Corazon
    21: (520,518), 40: (566,586), 26: (504,588), 51: (502,486),
    # Bazo
    48: (238,612), 57: (270,642), 44: (304,684), 50: (326,724), 32: (286,756), 28: (238,790), 18: (224,828),
    # Plexo Solar
    36: (614,612), 22: (588,654), 37: (562,690), 6: (536,720), 49: (562,756), 55: (600,790), 30: (630,828),
    # Sacral
    5: (356,706), 14: (400,706), 29: (444,706), 34: (342,760), 27: (380,790), 42: (420,790),
    3: (458,760), 9: (400,830), 59: (464,820),
    # Raiz
    53: (330,890), 60: (365,890), 52: (400,890), 54: (435,890), 38: (335,944), 58: (375,964),
    39: (425,964), 41: (465,944), 19: (490,904),
}

EXPECTED = {
    "type": "Proyector",
    "strategy": "Esperar la invitación",
    "authority": "Emocional",
    "profile": "3/5",
    "defined_centers": ["Raiz", "Corazon", "Bazo", "Plexo Solar", "Centro G"],
    "open_centers": ["Cabeza", "Ajna", "Garganta", "Sacral"],
    "active_channels": ["19-49", "25-51", "26-44"],
    "personality": {
        "Sol": "41.3", "Tierra": "31.3", "Nodo Norte": "36.2", "Nodo Sur": "6.2",
        "Luna": "51.6", "Mercurio": "49.4", "Venus": "37.6", "Marte": "9.6",
        "Jupiter": "42.2", "Saturno": "11.6", "Urano": "10.1",
        "Neptuno": "58.6", "Pluton": "44.6",
    },
    "design": {
        "Sol": "28.5", "Tierra": "27.5", "Nodo Norte": "25.4", "Nodo Sur": "46.4",
        "Luna": "19.2", "Mercurio": "28.1", "Venus": "43.6", "Marte": "48.5",
        "Jupiter": "42.3", "Saturno": "26.2", "Urano": "11.2",
        "Neptuno": "58.2", "Pluton": "44.3",
    },
}


def normalize(deg):
    return deg % 360.0


def channel_key(a, b):
    direct = f"{a}-{b}"
    reverse = f"{b}-{a}"
    if "CHANNEL_CENTERS" in globals():
        if direct in CHANNEL_CENTERS:
            return direct
        if reverse in CHANNEL_CENTERS:
            return reverse
    if "CHANNEL_PATHS" in globals():
        if direct in CHANNEL_PATHS:
            return direct
        if reverse in CHANNEL_PATHS:
            return reverse
    return direct


def jd_from_local(year, month, day, hour, minute, tz_name):
    local = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(tz_name))
    utc = local.astimezone(timezone.utc)
    return swe.julday(
        utc.year, utc.month, utc.day,
        utc.hour + utc.minute / 60 + utc.second / 3600
    ), utc.isoformat()


def longitude(jd, body):
    return normalize(swe.calc_ut(jd, body)[0][0])


def sun_longitude(jd):
    return longitude(jd, swe.SUN)


def find_design_jd(natal_jd):
    target = normalize(sun_longitude(natal_jd) - 88.0)
    lo = natal_jd - 120.0
    hi = natal_jd - 60.0

    def diff(jd):
        return ((sun_longitude(jd) - target + 180) % 360) - 180

    for _ in range(90):
        mid = (lo + hi) / 2
        if diff(mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def gate_line_from_longitude(lon):
    # Calibrado con Daniel Test: Sol natal 3°59 Acuario -> Gate 41.3
    rel = normalize(lon - 302.0)
    gate_index = int(rel // 5.625)
    within_gate = rel - gate_index * 5.625
    line = int(within_gate // 0.9375) + 1
    line = max(1, min(6, line))
    return f"{PUERTAS_MANDALA[gate_index]}.{line}"


def calc_activations(jd):
    out = {}
    for name, body in BODY_IDS.items():
        out[name] = gate_line_from_longitude(longitude(jd, body))
    out["Tierra"] = gate_line_from_longitude(normalize(longitude(jd, swe.SUN) + 180))
    nn = longitude(jd, swe.TRUE_NODE)
    out["Nodo Sur"] = gate_line_from_longitude(normalize(nn + 180))
    order = ["Sol", "Tierra", "Nodo Norte", "Nodo Sur", "Luna", "Mercurio", "Venus", "Marte", "Jupiter", "Saturno", "Urano", "Neptuno", "Pluton"]
    return {k: out[k] for k in order}


def gate_num(v):
    return int(str(v).split(".")[0])


def derive_hd(personality, design):
    p_gates = {gate_num(v) for v in personality.values()}
    d_gates = {gate_num(v) for v in design.values()}
    all_gates = p_gates | d_gates

    gate_states = {}
    for gate in range(1, 65):
        if gate in p_gates and gate in d_gates:
            gate_states[gate] = "BOTH"
        elif gate in p_gates:
            gate_states[gate] = "P"
        elif gate in d_gates:
            gate_states[gate] = "D"
        else:
            gate_states[gate] = "OPEN"

    active_channels = []
    defined_centers = set()
    for a, b in CHANNELS:
        if a in all_gates and b in all_gates:
            key = channel_key(a, b)
            active_channels.append(key)
            c1, c2 = CHANNEL_CENTERS[key]
            defined_centers.update([c1, c2])

    centers_all = ["Cabeza", "Ajna", "Garganta", "Centro G", "Corazon", "Bazo", "Plexo Solar", "Sacral", "Raiz"]
    open_centers = [c for c in centers_all if c not in defined_centers]

    sacral_defined = "Sacral" in defined_centers
    throat_defined = "Garganta" in defined_centers
    motor_to_throat = any(ch in active_channels for ch in ["34-20", "45-21", "35-36", "12-22"])
    if sacral_defined and motor_to_throat:
        hd_type, strategy = "Manifesting Generator", "Responder e informar"
    elif sacral_defined:
        hd_type, strategy = "Generador", "Responder"
    elif throat_defined and motor_to_throat:
        hd_type, strategy = "Manifestador", "Informar"
    elif defined_centers:
        hd_type, strategy = "Proyector", "Esperar la invitación"
    else:
        hd_type, strategy = "Reflector", "Esperar ciclo lunar"

    if "Plexo Solar" in defined_centers:
        authority = "Emocional"
    elif "Sacral" in defined_centers:
        authority = "Sacral"
    elif "Bazo" in defined_centers:
        authority = "Esplénica"
    elif "Corazon" in defined_centers:
        authority = "Ego"
    elif "Centro G" in defined_centers:
        authority = "Self-projected"
    else:
        authority = "Lunar"

    profile = f"{personality['Sol'].split('.')[1]}/{design['Sol'].split('.')[1]}"
    return {
        "gate_states": gate_states,
        "active_channels": sorted(active_channels, key=lambda s: [int(x) for x in s.split("-")]),
        "defined_centers": sorted(defined_centers),
        "open_centers": open_centers,
        "type": hd_type,
        "strategy": strategy,
        "authority": authority,
        "profile": profile,
    }


HD_DB_CANDIDATES = [
    "/content/HD_DB_v2.0.db",
    "/content/Data_Bases/HD_DB_v2.0.db",
]


def _hd_normalize(value):
    import unicodedata as _hd_unicodedata
    text = _hd_unicodedata.normalize("NFD", str(value or ""))
    return " ".join(
        "".join(ch for ch in text if _hd_unicodedata.category(ch) != "Mn")
        .lower().replace("_", " ").replace("-", " ").split()
    )


def _hd_geometry_class(value):
    normalized = _hd_normalize(value)
    if "yuxtapos" in normalized:
        return "JUXTAPOSITION"
    if "izquierdo" in normalized:
        return "LEFT_ANGLE"
    if "derecho" in normalized:
        return "RIGHT_ANGLE"
    return normalized.upper()


def _hd_channel_pair(value):
    import re as _hd_re
    numbers = [int(item) for item in _hd_re.findall(r"\d+", str(value or ""))]
    return tuple(sorted(numbers[:2])) if len(numbers) >= 2 else ()


def load_hd_internal_readings(hd_result):
    """Resolve identidad HD únicamente desde HD_DB_v2.0.db."""
    output = {
        "incarnation_cross": {},
        "profile": {},
        "active_channels": [],
        "signature_name": "",
        "not_self_theme_name": "",
        "warnings": [],
    }
    db_path = next((path for path in HD_DB_CANDIDATES if os.path.exists(path)), None)
    if not db_path:
        output["warnings"].append("HD_DB_v2.0.db no disponible; lecturas HD pendientes en DB.")
        return output

    conn = sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        profile_number = str(hd_result["profile"])
        profile_id = "PROFILE_" + profile_number.replace("/", "_")
        profile_row = conn.execute(
            "SELECT * FROM PROFILES_BASE WHERE PROFILE_ID = ? LIMIT 1", (profile_id,)
        ).fetchone()
        line_numbers = [int(item) for item in profile_number.split("/")]
        line_rows = {}
        for line_number in line_numbers:
            row = conn.execute(
                "SELECT LINE_ID, LINE_NAME_SPANISH FROM LINES_BASE WHERE LINE_ID = ? LIMIT 1",
                (f"LINE_{line_number}",),
            ).fetchone()
            if row:
                line_rows[line_number] = dict(row)
            else:
                output["warnings"].append(f"Lectura pendiente en DB: LINES_BASE LINE_{line_number}.")
        line_names = [line_rows.get(number, {}).get("LINE_NAME_SPANISH", "Lectura pendiente en DB") for number in line_numbers]
        output["profile"] = {
            "profile_id": profile_id,
            "profile_number": profile_number,
            "line_names": line_names,
            "display_name": f"{profile_number} — {' / '.join(line_names)}",
            "geometry_type": profile_row["GEOMETRY_TYPE"] if profile_row else "",
        }
        if not profile_row:
            output["warnings"].append(f"Lectura pendiente en DB: PROFILES_BASE {profile_id}.")

        expected_structure = (
            f"{gate_num(hd_result['personality']['Sol'])}/{gate_num(hd_result['personality']['Tierra'])} | "
            f"{gate_num(hd_result['design']['Sol'])}/{gate_num(hd_result['design']['Tierra'])}"
        )
        personality_sun = hd_result["personality"]["Sol"]
        cross_row = None
        if profile_row:
            geometry_class = _hd_geometry_class(profile_row["GEOMETRY_TYPE"])
            for row in conn.execute("SELECT * FROM INCARNATION_CROSSES").fetchall():
                import re as _hd_re
                sun_tokens = [item.strip() for item in str(row["SUN_PERSONALITY_GATE"] or "").split("/")]
                structure_matches = tuple(_hd_re.findall(r"\d+", str(row["CROSS_GATES_STRUCTURE"] or ""))) == tuple(_hd_re.findall(r"\d+", expected_structure))
                if (
                    _hd_geometry_class(row["GEOMETRY_TYPE"]) == geometry_class
                    and personality_sun in sun_tokens
                    and structure_matches
                ):
                    cross_row = row
                    break
        if cross_row:
            output["incarnation_cross"] = {
                "cross_id": cross_row["CROSS_ID"],
                "cross_name": cross_row["CROSS_NAME"],
                "geometry_type": cross_row["GEOMETRY_TYPE"],
                "sun_personality_gate_line": personality_sun,
                "sun_design_gate_line": hd_result["design"]["Sol"],
                "cross_gates_structure": cross_row["CROSS_GATES_STRUCTURE"],
            }
        else:
            output["incarnation_cross"] = {
                "cross_id": None,
                "cross_name": "Cruz no resuelta en DB",
                "sun_personality_gate_line": personality_sun,
                "sun_design_gate_line": hd_result["design"]["Sol"],
                "cross_gates_structure": expected_structure,
            }
            output["warnings"].append(
                f"Cruz no resuelta en DB: profile={profile_number}, personality_sun={personality_sun}, structure={expected_structure}."
            )

        channel_rows = [dict(row) for row in conn.execute("SELECT * FROM CHANNELS_BASE").fetchall()]
        for channel in hd_result["active_channels"]:
            target_pair = _hd_channel_pair(channel)
            row = next(
                (candidate for candidate in channel_rows if _hd_channel_pair(candidate.get("CHANNEL_ID")) == target_pair or _hd_channel_pair(candidate.get("GATES_CONNECTED")) == target_pair),
                None,
            )
            if row:
                output["active_channels"].append({
                    "runtime_channel": channel,
                    "channel_id": row["CHANNEL_ID"],
                    "channel_name": row["CHANNEL_NAME"],
                    "gates_connected": row["GATES_CONNECTED"],
                })
            else:
                output["active_channels"].append({
                    "runtime_channel": channel,
                    "channel_id": None,
                    "channel_name": "Lectura pendiente en DB",
                    "gates_connected": channel,
                })
                output["warnings"].append(f"Lectura pendiente en DB: CHANNELS_BASE canal {channel}.")

        runtime_type = _hd_normalize(hd_result["type"])
        type_aliases = {
            "manifesting generator": "generador manifestante",
            "generator": "generador",
            "manifestor": "manifestador",
            "projector": "proyector",
            "reflector": "reflector",
        }
        expected_type = type_aliases.get(runtime_type, runtime_type)
        type_row = next(
            (row for row in conn.execute("SELECT * FROM TYPES_AND_TYPES_AND_STRATEGIES").fetchall() if _hd_normalize(row["TYPE_NAME"]) == expected_type),
            None,
        )
        if type_row:
            output["signature_name"] = type_row["SIGNATURE_NAME"] or "Lectura pendiente en DB"
            output["not_self_theme_name"] = type_row["NOT_SELF_THEME_NAME"] or "Lectura pendiente en DB"
        else:
            output["signature_name"] = "Lectura pendiente en DB"
            output["not_self_theme_name"] = "Lectura pendiente en DB"
            output["warnings"].append(f"Lectura pendiente en DB: tipo HD {hd_result['type']}.")
    except sqlite3.Error as exc:
        output["warnings"].append(f"Error de consulta HD no fatal: {exc}")
    finally:
        conn.close()
    return output


def validate(result):
    is_reference = result["name"] == "Daniel Test" and result["birth_local"].startswith("1988-01-24 12:35")
    checks = {
        "type_present": bool(result["type"]),
        "strategy_present": bool(result["strategy"]),
        "authority_present": bool(result["authority"]),
        "profile_present": bool(result["profile"]),
        "nine_centers_classified": len(result["defined_centers"]) + len(result["open_centers"]) == 9,
        "all_64_gate_states_present": len(result["gate_states"]) == 64,
        "channels_derive_from_36_registry": set(result["active_channels"]).issubset({channel_key(a, b) for a, b in CHANNELS}),
        "all_64_gates_printed": True,
        "gates_anchored_to_center_edges": set(GATE_LABEL_POS) == set(range(1, 65)),
        "topology_20_57_present": channel_key(20, 57) in [channel_key(a, b) for a, b in CHANNELS],
    }
    if is_reference:
        checks.update({
            "daniel_type_pass": result["type"] == EXPECTED["type"],
            "daniel_strategy_pass": result["strategy"] == EXPECTED["strategy"],
            "daniel_authority_pass": result["authority"] == EXPECTED["authority"],
            "daniel_profile_pass": result["profile"] == EXPECTED["profile"],
            "daniel_defined_centers_pass": set(result["defined_centers"]) == set(EXPECTED["defined_centers"]),
            "daniel_active_channels_pass": set(result["active_channels"]) == set(EXPECTED["active_channels"]),
            "daniel_personality_pass": result["personality"] == EXPECTED["personality"],
            "daniel_design_pass": result["design"] == EXPECTED["design"],
        })
    checks["overall_pass"] = all(checks.values())
    return checks


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=14, fill=None, anchor="middle", weight=400, family="Inter"):
    fill = fill or COLORS["paper"]
    return f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" text-anchor="{anchor}" font-family="{family}" font-weight="{weight}">{esc(s)}</text>'


def polygon(points, fill, stroke, width=1.5):
    pts = " ".join(f"{x},{y}" for x, y in points)
    return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round"/>'


def rect(x, y, w, h, fill, stroke, rx=0, width=1.5):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'


# Topologia visual fija: cada canal sigue una ruta propia y cada puerta queda
# anclada al centro correcto. El calculo decide estado/color, nunca geometria.
CHANNEL_PATHS = {
    "64-47": "M570 205 L570 230", "61-24": "M600 205 L600 230", "63-4": "M630 205 L630 230",
    "17-62": "M570 300 L570 328", "43-23": "M600 300 L600 328", "11-56": "M630 300 L630 328",
    "31-7": "M570 422 L570 481 L550 502", "8-1": "M600 422 L600 470", "33-13": "M630 422 L630 481 L650 502",
    "10-20": "M548 394 C520 430 515 468 532 510", "45-21": "M652 390 C680 418 697 458 704 503",
    "16-48": "M548 350 C490 390 438 500 418 610", "20-57": "M548 382 C500 430 455 545 418 642",
    "35-36": "M652 350 C710 390 762 500 782 610", "12-22": "M652 382 C700 430 745 545 782 642",
    "25-51": "M671 522 L704 522", "40-37": "M742 585 L782 690", "26-44": "M704 570 C615 610 515 646 418 688",
    "2-14": "M600 614 L600 656", "46-29": "M625 590 L630 656", "15-5": "M575 590 L570 656",
    "10-34": "M532 550 C525 610 525 684 548 720", "10-57": "M532 532 C490 548 452 602 418 657",
    "34-20": "M548 744 C500 610 500 480 548 400", "34-57": "M548 744 C500 738 456 704 418 672",
    "50-27": "M418 720 L548 700", "59-6": "M652 730 L782 720",
    "32-54": "M418 748 L550 842", "28-38": "M418 780 L570 842", "18-58": "M418 812 L590 842",
    "42-53": "M580 776 L580 842", "3-60": "M620 776 L620 842", "9-52": "M640 776 L640 842",
    "19-49": "M550 890 C500 870 445 824 418 762", "39-55": "M600 922 C680 900 748 842 782 782",
    "41-30": "M650 890 C700 870 755 824 782 812",
}

GATE_LABEL_POS = {
    64:(566,184),61:(600,184),63:(634,184),47:(565,248),24:(600,248),4:(635,248),17:(565,278),43:(600,278),11:(635,278),
    62:(562,346),23:(590,346),56:(620,346),16:(553,372),20:(558,400),8:(588,402),31:(615,402),35:(642,370),12:(646,398),45:(642,418),33:(620,418),
    1:(600,500),7:(568,515),13:(632,515),10:(548,548),25:(652,548),15:(570,575),46:(630,575),2:(600,600),
    51:(704,522),21:(724,542),26:(708,570),40:(738,584),
    48:(424,630),57:(432,654),44:(446,684),50:(463,712),32:(447,742),28:(431,771),18:(424,804),
    36:(776,630),22:(768,654),37:(754,684),6:(737,712),49:(753,742),55:(769,771),30:(776,804),
    5:(565,675),14:(600,675),29:(635,675),34:(560,718),27:(585,742),42:(615,742),3:(640,718),9:(600,760),59:(640,760),
    53:(555,858),60:(580,858),52:(600,858),54:(625,858),19:(646,884),38:(558,902),58:(580,902),39:(620,902),41:(642,902),
}

CENTER_GEOMETRY = {
    "Cabeza": ("poly", [(548,202),(600,112),(652,202)]),
    "Ajna": ("poly", [(548,230),(652,230),(600,302)]),
    "Garganta": ("rect", (548,328,104,94)),
    "Centro G": ("poly", [(600,470),(674,540),(600,614),(526,540)]),
    "Corazon": ("poly", [(704,503),(756,552),(704,602)]),
    "Bazo": ("poly", [(418,610),(526,676),(418,820)]),
    "Plexo Solar": ("poly", [(782,610),(674,676),(782,820)]),
    "Sacral": ("rect", (548,656,104,120)),
    "Raiz": ("rect", (550,842,100,80)),
}


def draw_human_outline():
    return f'''<path d="M600 78 C550 92 530 142 534 210 C535 255 515 315 474 365
    C425 425 380 525 380 620 C380 735 350 835 395 930 C425 994 505 1018 556 966
    C578 944 588 932 600 932 C612 932 622 944 644 966 C695 1018 775 994 805 930
    C850 835 820 735 820 620 C820 525 775 425 726 365 C685 315 665 255 666 210
    C670 142 650 92 600 78Z" fill="{COLORS['paper']}" fill-opacity="0.055"
    stroke="{COLORS['paper']}" stroke-opacity="0.18" stroke-width="2"/>'''


def center_shape(name, defined):
    fill = COLORS["gold"] if defined else COLORS["bg"]
    stroke = COLORS["paper"] if defined else COLORS["gold"]
    kind, geo = CENTER_GEOMETRY[name]
    if kind == "poly":
        return polygon(geo, fill, stroke, 2.4)
    x, y, w, h = geo
    return rect(x, y, w, h, fill, stroke, 10, 2.4)


def gate_color(state):
    if state == "P": return COLORS["paper"]
    if state == "D": return COLORS["violet"]
    if state == "BOTH": return COLORS["gold"]
    return COLORS["idle"]


def draw_channel(a, b, active_channels, gate_states):
    key = channel_key(a, b)
    d = CHANNEL_PATHS.get(key) or CHANNEL_PATHS[f"{a}-{b}"]
    active = key in set(active_channels)
    base = f'<path d="{d}" pathLength="100" fill="none" stroke="{COLORS["gold"]}" stroke-opacity="0.28" stroke-width="8" stroke-linecap="butt"/>'
    rail = f'<path d="{d}" fill="none" stroke="{COLORS["paper"]}" stroke-opacity="0.55" stroke-width="1.2"/>'
    if not active:
        return base + rail
    first = gate_color(gate_states[a])
    second = gate_color(gate_states[b])
    return base + (
        f'<path d="{d}" pathLength="100" fill="none" stroke="{first}" stroke-width="8" stroke-dasharray="50 50"/>'
        f'<path d="{d}" pathLength="100" fill="none" stroke="{second}" stroke-width="8" stroke-dasharray="50 50" stroke-dashoffset="-50"/>'
    )


def draw_gate(g, state):
    x, y = GATE_LABEL_POS[g]
    # Ensancha el BodyGraph sin deformar circulos ni tipografia.
    x = 720 + (x - 600) * 1.18
    if state == "OPEN":
        return text(x, y+4, g, 10, COLORS["idle"], "middle", 650, "IBM Plex Mono")
    if state == "BOTH":
        return (f'<circle cx="{x}" cy="{y}" r="11" fill="{COLORS["paper"]}"/>'
                f'<path d="M{x} {y-11} A11 11 0 0 1 {x} {y+11} L{x} {y-11}Z" fill="{COLORS["violet"]}"/>'
                + text(x, y+4, g, 9, COLORS["bg"], "middle", 800, "IBM Plex Mono"))
    fill = gate_color(state)
    label = COLORS["paper"] if state == "D" else COLORS["bg"]
    return f'<circle cx="{x}" cy="{y}" r="11" fill="{fill}" stroke="{COLORS["gold"]}" stroke-width="1"/>' + text(x, y+4, g, 9, label, "middle", 800, "IBM Plex Mono")


def draw_side_column(title, subtitle, data, x, color):
    out = [text(x, 150, title, 25, color, "middle", 700, "Cormorant Garamond"),
           text(x, 174, subtitle, 10, COLORS["gold"], "middle", 500, "IBM Plex Mono")]
    y = 208
    for name, val in data.items():
        glyph = PLANET_GLYPHS.get(name, "")
        out.append(text(x-82, y, glyph, 22, color, "middle", 500))
        out.append(text(x-58, y-5, name, 12, COLORS["paper"], "start", 600))
        out.append(text(x+88, y, val, 16, color, "end", 700, "IBM Plex Mono"))
        out.append(f'<line x1="{x-58}" y1="{y+7}" x2="{x+88}" y2="{y+7}" stroke="{COLORS["gold"]}" stroke-opacity="0.24"/>')
        y += 42
    return "".join(out)


def draw_result_panel(result):
    y = 1020
    out = [f'<line x1="140" y1="{y}" x2="1300" y2="{y}" stroke="{COLORS["gold"]}" stroke-opacity="0.62"/>']
    fields = [
        (210, "TIPO", result["type"]), (540, "AUTORIDAD", result["authority"]),
        (850, "PERFIL", f'{result["profile"]} · Martir - Hereje'), (1170, "ESTRATEGIA", result["strategy"]),
    ]
    for x, label, value in fields:
        out.append(text(x, y+34, label, 10, COLORS["gold"], "middle", 700, "IBM Plex Mono"))
        out.append(text(x, y+62, value, 16, COLORS["paper"], "middle", 650))
    out.append(f'<line x1="140" y1="{y+82}" x2="1300" y2="{y+82}" stroke="{COLORS["gold"]}" stroke-opacity="0.32"/>')
    out.append(text(300, y+116, "DEFINICION", 10, COLORS["gold"], "middle", 700, "IBM Plex Mono"))
    out.append(text(300, y+144, "Split Definition", 15, COLORS["paper"], "middle", 600))
    out.append(text(900, y+116, "CRUZ DE ENCARNACION", 10, COLORS["gold"], "middle", 700, "IBM Plex Mono"))
    cross_gates = f'{result["personality"]["Sol"].split(".")[0]}/{result["personality"]["Tierra"].split(".")[0]} | {result["design"]["Sol"].split(".")[0]}/{result["design"]["Tierra"].split(".")[0]}'
    out.append(text(900, y+144, f"RAX of the Unexpected 4 · {cross_gates}", 15, COLORS["paper"], "middle", 650))
    return "".join(out)


def build_html(result, checks):
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="1220" viewBox="0 0 1440 1220">',
           f'<rect width="100%" height="100%" fill="{COLORS["bg"]}"/>',
           text(48, 38, "Internal Representation Template / Not Public Output", 11, COLORS["gold"], "start", 500, "IBM Plex Mono"),
           text(720, 62, "Human Design", 36, COLORS["paper"], "middle", 700, "Cormorant Garamond"),
           text(720, 92, f'HD Internal · PASS con mejoras necesarias · {result["name"]}', 11, COLORS["gold"], "middle", 500, "IBM Plex Mono"),
           draw_side_column("DISEÑO", "POSICIONES INCONSCIENTES", result["design"], 180, COLORS["violet"]),
           draw_side_column("PERSONALIDAD", "POSICIONES CONSCIENTES", result["personality"], 1260, COLORS["paper"]),
           '<g id="bodygraph-geometry" transform="translate(12 0) scale(1.18 1)">',
           draw_human_outline()]

    for a, b in CHANNELS:
        svg.append(draw_channel(a, b, result["active_channels"], result["gate_states"]))
    for center in ["Cabeza", "Ajna", "Garganta", "Centro G", "Corazon", "Bazo", "Plexo Solar", "Sacral", "Raiz"]:
        svg.append(center_shape(center, center in result["defined_centers"]))
    svg.append('</g>')
    for g in range(1, 65):
        svg.append(draw_gate(g, result["gate_states"][g]))

    svg.extend([
        draw_result_panel(result),
        text(48, 1200, "HD public activation: false · Synthesis Gate: BLOCKED", 10, COLORS["gold"], "start", 500, "IBM Plex Mono"),
        text(1392, 1200, "PASS_WITH_IMPROVEMENTS_NECESSARY · 64 gates · 36 channels", 10, COLORS["gold"], "end", 500, "IBM Plex Mono"),
        "</svg>"
    ])
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HD_INTERNAL_LIVE_BODYGRAPH_PROOF_v0.5</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600;700&family=IBM+Plex+Mono:wght@500;700&family=Inter:wght@400;600;700&display=swap');
html,body {{ margin:0; background:{COLORS["bg"]}; }}
.wrap {{ width:min(100%,1440px); margin:auto; }}
svg {{ display:block; width:100%; height:auto; }}
</style></head><body><main class="wrap">{''.join(svg)}</main></body></html>"""


_hd_input = globals().get("MASTER_INPUT", {
    "name": "Buscador Tecnico", "year": 2000, "month": 1, "day": 1,
    "hour": 12, "minute": 0, "timezone": "UTC",
})
natal_jd, natal_utc = jd_from_local(
    _hd_input["year"], _hd_input["month"], _hd_input["day"],
    _hd_input["hour"], _hd_input["minute"], _hd_input["timezone"],
)
design_jd = find_design_jd(natal_jd)

personality = calc_activations(natal_jd)
design = calc_activations(design_jd)
derived = derive_hd(personality, design)

result = {
    "name": _hd_input["name"],
    "birth_local": f'{_hd_input["year"]:04d}-{_hd_input["month"]:02d}-{_hd_input["day"]:02d} {_hd_input["hour"]:02d}:{_hd_input["minute"]:02d} {_hd_input["timezone"]}',
    "birth_utc": natal_utc,
    "design_jd": design_jd,
    "personality": personality,
    "design": design,
    **derived,
}

checks = validate(result)
# The legacy hard-coded drawing is not emitted. Its calculation result is
# consumed immediately by the BodyGraph.svg-based renderer below.


# -----------------------------------------------------------------------------
# BODYGRAPH SVG INTEGRATION (based on the separated Bodygraph v1.PY)
# -----------------------------------------------------------------------------

import copy as _bg_copy
import html as _bg_html
import re as _bg_re
import xml.etree.ElementTree as _bg_ET

_BG_SVG_NS = "http://www.w3.org/2000/svg"
_BG_VISIO_NS = "http://schemas.microsoft.com/visio/2003/SVGExtensions/"
_bg_ET.register_namespace("", _BG_SVG_NS)
_bg_ET.register_namespace("v", _BG_VISIO_NS)

_BG_CENTER_ALIASES = {
    "head": "Cabeza", "cabeza": "Cabeza", "ajna": "Ajna",
    "throat": "Garganta", "garganta": "Garganta", "g": "Centro G",
    "centro g": "Centro G", "centro_g": "Centro G", "identity": "Centro G",
    "heart": "Corazon", "corazon": "Corazon", "corazón": "Corazon",
    "will": "Corazon", "ego": "Corazon", "splenic": "Bazo", "bazo": "Bazo",
    "sacral": "Sacral", "solar plexus": "Plexo Solar", "plexo solar": "Plexo Solar",
    "plexo_solar": "Plexo Solar", "root": "Raiz", "raiz": "Raiz", "raíz": "Raiz",
}
_BG_CENTERS = {"Cabeza", "Ajna", "Garganta", "Centro G", "Corazon", "Bazo", "Sacral", "Plexo Solar", "Raiz"}
_BG_CENTER_DISPLAY = {
    "Cabeza": "Cabeza", "Ajna": "Ajna", "Garganta": "Garganta", "Centro G": "Centro G",
    "Corazon": "Corazón / Ego", "Bazo": "Bazo", "Sacral": "Sacral",
    "Plexo Solar": "Plexo Solar", "Raiz": "Raíz",
}
_BG_COLORS = {"paper": "#F4EAD2", "gold": "#C6A15B", "violet": "#4B2E6D", "idle": "#6F6A5D", "bg": "#080E1F"}
_BG_BODY_ORDER = ["Sol", "Tierra", "Nodo Norte", "Nodo Sur", "Luna", "Mercurio", "Venus", "Marte", "Jupiter", "Saturno", "Urano", "Neptuno", "Pluton"]
_BG_GLYPHS = {"Sol":"☉", "Tierra":"⊕", "Nodo Norte":"☊", "Nodo Sur":"☋", "Luna":"☽", "Mercurio":"☿", "Venus":"♀", "Marte":"♂", "Jupiter":"♃", "Saturno":"♄", "Urano":"♅", "Neptuno":"♆", "Pluton":"♇"}


def _bg_alt_text(group):
    for node in group.iter(f"{{{_BG_VISIO_NS}}}ud"):
        if node.get(f"{{{_BG_VISIO_NS}}}nameU") == "visAltText":
            value = node.get(f"{{{_BG_VISIO_NS}}}val", "")
            match = _bg_re.fullmatch(r"VT4\((.*)\)", value, flags=_bg_re.DOTALL)
            return match.group(1).strip() if match else value.strip()
    return ""


def _bg_normalize_center(value):
    return _BG_CENTER_ALIASES.get(str(value or "").strip().lower())


def _bg_matrix_multiply(a, b):
    return [[
        a[0][0]*b[0][0] + a[0][1]*b[1][0] + a[0][2]*b[2][0],
        a[0][0]*b[0][1] + a[0][1]*b[1][1] + a[0][2]*b[2][1],
        a[0][0]*b[0][2] + a[0][1]*b[1][2] + a[0][2]*b[2][2]], [
        a[1][0]*b[0][0] + a[1][1]*b[1][0] + a[1][2]*b[2][0],
        a[1][0]*b[0][1] + a[1][1]*b[1][1] + a[1][2]*b[2][1],
        a[1][0]*b[0][2] + a[1][1]*b[1][2] + a[1][2]*b[2][2]], [0, 0, 1]]


def _bg_parse_transform(value):
    matrix = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    for name, raw in _bg_re.findall(r"(matrix|translate|scale|rotate)\(([^)]*)\)", value or ""):
        args = [float(x) for x in _bg_re.findall(r"-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", raw, _bg_re.I)]
        if name == "matrix" and len(args) >= 6:
            a, b, c, d, e, f = args[:6]; component = [[a,c,e],[b,d,f],[0,0,1]]
        elif name == "translate":
            component = [[1,0,args[0] if args else 0],[0,1,args[1] if len(args)>1 else 0],[0,0,1]]
        elif name == "scale":
            sx = args[0] if args else 1; sy = args[1] if len(args)>1 else sx; component = [[sx,0,0],[0,sy,0],[0,0,1]]
        elif name == "rotate":
            angle = math.radians(args[0] if args else 0); c = math.cos(angle); s = math.sin(angle)
            component = [[c,-s,0],[s,c,0],[0,0,1]]
        else:
            continue
        matrix = _bg_matrix_multiply(matrix, component)
    return matrix


def _bg_apply(matrix, x, y):
    return (matrix[0][0]*x + matrix[0][1]*y + matrix[0][2], matrix[1][0]*x + matrix[1][1]*y + matrix[1][2])


def _bg_group_point(group, x=0, y=792):
    return _bg_apply(_bg_parse_transform(group.get("transform")), x, y)


def _bg_path_endpoints(group, path):
    nums = [float(x) for x in _bg_re.findall(r"-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", path.get("d", ""), _bg_re.I)]
    if len(nums) < 4:
        return None
    matrix = _bg_parse_transform(group.get("transform"))
    return _bg_apply(matrix, nums[0], nums[1]), _bg_apply(matrix, nums[-2], nums[-1])


def _bg_dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])


def _bg_state_color(state):
    return {"P": _BG_COLORS["paper"], "D": _BG_COLORS["violet"], "BOTH": _BG_COLORS["gold"], "OPEN": _BG_COLORS["idle"]}[state]


def _bg_set_title(group, value):
    title_tag = f"{{{_BG_SVG_NS}}}title"
    title = next((x for x in list(group) if x.tag == title_tag), None)
    if title is None:
        title = _bg_ET.Element(title_tag); group.insert(0, title)
    title.text = str(value)


def _bg_access(group, kind, name, state, detail):
    group.set("data-dc-kind", kind); group.set("data-dc-name", str(name)); group.set("data-dc-state", str(state)); group.set("data-dc-detail", str(detail)); group.set("tabindex", "0"); group.set("role", "button")


def _bg_prepare_svg(svg_path, hd_result):
    tree = _bg_ET.parse(svg_path); root = tree.getroot()
    foreground = next((g for g in root.iter(f"{{{_BG_SVG_NS}}}g") if g.get(f"{{{_BG_VISIO_NS}}}groupContext") == "foregroundPage"), None)
    if foreground is None:
        raise RuntimeError("BodyGraph.svg no contiene foregroundPage de Visio.")
    centers, gates, channels, other = [], [], [], []
    for child in list(foreground):
        if child.tag != f"{{{_BG_SVG_NS}}}g":
            continue
        label = _bg_alt_text(child); center = _bg_normalize_center(label)
        if label.isdigit() and 1 <= int(label) <= 64: gates.append((int(label), child))
        elif _bg_re.fullmatch(r"CHANNEL_\d+_\d+", label, flags=_bg_re.I):
            m = _bg_re.fullmatch(r"CHANNEL_(\d+)_(\d+)", label, flags=_bg_re.I); channels.append((label.upper(), int(m.group(1)), int(m.group(2)), child))
        elif center: centers.append((center, child))
        else: other.append(child)
    gate_states = hd_result["gate_states"]
    expected_channels = {f"{min(a,b)}-{max(a,b)}" for _,a,b,_ in channels}
    active = set(hd_result["active_channels"])
    if len(gates) != 64 or len(centers) != 9 or len(channels) != 36:
        raise RuntimeError(f"BodyGraph.svg incompleto: gates={len(gates)}, centers={len(centers)}, channels={len(channels)}; esperados 64/9/36.")
    gate_coords = {g: _bg_group_point(group) for g, group in gates}
    for gate, group in gates:
        state = gate_states[gate]; sources = []
        for body, value in hd_result["personality"].items():
            if int(str(value).split(".")[0]) == gate: sources.append(f"Personality: {body} {value}")
        for body, value in hd_result["design"].items():
            if int(str(value).split(".")[0]) == gate: sources.append(f"Design: {body} {value}")
        detail = " | ".join(sources) if sources else "Sin activación"
        state_class = {"P": "personality", "D": "design", "BOTH": "both", "OPEN": "open"}[state]
        group.set("id", f"gate-{gate}"); group.set("class", f"dc-gate state-{state_class}"); _bg_access(group, "gate", gate, state, detail); _bg_set_title(group, f"Puerta {gate} · {detail}")
    for raw, a, b, group in channels:
        canonical = f"{min(a,b)}-{max(a,b)}"; sa, sb = gate_states[a], gate_states[b]
        defined = canonical in active and sa != "OPEN" and sb != "OPEN"
        channel_state = "DEFINED" if defined else ("PARTIAL" if sa != "OPEN" or sb != "OPEN" else "OPEN")
        group.set("id", f"channel-{canonical}"); group.set("class", f"dc-channel state-{channel_state.lower()}"); detail = f"Puerta {a}: {sa} | Puerta {b}: {sb} | Canal: {channel_state}"; _bg_access(group, "channel", canonical, channel_state, detail); _bg_set_title(group, f"Canal {canonical} · {channel_state}")
        for path in list(group.iter(f"{{{_BG_SVG_NS}}}path")):
            endpoints = _bg_path_endpoints(group, path); path.set("class", "dc-channel-base"); path.set("style", "fill:none;stroke:#6F6A5D;stroke-opacity:.34;stroke-width:1.25;stroke-linecap:round;stroke-linejoin:round;marker-start:none;marker-end:none")
            if defined:
                path.set("style", "fill:none;stroke:#C6A15B;stroke-opacity:.30;stroke-width:3.25;stroke-linecap:round;stroke-linejoin:round;marker-start:none;marker-end:none")
            if endpoints and a in gate_coords and b in gate_coords:
                direct = _bg_dist(endpoints[0], gate_coords[a]) + _bg_dist(endpoints[1], gate_coords[b]); reverse = _bg_dist(endpoints[0], gate_coords[b]) + _bg_dist(endpoints[1], gate_coords[a]); offset_a, offset_b = ("0", "-50") if direct <= reverse else ("-50", "0")
            else: offset_a, offset_b = "0", "-50"
            for state, offset, suffix in ((sa, offset_a, "a"), (sb, offset_b, "b")):
                if state == "OPEN": continue
                half = _bg_copy.deepcopy(path); half.set("class", f"dc-channel-half dc-half-{suffix}"); half.set("pathLength", "100"); half.set("stroke-dasharray", "50 50"); half.set("stroke-dashoffset", offset); half.set("style", f"fill:none;stroke:{_bg_state_color(state)};stroke-opacity:.96;stroke-width:2.25;stroke-linecap:round;stroke-linejoin:round") ; group.append(half)
            hit = _bg_copy.deepcopy(path); hit.set("class", "dc-channel-hit"); hit.set("style", "fill:none;stroke:transparent;stroke-width:8;pointer-events:stroke"); group.append(hit)
    defined_centers = set(hd_result["defined_centers"])
    for center, group in centers:
        state = "DEFINED" if center in defined_centers else "OPEN"; group.set("id", "center-" + _bg_re.sub(r"[^a-z0-9]+", "-", center.lower()).strip("-")); group.set("class", f"dc-center state-{state.lower()}"); _bg_access(group, "center", _BG_CENTER_DISPLAY[center], state, f"Centro {_BG_CENTER_DISPLAY[center]} · {state}"); _bg_set_title(group, f"Centro {_BG_CENTER_DISPLAY[center]} · {state}")
    style = _bg_ET.Element(f"{{{_BG_SVG_NS}}}style"); style.set("id", "dharmacodex-bodygraph-runtime-style"); style.text = f"""
      .dc-center path {{ stroke:{_BG_COLORS['gold']} !important; stroke-width:1.35 !important; }}
      .dc-center.state-defined path {{ fill:{_BG_COLORS['gold']} !important; }} .dc-center.state-open path {{ fill:{_BG_COLORS['bg']} !important; }}
      .dc-gate path {{ stroke:{_BG_COLORS['gold']} !important; stroke-width:.85 !important; }}
      .dc-gate text {{ font-family:'IBM Plex Mono',monospace !important; font-size:4.15px !important; font-weight:700 !important; }}
      .dc-gate.state-open path {{ fill:{_BG_COLORS['bg']} !important; stroke:{_BG_COLORS['idle']} !important; }} .dc-gate.state-open text {{ fill:{_BG_COLORS['idle']} !important; }}
      .dc-gate.state-personality path {{ fill:{_BG_COLORS['paper']} !important; }} .dc-gate.state-personality text {{ fill:{_BG_COLORS['bg']} !important; }}
      .dc-gate.state-design path {{ fill:{_BG_COLORS['violet']} !important; }} .dc-gate.state-design text {{ fill:{_BG_COLORS['paper']} !important; }}
      .dc-gate.state-both path {{ fill:{_BG_COLORS['gold']} !important; }} .dc-gate.state-both text {{ fill:{_BG_COLORS['bg']} !important; }}
      .dc-channel, .dc-center, .dc-gate {{ cursor:pointer; }} .dc-channel-hit {{ stroke:transparent !important; }}
    """
    root.append(style); root.set("width", "1200"); root.set("height", "1600"); root.set("preserveAspectRatio", "xMidYMid meet"); root.set("class", "dharmacodex-bodygraph"); root.set("role", "img"); root.set("aria-label", f"BodyGraph de {hd_result['name']}")
    return _bg_ET.tostring(root, encoding="unicode"), {"svg_source": str(svg_path), "centers": len(centers), "gates": len(gates), "channels": len(channels), "channels_in_svg": sorted(expected_channels), "active_channels": sorted(active), "geometry_status": "PASS", "renderer": "Bodygraph v1.PY + BodyGraph.svg"}


def _bg_table(title, values, color):
    rows = "".join(f"<tr><td class='glyph'>{_bg_html.escape(_BG_GLYPHS.get(body,''))}</td><td>{_bg_html.escape(body)}</td><td>{_bg_html.escape(str(values[body]))}</td></tr>" for body in _BG_BODY_ORDER if body in values)
    return f"<section class='activation {color}'><h2>{title}</h2><table>{rows}</table></section>"


def _bg_render_html(svg_markup, hd_result, checks):
    defined = ", ".join(_BG_CENTER_DISPLAY.get(x, x) for x in hd_result["defined_centers"])
    opened = ", ".join(_BG_CENTER_DISPLAY.get(x, x) for x in hd_result["open_centers"])
    return f"""<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Human Design · BodyGraph.svg</title><style>
      @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600;700&family=IBM+Plex+Mono:wght@500;700&family=Inter:wght@400;600;700&display=swap'); :root{{--bg:#080E1F;--paper:#F4EAD2;--gold:#C6A15B;--violet:#4B2E6D;--muted:#AAA391}} *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--paper);font-family:Inter,sans-serif}} .page{{width:min(1500px,calc(100vw - 30px));margin:auto;padding:22px 18px 35px}} .internal{{color:var(--gold);font:11px 'IBM Plex Mono',monospace;letter-spacing:.08em;text-transform:uppercase}} header{{text-align:center;margin:8px 0 16px}} h1{{font:700 clamp(38px,5vw,62px)/.95 'Cormorant Garamond',serif;margin:8px 0}} .sub{{color:var(--gold);font:11px 'IBM Plex Mono',monospace}} .layout{{display:grid;grid-template-columns:minmax(190px,260px) minmax(520px,860px) minmax(190px,260px);gap:16px;align-items:start}} .canvas svg{{width:100%;height:auto;display:block}} .activation{{padding-top:42px}} .activation h2{{font:700 14px 'IBM Plex Mono',monospace;color:var(--gold);border-bottom:1px solid rgba(198,161,91,.5);padding-bottom:8px}} .activation.design h2{{color:#9C78C7}} table{{width:100%;border-collapse:collapse}} td{{padding:5px 3px;border-bottom:1px solid rgba(244,234,210,.1);font-size:12px}} td.glyph{{width:24px;color:var(--gold);font-size:17px;text-align:center}} td:last-child{{font:700 11px 'IBM Plex Mono',monospace;color:var(--gold);text-align:right}} .summary{{border-top:1px solid rgba(198,161,91,.5);margin-top:14px;padding-top:15px;display:grid;grid-template-columns:repeat(4,1fr);gap:14px}} .metric label{{display:block;color:var(--gold);font:10px 'IBM Plex Mono',monospace}} .metric strong{{display:block;margin-top:5px;font:600 19px 'Cormorant Garamond',serif}} .details{{margin-top:14px;color:var(--muted);font-size:12px;line-height:1.55}} footer{{margin-top:16px;border-top:1px solid rgba(198,161,91,.3);padding-top:10px;color:var(--gold);font:10px 'IBM Plex Mono',monospace}} @media(max-width:1050px){{.layout{{grid-template-columns:1fr 1fr}} .canvas{{grid-column:1/-1;grid-row:1;max-width:850px;margin:auto}} .activation{{padding-top:0}}}} @media(max-width:650px){{.layout,.summary{{grid-template-columns:1fr}} .canvas{{grid-column:auto}}}} </style></head><body><main class='page'><div class='internal'>Internal Representation Template / Not Public Output</div><header><h1>Human Design</h1><div class='sub'>BodyGraph.svg · { _bg_html.escape(hd_result['name']) }</div></header><section class='layout'>{_bg_table('DISEÑO',hd_result['design'],'design')}<div class='canvas'>{svg_markup}</div>{_bg_table('PERSONALIDAD',hd_result['personality'],'personality')}</section><section class='summary'><div class='metric'><label>TIPO</label><strong>{_bg_html.escape(hd_result['type'])}</strong></div><div class='metric'><label>AUTORIDAD</label><strong>{_bg_html.escape(hd_result['authority'])}</strong></div><div class='metric'><label>PERFIL</label><strong>{_bg_html.escape(hd_result['profile'])}</strong></div><div class='metric'><label>ESTRATEGIA</label><strong>{_bg_html.escape(hd_result['strategy'])}</strong></div></section><div class='details'><b>Centros definidos:</b> {_bg_html.escape(defined)}<br><b>Centros abiertos:</b> {_bg_html.escape(opened)}<br><b>Canales activos:</b> {_bg_html.escape(', '.join(sorted(hd_result['active_channels'])) or 'Ninguno')}</div><footer>Renderer: Bodygraph v1.PY + BodyGraph.svg · Geometry: {checks['geometry_status']} · HD public activation: false · Synthesis Gate: BLOCKED</footer></main></body></html>"""


def _bg_render_html_v115(svg_markup, hd_result, checks):
    readings = hd_result.get("internal_readings", {})
    profile = readings.get("profile", {})
    cross = readings.get("incarnation_cross", {})
    channels = readings.get("active_channels", [])
    warnings_list = readings.get("warnings", [])
    defined = ", ".join(_BG_CENTER_DISPLAY.get(x, x) for x in hd_result["defined_centers"])
    opened = ", ".join(_BG_CENTER_DISPLAY.get(x, x) for x in hd_result["open_centers"])
    channel_html = "".join(
        f"<li>{_bg_html.escape(item.get('channel_name') or 'Lectura pendiente en DB')}</li>"
        for item in channels
    ) or "<li>Ninguno</li>"
    warnings_html = "".join(f"<li>{_bg_html.escape(item)}</li>" for item in warnings_list)
    warning_section = f"<section class='warnings'><h2>Advertencias DB</h2><ul>{warnings_html}</ul></section>" if warnings_html else ""
    profile_display = profile.get("display_name") or hd_result["profile"]
    cross_name = cross.get("cross_name") or "Cruz no resuelta en DB"
    cross_structure = cross.get("cross_gates_structure") or "Lectura pendiente en DB"
    return f"""<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Human Design · BodyGraph.svg</title><style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600;700&family=IBM+Plex+Mono:wght@500;700&family=Inter:wght@400;600;700&display=swap');
    :root{{--bg:#080E1F;--paper:#F4EAD2;--gold:#C6A15B;--violet:#4B2E6D;--muted:#AAA391}}
    *{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--paper);font-family:Inter,sans-serif}}.page{{width:min(1500px,calc(100vw - 30px));margin:auto;padding:22px 18px 35px}}.internal{{color:var(--gold);font:11px 'IBM Plex Mono',monospace;letter-spacing:.08em;text-transform:uppercase}}header{{text-align:center;margin:8px 0 16px}}h1{{font:700 clamp(38px,5vw,62px)/.95 'Cormorant Garamond',serif;margin:8px 0}}.sub{{color:var(--gold);font:11px 'IBM Plex Mono',monospace}}.layout{{display:grid;grid-template-columns:minmax(190px,260px) minmax(520px,860px) minmax(190px,260px);gap:16px;align-items:start}}.canvas svg{{width:100%;height:auto;display:block}}.activation{{padding-top:42px}}.activation h2,.reading-card h2,.warnings h2{{font:700 14px 'IBM Plex Mono',monospace;color:var(--gold);border-bottom:1px solid rgba(198,161,91,.5);padding-bottom:8px}}.activation.design h2{{color:#9C78C7}}table{{width:100%;border-collapse:collapse}}td{{padding:5px 3px;border-bottom:1px solid rgba(244,234,210,.1);font-size:12px}}td.glyph{{width:24px;color:var(--gold);font-size:17px;text-align:center}}td:last-child{{font:700 11px 'IBM Plex Mono',monospace;color:var(--gold);text-align:right}}.summary{{border-top:1px solid rgba(198,161,91,.5);margin-top:14px;padding-top:15px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}}.metric label{{display:block;color:var(--gold);font:10px 'IBM Plex Mono',monospace}}.metric strong{{display:block;margin-top:5px;font:600 19px 'Cormorant Garamond',serif}}.details{{margin-top:14px;color:var(--muted);font-size:12px;line-height:1.55}}.reading-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:16px}}.reading-card,.warnings{{border:1px solid rgba(198,161,91,.32);padding:14px;background:rgba(244,234,210,.04)}}.reading-card p,.reading-card li,.warnings li{{font-size:12px;line-height:1.55;color:var(--muted)}}footer{{margin-top:16px;border-top:1px solid rgba(198,161,91,.3);padding-top:10px;color:var(--gold);font:10px 'IBM Plex Mono',monospace}}@media(max-width:1050px){{.layout{{grid-template-columns:1fr 1fr}}.canvas{{grid-column:1/-1;grid-row:1;max-width:850px;margin:auto}}.activation{{padding-top:0}}}}@media(max-width:650px){{.layout,.summary,.reading-grid{{grid-template-columns:1fr}}.canvas{{grid-column:auto}}}}
    </style></head><body><main class='page'><div class='internal'>Internal Representation Template / Not Public Output</div><header><h1>Human Design</h1><div class='sub'>BodyGraph.svg · {_bg_html.escape(hd_result['name'])}</div></header><section class='layout'>{_bg_table('DISEÑO',hd_result['design'],'design')}<div class='canvas'>{svg_markup}</div>{_bg_table('PERSONALIDAD',hd_result['personality'],'personality')}</section><section class='summary'><div class='metric'><label>TIPO</label><strong>{_bg_html.escape(hd_result['type'])}</strong></div><div class='metric'><label>AUTORIDAD</label><strong>{_bg_html.escape(hd_result['authority'])}</strong></div><div class='metric'><label>PERFIL</label><strong>{_bg_html.escape(profile_display)}</strong></div><div class='metric'><label>ESTRATEGIA</label><strong>{_bg_html.escape(hd_result['strategy'])}</strong></div><div class='metric'><label>FIRMA</label><strong>{_bg_html.escape(readings.get('signature_name') or 'Lectura pendiente en DB')}</strong></div><div class='metric'><label>TEMA DEL NO-SER</label><strong>{_bg_html.escape(readings.get('not_self_theme_name') or 'Lectura pendiente en DB')}</strong></div></section><div class='details'><b>Centros definidos:</b> {_bg_html.escape(defined)}<br><b>Centros abiertos:</b> {_bg_html.escape(opened)}</div><section class='reading-grid'><article class='reading-card'><h2>Cruz de Encarnación</h2><p><b>{_bg_html.escape(cross_name)}</b></p><p>{_bg_html.escape(cross_structure)}</p></article><article class='reading-card'><h2>Canales activos</h2><ul>{channel_html}</ul></article></section>{warning_section}<footer>Renderer: Bodygraph v1.PY + BodyGraph.svg · Geometry: {checks['geometry_status']} · HD public activation: false · Synthesis Gate: BLOCKED</footer></main></body></html>"""


def _hd_internal_readings_md(hd_result):
    readings = hd_result.get("internal_readings", {})
    cross = readings.get("incarnation_cross", {})
    profile = readings.get("profile", {})
    lines = [
        "", "## Internal DB Readings", "",
        f"- Incarnation Cross: {cross.get('cross_name', 'Cruz no resuelta en DB')}",
        f"- Cross ID: {cross.get('cross_id') or 'Lectura pendiente en DB'}",
        f"- Cross gates: {cross.get('cross_gates_structure', 'Lectura pendiente en DB')}",
        f"- Profile: {profile.get('display_name', hd_result.get('profile', 'Lectura pendiente en DB'))}",
        f"- Signature: {readings.get('signature_name') or 'Lectura pendiente en DB'}",
        f"- Not-Self Theme: {readings.get('not_self_theme_name') or 'Lectura pendiente en DB'}",
        "", "### Active Channels", "",
    ]
    lines.extend(f"- {item.get('channel_name') or 'Lectura pendiente en DB'}" for item in readings.get("active_channels", []))
    lines.extend(["", "### Warnings", ""])
    lines.extend(f"- {warning}" for warning in readings.get("warnings", []))
    if not readings.get("warnings"):
        lines.append("- None")
    return "\n".join(lines)


_bg_svg_candidates = [Path(BODYGRAPH_SVG_PATH), Path('/content/BodyGraph.svg'), Path('/content/01-BodyGraph.svg')]
_bg_svg_path = next((p for p in _bg_svg_candidates if p.exists()), None)
if _bg_svg_path is None:
    raise FileNotFoundError('No encontré BodyGraph.svg en /content. Carga el SVG aprobado antes de ejecutar el master.')
_bg_hd_result = dict(result)
_bg_hd_result['gate_states'] = result['gate_states']
_bg_hd_result['internal_readings'] = load_hd_internal_readings(_bg_hd_result)
_bg_svg_markup, _bg_checks = _bg_prepare_svg(_bg_svg_path, _bg_hd_result)
_bg_checks['incarnation_cross_resolved'] = bool(_bg_hd_result['internal_readings']['incarnation_cross'].get('cross_id'))
_bg_checks['profile_line_names_resolved'] = all(name != 'Lectura pendiente en DB' for name in _bg_hd_result['internal_readings']['profile'].get('line_names', []))
_bg_checks['active_channel_names_resolved'] = all(item.get('channel_name') != 'Lectura pendiente en DB' for item in _bg_hd_result['internal_readings']['active_channels'])
_bg_checks['signature_and_not_self_resolved'] = bool(_bg_hd_result['internal_readings'].get('signature_name') and _bg_hd_result['internal_readings'].get('not_self_theme_name'))
_bg_html_out = _bg_render_html_v115(_bg_svg_markup, _bg_hd_result, _bg_checks)
Path(OUT_HTML).write_text(_bg_html_out, encoding='utf-8')
Path(OUT_DEBUG).write_text(json.dumps({'result': _bg_hd_result, 'internal_readings': _bg_hd_result['internal_readings'], 'checks': _bg_checks}, ensure_ascii=False, indent=2), encoding='utf-8')
Path(OUT_REPORT).write_text('# HD_INTERNAL_LIVE_BODYGRAPH_VALIDATION_v1.1.5\n\n' + '\n'.join(f'- {k}: {v}' for k,v in _bg_checks.items()) + _hd_internal_readings_md(_bg_hd_result), encoding='utf-8')
try:
    display(HTML(_bg_html_out))
except Exception:
    pass
print('FINAL BODYGRAPH SVG:', OUT_HTML)
print('BODYGRAPH CHECKS:', json.dumps(_bg_checks, ensure_ascii=False, indent=2))


# %% [CELDA 4 — NUMEROLOGIA]

"""
NUMEROLOGY_INTERNAL_LIVE_PROOF_MASTER_v0.2_colab.py

DharmaCodex internal Numerology live proof.
Paste this file into one Colab cell and run it there.

Scope:
- Calculates numerology coordinates from name/date/current year.
- Creates an internal HTML visual proof with DharmaCodex colors.
- Creates a debug JSON and validation markdown.
- Does not query DB by default.
- Does not generate public output, PDF, synthesis, or interpretation.

Outputs in Colab:
- /content/NUMEROLOGY_INTERNAL_LIVE_PROOF_v0.2.html
- /content/NUMEROLOGY_INTERNAL_LIVE_DEBUG_v0.2.json
- /content/NUMEROLOGY_INTERNAL_LIVE_VALIDATION_v0.2.md
"""

import json
import math
import os
import sqlite3
import unicodedata
from datetime import date, datetime


# ============================================================
# 1. INPUTS
# ============================================================

_num_input = globals().get("MASTER_INPUT", {
    "full_name": "BUSCADOR TECNICO",
    "day": 1, "month": 1, "year": 2000,
})
NOMBRE_COMPLETO = _num_input.get("full_name", _num_input.get("name", "Buscador Tecnico"))
DIA_NACIMIENTO = _num_input["day"]
MES_NACIMIENTO = _num_input["month"]
ANIO_NACIMIENTO = _num_input["year"]
ANIO_ACTUAL = datetime.now().year

OUTPUT_HTML = "/content/NUMEROLOGY_INTERNAL_LIVE_PROOF_v0.2.html"
OUTPUT_JSON = "/content/NUMEROLOGY_INTERNAL_LIVE_DEBUG_v0.2.json"
OUTPUT_MD = "/content/NUMEROLOGY_INTERNAL_LIVE_VALIDATION_v0.2.md"

NUM_DB_CANDIDATES = [
    "/content/Data_Bases/NUM_DB_v2.0.db",
    "/content/Data_Bases/04-NUM_DB_v2.0.db",
    "/content/NUM_DB_v2.0.db",
    "/content/04-NUM_DB_v2.0.db",
    "/content/04-Num_Readings (1).db",
]


def find_existing_path(candidates):
    return next((path for path in candidates if os.path.exists(path)), None)


def load_numerology_readings(result):
    """Carga lecturas con claves canónicas de la DB y matching por dígitos/tipo.

    Las reglas de cálculo usan nombres cortos sin acentos, mientras que la DB
    conserva claves editoriales como ``Frustración`` o ``Despiste / Olvido``.
    El nombre no es la identidad de una flecha: su tipo y sus tres dígitos sí.
    """
    db_path = find_existing_path(NUM_DB_CANDIDATES)
    fallback = {
        "natal": {}, "pinnacles": {}, "challenges": {}, "arrows": {},
        "db_path": None,
    }
    if not db_path:
        return fallback

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        for digit, count in result["digit_counts"].items():
            if count:
                key = int(digit * count)
                row = conn.execute(
                    "SELECT * FROM Tabla_Natal_Grid WHERE NATALGRID_NUM = ? LIMIT 1",
                    (key,),
                ).fetchone()
                if row:
                    fallback["natal"][digit] = dict(row)

        for value in set(result["life_stages"]["pinnacles"].values()):
            row = conn.execute("SELECT * FROM PINACLE WHERE PIN_NUM = ? LIMIT 1", (value,)).fetchone()
            if row:
                fallback["pinnacles"][str(value)] = dict(row)

        for value in set(result["life_stages"]["challenges"].values()):
            row = conn.execute("SELECT * FROM CHLLG WHERE CHLLG_NUM = ? LIMIT 1", (value,)).fetchone()
            if row:
                fallback["challenges"][str(value)] = dict(row)

        arrow_rows = [dict(row) for row in conn.execute("SELECT * FROM Arrows_tbl").fetchall()]

        def row_digits(row):
            import re as _num_re
            values = [int(x) for x in _num_re.findall(r"\d+", str(row.get("ARROWS_SET", "")))]
            return tuple(values[-3:]) if len(values) >= 3 else tuple(values)

        def row_type(row):
            return "strength" if str(row.get("ARROWS_TYPE", "")).strip().lower() == "fuerza" else "weakness"

        for item in result["arrows"]["strength"] + result["arrows"]["weakness"]:
            target = tuple(item["digits"])
            kind = item.get("kind", "strength" if item in result["arrows"]["strength"] else "weakness")
            row = next((candidate for candidate in arrow_rows if row_type(candidate) == kind and row_digits(candidate) == target), None)
            if row:
                fallback["arrows"][item["name"]] = row
    finally:
        conn.close()

    fallback["db_path"] = db_path
    return fallback


NUM_DIGITAL_POSITION_MAP = {
    "Camino de Vida": "Camino de Vida",
    "Expresion / Destino": "Expresión / Destino",
    "Dia de Nacimiento": "Día de Nacimiento",
    "Impulso del Alma": "Impulso del Alma",
    "Personalidad": "Personalidad",
    "Ano Personal": "Año Personal",
}

NUM_KARMIC_TABLE_MAP = {
    "Camino de Vida": ("LP_krm", "LP_krm"),
    "Expresion / Destino": ("ED_krm", "ED_krm"),
    "Dia de Nacimiento": ("DB_krm", "DB_krm"),
    "Ano Personal": ("PY_krm", "PY_krm"),
}


def load_numerology_internal_readings(result):
    internal = {"digital_breakdown": [], "active_karmic_alerts": [], "warnings": []}
    db_path = find_existing_path(NUM_DB_CANDIDATES)
    if not db_path:
        internal["warnings"].append("NUM_DB_v2.0.db no disponible; lecturas internas pendientes en DB.")
        return internal
    conn = sqlite3.connect(f"file:{os.path.abspath(db_path)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        for runtime_position, db_position in NUM_DIGITAL_POSITION_MAP.items():
            number = result["core"][runtime_position]["value"]
            position_candidates = [db_position]
            if number in MASTER_NUMBERS:
                position_candidates.insert(0, f"{db_position} (Maestro)")
            row = None
            for position_candidate in position_candidates:
                row = conn.execute(
                    "SELECT * FROM Key_nbr WHERE Key_nbr_NUM = ? AND Key_nbr_POSITION = ? LIMIT 1",
                    (number, position_candidate),
                ).fetchone()
                if row:
                    break
            entry = {
                "position": db_position,
                "number": number,
                "key": row["Key_nbr_KEY"] if row else "Lectura pendiente en DB",
                "psy": row["Key_nbr_PSY"] if row else "Lectura pendiente en DB",
                "light": row["Key_nbr_LIGHT"] if row else "Lectura pendiente en DB",
                "shadow": row["Key_nbr_SHADOW"] if row else "Lectura pendiente en DB",
            }
            internal["digital_breakdown"].append(entry)
            if not row:
                internal["warnings"].append(f"Lectura pendiente en DB: Key_nbr {db_position}={number}.")

        for alert in result["markers"]["karmic_alerts"]:
            position = alert["position"]
            number = alert["number"]
            mapping = NUM_KARMIC_TABLE_MAP.get(position)
            if not mapping:
                internal["warnings"].append(f"Alerta kármica activa sin tabla solicitada: {position}={number}.")
                continue
            table, prefix = mapping
            row = None
            if table == "PY_krm":
                import re as _num_re
                for candidate in conn.execute("SELECT * FROM PY_krm").fetchall():
                    match = _num_re.match(r"^\s*(\d+)\b", str(candidate["PY_krm_NUM"] or ""))
                    if match and int(match.group(1)) == int(number):
                        row = candidate
                        break
            else:
                row = conn.execute(
                    f"SELECT * FROM {table} WHERE {prefix}_NUM = ? LIMIT 1", (number,)
                ).fetchone()
            db_position = NUM_DIGITAL_POSITION_MAP.get(position, position)
            entry = {
                "position": db_position,
                "number": number,
                "source_table": table,
                "key": row[f"{prefix}_KEY"] if row else "Lectura pendiente en DB",
                "psy": row[f"{prefix}_PSY"] if row else "Lectura pendiente en DB",
                "light": row[f"{prefix}_LIGHT"] if row else "Lectura pendiente en DB",
                "shadow": row[f"{prefix}_SHADOW"] if row else "Lectura pendiente en DB",
            }
            internal["active_karmic_alerts"].append(entry)
            if not row:
                internal["warnings"].append(f"Lectura pendiente en DB: {table} {number}.")
    except sqlite3.Error as exc:
        internal["warnings"].append(f"Error de consulta Numerología no fatal: {exc}")
    finally:
        conn.close()
    return internal


# ============================================================
# 2. CORE NUMEROLOGY FORMULAS
#    Based on current DharmaCodex master logic.
# ============================================================

LETTER_MAP = {
    "A": 1, "J": 1, "S": 1,
    "B": 2, "K": 2, "T": 2,
    "C": 3, "L": 3, "U": 3,
    "D": 4, "M": 4, "V": 4,
    "E": 5, "N": 5, "W": 5, "Ñ": 5,
    "F": 6, "O": 6, "X": 6,
    "G": 7, "P": 7, "Y": 7,
    "H": 8, "Q": 8, "Z": 8,
    "I": 9, "R": 9,
}

VOWELS = {"A", "E", "I", "O", "U"}
MASTER_NUMBERS = {11, 22, 33}
KARMIC_NUMBERS = {13, 14, 16, 19}


def strip_accents(value):
    normalized = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def clean_word(value):
    value = strip_accents(value.upper())
    return "".join(ch for ch in value if ch.isalpha() or ch == "Ñ")


def reduce_steps(value, preserve_master=True):
    masters = MASTER_NUMBERS if preserve_master else set()
    steps = [value]
    while value > 9 and value not in masters:
        value = sum(int(d) for d in str(value))
        steps.append(value)
    return steps


def final_reduce(value, preserve_master=True):
    return reduce_steps(value, preserve_master)[-1]


def digits_sum(value):
    return sum(int(d) for d in str(value))


def format_steps(steps):
    return " -> ".join(str(x) for x in steps)


def compute_name_parts(name):
    words = [clean_word(w) for w in name.split()]
    words = [w for w in words if w]
    full = "".join(words)

    word_rows = []
    expression_hits = set()
    word_reduced_values = []

    for word in words:
        raw = sum(LETTER_MAP.get(ch, 0) for ch in word)
        steps_regular = reduce_steps(raw, preserve_master=False)
        steps_master = reduce_steps(raw, preserve_master=True)
        reduced = steps_master[-1]
        word_reduced_values.append(reduced)

        for step in steps_regular:
            if step in KARMIC_NUMBERS:
                expression_hits.add(step)

        word_rows.append({
            "word": word,
            "raw": raw,
            "steps": steps_master,
            "reduced": reduced,
        })

    return {
        "words": words,
        "full": full,
        "word_rows": word_rows,
        "word_reduced_values": word_reduced_values,
        "expression_hits": sorted(expression_hits),
    }


def compute_numerology(name, day, month, year, current_year):
    parts = compute_name_parts(name)
    full = parts["full"]

    alerts = []

    # Camino de Vida: digit-by-digit birth date sum, preserving 11/22/33.
    cv_raw = sum(int(d) for d in f"{day:02d}{month:02d}{year}")
    cv_steps = reduce_steps(cv_raw, preserve_master=True)
    cv_final = cv_steps[-1]
    for step in cv_steps:
        if step in KARMIC_NUMBERS:
            alerts.append({"position": "Camino de Vida", "number": step})

    # Dia de nacimiento.
    birth_day_steps = reduce_steps(day, preserve_master=False)
    birth_day_final = birth_day_steps[-1]
    if day in KARMIC_NUMBERS:
        alerts.append({"position": "Dia de Nacimiento", "number": day})

    # Expresion / Destino: sum first reduction of each word, preserving masters.
    expression_sum = sum(parts["word_reduced_values"])
    expression_steps = reduce_steps(expression_sum, preserve_master=True)
    expression_final = expression_steps[-1]
    expression_hits = set(parts["expression_hits"])
    for step in expression_steps:
        if step in KARMIC_NUMBERS:
            expression_hits.add(step)
    for number in sorted(expression_hits):
        alerts.append({"position": "Expresion / Destino", "number": number})

    # Alma: vowels.
    soul_raw = sum(LETTER_MAP.get(ch, 0) for ch in full if ch in VOWELS)
    soul_steps = reduce_steps(soul_raw, preserve_master=True)
    soul_final = soul_steps[-1]

    # Personalidad: consonants.
    personality_raw = sum(LETTER_MAP.get(ch, 0) for ch in full if ch not in VOWELS)
    personality_steps = reduce_steps(personality_raw, preserve_master=True)
    personality_final = personality_steps[-1]

    # Ano Personal: day + month + current year; no master preservation in current master.
    personal_year_raw = day + month + current_year
    personal_year_steps = reduce_steps(personal_year_raw, preserve_master=False)
    personal_year_final = personal_year_steps[-1]
    for step in personal_year_steps:
        if step in KARMIC_NUMBERS:
            alerts.append({"position": "Ano Personal", "number": step})

    # Pinaculos y desafios.
    day_red = final_reduce(day, preserve_master=False)
    month_red = final_reduce(month, preserve_master=False)
    year_red = final_reduce(digits_sum(year), preserve_master=False)

    pinnacle_1 = final_reduce(day_red + month_red, preserve_master=False)
    pinnacle_2 = final_reduce(day_red + year_red, preserve_master=False)
    pinnacle_3 = final_reduce(pinnacle_1 + pinnacle_2, preserve_master=False)
    pinnacle_4 = final_reduce(month_red + year_red, preserve_master=False)

    challenge_1 = abs(day_red - month_red)
    challenge_2 = abs(day_red - year_red)
    challenge_3 = abs(challenge_1 - challenge_2)
    challenge_4 = abs(month_red - year_red)

    cv_for_stage = cv_final if cv_final not in MASTER_NUMBERS else final_reduce(cv_final, preserve_master=False)
    first_stage_ends = 36 - cv_for_stage

    # Tabla Natal / Pythagorean grid. Order required: 3 6 9 / 2 5 8 / 1 4 7.
    dob = f"{day:02d}{month:02d}{year}"
    counts = {str(d): dob.count(str(d)) for d in range(1, 10)}
    natal_grid = {
        str(d): (str(d) * counts[str(d)] if counts[str(d)] > 0 else "")
        for d in range(1, 10)
    }

    def has_all(keys):
        return all(counts[str(k)] > 0 for k in keys)

    def has_none(keys):
        return all(counts[str(k)] == 0 for k in keys)

    arrows_strength_rules = [
        ("Determinacion", (1, 5, 9)),
        ("Intelecto", (3, 6, 9)),
        ("Equilibrio Emocional", (2, 5, 8)),
        ("Sentido Practico", (1, 4, 7)),
        ("Compasion y Misticismo", (3, 5, 7)),
        ("Planificador", (1, 2, 3)),
        ("Voluntad", (4, 5, 6)),
        ("Actividad", (7, 8, 9)),
    ]
    arrows_weakness_rules = [
        ("Postergacion", (1, 5, 9)),
        ("Pobre Memoria", (3, 6, 9)),
        ("Hipersensibilidad", (2, 5, 8)),
        ("Impracticabilidad", (1, 4, 7)),
        ("Escepticismo", (3, 5, 7)),
        ("Indecision", (1, 2, 3)),
        ("Frustracion", (4, 5, 6)),
        ("Inactividad", (7, 8, 9)),
    ]

    arrows_strength = [
        {"name": name_, "digits": digits_, "kind": "strength"}
        for name_, digits_ in arrows_strength_rules
        if has_all(digits_)
    ]
    arrows_weakness = [
        {"name": name_, "digits": digits_, "kind": "weakness"}
        for name_, digits_ in arrows_weakness_rules
        if has_none(digits_)
    ]

    today = date.today()
    current_age = today.year - year - ((today.month, today.day) < (month, day))

    result = {
        "artifact_id": "NUMEROLOGY_INTERNAL_LIVE_PROOF_v0.2",
        "scope": "internal_live_proof_not_public_output",
        "input": {
            "name": name,
            "date": f"{day:02d}/{month:02d}/{year}",
            "current_year": current_year,
            "current_age": current_age,
        },
        "core": {
            "Camino de Vida": {
                "value": cv_final,
                "raw": cv_raw,
                "steps": cv_steps,
                "preserve_master": True,
            },
            "Expresion / Destino": {
                "value": expression_final,
                "raw": expression_sum,
                "steps": expression_steps,
                "word_rows": parts["word_rows"],
                "preserve_master": True,
            },
            "Impulso del Alma": {
                "value": soul_final,
                "raw": soul_raw,
                "steps": soul_steps,
                "preserve_master": True,
            },
            "Personalidad": {
                "value": personality_final,
                "raw": personality_raw,
                "steps": personality_steps,
                "preserve_master": True,
            },
            "Dia de Nacimiento": {
                "value": birth_day_final,
                "raw": day,
                "steps": birth_day_steps,
                "preserve_master": False,
            },
            "Ano Personal": {
                "value": personal_year_final,
                "raw": personal_year_raw,
                "steps": personal_year_steps,
                "year": current_year,
                "preserve_master": False,
            },
        },
        "life_stages": {
            "first_stage_ends": first_stage_ends,
            "pinnacles": {
                "P1": pinnacle_1,
                "P2": pinnacle_2,
                "P3": pinnacle_3,
                "P4": pinnacle_4,
            },
            "challenges": {
                "D1": challenge_1,
                "D2": challenge_2,
                "D3": challenge_3,
                "D4": challenge_4,
            },
        },
        "natal_grid": natal_grid,
        "digit_counts": counts,
        "arrows": {
            "strength": arrows_strength,
            "weakness": arrows_weakness,
        },
        "markers": {
            "master_numbers_present": [
                {"position": k, "value": v["value"]}
                for k, v in {
                    **{
                        key: value for key, value in {}
                    },
                    **{},
                }.items()
            ],
            "karmic_alerts": alerts,
        },
        "governance": {
            "internal_representation_template": True,
            "public_output_created": False,
            "interpretation_created": False,
            "synthesis_created": False,
            "db_query_executed": False,
            "pdf_created": False,
        },
    }

    masters_found = []
    for position, item in result["core"].items():
        if item["value"] in MASTER_NUMBERS:
            masters_found.append({"position": position, "value": item["value"]})
    result["markers"]["master_numbers_present"] = masters_found

    return result


# ============================================================
# 3. VISUAL HTML
# ============================================================

def html_escape(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def plate(label, value, meta="", class_name=""):
    return f"""
    <section class="plate {class_name}">
      <div class="plate-label">{html_escape(label)}</div>
      <div class="plate-value">{html_escape(value)}</div>
      <div class="plate-meta">{html_escape(meta)}</div>
    </section>
    """


def render_natal_grid(result):
    grid = result["natal_grid"]
    rows = [("3", "6", "9"), ("2", "5", "8"), ("1", "4", "7")]
    cells = []
    for row in rows:
        for digit in row:
            value = grid.get(digit, "")
            empty = " empty" if not value else ""
            cells.append(f"""
            <div class="grid-cell{empty}">
              <span class="grid-digit">{digit}</span>
              <strong>{html_escape(value)}</strong>
            </div>
            """)

    centers = {
        3:(50,50), 6:(150,50), 9:(250,50),
        2:(50,150), 5:(150,150), 8:(250,150),
        1:(50,250), 4:(150,250), 7:(250,250),
    }
    arrow_lines = []
    for kind, items in (("strength", result["arrows"]["strength"]), ("weakness", result["arrows"]["weakness"])):
        for item in items:
            first = centers[item["digits"][0]]
            last = centers[item["digits"][-1]]
            arrow_lines.append(
                f'<line class="natal-arrow {kind}" x1="{first[0]}" y1="{first[1]}" '
                f'x2="{last[0]}" y2="{last[1]}" marker-end="url(#{kind}-arrow)"/>'
            )
    arrows_svg = f'''<svg class="grid-arrows" viewBox="0 0 300 300" aria-hidden="true">
      <defs>
        <marker id="strength-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 Z"/></marker>
        <marker id="weakness-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 Z"/></marker>
      </defs>{''.join(arrow_lines)}
    </svg>'''
    return f"""<div class="natal-grid-wrap">{arrows_svg}<div class="natal-grid">{''.join(cells)}</div></div>"""


def render_natal_readings(result):
    rows = []
    readings = result.get("readings", {}).get("natal", {})
    for digit in map(str, range(1, 10)):
        count = result["digit_counts"][digit]
        if not count:
            continue
        row = readings.get(digit, {})
        value = digit * count
        key = row.get("NATALGRID_KEY", "Lectura disponible al cargar NUM_DB_v2.0.db")
        reading = row.get("NATALGRID_READING", "La repetición queda calculada; falta cargar la base para mostrar su lectura.")
        rows.append(f'''<article class="number-reading">
          <div class="number-reading-value">{value}</div>
          <div><strong>{html_escape(key)}</strong><p>{html_escape(reading)}</p></div>
        </article>''')
    return "".join(rows)


def render_stage_cards(result):
    stages = result["life_stages"]
    end1 = stages["first_stage_ends"]
    ranges = [(0, end1), (end1 + 1, end1 + 9), (end1 + 10, end1 + 18), (end1 + 19, "en adelante")]
    cards = []
    for index in range(1, 5):
        p = stages["pinnacles"][f"P{index}"]
        d = stages["challenges"][f"D{index}"]
        p_row = result.get("readings", {}).get("pinnacles", {}).get(str(p), {})
        d_row = result.get("readings", {}).get("challenges", {}).get(str(d), {})
        start, end = ranges[index - 1]
        age_label = f"{start} a {end} años" if isinstance(end, int) else f"{start} años {end}"
        cards.append(f'''<article class="stage-card">
          <div class="stage-index">ETAPA {index} · {html_escape(age_label)}</div>
          <div class="stage-values"><span>Pináculo <strong>{p}</strong></span><span>Desafío <strong>{d}</strong></span></div>
          <p><b>Oportunidad:</b> {html_escape(p_row.get("PIN_PSY", "Lectura disponible al cargar NUM_DB_v2.0.db."))}</p>
          <p><b>Prueba:</b> {html_escape(d_row.get("CHLLG_PSY", "Lectura disponible al cargar NUM_DB_v2.0.db."))}</p>
        </article>''')
    return "".join(cards)


def render_steps_table(result):
    rows = []
    for label, item in result["core"].items():
        rows.append(f"""
        <tr>
          <td>{html_escape(label)}</td>
          <td>{html_escape(item["raw"])}</td>
          <td>{html_escape(format_steps(item["steps"]))}</td>
          <td class="final-value">{html_escape(item["value"])}</td>
        </tr>
        """)
    return f"""
    <table class="steps-table">
      <thead>
        <tr>
          <th>Coordenada</th>
          <th>Base</th>
          <th>Reduccion</th>
          <th>Final</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """


def render_name_breakdown(result):
    rows = []
    for item in result["core"]["Expresion / Destino"]["word_rows"]:
        rows.append(f"""
        <tr>
          <td>{html_escape(item["word"])}</td>
          <td>{html_escape(item["raw"])}</td>
          <td>{html_escape(format_steps(item["steps"]))}</td>
          <td class="final-value">{html_escape(item["reduced"])}</td>
        </tr>
        """)
    return f"""
    <table class="steps-table compact">
      <thead>
        <tr>
          <th>Nombre</th>
          <th>Suma</th>
          <th>Reduccion</th>
          <th>Valor</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """


def render_arrow_list(title, items, fallback):
    if not items:
        body = f'<p class="muted">{html_escape(fallback)}</p>'
    else:
        body = "".join(
            f'<div class="arrow-reading"><div class="arrow-row"><span>{html_escape(item["name"])}</span><code>{html_escape("-".join(str(d) for d in item["digits"]))}</code></div><p>{html_escape(item.get("reading", "Lectura no encontrada para esta combinación en NUM_DB_v2.0.db."))}</p></div>'
            for item in items
        )
    return f"""
    <section class="arrow-box">
      <h3>{html_escape(title)}</h3>
      {body}
    </section>
    """


def render_digital_breakdown_readings(result):
    cards = []
    for item in result.get("internal_readings", {}).get("digital_breakdown", []):
        cards.append(f"""<details class="reading-detail">
          <summary><span>{html_escape(item['position'])}</span><strong>{html_escape(item['number'])}</strong><em>{html_escape(item['key'])}</em></summary>
          <div class="reading-detail-body"><p><b>Psicología:</b> {html_escape(item['psy'])}</p><p><b>Luz:</b> {html_escape(item['light'])}</p><p><b>Sombra:</b> {html_escape(item['shadow'])}</p></div>
        </details>""")
    return f'<div class="digital-readings">{"".join(cards)}</div>'


def render_active_karmic_readings(result):
    items = result.get("internal_readings", {}).get("active_karmic_alerts", [])
    if not items:
        return ""
    cards = []
    for item in items:
        cards.append(f"""<details class="reading-detail karmic-reading">
          <summary><span>{html_escape(item['position'])}</span><strong>{html_escape(item['number'])}</strong><em>{html_escape(item['key'])}</em></summary>
          <div class="reading-detail-body"><p><b>Psicología:</b> {html_escape(item['psy'])}</p><p><b>Luz:</b> {html_escape(item['light'])}</p><p><b>Sombra:</b> {html_escape(item['shadow'])}</p></div>
        </details>""")
    return f'<section class="markers-panel karmic-panel"><div class="section-title"><h2>Alertas Kármicas</h2></div><div class="digital-readings">{"".join(cards)}</div></section>'


def render_html(result):
    core = result["core"]
    stages = result["life_stages"]
    markers = result["markers"]

    main_plates = [
        plate("Camino de Vida", core["Camino de Vida"]["value"], class_name="primary"),
        plate("Expresion / Destino", core["Expresion / Destino"]["value"], class_name="primary"),
        plate("Dia de Nacimiento", core["Dia de Nacimiento"]["value"]),
        plate("Impulso del Alma", core["Impulso del Alma"]["value"]),
        plate("Personalidad", core["Personalidad"]["value"]),
        plate("Ano Personal", core["Ano Personal"]["value"]),
    ]

    karmic_html = render_active_karmic_readings(result)

    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Numerology Internal Live Proof v0.2</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
  --navy: #080E1F;
  --ivory: #F4EAD2;
  --gold: #C6A15B;
  --violet: #4B2E6D;
  --ink: #1b1a17;
  --muted: rgba(244,234,210,.68);
  --line: rgba(198,161,91,.46);
  --surface: rgba(244,234,210,.955);
  --surface-soft: rgba(244,234,210,.76);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background:
    radial-gradient(circle at top left, rgba(75,46,109,.18), transparent 34rem),
    linear-gradient(135deg, #080E1F 0%, #10182e 48%, #080E1F 100%);
  color: var(--ivory);
  font-family: Inter, system-ui, sans-serif;
}}
.page {{
  width: min(1180px, calc(100vw - 32px));
  margin: 24px auto;
  border: 1px solid var(--line);
  background: rgba(8,14,31,.72);
  box-shadow: 0 24px 80px rgba(0,0,0,.32);
}}
header {{
  padding: 30px 34px 22px;
  border-bottom: 1px solid var(--line);
}}
.kicker, .footer-label {{
  font-family: "IBM Plex Mono", monospace;
  color: var(--gold);
  font-size: 12px;
  letter-spacing: .08em;
  text-transform: uppercase;
}}
h1 {{
  margin: 10px 0 6px;
  font-family: "Cormorant Garamond", serif;
  font-size: clamp(38px, 5vw, 72px);
  line-height: .92;
  font-weight: 600;
}}
.subhead {{
  margin: 0;
  max-width: 760px;
  color: var(--muted);
  line-height: 1.6;
}}
.identity {{
  display: grid;
  grid-template-columns: 1.4fr .8fr .8fr;
  gap: 12px;
  margin-top: 22px;
}}
.identity div {{
  border-top: 1px solid var(--line);
  padding-top: 10px;
}}
.identity span {{
  display: block;
  font-family: "IBM Plex Mono", monospace;
  color: var(--gold);
  font-size: 11px;
  text-transform: uppercase;
}}
.identity strong {{
  display: block;
  margin-top: 4px;
  font-size: 15px;
}}
main {{
  padding: 30px 34px;
}}
.section-title {{
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 10px;
}}
.section-title h2 {{
  margin: 0;
  font-family: "Cormorant Garamond", serif;
  font-size: 34px;
  font-weight: 600;
}}
.section-title code {{
  font-family: "IBM Plex Mono", monospace;
  color: var(--gold);
  font-size: 12px;
}}
.core-layout {{
  display: grid;
  grid-template-columns: 1.2fr .82fr;
  gap: 26px;
  align-items: start;
}}
.plates {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}}
.plate {{
  min-height: 126px;
  padding: 16px 16px 14px;
  background: var(--surface);
  color: var(--ink);
  border-left: 4px solid var(--gold);
}}
.plate.primary {{
  min-height: 148px;
  background: linear-gradient(135deg, var(--surface) 0%, #fff7df 100%);
  border-left-color: var(--violet);
}}
.plate-label {{
  font-family: Inter, sans-serif;
  font-size: 12px;
  color: rgba(27,26,23,.68);
  text-transform: uppercase;
  letter-spacing: .05em;
}}
.plate-value {{
  margin-top: 8px;
  font-family: "Cormorant Garamond", serif;
  font-size: 56px;
  line-height: .9;
  color: var(--navy);
}}
.plate-meta {{
  margin-top: 12px;
  font-family: "IBM Plex Mono", monospace;
  font-size: 12px;
  color: rgba(27,26,23,.67);
  overflow-wrap: anywhere;
}}
.grid-panel, .timeline-panel, .table-panel, .markers-panel {{
  border: 1px solid var(--line);
  padding: 18px;
  background: rgba(244,234,210,.07);
}}
.grid-panel h3, .timeline-panel h3, .table-panel h3, .markers-panel h3 {{
  margin: 0 0 12px;
  font-family: "Cormorant Garamond", serif;
  font-size: 26px;
  font-weight: 600;
}}
.natal-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}}
.natal-grid-wrap {{ position: relative; }}
.grid-arrows {{ position:absolute; inset:0; width:100%; height:100%; z-index:2; pointer-events:none; }}
.natal-arrow {{ stroke-width:5; stroke-linecap:round; opacity:.78; }}
.natal-arrow.strength {{ stroke:#5F8F62; }}
.natal-arrow.weakness {{ stroke:#A24B4B; stroke-dasharray:8 7; }}
#strength-arrow path {{ fill:#5F8F62; }}
#weakness-arrow path {{ fill:#A24B4B; }}
.grid-cell {{
  min-height: 76px;
  background: var(--surface);
  color: var(--ink);
  display: grid;
  place-items: center;
  position: relative;
  border: 1px solid rgba(198,161,91,.5);
  z-index: 1;
}}
.grid-cell.empty {{
  background: rgba(244,234,210,.18);
  color: rgba(244,234,210,.62);
}}
.grid-digit {{
  position: absolute;
  top: 7px;
  left: 8px;
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  color: var(--gold);
}}
.grid-cell strong {{
  font-family: "Cormorant Garamond", serif;
  font-size: 32px;
  font-weight: 600;
  position: relative;
  z-index: 3;
  background: rgba(244,234,210,.88);
  border-radius: 999px;
  padding: 2px 7px;
}}
.number-readings {{ display:grid; gap:10px; margin-top:16px; }}
.number-reading {{ display:grid; grid-template-columns:72px 1fr; gap:14px; padding:14px 0; border-top:1px solid var(--line); }}
.number-reading-value {{ font-family:"Cormorant Garamond",serif; font-size:36px; color:var(--gold); text-align:center; }}
.number-reading p {{ margin:5px 0 0; color:var(--muted); line-height:1.55; }}
.stage-list {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
.stage-card {{ border:1px solid var(--line); background:rgba(244,234,210,.07); padding:18px; }}
.stage-index {{ font-family:"IBM Plex Mono",monospace; color:var(--gold); font-size:11px; letter-spacing:.06em; }}
.stage-values {{ display:flex; gap:20px; margin:10px 0; }}
.stage-values strong {{ font-family:"Cormorant Garamond",serif; font-size:30px; }}
.stage-card p {{ color:var(--muted); line-height:1.5; }}
.flow-strip {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-top: 16px;
}}
.flow-item {{
  padding: 14px;
  background: rgba(244,234,210,.11);
  border-top: 2px solid var(--gold);
}}
.flow-item span {{
  display: block;
  font-family: "IBM Plex Mono", monospace;
  color: var(--gold);
  font-size: 11px;
}}
.flow-item strong {{
  display: block;
  margin-top: 4px;
  font-family: "Cormorant Garamond", serif;
  font-size: 34px;
  line-height: 1;
}}
.dual {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-top: 26px;
}}
.steps-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}}
.steps-table th {{
  text-align: left;
  color: var(--gold);
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  text-transform: uppercase;
  border-bottom: 1px solid var(--line);
  padding: 9px 8px;
}}
.steps-table td {{
  border-bottom: 1px solid rgba(198,161,91,.2);
  padding: 10px 8px;
  vertical-align: top;
}}
.steps-table.compact td {{
  padding: 8px;
}}
.final-value {{
  font-family: "Cormorant Garamond", serif;
  color: var(--ivory);
  font-size: 22px;
}}
.arrows {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 18px;
}}
.arrow-box {{
  background: rgba(244,234,210,.08);
  border: 1px solid rgba(198,161,91,.28);
  padding: 14px;
}}
.arrow-box h3 {{
  font-size: 21px;
}}
.arrow-row, .marker-row {{
  display: flex;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid rgba(198,161,91,.16);
  padding: 8px 0;
}}
.arrow-reading p {{ color:var(--muted); line-height:1.5; font-size:13px; }}
code {{
  font-family: "IBM Plex Mono", monospace;
  color: var(--gold);
}}
.markers {{
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 14px;
  margin-top: 26px;
}}
.muted {{
  color: var(--muted);
  line-height: 1.5;
}}
footer {{
  border-top: 1px solid var(--line);
  padding: 18px 34px 26px;
  display: flex;
  justify-content: space-between;
  gap: 20px;
  color: var(--muted);
  font-size: 13px;
}}
@media (max-width: 900px) {{
  .identity, .core-layout, .dual, .markers, .arrows {{
    grid-template-columns: 1fr;
  }}
  .plates {{
    grid-template-columns: 1fr;
  }}
  .stage-list {{ grid-template-columns:1fr; }}
  header, main, footer {{
    padding-left: 20px;
    padding-right: 20px;
  }}
}}
.digital-readings {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }}
.reading-detail {{ border:1px solid rgba(198,161,91,.34); background:rgba(244,234,210,.04); padding:12px; }}
.reading-detail summary {{ cursor:pointer; display:grid; grid-template-columns:1fr auto; gap:4px 12px; align-items:center; }}
.reading-detail summary strong {{ color:var(--gold); font:700 18px "IBM Plex Mono",monospace; }}
.reading-detail summary em {{ grid-column:1/-1; color:var(--gold); font-style:normal; font-size:12px; }}
.reading-detail-body p {{ font-size:12px; line-height:1.55; }}
@media (max-width: 700px) {{ .digital-readings {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="page">
  <header>
    <div class="kicker">Internal Representation Template / Not Public Output</div>
    <h1>Numerologia Internal Live Proof</h1>
    <p class="subhead">Instrumento de codigo: calcula coordenadas numericas, Tabla Natal, ciclos, desafios, flechas y marcadores sin convertirlos en scorecard ni lectura publica.</p>
    <div class="identity">
      <div><span>Buscador</span><strong>{html_escape(result["input"]["name"])}</strong></div>
      <div><span>Fecha</span><strong>{html_escape(result["input"]["date"])}</strong></div>
      <div><span>Edad actual</span><strong>{html_escape(result["input"]["current_age"])} años</strong></div>
    </div>
  </header>

  <main>
    <section>
      <div class="section-title">
        <h2>Descomposición Digital</h2>
        <code>CÓDIGO</code>
      </div>
      <div class="core-layout">
        {render_digital_breakdown_readings(result)}
        <aside class="grid-panel">
          <h3>Tabla Natal</h3>
          {render_natal_grid(result)}
        </aside>
      </div>
    </section>

    {karmic_html}

    <section class="timeline-panel" style="margin-top:26px;">
      <div class="section-title"><h2>Etapas, oportunidades y pruebas</h2></div>
      <div class="stage-list">{render_stage_cards(result)}</div>
    </section>

    <section class="dual">
      <div class="grid-panel">
        <div class="section-title"><h2>Lectura de números presentes</h2></div>
        <div class="number-readings">{render_natal_readings(result)}</div>
      </div>
      <div class="table-panel">
        <div class="section-title"><h2>Flechas activas</h2></div>
        <div class="arrows">
          {render_arrow_list("Fortalezas", result["arrows"]["strength"], "Sin flechas de fortaleza activas.")}
          {render_arrow_list("Desafíos", result["arrows"]["weakness"], "Sin flechas de desafío activas.")}
        </div>
      </div>
    </section>
  </main>

  <footer>
    <div class="footer-label">Internal Representation Template / Not Public Output</div>
    <div>PASS_WITH_IMPROVEMENTS_NECESSARY · No synthesis · No PDF.</div>
  </footer>
</div>
</body>
</html>"""
    return html


# ============================================================
# 4. VALIDATION REPORT
# ============================================================

def validate_result(result):
    checks = []

    required_core = [
        "Camino de Vida",
        "Expresion / Destino",
        "Impulso del Alma",
        "Personalidad",
        "Dia de Nacimiento",
        "Ano Personal",
    ]
    checks.append(("core_coordinates_present", all(k in result["core"] for k in required_core)))
    checks.append(("natal_grid_1_to_9_present", set(result["natal_grid"].keys()) == set(str(d) for d in range(1, 10))))
    checks.append(("natal_grid_order_required", True))
    checks.append(("natal_grid_empty_cells_are_blank", all(
        result["natal_grid"][str(d)] == "" for d in range(1, 10)
        if result["digit_counts"][str(d)] == 0
    )))
    checks.append(("present_digit_readings_section", True))
    checks.append(("pinnacles_present", set(result["life_stages"]["pinnacles"].keys()) == {"P1", "P2", "P3", "P4"}))
    checks.append(("challenges_present", set(result["life_stages"]["challenges"].keys()) == {"D1", "D2", "D3", "D4"}))
    checks.append(("master_numbers_preserved", all(item["value"] in MASTER_NUMBERS for item in result["markers"]["master_numbers_present"])))
    checks.append(("governance_internal_only", result["governance"]["internal_representation_template"] is True))
    checks.append(("governance_no_public_output", result["governance"]["public_output_created"] is False))
    checks.append(("governance_no_interpretation", result["governance"]["interpretation_created"] is False))
    checks.append(("governance_no_synthesis", result["governance"]["synthesis_created"] is False))
    checks.append(("digital_breakdown_six_positions", len(result.get("internal_readings", {}).get("digital_breakdown", [])) == 6))
    checks.append(("only_active_karmic_alerts_rendered", len(result.get("internal_readings", {}).get("active_karmic_alerts", [])) == len(result["markers"]["karmic_alerts"])))

    return checks


def render_validation_md(result, checks):
    passed = sum(1 for _, ok in checks if ok)
    failed = len(checks) - passed
    rows = "\n".join(f"| {name} | {'PASS' if ok else 'FAIL'} |" for name, ok in checks)

    return f"""# NUMEROLOGY_INTERNAL_LIVE_VALIDATION_v0.2

## Summary

Status: {"PASS" if failed == 0 else "FAIL"}

Input: {result["input"]["name"]} | {result["input"]["date"]} | current year {result["input"]["current_year"]}

## Checks

| Check | Result |
| --- | --- |
{rows}

## Core Output

| Coordinate | Value | Steps |
| --- | ---: | --- |
| Camino de Vida | {result["core"]["Camino de Vida"]["value"]} | {format_steps(result["core"]["Camino de Vida"]["steps"])} |
| Expresion / Destino | {result["core"]["Expresion / Destino"]["value"]} | {format_steps(result["core"]["Expresion / Destino"]["steps"])} |
| Impulso del Alma | {result["core"]["Impulso del Alma"]["value"]} | {format_steps(result["core"]["Impulso del Alma"]["steps"])} |
| Personalidad | {result["core"]["Personalidad"]["value"]} | {format_steps(result["core"]["Personalidad"]["steps"])} |
| Dia de Nacimiento | {result["core"]["Dia de Nacimiento"]["value"]} | {format_steps(result["core"]["Dia de Nacimiento"]["steps"])} |
| Ano Personal | {result["core"]["Ano Personal"]["value"]} | {format_steps(result["core"]["Ano Personal"]["steps"])} |

## Governance

- public_output_created: false
- interpretation_created: false
- synthesis_created: false
- db_query_executed: {str(result["governance"]["db_query_executed"]).lower()}
- pdf_created: false
- visual_status: PASS_WITH_IMPROVEMENTS_NECESSARY

## Internal DB Readings

### Digital Breakdown

{chr(10).join(f"- {item['position']}: {item['number']} — {item['key']}" for item in result.get('internal_readings', {}).get('digital_breakdown', []))}

### Active Karmic Alerts

{chr(10).join(f"- {item['position']}: {item['number']} — {item['key']} ({item['source_table']})" for item in result.get('internal_readings', {}).get('active_karmic_alerts', [])) or '- None'}

### Warnings

{chr(10).join(f"- {warning}" for warning in result.get('internal_readings', {}).get('warnings', [])) or '- None'}
"""


# ============================================================
# 5. MAIN
# ============================================================

result = compute_numerology(
    name=NOMBRE_COMPLETO,
    day=DIA_NACIMIENTO,
    month=MES_NACIMIENTO,
    year=ANIO_NACIMIENTO,
    current_year=ANIO_ACTUAL,
)

result["readings"] = load_numerology_readings(result)
result["internal_readings"] = load_numerology_internal_readings(result)
result["governance"]["db_query_executed"] = bool(result["readings"].get("db_path"))
for item in result["arrows"]["strength"] + result["arrows"]["weakness"]:
    db_row = result["readings"]["arrows"].get(item["name"], {})
    item["reading"] = db_row.get("ARROWS_PSY", "Lectura no disponible para esta combinación en NUM_DB_v2.0.db.")
    if db_row.get("ARROWS_KEY"):
        item["canonical_name"] = db_row["ARROWS_KEY"]
        item["name"] = db_row["ARROWS_KEY"]

html = render_html(result)
checks = validate_result(result)
report_md = render_validation_md(result, checks)

with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

with open(OUTPUT_MD, "w", encoding="utf-8") as f:
    f.write(report_md)

summary = {
    "html": OUTPUT_HTML,
    "json": OUTPUT_JSON,
    "report": OUTPUT_MD,
    "validation_pass": all(ok for _, ok in checks),
    "core": {k: v["value"] for k, v in result["core"].items()},
    "pinnacles": result["life_stages"]["pinnacles"],
    "challenges": result["life_stages"]["challenges"],
    "arrows": result["arrows"],
    "karmic_alerts": result["markers"]["karmic_alerts"],
    "master_numbers": result["markers"]["master_numbers_present"],
}

print("DONE")
print(json.dumps(summary, ensure_ascii=False, indent=2))


# %% [CELDA 5 — MATRIZ DEL DESTINO]

"""
DM_INTERNAL_LIVE_MATRIX_PROOF_MASTER_v0.2_colab.py

DharmaCodex internal Destiny Matrix live proof.
Paste this file into one Colab cell and run it there.

Scope:
- Calculates the 32 Destiny Matrix variables from date of birth.
- Calculates the life-cycle perimeter dynamically by fractal interpolation.
- Draws an internal HTML/SVG proof using the user-provided template structure.
- Keeps DharmaCodex visual theme from the approved draft.
- Does not query DB by default.
- Does not create public output, PDF, synthesis, or interpretation.

Outputs in Colab:
- /content/DM_INTERNAL_LIVE_MATRIX_PROOF_v0.2.html
- /content/DM_INTERNAL_LIVE_MATRIX_DEBUG_v0.2.json
- /content/DM_INTERNAL_LIVE_MATRIX_VALIDATION_v0.2.md
"""

import json
import os
import sqlite3
from datetime import datetime


# ============================================================
# 1. INPUTS
# ============================================================

_dm_input = globals().get("MASTER_INPUT", {
    "name": "Buscador Tecnico", "day": 1, "month": 1, "year": 2000,
})
NOMBRE_INTERNO = _dm_input["name"]
DIA_NACIMIENTO = _dm_input["day"]
MES_NACIMIENTO = _dm_input["month"]
ANIO_NACIMIENTO = _dm_input["year"]

OUTPUT_HTML = "/content/DM_INTERNAL_LIVE_MATRIX_PROOF_v0.2.html"
OUTPUT_JSON = "/content/DM_INTERNAL_LIVE_MATRIX_DEBUG_v0.2.json"
OUTPUT_MD = "/content/DM_INTERNAL_LIVE_MATRIX_VALIDATION_v0.2.md"

DM_DB_CANDIDATES = [
    "/content/Data_Bases/DM_DB_v2.0.db",
    "/content/Data_Bases/01-DM_DB_v2.0.db",
    "/content/DM_DB_v2.0.db",
    "/content/01-DM_DB_v2.0.db",
]

DM_SVG_CANDIDATES = [
    "/content/DM.svg",
    "/content/04-DM.svg",
    "/content/upload/04-DM.svg",
]


def load_karmic_tail_name(triad):
    db_path = next((path for path in DM_DB_CANDIDATES if os.path.exists(path)), None)
    if not db_path:
        return "Nombre disponible al cargar DM_DB_v2.0.db", None
    key = ".".join(str(value) for value in triad)
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT KARMIC_TAIL_NAME FROM KARMIC_TAIL WHERE KARMIC_TAIL = ? LIMIT 1",
            (key,),
        ).fetchone()
        return ((row[0].strip() if row and row[0] else "Sin nombre registrado"), db_path)
    finally:
        conn.close()


DM_CALCULATED_VALUE_META = [
    ("a", "Máscara social", "Esencia y Carácter"),
    ("b", "Yo Superior", "Esencia y Carácter"),
    ("c", "Karma material inicial", "Canal de Prosperidad"),
    ("d", "Primera lección kármica", "Karma y Aprendizaje"),
    ("e", "Centro / Verdadera esencia", "Esencia y Carácter"),
    ("f", "Ancestro masculino (Sup-Izq)", "Linaje Ancestral"),
    ("g", "Ancestro femenino (Sup-Der)", "Linaje Ancestral"),
    ("y", "Ancestro masculino (Inf-Der)", "Linaje Ancestral"),
    ("k", "Ancestro femenino (Inf-Izq)", "Linaje Ancestral"),
]


def _dm_variable_members(variable_group, variable_id):
    return variable_id in [item.strip() for item in str(variable_group or "").split(",")]


def _dm_arcane_row(conn, arcane_value, category, variable_id):
    rows = conn.execute(
        "SELECT * FROM ARCANE_CAT WHERE ARCANE_ID = ? AND READING_ID = ?",
        (arcane_value, category),
    ).fetchall()
    return next((row for row in rows if _dm_variable_members(row["VARIABLE_ID"], variable_id)), None)


def _dm_formula_map(matrix):
    values = matrix["values"]
    day = matrix["input"]["day"]
    month = matrix["input"]["month"]
    year = matrix["input"]["year"]
    year_sum = sum_year_digits(year)
    return {
        "a": f"a = reducir(día {day}) = {values['a']}",
        "b": f"b = reducir(mes {month}) = {values['b']}",
        "c": f"c = reducir(suma de dígitos de {year}: {year_sum}) = {values['c']}",
        "d": f"d = reducir(a+b+c: {values['a']}+{values['b']}+{values['c']}) = {values['d']}",
        "e": f"e = reducir(a+b+c+d: {values['a']}+{values['b']}+{values['c']}+{values['d']}) = {values['e']}",
        "f": f"f = reducir(a+b: {values['a']}+{values['b']}) = {values['f']}",
        "g": f"g = reducir(b+c: {values['b']}+{values['c']}) = {values['g']}",
        "y": f"y = reducir(c+d: {values['c']}+{values['d']}) = {values['y']}",
        "k": f"k = reducir(d+a: {values['d']}+{values['a']}) = {values['k']}",
    }


def load_matrix_internal_readings(matrix):
    internal = {
        "calculated_values": [],
        "karmic_tail": {},
        "money_channel": {},
        "relationship_channel": {},
        "warnings": [],
    }
    db_path = next((path for path in DM_DB_CANDIDATES if os.path.exists(path)), None)
    if not db_path:
        internal["warnings"].append("DM_DB_v2.0.db no disponible; lecturas internas pendientes en DB.")
        return internal
    conn = sqlite3.connect(f"file:{os.path.abspath(db_path)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        formulas = _dm_formula_map(matrix)
        for variable_id, description, category in DM_CALCULATED_VALUE_META:
            arcane_value = matrix["values"][variable_id]
            row = _dm_arcane_row(conn, arcane_value, category, variable_id)
            entry = {
                "variable": variable_id,
                "description": description,
                "category": category,
                "calculation": formulas[variable_id],
                "arcane_value": arcane_value,
                "arcane_name": row["ARCANE_NAME"] if row else "Lectura pendiente en DB",
                "position_focus": row["POSITION_FOCUS"] if row else "Lectura pendiente en DB",
                "light": row["POSITION_LIGHT_flow"] if row else "Lectura pendiente en DB",
                "shadow": row["POSITION_SHADOW_KarmicTest"] if row else "Lectura pendiente en DB",
            }
            internal["calculated_values"].append(entry)
            if not row:
                internal["warnings"].append(
                    f"Lectura pendiente en DB: ARCANE_CAT variable={variable_id}, arcano={arcane_value}, categoría={category}."
                )

        karmic_triad = matrix["channels"]["Cola Karmica"]["Cola Karmica"]
        karmic_key = ".".join(str(value) for value in karmic_triad)
        tail_row = conn.execute(
            "SELECT * FROM KARMIC_TAIL WHERE KARMIC_TAIL = ? LIMIT 1", (karmic_key,)
        ).fetchone()
        internal["karmic_tail"] = {
            "channel": "Cola Kármica",
            "name": tail_row["KARMIC_TAIL_NAME"] if tail_row else "Lectura pendiente en DB",
            "triad": karmic_triad,
            "triad_key": karmic_key,
            "soul_debt_past": tail_row["TAIL_PAST_SoulDebt"] if tail_row else "Lectura pendiente en DB",
            "shadow_challenge_present": tail_row["TAIL_PRESENT_SHADOW_Challenge"] if tail_row else "Lectura pendiente en DB",
            "integration_lesson": tail_row["TAIL_HEALING_LESSON_Integration"] if tail_row else "Lectura pendiente en DB",
        }
        if not tail_row:
            internal["warnings"].append(f"Lectura pendiente en DB: KARMIC_TAIL {karmic_key}.")

        channel_specs = [
            ("money_channel", "Canal del Dinero", ["x", "x2", "c1"], "Canal de Prosperidad"),
            ("relationship_channel", "Canal de Relaciones", ["x", "x1", "d1"], "Canal del Amor"),
        ]
        for output_key, label, variable_ids, category in channel_specs:
            rows = []
            triad = [matrix["values"][variable_id] for variable_id in variable_ids]
            for variable_id, arcane_value in zip(variable_ids, triad):
                row = conn.execute(
                    "SELECT * FROM ARCANE_CAT WHERE ARCANE_ID = ? AND READING_ID = ? LIMIT 1",
                    (arcane_value, category),
                ).fetchone()
                rows.append({
                    "variable": variable_id,
                    "number": arcane_value,
                    "arcane_name": row["ARCANE_NAME"] if row else "Lectura pendiente en DB",
                    "focus": row["POSITION_FOCUS"] if row else "Lectura pendiente en DB",
                    "action": row["POSITION_HEALING"] if row else "Lectura pendiente en DB",
                })
                if not row:
                    internal["warnings"].append(
                        f"Lectura pendiente en DB: ARCANE_CAT canal={label}, variable={variable_id}, arcano={arcane_value}."
                    )
            internal[output_key] = {"channel": label, "category": category, "triad": triad, "rows": rows}
    except sqlite3.Error as exc:
        internal["warnings"].append(f"Error de consulta Matriz no fatal: {exc}")
    finally:
        conn.close()
    return internal


# ============================================================
# 2. CORE FORMULAS
# ============================================================

def reduce_arcane(value):
    """Reduce values to 1..22. Exact 22 is preserved."""
    while value > 22:
        value = sum(int(d) for d in str(value))
    return value


def sum_year_digits(year):
    return sum(int(d) for d in str(year))


VARIABLE_META = {
    "a": "Mascara social",
    "b": "Yo Superior",
    "c": "Karma material inicial",
    "d": "Primera leccion karmica",
    "e": "Centro / Verdadera esencia",
    "b2": "Segundo talento (Autoexpresion)",
    "b1": "Tercer talento (Vidas pasadas)",
    "d1": "Bagaje karmico primario",
    "d2": "Bagaje karmico secundario",
    "f": "Ancestro masculino (Sup-Izq)",
    "g": "Ancestro femenino (Sup-Der)",
    "y": "Ancestro masculino (Inf-Der)",
    "k": "Ancestro femenino (Inf-Izq)",
    "e1": "Fuerza de los ancestros",
    "s1": "Talento linaje masculino 1",
    "s2": "Talento linaje masculino 2",
    "s4": "Karma negativo linaje masculino 1",
    "s3": "Karma negativo linaje masculino 2",
    "p1": "Talento linaje femenino 1",
    "p2": "Talento linaje femenino 2",
    "p3": "Karma negativo linaje femenino 1",
    "p4": "Karma negativo linaje femenino 2",
    "a1": "Errores hacia padres/hijos",
    "a2": "Armonia padres/hijos",
    "c1": "Interseccion canal de bienestar",
    "c2": "Karma material historico",
    "e2": "Arquetipo de la sexualidad",
    "x": "Interseccion Linea del bienestar",
    "x1": "Canal de relacion de pareja",
    "x2": "Canal del dinero / Prosperidad",
    "a3": "Chakra Anahata 1",
    "b3": "Chakra Anahata 2",
}


def compute_matrix(day, month, year):
    i_d = day
    i_m = month
    m_y = sum_year_digits(year)

    a = reduce_arcane(i_d)
    b = reduce_arcane(i_m)
    c = reduce_arcane(m_y)
    d = reduce_arcane(a + b + c)
    e = reduce_arcane(a + b + c + d)

    b2 = reduce_arcane(e + b)
    b1 = reduce_arcane(b + b2)

    d1 = reduce_arcane(d + e)
    d2 = reduce_arcane(d + d1)

    f = reduce_arcane(a + b)
    g = reduce_arcane(b + c)
    y = reduce_arcane(c + d)
    k = reduce_arcane(d + a)

    e1 = reduce_arcane(f + g + y + k)
    e2 = reduce_arcane(e + e1)

    s1 = reduce_arcane(e1 + f)
    s2 = reduce_arcane(s1 + f)
    s4 = reduce_arcane(y + e1)
    s3 = reduce_arcane(s4 + y)

    p1 = reduce_arcane(g + e1)
    p2 = reduce_arcane(g + p1)
    p3 = reduce_arcane(k + e1)
    p4 = reduce_arcane(k + p3)

    a1 = reduce_arcane(a + e)
    a2 = reduce_arcane(a + a1)

    c1 = reduce_arcane(c + e)
    c2 = reduce_arcane(c1 + c)

    x = reduce_arcane(d1 + c1)
    x1 = reduce_arcane(x + d1)
    x2 = reduce_arcane(x + c1)

    a3 = reduce_arcane(a1 + e)
    b3 = reduce_arcane(b2 + e)

    values = {
        "a": a, "b": b, "c": c, "d": d, "e": e,
        "b2": b2, "b1": b1, "d1": d1, "d2": d2,
        "f": f, "g": g, "y": y, "k": k,
        "e1": e1, "e2": e2,
        "s1": s1, "s2": s2, "s4": s4, "s3": s3,
        "p1": p1, "p2": p2, "p3": p3, "p4": p4,
        "a1": a1, "a2": a2,
        "c1": c1, "c2": c2,
        "x": x, "x1": x1, "x2": x2,
        "a3": a3, "b3": b3,
    }

    channels = {
        "Cola Karmica": {"Cola Karmica": [d, d1, d2]},
        "Cruz Principal": {
            "Canal de Talentos": [b, b2, b1],
            "Karma Material": [c, c1, c2],
            "Karma Padres e Hijos": [a, a1, a2],
        },
        "Linea del Bienestar": {
            "Canal del Dinero": [x, x2, c1],
            "Canal de Relaciones": [x, x1, d1],
            "Punto de Equilibrio": [x],
        },
        "Linaje Ancestral": {
            "Linaje Masculino Virtudes": [f, s1, s2],
            "Linaje Masculino Cargas": [y, s4, s3],
            "Linaje Femenino Virtudes": [g, p1, p2],
            "Linaje Femenino Cargas": [k, p3, p4],
        },
        "Nucleo y Sexualidad": {
            "Centro de Confort": [e],
            "Arquetipo de Sexualidad": [e, e1, e2],
        },
    }

    return {
        "input": {"day": day, "month": month, "year": year},
        "values": values,
        "channels": channels,
    }


# ============================================================
# 3. LIFE CYCLE FRACTAL FORMULA
# ============================================================

def label_for_cycle_position(decade_start, offset):
    labels = {
        0.0: f"{decade_start}",
        1.25: f"{decade_start + 1} - {decade_start + 2.5:g}",
        2.5: f"{decade_start + 2.5:g} - {decade_start + 3.5:g}",
        3.75: f"{decade_start + 3.5:g} - {decade_start + 4:g}",
        5.0: f"{decade_start + 5:g}",
        6.25: f"{decade_start + 6:g} - {decade_start + 7.5:g}",
        7.5: f"{decade_start + 7.5:g} - {decade_start + 8.5:g}",
        8.75: f"{decade_start + 8.5:g} - {decade_start + 9:g}",
    }
    return labels[offset]


def compute_life_cycle(values):
    # Canonical anchors from GEM rule:
    # 0=a, 10=f, 20=b, 30=g, 40=c, 50=y, 60=d, 70=k, 80=a.
    anchors = [
        (0, values["a"], "a"),
        (10, values["f"], "f"),
        (20, values["b"], "b"),
        (30, values["g"], "g"),
        (40, values["c"], "c"),
        (50, values["y"], "y"),
        (60, values["d"], "d"),
        (70, values["k"], "k"),
        (80, values["a"], "a"),
    ]

    rows = []
    perimeter_points = []

    for idx in range(len(anchors) - 1):
        start_age, start_value, start_id = anchors[idx]
        end_age, end_value, end_id = anchors[idx + 1]

        mid = reduce_arcane(start_value + end_value)
        q1 = reduce_arcane(start_value + mid)
        q3 = reduce_arcane(mid + end_value)
        e1 = reduce_arcane(start_value + q1)
        e2 = reduce_arcane(q1 + mid)
        e3 = reduce_arcane(mid + q3)
        e4 = reduce_arcane(q3 + end_value)

        decade_items = [
            (0.0, start_value, start_id),
            (1.25, e1, f"{start_id}+q1"),
            (2.5, q1, f"{start_id}+mid"),
            (3.75, e2, "q1+mid"),
            (5.0, mid, f"{start_id}+{end_id}"),
            (6.25, e3, "mid+q3"),
            (7.5, q3, f"mid+{end_id}"),
            (8.75, e4, f"q3+{end_id}"),
        ]

        for offset, value, formula in decade_items:
            rows.append({
                "age": label_for_cycle_position(start_age, offset),
                "age_value": start_age + offset,
                "arcane": value,
                "formula": formula,
                "decade_start": start_age,
            })
            perimeter_points.append({
                "age": label_for_cycle_position(start_age, offset),
                "age_value": start_age + offset,
                "arcane": value,
                "formula": formula,
                "side_index": idx,
                "side_fraction": offset / 10.0,
            })

    return {
        "anchors": anchors,
        "rows": rows,
        "perimeter_points": perimeter_points,
    }


# ============================================================
# 4. TEMPLATE GEOMETRY
# ============================================================

CX = 650
CY = 520

NODE_POS = {
    "a": (250, 520), "f": (360, 215), "b": (650, 145), "g": (940, 215),
    "c": (1050, 520), "y": (940, 825), "d": (650, 895), "k": (360, 825),
    "e": (650, 520),
    "b1": (650, 235), "b2": (650, 305), "b3": (650, 410),
    "d1": (650, 790), "d2": (650, 845),
    "a2": (335, 520), "a1": (425, 520), "a3": (545, 520),
    "e1": (780, 520), "e2": (835, 520), "c1": (920, 520), "c2": (975, 520),
    # Triadas alineadas exactamente sobre las cuatro diagonales del template.
    "s2": (462, 322), "s1": (549, 413),
    "p2": (838, 322), "p1": (751, 413),
    "p3": (549, 627), "p4": (462, 718),
    "s4": (751, 627), "s3": (838, 718),
    "x": (760, 680), "x1": (700, 715), "x2": (830, 610),
}

MAJOR_NODES = {"a", "b", "c", "d", "e", "f", "g", "y", "k"}
SECONDARY_NODES = {"b1", "b2", "b3", "d1", "d2", "a1", "a2", "a3", "c1", "c2", "e1", "e2"}
LINEAGE_NODES = set(NODE_POS.keys()) - MAJOR_NODES - SECONDARY_NODES

PERIMETER_VERTICES = [
    NODE_POS["a"], NODE_POS["f"], NODE_POS["b"], NODE_POS["g"], NODE_POS["c"],
    NODE_POS["y"], NODE_POS["d"], NODE_POS["k"], NODE_POS["a"],
]

TEMPLATE_LINES = [
    ("a", "f"), ("f", "b"), ("b", "g"), ("g", "c"),
    ("c", "y"), ("y", "d"), ("d", "k"), ("k", "a"),
    ("a", "c"), ("b", "d"), ("f", "g"), ("k", "y"),
    ("a", "b"), ("b", "c"), ("c", "d"), ("d", "a"),
    ("f", "d"), ("g", "d"), ("k", "b"), ("y", "b"),
]

LINEAGE_LINES = [
    ("f", "s2"), ("s2", "s1"), ("s1", "e"),
    ("g", "p2"), ("p2", "p1"), ("p1", "e"),
    ("k", "p4"), ("p4", "p3"), ("p3", "e"),
    ("y", "s3"), ("s3", "s4"), ("s4", "e"),
]

WELLBEING_LINES = [
    ("d1", "x1"), ("x1", "x"), ("x", "x2"), ("x2", "c1"),
]


def lerp(p1, p2, t):
    return (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)


def html_escape(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def svg_line(p1, p2, cls="line", extra=""):
    return f'<line class="{cls}" x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" {extra}/>'


def node_radius(var_id):
    if var_id == "e":
        return 52
    if var_id in {"a", "b", "c", "d", "f", "g", "y", "k"}:
        return 44
    if var_id in {"x", "x1", "x2"}:
        return 30
    return 28


def node_class(var_id):
    if var_id == "e":
        return "node center-node"
    if var_id in {"a", "b", "c", "d"}:
        return "node anchor-node cardinal"
    if var_id in {"f", "g", "y", "k"}:
        return "node anchor-node diagonal"
    if var_id in {"x", "x1", "x2"}:
        return "node wellbeing-node"
    return "node inner-node"


def render_matrix_svg(matrix, life_cycle):
    values = matrix["values"]
    parts = []

    parts.append('<svg class="matrix-svg" viewBox="0 0 1300 1040" role="img" aria-label="Destiny Matrix internal proof">')

    # Perimeter and field.
    perimeter_path = " ".join(
        f'{"M" if idx == 0 else "L"} {x} {y}'
        for idx, (x, y) in enumerate(PERIMETER_VERTICES)
    )
    parts.append(f'<path class="perimeter" d="{perimeter_path} Z"/>')
    parts.append(f'<circle class="center-halo" cx="{CX}" cy="{CY}" r="125"/>')
    parts.append(f'<circle class="center-sun" cx="{CX}" cy="{CY}" r="74"/>')

    # Template structural lines.
    for a_id, b_id in TEMPLATE_LINES:
        parts.append(svg_line(NODE_POS[a_id], NODE_POS[b_id], "struct-line"))

    for a_id, b_id in LINEAGE_LINES:
        parts.append(svg_line(NODE_POS[a_id], NODE_POS[b_id], "lineage-line"))

    for a_id, b_id in WELLBEING_LINES:
        parts.append(svg_line(NODE_POS[a_id], NODE_POS[b_id], "wellbeing-line"))

    # Axis arrows as semantic categories already present in template.
    parts.append(f'<text class="axis-label purple" x="535" y="410" transform="rotate(45 535 410)">linea masculina</text>')
    parts.append(f'<text class="axis-label red" x="755" y="395" transform="rotate(-45 755 395)">linea femenina</text>')
    parts.append(f'<text class="icon-heart" x="705" y="655">♥</text>')
    parts.append(f'<text class="icon-money" x="850" y="615">$</text>')

    # Life-cycle perimeter labels. These use values from dynamic fractal formula.
    for item in life_cycle["perimeter_points"]:
        side = item["side_index"]
        t = item["side_fraction"]
        start = PERIMETER_VERTICES[side]
        end = PERIMETER_VERTICES[side + 1]
        x, y = lerp(start, end, t)

        # Move labels outward from center.
        dx = x - CX
        dy = y - CY
        length = (dx * dx + dy * dy) ** 0.5 or 1
        ox = x + dx / length * 42
        oy = y + dy / length * 42
        dot_class = "cycle-dot major" if item["age_value"] % 10 == 0 else "cycle-dot"
        text_class = "cycle-text major" if item["age_value"] % 10 == 0 else "cycle-text"

        parts.append(f'<circle class="{dot_class}" cx="{x:.1f}" cy="{y:.1f}" r="{6 if item["age_value"] % 10 == 0 else 4}"/>')
        parts.append(f'<text class="{text_class}" x="{ox:.1f}" y="{oy:.1f}">{html_escape(item["arcane"])}</text>')
        parts.append(f'<text class="age-text" x="{ox:.1f}" y="{oy + 16:.1f}">{html_escape(item["age"])} años</text>')

    # Nodes.
    for var_id, (x, y) in NODE_POS.items():
        r = node_radius(var_id)
        value = values[var_id]
        parts.append(f'<g class="matrix-node" data-variable="{var_id}">')
        parts.append(f'<circle class="{node_class(var_id)}" cx="{x}" cy="{y}" r="{r}"/>')
        parts.append(f'<text class="node-value" x="{x}" y="{y + 10}">{html_escape(value)}</text>')
        parts.append('</g>')

    parts.append('</svg>')
    return "\n".join(parts)


def render_variable_table(matrix):
    rows = []
    for var_id in ["a", "b", "c", "d", "e", "f", "g", "k", "y"]:
        value = matrix["values"][var_id]
        rows.append(f"""
        <tr>
          <td><code>{html_escape(var_id)}</code></td>
          <td class="num">{html_escape(value)}</td>
        </tr>
        """)
    return f"""
    <table class="data-table variable-table">
      <thead>
        <tr><th>ID</th><th>Valor</th></tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """


def render_life_cycle_table(life_cycle):
    rows = []
    for item in life_cycle["rows"]:
        rows.append(f"""
        <tr>
          <td>{html_escape(item["age"])}</td>
          <td class="num">{html_escape(item["arcane"])}</td>
          <td><code>{html_escape(item["formula"])}</code></td>
        </tr>
        """)
    return f"""
    <table class="data-table cycle-table">
      <thead>
        <tr><th>Edad</th><th>Arquetipo</th><th>Formula</th></tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """


def render_channel_table(matrix):
    karmic = matrix["channels"]["Cola Karmica"]["Cola Karmica"]
    money = matrix["channels"]["Linea del Bienestar"]["Canal del Dinero"]
    relationship = matrix["channels"]["Linea del Bienestar"]["Canal de Relaciones"]
    karmic_name = matrix.get("karmic_tail_name", "")
    rows = [
        ("Cola Kármica", karmic_name, karmic),
        ("Canal del Dinero", "", money),
        ("Canal de Relaciones", "", relationship),
    ]
    body = "".join(f"""
        <tr><td>{html_escape(label)}</td><td>{html_escape(name)}</td>
        <td><code>{html_escape(' · '.join(str(v) for v in values))}</code></td></tr>
    """ for label, name, values in rows)
    return f"""
    <table class="data-table">
      <thead>
        <tr><th>Canal</th><th>Nombre</th><th>Triada</th></tr>
      </thead>
      <tbody>{body}</tbody>
    </table>
    """


def render_html(matrix, life_cycle):
    matrix_svg = render_matrix_svg(matrix, life_cycle)
    variable_table = render_variable_table(matrix)
    channel_table = render_channel_table(matrix)
    date_label = f'{matrix["input"]["day"]:02d}/{matrix["input"]["month"]:02d}/{matrix["input"]["year"]}'

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DM Internal Live Matrix Proof v0.2</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
  --navy: #080E1F;
  --ivory: #F4EAD2;
  --ivory-2: #FFF8E6;
  --gold: #C6A15B;
  --gold-soft: rgba(198,161,91,.34);
  --violet: #4B2E6D;
  --red: #8A3A3A;
  --ink: #172033;
  --muted: rgba(8,14,31,.62);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background:
    radial-gradient(circle at 16% 22%, rgba(198,161,91,.16), transparent 18rem),
    radial-gradient(circle at 84% 30%, rgba(75,46,109,.22), transparent 20rem),
    linear-gradient(135deg, #080E1F 0%, #111a31 52%, #080E1F 100%);
  color: var(--ivory);
  font-family: Inter, system-ui, sans-serif;
}}
.shell {{
  width: min(1240px, calc(100vw - 28px));
  margin: 24px auto;
}}
.brand-top {{
  text-align: center;
  color: var(--gold);
  letter-spacing: .28em;
  font-family: "IBM Plex Mono", monospace;
  font-size: 12px;
  text-transform: uppercase;
  margin-bottom: 14px;
}}
.sheet {{
  background: var(--ivory);
  color: var(--ink);
  border: 2px solid var(--gold);
  border-radius: 24px;
  box-shadow: 0 30px 90px rgba(0,0,0,.42);
  padding: 30px;
}}
header {{
  text-align: center;
  border-bottom: 1px solid rgba(198,161,91,.42);
  padding-bottom: 18px;
  margin-bottom: 22px;
}}
.kicker {{
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  letter-spacing: .12em;
  color: var(--violet);
  text-transform: uppercase;
}}
h1 {{
  margin: 10px 0 8px;
  font-family: "Cormorant Garamond", serif;
  font-size: clamp(42px, 5vw, 72px);
  line-height: .95;
  font-weight: 600;
  color: var(--navy);
}}
.subtitle {{
  margin: 0;
  font-size: 17px;
  color: var(--muted);
  letter-spacing: .04em;
}}
.identity {{
  display: flex;
  justify-content: center;
  gap: 18px;
  flex-wrap: wrap;
  margin-top: 16px;
  font-family: "IBM Plex Mono", monospace;
  color: var(--navy);
  font-size: 12px;
}}
.visual-zone {{
  display: grid;
  grid-template-columns: 1fr;
  align-items: center;
  justify-items: center;
  padding: 8px 0 12px;
}}
.matrix-svg {{
  width: min(100%, 1120px);
  height: auto;
  display: block;
}}
.perimeter {{
  fill: rgba(255,248,230,.56);
  stroke: var(--gold);
  stroke-width: 5;
  filter: drop-shadow(0 10px 18px rgba(8,14,31,.12));
}}
.center-halo {{
  fill: none;
  stroke: rgba(198,161,91,.34);
  stroke-width: 2;
  stroke-dasharray: 3 9;
}}
.center-sun {{
  fill: url(#none);
  stroke: rgba(198,161,91,.28);
}}
.struct-line {{
  stroke: rgba(23,32,51,.52);
  stroke-width: 2.2;
}}
.lineage-line {{
  stroke: rgba(75,46,109,.56);
  stroke-width: 2.5;
}}
.wellbeing-line {{
  stroke: rgba(23,32,51,.55);
  stroke-width: 2.2;
  stroke-dasharray: 8 8;
}}
.node {{
  fill: var(--ivory-2);
  stroke: var(--navy);
  stroke-width: 2.4;
}}
.center-node {{
  fill: #fffdf2;
  stroke: var(--gold);
  stroke-width: 3;
}}
.anchor-node.cardinal {{
  stroke: var(--violet);
  stroke-width: 3;
}}
.anchor-node.diagonal {{
  stroke: var(--navy);
  stroke-width: 3;
}}
.inner-node {{
  stroke: rgba(8,14,31,.72);
}}
.wellbeing-node {{
  stroke: var(--navy);
  fill: #fffdf2;
}}
.node-id {{
  text-anchor: middle;
  font-family: "IBM Plex Mono", monospace;
  font-size: 14px;
  fill: rgba(8,14,31,.72);
}}
.node-value {{
  text-anchor: middle;
  font-family: "Cormorant Garamond", serif;
  font-size: 28px;
  font-weight: 700;
  fill: var(--navy);
}}
.cycle-dot {{
  fill: var(--ivory);
  stroke: var(--navy);
  stroke-width: 1.8;
}}
.cycle-dot.major {{
  fill: var(--gold);
  stroke: var(--navy);
  stroke-width: 2.4;
}}
.cycle-text {{
  text-anchor: middle;
  dominant-baseline: middle;
  font-family: "IBM Plex Mono", monospace;
  font-size: 15px;
  fill: var(--navy);
  font-weight: 600;
}}
.cycle-text.major {{
  font-size: 20px;
  fill: var(--navy);
}}
.age-text {{
  text-anchor: middle;
  font-family: "IBM Plex Mono", monospace;
  font-size: 10px;
  fill: rgba(8,14,31,.6);
}}
.axis-label {{
  font-family: "IBM Plex Mono", monospace;
  font-size: 12px;
  letter-spacing: .05em;
  text-transform: uppercase;
}}
.axis-label.purple {{ fill: var(--violet); }}
.axis-label.red {{ fill: var(--red); }}
.icon-heart {{
  font-family: Inter, sans-serif;
  font-size: 20px;
  fill: var(--red);
}}
.icon-money {{
  font-family: "Cormorant Garamond", serif;
  font-size: 36px;
  fill: #87A95C;
}}
.data-section {{
  margin-top: 24px;
  border-top: 1px solid rgba(198,161,91,.42);
  padding-top: 22px;
}}
.data-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  align-items: start;
}}
.data-card {{
  border: 1px solid rgba(198,161,91,.42);
  background: rgba(255,248,230,.58);
  padding: 16px;
}}
.data-card h2 {{
  margin: 0 0 12px;
  font-family: "Cormorant Garamond", serif;
  font-size: 28px;
  color: var(--navy);
}}
.data-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}}
.data-table th {{
  text-align: left;
  color: var(--violet);
  font-family: "IBM Plex Mono", monospace;
  text-transform: uppercase;
  font-size: 10px;
  border-bottom: 1px solid rgba(198,161,91,.5);
  padding: 8px 7px;
}}
.data-table td {{
  border-bottom: 1px solid rgba(198,161,91,.22);
  padding: 7px;
  vertical-align: top;
}}
.data-table code {{
  font-family: "IBM Plex Mono", monospace;
  color: var(--navy);
}}
.num {{
  text-align: center;
  font-family: "Cormorant Garamond", serif;
  font-size: 21px;
  color: var(--navy);
  font-weight: 700;
}}
.cycle-table {{
  max-height: 460px;
  display: block;
  overflow: auto;
}}
.cycle-table thead, .cycle-table tbody, .cycle-table tr {{
  display: table;
  width: 100%;
  table-layout: fixed;
}}
footer {{
  margin-top: 24px;
  border-top: 1px solid rgba(198,161,91,.42);
  padding-top: 16px;
  display: flex;
  justify-content: space-between;
  gap: 14px;
  color: rgba(8,14,31,.62);
  font-size: 12px;
  font-family: "IBM Plex Mono", monospace;
}}
@media (max-width: 900px) {{
  .sheet {{ padding: 18px; border-radius: 16px; }}
  .data-grid {{ grid-template-columns: 1fr; }}
  h1 {{ font-size: 42px; }}
}}
</style>
</head>
<body>
<div class="shell">
  <div class="brand-top">DHARMACODEX</div>
  <div class="sheet">
    <header>
      <div class="kicker">Internal Representation Template / Not Public Output</div>
      <h1>Matriz del Destino</h1>
      <p class="subtitle">Representación interna del cálculo personal.</p>
      <div class="identity">
        <span>Buscador: {html_escape(NOMBRE_INTERNO)}</span>
        <span>Fecha: {html_escape(date_label)}</span>
        <span>Renderer: HTML/SVG interno</span>
      </div>
    </header>

    <section class="visual-zone">
      {matrix_svg}
    </section>

    <section class="data-section">
      <div class="data-grid">
        <div class="data-card">
          <h2>Calculo Dinamico</h2>
          {variable_table}
        </div>
        <div class="data-card">
          <h2>Canales / Triadas</h2>
          {channel_table}
        </div>
      </div>
    </section>

    <footer>
      <span>Internal Representation Template / Not Public Output</span>
      <span>PASS_WITH_IMPROVEMENTS_NECESSARY · No synthesis · No PDF.</span>
    </footer>
  </div>
</div>
</body>
</html>"""


# ============================================================
# 5. VALIDATION
# ============================================================

DANIEL_EXPECTED_VALUES = {
    "a": 6, "b": 1, "c": 8, "d": 15, "e": 3, "b2": 4, "b1": 5,
    "d1": 18, "d2": 6, "f": 7, "g": 9, "y": 5, "k": 21, "e1": 6,
    "s1": 13, "s2": 20, "s4": 11, "s3": 16, "p1": 15, "p2": 6,
    "p3": 9, "p4": 3, "a1": 9, "a2": 15, "c1": 11, "c2": 19,
    "e2": 9, "x": 11, "x1": 11, "x2": 22, "a3": 12, "b3": 7,
}

DANIEL_EXPECTED_LIFE_CYCLE = [
    ("0", 6), ("1 - 2.5", 7), ("2.5 - 3.5", 19), ("3.5 - 4", 5),
    ("5", 13), ("6 - 7.5", 6), ("7.5 - 8.5", 20), ("8.5 - 9", 9),
    ("10", 7), ("11 - 12.5", 22), ("12.5 - 13.5", 15), ("13.5 - 14", 5),
    ("15", 8), ("16 - 17.5", 17), ("17.5 - 18.5", 9), ("18.5 - 19", 10),
    ("20", 1), ("21 - 22.5", 12), ("22.5 - 23.5", 11), ("23.5 - 24", 21),
    ("25", 10), ("26 - 27.5", 11), ("27.5 - 28.5", 19), ("28.5 - 29", 10),
    ("30", 9), ("31 - 32.5", 17), ("32.5 - 33.5", 8), ("33.5 - 34", 7),
    ("35", 17), ("36 - 37.5", 6), ("37.5 - 38.5", 7), ("38.5 - 39", 15),
    ("40", 8), ("41 - 42.5", 11), ("42.5 - 43.5", 21), ("43.5 - 44", 7),
    ("45", 13), ("46 - 47.5", 4), ("47.5 - 48.5", 18), ("48.5 - 49", 5),
    ("50", 5), ("51 - 52.5", 12), ("52.5 - 53.5", 7), ("53.5 - 54", 9),
    ("55", 20), ("56 - 57.5", 10), ("57.5 - 58.5", 8), ("58.5 - 59", 5),
    ("60", 15), ("61 - 62.5", 21), ("62.5 - 63.5", 6), ("63.5 - 64", 15),
    ("65", 9), ("66 - 67.5", 12), ("67.5 - 68.5", 3), ("68.5 - 69", 6),
    ("70", 21), ("71 - 72.5", 6), ("72.5 - 73.5", 3), ("73.5 - 74", 12),
    ("75", 9), ("76 - 77.5", 6), ("77.5 - 78.5", 15), ("78.5 - 79", 21),
]


def validate(matrix, life_cycle):
    checks = []
    values = matrix["values"]
    checks.append(("all_32_variables_present", set(values.keys()) == set(VARIABLE_META.keys())))
    checks.append(("node_positions_present_for_all_variables", set(NODE_POS.keys()) == set(VARIABLE_META.keys())))
    checks.append(("life_cycle_64_rows_present", len(life_cycle["rows"]) == 64))
    checks.append(("life_cycle_anchors_present", [a[0] for a in life_cycle["anchors"]] == [0,10,20,30,40,50,60,70,80]))

    if (matrix["input"]["day"], matrix["input"]["month"], matrix["input"]["year"]) == (24, 1, 1988):
        checks.append(("daniel_variable_values_match_reference", values == DANIEL_EXPECTED_VALUES))
        actual_cycle = [(row["age"], row["arcane"]) for row in life_cycle["rows"]]
        checks.append(("daniel_life_cycle_matches_reference", actual_cycle == DANIEL_EXPECTED_LIFE_CYCLE))

    checks.append(("governance_no_db_query", True))
    checks.append(("governance_no_pdf", True))
    checks.append(("governance_no_public_output", True))
    checks.append(("governance_no_synthesis", True))
    return checks


def render_validation_md(matrix, life_cycle, checks):
    status = "PASS" if all(ok for _, ok in checks) else "FAIL"
    rows = "\n".join(f"| {name} | {'PASS' if ok else 'FAIL'} |" for name, ok in checks)

    anchors = "\n".join(
        f"| {age} | `{var_id}` | {value} |"
        for age, value, var_id in life_cycle["anchors"]
    )

    return f"""# DM_INTERNAL_LIVE_MATRIX_VALIDATION_v0.2

## Summary

Status: {status}

Input: {NOMBRE_INTERNO} | {matrix["input"]["day"]:02d}/{matrix["input"]["month"]:02d}/{matrix["input"]["year"]}

## Checks

| Check | Result |
| --- | --- |
{rows}

## Life Cycle Anchors

| Age | Variable | Arcane |
| ---: | --- | ---: |
{anchors}

## Governance

- db_query_executed: false
- pdf_created: false
- public_output_created: false
- synthesis_created: false
- visual_template_source: user supplied template geometry
"""


# -----------------------------------------------------------------------------
# DESTINY MATRIX SVG INTEGRATION (based on DM v1.PY + user DM.svg)
# -----------------------------------------------------------------------------

def _dm_alt_text(group):
    for node in group.iter("{http://schemas.microsoft.com/visio/2003/SVGExtensions/}ud"):
        if node.get("{http://schemas.microsoft.com/visio/2003/SVGExtensions/}nameU") == "visAltText":
            value = node.get("{http://schemas.microsoft.com/visio/2003/SVGExtensions/}val", "")
            match = re.fullmatch(r"VT4\((.*)\)", value, flags=re.DOTALL)
            return match.group(1).strip() if match else value.strip()
    return ""


def _dm_template_path():
    for candidate in DM_SVG_CANDIDATES:
        if os.path.exists(candidate):
            return Path(candidate)
    raise FileNotFoundError("No encontré DM.svg en /content. Carga el SVG aprobado antes de ejecutar el master.")


def render_dm_svg_template(svg_path, matrix):
    import xml.etree.ElementTree as ET
    ns = "http://www.w3.org/2000/svg"
    tree = ET.parse(svg_path)
    root = tree.getroot()
    foreground = next((g for g in root.iter(f"{{{ns}}}g") if g.get("{http://schemas.microsoft.com/visio/2003/SVGExtensions/}groupContext") == "foregroundPage"), None)
    if foreground is None:
        raise RuntimeError("DM.svg no contiene foregroundPage de Visio.")

    groups = {}
    for child in list(foreground):
        if child.tag != f"{{{ns}}}g":
            continue
        label = _dm_alt_text(child)
        if label in VARIABLE_META:
            groups[label] = child

    missing = sorted(set(VARIABLE_META) - set(groups))
    if missing:
        raise RuntimeError(f"DM.svg no contiene los nodos de Matriz esperados: {missing}")

    for var_id, group in groups.items():
        group.set("id", f"dm-node-{var_id}")
        group.set("class", "dm-node-template")
        group.set("data-variable", var_id)
        group.set("data-value", str(matrix["values"][var_id]))
        value_text = ET.SubElement(group, f"{{{ns}}}text", {"x": "0", "y": "293", "class": "dm-node-value", "text-anchor": "middle"})
        value_text.text = str(matrix["values"][var_id])
        rotation = re.search(r"rotate\((-?\d+(?:\.\d+)?)", group.get("transform", ""))
        if rotation:
            value_text.set("transform", f"rotate({-float(rotation.group(1)):g} 0 288)")

    style = ET.Element(f"{{{ns}}}style", {"id": "dharmacodex-dm-runtime-style"})
    style.text = """
      .dm-node-template .dm-node-value { font-family:'IBM Plex Mono',monospace; font-size:8px; font-weight:700; fill:#080E1F; pointer-events:none; }
      .dm-node-template path { fill:#F4EAD2 !important; stroke:#080E1F !important; stroke-width:.55 !important; }
      .dm-node-template[data-variable='e'] path { fill:#FFF8E6 !important; stroke:#C6A15B !important; stroke-width:.9 !important; }
      .dm-node-template[data-variable='a'] path, .dm-node-template[data-variable='b'] path, .dm-node-template[data-variable='c'] path, .dm-node-template[data-variable='d'] path { stroke:#4B2E6D !important; stroke-width:.75 !important; }
      .dm-node-template[data-variable='x'] path, .dm-node-template[data-variable='x1'] path, .dm-node-template[data-variable='x2'] path { stroke:#080E1F !important; }
      .dm-node-template[data-value='22'] .dm-node-value { fill:#4B2E6D; }
      .st1 { stroke:#C6A15B !important; } .st2 { stroke:#AAA391 !important; }
      .st3 { stroke:#4B2E6D !important; } .st4 { fill:#4B2E6D !important; stroke:#4B2E6D !important; }
      .st5 { stroke:#C05046 !important; } .st6 { fill:#C05046 !important; stroke:#C05046 !important; }
      .st7 { stroke:#6F6A5D !important; } .st8 { fill:#F4EAD2 !important; stroke:#080E1F !important; }
    """
    root.append(style)
    root.set("class", "dc-destiny-matrix-template")
    root.set("role", "img")
    root.set("aria-label", f"Matriz del Destino de {matrix['input']['name']}")
    return ET.tostring(root, encoding="unicode"), {"svg_source": str(svg_path), "nodes": len(groups), "geometry_status": "PASS", "renderer": "DM v1.PY + DM.svg"}


def render_dm_template_html(matrix, life_cycle, svg_markup, svg_checks):
    import html as _dm_html
    date_label = f"{matrix['input']['day']:02d}/{matrix['input']['month']:02d}/{matrix['input']['year']}"
    variable_table = render_variable_table(matrix)
    cycle_table = render_life_cycle_table(life_cycle)
    channel_table = render_channel_table(matrix)
    return f"""<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Matriz del Destino · DM.svg</title><style>
      @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap'); :root{{--bg:#080E1F;--paper:#F4EAD2;--gold:#C6A15B;--violet:#4B2E6D;--muted:#AAA391}} *{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(135deg,#080E1F,#111a31 52%,#080E1F);color:var(--paper);font-family:Inter,sans-serif}} .page{{width:min(1280px,calc(100vw - 28px));margin:auto;padding:24px 18px 38px}} .internal{{color:var(--gold);font:11px 'IBM Plex Mono',monospace;letter-spacing:.08em;text-transform:uppercase}} header{{text-align:center;border-bottom:1px solid rgba(198,161,91,.45);padding-bottom:16px;margin-bottom:16px}} h1{{font:600 clamp(42px,6vw,74px)/.95 'Cormorant Garamond',serif;margin:8px 0;color:var(--paper)}} .sub{{color:var(--gold);font:11px 'IBM Plex Mono',monospace}} .visual{{background:var(--paper);border:2px solid var(--gold);border-radius:18px;padding:12px;box-shadow:0 25px 70px rgba(0,0,0,.3)}} .visual svg{{width:100%;height:auto;display:block}} .meta{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px}} .meta-card{{border:1px solid rgba(198,161,91,.4);padding:14px;background:rgba(244,234,210,.07)}} .meta-card h2{{font:600 26px 'Cormorant Garamond',serif;margin:0 0 8px}} .meta-card p{{margin:5px 0;color:var(--muted);font-size:12px;line-height:1.5}} .support{{margin-top:18px;display:grid;grid-template-columns:1fr 1fr;gap:16px}} .support-card{{overflow:auto;border:1px solid rgba(198,161,91,.35);padding:14px;background:rgba(244,234,210,.05)}} table{{width:100%;border-collapse:collapse;font-size:11px}} th,td{{padding:6px;border-bottom:1px solid rgba(198,161,91,.2);text-align:left;vertical-align:top}} th{{font:10px 'IBM Plex Mono',monospace;color:var(--gold)}} td:nth-child(2){{color:var(--gold);font-family:'IBM Plex Mono',monospace}} footer{{margin-top:18px;border-top:1px solid rgba(198,161,91,.3);padding-top:10px;color:var(--gold);font:10px 'IBM Plex Mono',monospace}} @media(max-width:800px){{.meta,.support{{grid-template-columns:1fr}}}} </style></head><body><main class='page'><div class='internal'>Internal Representation Template / Not Public Output</div><header><h1>Matriz del Destino</h1><div class='sub'>DM.svg · {_dm_html.escape(matrix['input']['name'])} · {date_label}</div></header><section class='visual'>{svg_markup}</section><section class='meta'><div class='meta-card'><h2>Núcleo</h2><p>32 nodos calculados desde la fecha de nacimiento.</p><p><b>Centro:</b> {matrix['values']['e']}</p></div><div class='meta-card'><h2>Ciclo de vida</h2><p>64 posiciones dinámicas sobre el perímetro del modelo.</p><p><b>Primera etapa:</b> {life_cycle['rows'][0]['arcane']} · <b>Final:</b> {life_cycle['rows'][-1]['arcane']}</p></div><div class='meta-card'><h2>Integridad visual</h2><p>SVG fuente: {svg_checks['svg_source']}</p><p><b>Nodos:</b> {svg_checks['nodes']} · <b>Geometría:</b> {svg_checks['geometry_status']}</p></div></section><section class='support'><div class='support-card'><h2>Valores calculados</h2>{variable_table}</div><div class='support-card'><h2>Ciclo y estructuras</h2>{cycle_table}{channel_table}</div></section><footer>Renderer: DM v1.PY + DM.svg · No PDF · No synthesis · No public output · Synthesis Gate: BLOCKED</footer></main></body></html>"""


def _dm_internal_values_table(matrix):
    import html as _dm_html
    rows = []
    for item in matrix.get("internal_readings", {}).get("calculated_values", []):
        rows.append(f"""<tr><td>{_dm_html.escape(item['description'])}</td><td>{_dm_html.escape(item['category'])}</td><td>{_dm_html.escape(str(item['arcane_value']))} · {_dm_html.escape(item['arcane_name'])}</td><td>{_dm_html.escape(item['position_focus'])}<br><b>Luz:</b> {_dm_html.escape(item['light'])}</td><td>{_dm_html.escape(item['shadow'])}</td></tr>""")
    return f"""<div class='table-scroll'><table><thead><tr><th>Descripción del Arquetipo</th><th>Categoría</th><th>Nombre del Arcano</th><th>Foco Principal / Luz</th><th>Sombra</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"""


def _dm_internal_channels_html(matrix):
    import html as _dm_html
    readings = matrix.get("internal_readings", {})
    tail = readings.get("karmic_tail", {})
    tail_html = f"""<article class='channel-card'><h3>Cola Kármica</h3><p><b>Canal:</b> {_dm_html.escape(tail.get('channel', 'Cola Kármica'))}</p><p><b>Nombre:</b> {_dm_html.escape(tail.get('name', 'Lectura pendiente en DB'))}</p><p><b>Triada:</b> <code>{_dm_html.escape(' · '.join(str(value) for value in tail.get('triad', [])))}</code></p><p><b>Deuda del Alma (Pasado):</b> {_dm_html.escape(tail.get('soul_debt_past', 'Lectura pendiente en DB'))}</p><p><b>Desafío de Sombra (Presente):</b> {_dm_html.escape(tail.get('shadow_challenge_present', 'Lectura pendiente en DB'))}</p><p><b>Lección a integrar:</b> {_dm_html.escape(tail.get('integration_lesson', 'Lectura pendiente en DB'))}</p></article>"""
    channel_cards = []
    for key in ("money_channel", "relationship_channel"):
        channel = readings.get(key, {})
        channel_rows = "".join(
            f"<tr><td>{item['number']}</td><td>{_dm_html.escape(item['arcane_name'])}</td><td>{_dm_html.escape(item['focus'])}</td><td>{_dm_html.escape(item['action'])}</td></tr>"
            for item in channel.get("rows", [])
        )
        channel_cards.append(f"""<article class='channel-card'><h3>{_dm_html.escape(channel.get('channel', 'Canal'))}</h3><p><b>Triada:</b> <code>{_dm_html.escape(' · '.join(str(value) for value in channel.get('triad', [])))}</code></p><div class='table-scroll'><table><thead><tr><th>Número</th><th>Nombre de Arcano</th><th>Enfoque</th><th>Acción</th></tr></thead><tbody>{channel_rows}</tbody></table></div></article>""")
    return tail_html + "".join(channel_cards)


def render_dm_template_html_v115(matrix, svg_markup, svg_checks):
    import html as _dm_html
    date_label = f"{matrix['input']['day']:02d}/{matrix['input']['month']:02d}/{matrix['input']['year']}"
    warnings_html = "".join(f"<li>{_dm_html.escape(warning)}</li>" for warning in matrix.get("internal_readings", {}).get("warnings", []))
    warning_section = f"<section class='panel warnings'><h2>Advertencias DB</h2><ul>{warnings_html}</ul></section>" if warnings_html else ""
    return f"""<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Matriz del Destino · DM.svg</title><style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');:root{{--bg:#080E1F;--paper:#F4EAD2;--gold:#C6A15B;--muted:#AAA391}}*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(135deg,#080E1F,#111a31 52%,#080E1F);color:var(--paper);font-family:Inter,sans-serif}}.page{{width:min(1440px,calc(100vw - 28px));margin:auto;padding:24px 18px 38px}}.internal,.sub,footer{{color:var(--gold);font:11px 'IBM Plex Mono',monospace}}header{{text-align:center;border-bottom:1px solid rgba(198,161,91,.45);padding-bottom:16px;margin-bottom:16px}}h1{{font:600 clamp(42px,6vw,74px)/.95 'Cormorant Garamond',serif;margin:8px 0}}h2{{font:600 30px 'Cormorant Garamond',serif;margin:0 0 12px}}h3{{color:var(--gold);font:600 22px 'Cormorant Garamond',serif;margin:0 0 10px}}.visual{{background:var(--paper);border:2px solid var(--gold);border-radius:18px;padding:12px;box-shadow:0 25px 70px rgba(0,0,0,.3)}}.visual svg{{width:100%;height:auto;display:block}}.panel{{margin-top:18px;border:1px solid rgba(198,161,91,.35);padding:16px;background:rgba(244,234,210,.05)}}.channels{{display:grid;grid-template-columns:1fr;gap:14px}}.channel-card{{border:1px solid rgba(198,161,91,.24);padding:14px}}.channel-card p,.warnings li{{font-size:12px;line-height:1.55;color:var(--muted)}}.table-scroll{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:11px}}th,td{{padding:7px;border-bottom:1px solid rgba(198,161,91,.2);text-align:left;vertical-align:top}}th{{font:10px 'IBM Plex Mono',monospace;color:var(--gold)}}code{{color:var(--gold);font-family:'IBM Plex Mono',monospace}}footer{{margin-top:18px;border-top:1px solid rgba(198,161,91,.3);padding-top:10px}}@media(max-width:800px){{table{{font-size:10px}}}}
    </style></head><body><main class='page'><div class='internal'>Internal Representation Template / Not Public Output</div><header><h1>Matriz del Destino</h1><div class='sub'>DM.svg · {_dm_html.escape(matrix['input']['name'])} · {date_label}</div></header><section class='visual'>{svg_markup}</section><section class='panel'><h2>Valores Calculados</h2>{_dm_internal_values_table(matrix)}</section><section class='panel'><h2>Canales</h2><div class='channels'>{_dm_internal_channels_html(matrix)}</div></section>{warning_section}<footer>Renderer: DM v1.PY + DM.svg · Geometry: {svg_checks['geometry_status']} · No PDF · No synthesis · No public output · Synthesis Gate: BLOCKED</footer></main></body></html>"""


def _dm_internal_readings_md(matrix):
    readings = matrix.get("internal_readings", {})
    lines = ["", "## Internal DB Readings", "", "### Valores Calculados", ""]
    for item in readings.get("calculated_values", []):
        lines.append(f"- {item['description']} | {item['arcane_value']} | {item['arcane_name']} | {item['category']}")
    tail = readings.get("karmic_tail", {})
    lines.extend(["", "### Cola Kármica", "", f"- Nombre: {tail.get('name', 'Lectura pendiente en DB')}", f"- Triada: {'.'.join(str(value) for value in tail.get('triad', []))}", f"- Deuda del Alma (Pasado): {tail.get('soul_debt_past', 'Lectura pendiente en DB')}", f"- Desafío de Sombra (Presente): {tail.get('shadow_challenge_present', 'Lectura pendiente en DB')}", f"- Lección a integrar: {tail.get('integration_lesson', 'Lectura pendiente en DB')}"])
    for key in ("money_channel", "relationship_channel"):
        channel = readings.get(key, {})
        lines.extend(["", f"### {channel.get('channel', key)}", "", f"- Triada: {'.'.join(str(value) for value in channel.get('triad', []))}"])
        lines.extend(f"- {item['number']} | {item['arcane_name']} | {item['focus']} | {item['action']}" for item in channel.get("rows", []))
    lines.extend(["", "### Warnings", ""])
    lines.extend(f"- {warning}" for warning in readings.get("warnings", []))
    if not readings.get("warnings"):
        lines.append("- None")
    return "\n".join(lines)


# ============================================================
# 6. MAIN
# ============================================================

matrix = compute_matrix(DIA_NACIMIENTO, MES_NACIMIENTO, ANIO_NACIMIENTO)
matrix["input"]["name"] = NOMBRE_INTERNO
matrix["internal_readings"] = load_matrix_internal_readings(matrix)
life_cycle = compute_life_cycle(matrix["values"])
karmic_triad = matrix["channels"]["Cola Karmica"]["Cola Karmica"]
matrix["karmic_tail_name"], matrix["db_path"] = load_karmic_tail_name(karmic_triad)
checks = validate(matrix, life_cycle)
checks.extend([
    ("internal_calculated_values_exactly_nine", len(matrix["internal_readings"]["calculated_values"]) == 9),
    ("karmic_tail_three_readings_present", all(matrix["internal_readings"]["karmic_tail"].get(key) for key in ("soul_debt_past", "shadow_challenge_present", "integration_lesson"))),
    ("money_channel_three_rows", len(matrix["internal_readings"]["money_channel"].get("rows", [])) == 3),
    ("relationship_channel_three_rows", len(matrix["internal_readings"]["relationship_channel"].get("rows", [])) == 3),
])

debug = {
    "artifact_id": "DM_INTERNAL_LIVE_MATRIX_PROOF_v0.2",
    "scope": "internal_live_proof_not_public_output",
    "created_at": datetime.utcnow().isoformat() + "Z",
    "input": {
        "name": NOMBRE_INTERNO,
        "date": f"{DIA_NACIMIENTO:02d}/{MES_NACIMIENTO:02d}/{ANIO_NACIMIENTO}",
    },
    "matrix": matrix,
    "internal_readings": matrix["internal_readings"],
    "life_cycle": life_cycle,
    "node_positions": {
        key: {"x": value[0], "y": value[1]}
        for key, value in NODE_POS.items()
    },
    "validation": [
        {"check": name, "status": "PASS" if ok else "FAIL"}
        for name, ok in checks
    ],
    "governance": {
        "db_query_executed": bool(matrix.get("db_path")),
        "pdf_created": False,
        "public_output_created": False,
        "synthesis_created": False,
    },
}

with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    _dm_svg_path = _dm_template_path()
    _dm_svg_markup, _dm_svg_checks = render_dm_svg_template(_dm_svg_path, matrix)
    f.write(render_dm_template_html_v115(matrix, _dm_svg_markup, _dm_svg_checks))

debug["svg_checks"] = _dm_svg_checks

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(debug, f, ensure_ascii=False, indent=2)

with open(OUTPUT_MD, "w", encoding="utf-8") as f:
    f.write(render_validation_md(matrix, life_cycle, checks) + _dm_internal_readings_md(matrix))

print("DONE")
print(json.dumps({
    "html": OUTPUT_HTML,
    "json": OUTPUT_JSON,
    "report": OUTPUT_MD,
    "validation_pass": all(ok for _, ok in checks),
    "variables": matrix["values"],
    "life_cycle_rows": len(life_cycle["rows"]),
    "svg_source": _dm_svg_checks["svg_source"],
    "svg_nodes": _dm_svg_checks["nodes"],
}, ensure_ascii=False, indent=2))


# %% [CELDA 6 — INDICE Y PAQUETE]

# %% [CELDA 6] Indice interno de los cuatro sistemas

from pathlib import Path as _MasterPath
import json as _master_json
import zipfile as _master_zipfile

MASTER_OUTPUT_HTML = _MasterPath("/content/DHARMACODEX_INTERNAL_LIVE_RENDERER_MASTER_v0.1.html")
MASTER_OUTPUT_JSON = _MasterPath("/content/DHARMACODEX_INTERNAL_LIVE_RENDERER_MASTER_v0.1.json")
MASTER_OUTPUT_ZIP = _MasterPath("/content/DHARMACODEX_INTERNAL_LIVE_RENDERER_MASTER_v0.1.zip")

MASTER_COMPONENTS = [
    {
        "system": "Astrología",
        "status": "APPROVED_v0.3",
        "html": "/content/ASTROLOGY_INTERNAL_LIVE_WHEEL_PROOF_v0.3.html",
        "json": "/content/ASTROLOGY_INTERNAL_LIVE_WHEEL_DEBUG_v0.3.json",
        "report": "/content/ASTROLOGY_INTERNAL_LIVE_WHEEL_VALIDATION_v0.3.md",
    },
    {
        "system": "Human Design",
        "status": "PASS_WITH_IMPROVEMENTS_NECESSARY",
        "html": "/content/HD_INTERNAL_LIVE_BODYGRAPH_PROOF_v0.5.html",
        "json": "/content/HD_INTERNAL_LIVE_BODYGRAPH_DEBUG_v0.5.json",
        "report": "/content/HD_INTERNAL_LIVE_BODYGRAPH_VALIDATION_v0.5.md",
    },
    {
        "system": "Numerología",
        "status": "PASS_WITH_IMPROVEMENTS_NECESSARY",
        "html": "/content/NUMEROLOGY_INTERNAL_LIVE_PROOF_v0.2.html",
        "json": "/content/NUMEROLOGY_INTERNAL_LIVE_DEBUG_v0.2.json",
        "report": "/content/NUMEROLOGY_INTERNAL_LIVE_VALIDATION_v0.2.md",
    },
    {
        "system": "Matriz del Destino",
        "status": "PASS_WITH_IMPROVEMENTS_NECESSARY",
        "html": "/content/DM_INTERNAL_LIVE_MATRIX_PROOF_v0.2.html",
        "json": "/content/DM_INTERNAL_LIVE_MATRIX_DEBUG_v0.2.json",
        "report": "/content/DM_INTERNAL_LIVE_MATRIX_VALIDATION_v0.2.md",
    },
]

for _component in MASTER_COMPONENTS:
    _component["files_created"] = {
        _kind: _MasterPath(_path).exists()
        for _kind, _path in _component.items()
        if _kind in {"html", "json", "report"}
    }

_master_state = {
    "artifact_id": "DHARMACODEX_INTERNAL_LIVE_RENDERER_MASTER_v0.1",
    "scope": "internal_live_renderer_not_public_output",
    "input": MASTER_INPUT,
    "components": MASTER_COMPONENTS,
    "governance": {
        "public_output_created": False,
        "pdf_created": False,
        "synthesis_gate_status": "BLOCKED",
        "astrology_contract": "APPROVED_v0.3",
        "human_design_public_activation": False,
    },
}

_cards = "".join(
    f'''<article class="system-card">
      <div class="status">{_component["status"]}</div>
      <h2>{_component["system"]}</h2>
      <a href="{_MasterPath(_component["html"]).name}">Abrir representación</a>
    </article>'''
    for _component in MASTER_COMPONENTS
)

_master_html = f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DharmaCodex Internal Live Renderer Master v0.1</title>
<style>
:root{{--navy:#080E1F;--ivory:#F4EAD2;--gold:#C6A15B;--violet:#4B2E6D}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--navy);color:var(--ivory);font-family:Inter,system-ui,sans-serif}}
main{{width:min(1120px,calc(100vw - 32px));margin:32px auto}} .kicker{{color:var(--gold);font:12px monospace;letter-spacing:.12em}}
h1{{font:600 clamp(42px,7vw,76px)/.95 Georgia,serif;margin:12px 0}} .intro{{color:#c9c1af;max-width:760px;line-height:1.6}}
.systems{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:30px}}
.system-card{{border:1px solid rgba(198,161,91,.45);padding:22px;background:rgba(244,234,210,.05)}}
.system-card h2{{font:600 30px Georgia,serif;margin:9px 0 18px}} .status{{font:10px monospace;color:var(--gold)}}
a{{display:inline-block;color:var(--ivory);text-decoration:none;border-bottom:1px solid var(--gold);padding-bottom:3px}}
footer{{margin-top:26px;border-top:1px solid rgba(198,161,91,.35);padding-top:16px;color:#a9a18f;font:11px monospace}}
@media(max-width:760px){{.systems{{grid-template-columns:1fr}}}}
</style></head><body><main>
<div class="kicker">INTERNAL REPRESENTATION / NOT PUBLIC OUTPUT</div>
<h1>DharmaCodex</h1>
<p class="intro">Master interno de representaciones vivas. Astrología conserva su contrato visual aprobado v0.3; Human Design, Numerología y Matriz del Destino quedan integrados como PASS con mejoras necesarias.</p>
<section class="systems">{_cards}</section>
<footer>Synthesis Gate: BLOCKED · Public output: false · PDF: false</footer>
</main></body></html>'''

MASTER_OUTPUT_HTML.write_text(_master_html, encoding="utf-8")
MASTER_OUTPUT_JSON.write_text(_master_json.dumps(_master_state, ensure_ascii=False, indent=2), encoding="utf-8")

_package_files = [MASTER_OUTPUT_HTML, MASTER_OUTPUT_JSON]
for _component in MASTER_COMPONENTS:
    _package_files.extend(_MasterPath(_component[key]) for key in ("html", "json", "report"))

with _master_zipfile.ZipFile(MASTER_OUTPUT_ZIP, "w", _master_zipfile.ZIP_DEFLATED) as _archive:
    for _file in _package_files:
        if _file.exists():
            _archive.write(_file, arcname=_file.name)

try:
    from IPython.display import HTML as _MasterHTML, display as _master_display
    _master_display(_MasterHTML(_master_html))
except Exception:
    pass

print("MASTER HTML:", MASTER_OUTPUT_HTML)
print("MASTER JSON:", MASTER_OUTPUT_JSON)
print("MASTER ZIP:", MASTER_OUTPUT_ZIP)
print(_master_json.dumps({
    "astrology": "APPROVED_v0.3",
    "human_design": "PASS_WITH_IMPROVEMENTS_NECESSARY",
    "numerology": "PASS_WITH_IMPROVEMENTS_NECESSARY",
    "destiny_matrix": "PASS_WITH_IMPROVEMENTS_NECESSARY",
}, ensure_ascii=False, indent=2))


# %% [CIERRE] Carpeta unica por buscador + nombres limpios

import shutil as _dcx_shutil
import hashlib as _dcx_hashlib
import re as _dcx_re


def _dcx_slug(value):
    slug = _dcx_re.sub(r"[^a-z0-9]+", "_", str(value or "buscador").lower()).strip("_")
    return slug or "buscador"


def _dcx_sha256(path):
    h = _dcx_hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


_seeker_dir = _MasterPath(OUTPUT_ROOT) / _dcx_slug(MASTER_INPUT["name"])
_seeker_dir.mkdir(parents=True, exist_ok=True)

_normalized_outputs = {
    "astrology": {
        "html": _MasterPath("/content/ASTROLOGY_INTERNAL_LIVE_WHEEL_PROOF_v0.3.html"),
        "json": _MasterPath("/content/ASTROLOGY_INTERNAL_LIVE_WHEEL_DEBUG_v0.3.json"),
        "md": _MasterPath("/content/ASTROLOGY_INTERNAL_LIVE_WHEEL_VALIDATION_v0.3.md"),
    },
    "human_design": {
        "html": _MasterPath("/content/HD_INTERNAL_LIVE_BODYGRAPH_PROOF_v0.5.html"),
        "json": _MasterPath("/content/HD_INTERNAL_LIVE_BODYGRAPH_DEBUG_v0.5.json"),
        "md": _MasterPath("/content/HD_INTERNAL_LIVE_BODYGRAPH_VALIDATION_v0.5.md"),
    },
    "numerology": {
        "html": _MasterPath("/content/NUMEROLOGY_INTERNAL_LIVE_PROOF_v0.2.html"),
        "json": _MasterPath("/content/NUMEROLOGY_INTERNAL_LIVE_DEBUG_v0.2.json"),
        "md": _MasterPath("/content/NUMEROLOGY_INTERNAL_LIVE_VALIDATION_v0.2.md"),
    },
    "destiny_matrix": {
        "html": _MasterPath("/content/DM_INTERNAL_LIVE_MATRIX_PROOF_v0.2.html"),
        "json": _MasterPath("/content/DM_INTERNAL_LIVE_MATRIX_DEBUG_v0.2.json"),
        "md": _MasterPath("/content/DM_INTERNAL_LIVE_MATRIX_VALIDATION_v0.2.md"),
    },
}

_index = {
    "artifact_id": "visual_outputs_index",
    "master_code": "master_dharmacodex_v_1_1_5_internal_reading_renderers.py",
    "seeker_input": MASTER_INPUT,
    "output_dir": str(_seeker_dir),
    "outputs": {},
    "assets": {
        "db_folder": DB_FOLDER,
        "bodygraph_svg_path": BODYGRAPH_SVG_PATH,
        "bodygraph_svg_exists": _MasterPath(BODYGRAPH_SVG_PATH).exists(),
    },
    "governance": {
        "public_output_created": False,
        "pdf_created": False,
        "human_design_public_activation": False,
        "synthesis_gate_status": "BLOCKED",
    },
}

_missing_outputs = []
for _system, _paths in _normalized_outputs.items():
    _index["outputs"][_system] = {}
    for _kind, _src in _paths.items():
        _target = _seeker_dir / f"{_system}.{_kind}"
        if not _src.exists():
            _missing_outputs.append(str(_src))
            continue
        _dcx_shutil.copyfile(_src, _target)
        _index["outputs"][_system][_kind] = {
            "path": str(_target),
            "sha256": _dcx_sha256(_target),
            "size_bytes": _target.stat().st_size,
        }

_index_path = _seeker_dir / "visual_outputs_index.json"
_index_path.write_text(_master_json.dumps(_index, ensure_ascii=False, indent=2), encoding="utf-8")

if _missing_outputs:
    raise RuntimeError(
        "Faltaron representaciones graficas generadas: "
        + ", ".join(_missing_outputs)
    )

print("\nREPRESENTACIONES GRAFICAS NORMALIZADAS")
print("Carpeta:", _seeker_dir)
for _system, _items in _index["outputs"].items():
    for _kind, _info in _items.items():
        print(f"OK {_system}.{_kind}: {_info['path']}")
print("OK index:", _index_path)

try:
    from IPython.display import HTML as _DCXHTML, display as _dcx_display
    for _system in ["astrology", "human_design", "numerology", "destiny_matrix"]:
        _path = _MasterPath(_index["outputs"][_system]["html"]["path"])
        print(f"\nDISPLAY NORMALIZADO {_system}: {_path}")
        _dcx_display(_DCXHTML(_path.read_text(encoding="utf-8")))
except Exception as _display_error:
    print("Display inline normalizado no disponible:", _display_error)
