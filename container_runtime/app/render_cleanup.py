from __future__ import annotations

import re


_TECHNICAL_PATTERNS = (
    r"PASS_WITH_IMPROVEMENTS_NECESSARY",
    r"Synthesis Gate:\s*BLOCKED",
    r"No synthesis",
    r"No PDF",
    r"HD public activation:\s*false",
    r"Renderer:\s*[^<]+",
    r"Geometry:\s*PASS",
    r"/content/[^<\s]+",
)


def clean_internal_html(document: str) -> str:
    """Remove implementation diagnostics while preserving the master visual."""
    cleaned = re.sub(r'<link[^>]+(?:fonts\.googleapis|fonts\.gstatic)[^>]*>', '', document, flags=re.I)
    cleaned = re.sub(r"@import\s+url\([^;]+fonts\.googleapis[^;]+;", "", cleaned, flags=re.I)
    cleaned = cleaned.replace("Internal Representation Template / Not Public Output", "Internal Reference — Not Public Output")
    cleaned = cleaned.replace("Internal Representation Template / Not Public Output", "Internal Reference — Not Public Output")
    cleaned = re.sub(r"<section class=['\"]warnings['\"][\s\S]*?</section>", "", cleaned, flags=re.I)
    cleaned = re.sub(r"<footer[\s\S]*?</footer>", "", cleaned, flags=re.I)
    for pattern in _TECHNICAL_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.I)
    cleaned = re.sub(r"Lectura pendiente en DB", "Información no disponible", cleaned)
    cleaned = re.sub(r"\s{3,}", " ", cleaned)
    return cleaned.strip()

