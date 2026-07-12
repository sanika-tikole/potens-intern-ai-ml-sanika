from __future__ import annotations

import logging
import re


try:  # pragma: no cover - optional dependency fallback
    from langdetect import DetectorFactory, detect
except ImportError:  # pragma: no cover - optional dependency fallback
    DetectorFactory = None  # type: ignore[assignment]

    def detect(text: str) -> str:  # type: ignore[no-redef]
        return "en"

from app.services.llm_client import GroqLLMClient, generate_text

if DetectorFactory is not None:
    DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGE_CODES = {"en", "hi", "mr"}
LANGUAGE_LABELS = {"en": "English", "hi": "Hindi", "mr": "Marathi"}
QA_TRANSLATION_SYSTEM_PROMPT = (
    "You are a precise translation engine. Preserve meaning, names, numbers, and formatting. "
    "Return only the translated text."
)


def _normalize_language_code(language: str | None) -> str:
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


def _contains_devanagari(text: str) -> bool:
    return bool(re.search(r"[\u0900-\u097F]", text))


def _looks_marathi(text: str) -> bool:
    lowered = f" {text.lower()} "
    marathi_markers = (" ??? ", " ???? ", " ???? ", " ?????????? ", " ?????? ", " ????? ", " ?? ")
    hindi_markers = (" ?? ", " ??? ", " ???? ", " ?? ??? ", " ??? ", " ?? ")
    marathi_hits = sum(1 for marker in marathi_markers if marker in lowered)
    hindi_hits = sum(1 for marker in hindi_markers if marker in lowered)
    return marathi_hits > hindi_hits


def detect_language(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return "en"

    if _contains_devanagari(cleaned):
        try:
            detected = detect(cleaned)
        except Exception:
            detected = ""
        language = _normalize_language_code(detected)
        if language in {"hi", "mr"}:
            return language
        return "mr" if _looks_marathi(cleaned) else "hi"

    try:
        detected = detect(cleaned)
        language = _normalize_language_code(detected)
        if language in {"hi", "mr"}:
            return language
    except Exception:
        pass

    lowered = cleaned.lower()
    if " hindi" in lowered or lowered.startswith("hindi") or "in hindi" in lowered:
        return "hi"
    if " marathi" in lowered or lowered.startswith("marathi") or "in marathi" in lowered:
        return "mr"

    return "en"


def _translate(text: str, *, source_lang: str, target_lang: str) -> str:
    source_lang = _normalize_language_code(source_lang)
    target_lang = _normalize_language_code(target_lang)
    if not text.strip() or source_lang == target_lang:
        return text

    source_name = LANGUAGE_LABELS.get(source_lang, source_lang)
    target_name = LANGUAGE_LABELS.get(target_lang, target_lang)

    logger.info(
        "translation_request source_lang=%s target_lang=%s preview=%r",
        source_lang,
        target_lang,
        text[:200],
    )

    primary_prompt = (
        f"Translate the following text from {source_name} to {target_name}. "
        f"Return only the translated text. Do not keep the original language.\n\nText:\n{text}"
    )
    translated = generate_text(
        primary_prompt,
        system_prompt=(
            f"You are a strict translation engine. Translate from {source_name} to {target_name}. "
            "Never answer in the source language. Return only the translated text."
        ),
        temperature=0.0,
    ).strip()

    if not translated:
        return text

    if target_lang in {"hi", "mr"} and not _contains_devanagari(translated):
        retry_prompt = (
            f"Rewrite the following translation so that it is entirely in {target_name}. "
            "Do not leave any English words unless they are names, numbers, or policy codes.\n\n"
            f"Text:\n{translated}"
        )
        translated = generate_text(
            retry_prompt,
            system_prompt=(
                f"You ensure the final output is fully in {target_name}. "
                "Do not return English when a non-English target language is requested."
            ),
            temperature=0.0,
        ).strip() or translated

    logger.info(
        "translation_result source_lang=%s target_lang=%s localized=%s preview=%r",
        source_lang,
        target_lang,
        _contains_devanagari(translated) if target_lang in {"hi", "mr"} else True,
        translated[:200],
    )
    return translated or text


def translate_to_english(text: str, source_lang: str) -> str:
    if _normalize_language_code(source_lang) == "en":
        return text
    return _translate(text, source_lang=source_lang, target_lang="en")


def translate_from_english(text: str, target_lang: str) -> str:
    target_lang = _normalize_language_code(target_lang)
    if target_lang == "en":
        return text
    return _translate(text, source_lang="en", target_lang=target_lang)


def normalize_query_to_english(user_query: str) -> tuple[str, str]:
    source_lang = detect_language(user_query)
    if source_lang == "en":
        return user_query, source_lang
    return translate_to_english(user_query, source_lang), source_lang


class TranslationService:
    """Backward-compatible translation helper for the existing service layer."""

    def __init__(self, llm_client: GroqLLMClient | None = None) -> None:
        self.llm_client = llm_client

    def detect_language(self, text: str) -> str:
        return detect_language(text)

    def translate_to_english(self, text: str, source_lang: str) -> str:
        if self.llm_client is None:
            return translate_to_english(text, source_lang)
        return translate_to_english(text, source_lang)

    def translate_from_english(self, text: str, target_lang: str) -> str:
        if self.llm_client is None:
            return translate_from_english(text, target_lang)
        return translate_from_english(text, target_lang)

    def normalize_query_to_english(self, user_query: str) -> tuple[str, str]:
        return normalize_query_to_english(user_query)

    def translate(self, text: str, *, source_language: str, target_language: str) -> str:
        source_language = _normalize_language_code(source_language)
        target_language = _normalize_language_code(target_language)
        if source_language == target_language:
            return text
        if target_language == "en":
            return self.translate_to_english(text, source_language)
        if source_language == "en":
            return self.translate_from_english(text, target_language)
        return _translate(text, source_lang=source_language, target_lang=target_language)
