# app/utils/language_utils.py
"""Utility helpers for language detection, normalization and Devanagari checks.
These are shared across the translation service and the QA pipeline so that the
behaviour is consistent and easy to maintain.
"""

from __future__ import annotations

import re
from typing import Tuple

try:
    from langdetect import DetectorFactory, detect  # type: ignore
except ImportError:  # pragma: no cover - fallback stub for environments without langdetect
    DetectorFactory = None  # type: ignore

    def detect(text: str) -> str:  # type: ignore
        """Fallback detector – always returns English when the library is missing.
        The real detection logic lives in ``detect_language`` which also applies
        Devanagari heuristics.
        """
        return "en"

if DetectorFactory is not None:
    # Ensure deterministic results across runs.
    DetectorFactory.seed = 0

SUPPORTED_LANGUAGE_CODES = {"en", "hi", "mr"}


def _normalize_language_code(language: str | None) -> str:
    """Return a canonical two‑letter language code.
    Accepts full names like ``"Hindi"`` or ``"marathi"`` and normalises them to
    ``"hi"`` / ``"mr"``.  Any unknown value falls back to ``"en"``.
    """
    if not language:
        return "en"
    normalized = language.lower().strip()
    if normalized.startswith("mr"):
        return "mr"
    if normalized.startswith("hi"):
        return "hi"
    if normalized in SUPPORTED_LANGUAGE_CODES:
        return normalized
    return "en"


def contains_devanagari(text: str) -> bool:
    """Return ``True`` if *any* Devanagari Unicode code‑point is present.
    Used to verify that a Hindi/Marathi answer is truly rendered in the target
    script.
    """
    return bool(re.search(r"[\u0900-\u097F]", text))


def _looks_marathi(text: str) -> bool:
    """Heuristic to decide between Hindi and Marathi when the detector is
    ambiguous.  The original implementation used a list of Marathi‑specific
    markers – we keep the same approach.
    """
    lowered = f" {text.lower()} "
    marathi_markers = (
        " ?? ", " ???? ", " ???? ", " ?????????? ", " ?????? ", " ????? ", " ?? "
    )
    hindi_markers = (
        " ?? ", " ??? ", " ???? ", " ?? ??? ", " ??? ", " ?? "
    )
    marathi_hits = sum(1 for marker in marathi_markers if marker in lowered)
    hindi_hits = sum(1 for marker in hindi_markers if marker in lowered)
    return marathi_hits > hindi_hits


def detect_language(text: str) -> str:
    """Detect the language of *text* and return ``"en"``, ``"hi"`` or ``"mr"``.
    The detection proceeds as follows:
    1. If Devanagari characters are present we first try ``langdetect``.
    2. If ``langdetect`` yields ``hi`` or ``mr`` we honour that.
    3. Otherwise we fall back to the Marathi‑vs‑Hindi heuristic.
    4. If no Devanagari characters are found we run ``langdetect`` on the
       whole string and return the normalized code.
    5. Finally explicit keywords ("hindi", "marathi") are checked as a last
       resort.
    """
    cleaned = text.strip()
    if not cleaned:
        return "en"

    # 1️⃣ Devanagari present – try detector first
    if contains_devanagari(cleaned):
        try:
            detected = detect(cleaned)
        except Exception:
            detected = ""
        language = _normalize_language_code(detected)
        if language in {"hi", "mr"}:
            return language
        # Detector was inconclusive – use heuristic
        return "mr" if _looks_marathi(cleaned) else "hi"

    # 2️⃣ No Devanagari – rely on detector
    try:
        detected = detect(cleaned)
        language = _normalize_language_code(detected)
        if language in {"hi", "mr"}:
            return language
    except Exception:
        pass

    # 3️⃣ Keyword fallback (e.g. user typed "question in Hindi")
    lowered = cleaned.lower()
    if " hindi" in lowered or lowered.startswith("hindi") or "in hindi" in lowered:
        return "hi"
    if " marathi" in lowered or lowered.startswith("marathi") or "in marathi" in lowered:
        return "mr"

    return "en"

# Exported names for convenient import
__all__ = [
    "detect_language",
    "contains_devanagari",
    "_normalize_language_code",
]
