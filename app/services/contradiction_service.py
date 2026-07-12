from __future__ import annotations

import logging

from app.config import settings
from app.schemas.api_models import ContradictResponse
from app.services.llm_client import generate_text
from app.services.retriever import retrieve
from app.services.translation_service import normalize_query_to_english, translate_from_english
from app.utils.citation_formatter import build_contradiction_evidence
from app.utils.language_utils import contains_devanagari
from app.utils.prompts import SAFE_CONTRADICTION_FALLBACKS, build_contradiction_prompt


logger = logging.getLogger(__name__)

LANGUAGE_LABELS = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}


def _validate_input(doc1_id: str, doc2_id: str, topic: str) -> tuple[str, str, str]:
    cleaned_doc1 = doc1_id.strip()
    cleaned_doc2 = doc2_id.strip()
    cleaned_topic = topic.strip()
    if not cleaned_doc1:
        raise ValueError("doc1_id must not be empty")
    if not cleaned_doc2:
        raise ValueError("doc2_id must not be empty")
    if not cleaned_topic:
        raise ValueError("topic must not be empty")
    return cleaned_doc1, cleaned_doc2, cleaned_topic


def _normalize_conflict_label(text: str) -> bool | None:
    lowered = text.lower().strip()
    if not lowered:
        return None

    insufficient_markers = (
        "insufficient",
        "unclear",
        "cannot determine",
        "can't determine",
        "not enough evidence",
        "not enough information",
    )
    if any(marker in lowered for marker in insufficient_markers):
        return None

    negative_markers = (
        "conflict: no",
        "conflict is false",
        "no conflict",
        "does not conflict",
        "consistent",
        "agree",
    )
    if any(marker in lowered for marker in negative_markers):
        return False

    positive_markers = (
        "conflict: yes",
        "conflict is true",
        "conflict",
        "contradict",
        "inconsistent",
        "disagree",
        "opposite",
    )
    if any(marker in lowered for marker in positive_markers):
        return True

    return None


def _translate_reasoning(reasoning: str, target_language: str) -> str:
    if target_language == "en":
        return reasoning
    language_label = LANGUAGE_LABELS.get(target_language, target_language)
    translated = translate_from_english(reasoning, target_language).strip()
    if translated and contains_devanagari(translated):
        return translated

    fallback_prompt = (
        f"Rewrite the reasoning below in {language_label} only. "
        "Do not include English unless it is a proper noun or code.\n\n"
        f"Reasoning: {reasoning}"
    )
    rewritten = generate_text(
        fallback_prompt,
        system_prompt=(
            f"You write concise reasoning fully in {language_label}. "
            "Never return English for a non-English target language."
        ),
        temperature=0.0,
    ).strip()
    return rewritten or translated or reasoning


def _fallback_reasoning(language: str) -> str:
    return SAFE_CONTRADICTION_FALLBACKS.get(language, SAFE_CONTRADICTION_FALLBACKS["en"])


def _retrieve_topic_chunks(doc_id: str, topic_en: str) -> list[dict[str, object]]:
    return retrieve(topic_en, top_k=settings.top_k, doc_id=doc_id)


def check_contradiction(doc1_id: str, doc2_id: str, topic: str) -> ContradictResponse:
    """Compare two documents on a topic and return structured contradiction evidence."""

    cleaned_doc1, cleaned_doc2, cleaned_topic = _validate_input(doc1_id, doc2_id, topic)
    topic_en, language = normalize_query_to_english(cleaned_topic)
    logger.info(
        "contradiction_request doc1=%s doc2=%s topic=%r language=%s normalized_topic=%r",
        cleaned_doc1,
        cleaned_doc2,
        cleaned_topic,
        language,
        topic_en,
    )

    doc1_chunks = _retrieve_topic_chunks(cleaned_doc1, topic_en)
    doc2_chunks = _retrieve_topic_chunks(cleaned_doc2, topic_en)
    logger.info("contradiction_retrieved doc1_chunks=%d doc2_chunks=%d", len(doc1_chunks), len(doc2_chunks))

    doc1_evidence = build_contradiction_evidence(doc1_chunks)
    doc2_evidence = build_contradiction_evidence(doc2_chunks)
    evidence = doc1_evidence + [
        item
        for item in doc2_evidence
        if item.chunk_id not in {e.chunk_id for e in doc1_evidence}
    ]

    if not doc1_chunks or not doc2_chunks:
        return ContradictResponse(
            topic=cleaned_topic,
            doc1=cleaned_doc1,
            doc2=cleaned_doc2,
            conflict=None,
            reasoning=_translate_reasoning(_fallback_reasoning(language), language),
            evidence=evidence,
        )

    prompt = build_contradiction_prompt(topic_en, doc1_chunks, doc2_chunks, target_language=language, original_language=language)
    reasoning_en = generate_text(
        prompt,
        system_prompt=f"You compare two documents using only the provided evidence and return a cautious judgment. Respond entirely in {LANGUAGE_LABELS.get(language, language)}.",
        temperature=0.0,
    )
    logger.info("contradiction_raw_reasoning preview=%r", reasoning_en[:300])

    if not reasoning_en.strip():
        return ContradictResponse(
            topic=cleaned_topic,
            doc1=cleaned_doc1,
            doc2=cleaned_doc2,
            conflict=None,
            reasoning=_translate_reasoning(_fallback_reasoning(language), language),
            evidence=evidence,
        )

    conflict = _normalize_conflict_label(reasoning_en)
    reasoning = _translate_reasoning(reasoning_en, language)
    logger.info("contradiction_final_language=%s preview=%r", language, reasoning[:300])

    return ContradictResponse(
        topic=cleaned_topic,
        doc1=cleaned_doc1,
        doc2=cleaned_doc2,
        conflict=conflict,
        reasoning=reasoning,
        evidence=evidence,
    )


class ContradictionService:
    """Backward-compatible wrapper around the contradiction flow."""

    def check_contradiction(self, doc1_id: str, doc2_id: str, topic: str) -> ContradictResponse:
        return check_contradiction(doc1_id, doc2_id, topic)

    def compare(self, doc1_id: str, doc2_id: str, topic: str) -> ContradictResponse:
        return check_contradiction(doc1_id, doc2_id, topic)
