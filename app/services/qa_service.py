from __future__ import annotations

import logging
import re

from app.config import settings
from app.schemas.api_models import AskResponse
from app.services.llm_client import generate_text
from app.services.translation_service import normalize_query_to_english, translate_from_english
from app.utils.language_utils import detect_language as utils_detect_language, contains_devanagari as utils_contains_devanagari
from app.utils.citation_formatter import make_citations
from app.utils.prompts import QA_UNSUPPORTED_RESPONSE, SAFE_FALLBACKS, build_qa_prompt
from app.services.retriever import retrieve


logger = logging.getLogger(__name__)

LANGUAGE_LABELS = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}


def _calculate_confidence(chunks: list[dict]) -> float | None:
    """Calculate confidence score as average of chunk scores (0-1 range)."""
    if not chunks:
        return None
    scores = [chunk.get("score", 0) for chunk in chunks]
    valid_scores = [s for s in scores if s is not None and isinstance(s, (int, float))]
    if not valid_scores:
        return None
    avg_score = sum(valid_scores) / len(valid_scores)
    return min(1.0, max(0.0, avg_score))  # Clamp to 0-1 range


def _contains_devanagari(text: str) -> bool:
    return utils_contains_devanagari(text)


def _validate_question(question: str) -> str:
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("question must not be empty")
    return cleaned


def _is_unsupported_answer(answer: str) -> bool:
    normalized = answer.strip()
    if not normalized:
        return True
    lowered = normalized.lower()
    unsupported_markers = (
        QA_UNSUPPORTED_RESPONSE.lower(),
        "i could not answer the question",
        "i cannot answer the question",
        "i can't answer the question",
        "not enough supporting information",
        "insufficient context",
        "cannot determine",
    )
    return any(marker in lowered for marker in unsupported_markers)


def _translate_answer(answer: str, target_language: str) -> str:
    if target_language == "en":
        return answer
    return translate_from_english(answer, target_language)


def _rewrite_answer_via_groq(answer: str, question_en: str, target_language: str) -> str:
    if not answer.strip():
        return answer

    language_label = LANGUAGE_LABELS.get(target_language, target_language)
    rewrite_prompt = (
        "Rewrite the policy answer below into a polished, natural sentence or two. "
        "Do not copy the line verbatim. Do not include section headers or raw numbering unless essential. "
        "Keep the meaning exactly the same. Return the final answer only in the requested language.\n\n"
        f"Question: {question_en}\n"
        f"Target language: {language_label}\n"
        f"Answer to rewrite: {answer}"
    )
    rewritten = generate_text(
        rewrite_prompt,
        system_prompt=(
            "You rewrite grounded policy answers into concise, natural-language responses without adding new facts. "
            "If the target language is Hindi or Marathi, write the final answer fully in that language."
        ),
        temperature=0.0,
    )
    return rewritten.strip() or answer


def _finalize_answer(answer: str, question_en: str, original_language: str) -> str:
    if original_language == "en":
        return answer.strip()

    # If the answer is already in the target language (e.g., LLM generated it directly in Hindi),
    # check if it has Devanagari script
    if original_language in {"hi", "mr"} and utils_contains_devanagari(answer):
        logger.info("answer_already_in_target_language lang=%s has_devanagari=true", original_language)
        return answer.strip()

    # If answer is in English, translate it to target language
    if not utils_contains_devanagari(answer):
        logger.info("answer_in_english_translating_to lang=%s", original_language)
        translated = _translate_answer(answer, original_language).strip()
        if translated and utils_contains_devanagari(translated):
            return translated

    # Last resort: rewrite via LLM for natural phrasing
    localized = _rewrite_answer_via_groq(answer, question_en, original_language).strip()
    if localized and utils_contains_devanagari(localized):
        return localized

    # If all else fails, return the best we have
    return answer.strip()


def _extractive_answer(question: str, retrieved_chunks: list[dict[str, object]]) -> str:
    question_terms = {
        token
        for token in re.findall(r"[a-z0-9]+", question.lower())
        if len(token) > 2
    }
    best_sentence = ""
    best_score = 0

    for chunk in retrieved_chunks:
        text = str(chunk.get("text", "")).strip()
        if not text:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            cleaned_sentence = sentence.strip()
            if not cleaned_sentence:
                continue
            sentence_terms = {
                token
                for token in re.findall(r"[a-z0-9]+", cleaned_sentence.lower())
                if len(token) > 2
            }
            overlap = len(question_terms & sentence_terms)
            numeric_bonus = 1 if re.search(r"\d", cleaned_sentence) else 0
            score = overlap * 2 + numeric_bonus
            if score > best_score:
                best_score = score
                best_sentence = cleaned_sentence

    return best_sentence


def _chunk_relevance_score(question: str, chunk: dict[str, object]) -> int:
    question_terms = {
        token
        for token in re.findall(r"[a-z0-9]+", question.lower())
        if len(token) > 2
    }
    chunk_text = " ".join(
        str(chunk.get(field, ""))
        for field in ("source_file", "doc_id", "text")
    ).lower()
    chunk_terms = {
        token
        for token in re.findall(r"[a-z0-9]+", chunk_text)
        if len(token) > 2
    }
    overlap = len(question_terms & chunk_terms)
    bonus = 0
    if any(keyword in chunk_text for keyword in ("leave", "attendance", "intern", "reimbursement", "grievance")):
        bonus += 2
    if any(token in chunk_terms for token in question_terms if token.isdigit()):
        bonus += 1
    return overlap * 2 + bonus


def _rank_relevant_chunks(question: str, retrieved_chunks: list[dict[str, object]]) -> list[dict[str, object]]:
    ranked = sorted(
        retrieved_chunks,
        key=lambda chunk: (_chunk_relevance_score(question, chunk), float(chunk.get("score", 0.0) or 0.0)),
        reverse=True,
    )
    return ranked


def answer_question(question: str) -> AskResponse:
    validated_question = _validate_question(question)
    question_en, original_language = normalize_query_to_english(validated_question)

    logger.info(
        "ask_service incoming_question=%r detected_language=%s normalized_question=%r",
        validated_question,
        original_language,
        question_en,
    )

    retrieved_chunks = retrieve(question_en, top_k=settings.top_k)
    retrieved_chunks = _rank_relevant_chunks(question_en, retrieved_chunks)
    logger.info("ask_service retrieved_chunks=%d", len(retrieved_chunks))
    for index, chunk in enumerate(retrieved_chunks, start=1):
        logger.debug(
            "ask_service chunk_%d source_file=%s doc_id=%s chunk_id=%s preview=%s",
            index,
            chunk.get("source_file"),
            chunk.get("doc_id"),
            chunk.get("chunk_id"),
            str(chunk.get("text", ""))[:200].replace("\n", " "),
        )

    if not retrieved_chunks:
        logger.info("ask_service_path=fallback reason=no_retrieved_chunks")
        fallback = SAFE_FALLBACKS.get(original_language, SAFE_FALLBACKS["en"])
        return AskResponse(question=validated_question, answer=fallback, language=original_language, confidence=None, citations=[])

    best_relevance = _chunk_relevance_score(question_en, retrieved_chunks[0])
    if best_relevance <= 0:
        logger.info("ask_service_path=fallback reason=low_relevance_top_chunk score=%d", best_relevance)
        fallback = SAFE_FALLBACKS.get(original_language, SAFE_FALLBACKS["en"])
        return AskResponse(question=validated_question, answer=fallback, language=original_language, confidence=None, citations=[])

    extractive_answer = _extractive_answer(question_en, retrieved_chunks[:2])
    if extractive_answer:
        logger.info("ask_service_path=extractive_first reason=top_chunks_have_direct_answer")
        answer = _finalize_answer(extractive_answer, question_en, original_language)
        logger.debug("ask_service_final_answer preview=%s", answer[:1500])
        citations = make_citations(retrieved_chunks)
        logger.debug("ask_service_returned_citations=%s", citations)
        return AskResponse(
            question=validated_question,
            answer=answer,
            language=original_language,
            confidence=_calculate_confidence(retrieved_chunks),
            citations=citations,
        )

    prompt = build_qa_prompt(question_en, retrieved_chunks, target_language=original_language, original_language=original_language)
    logger.debug("ask_service_prompt preview=%s", prompt[:1500])
    
    # Improved system prompt for better language-specific responses
    if original_language in {"hi", "mr"}:
        system_prompt = (
            f"You are a policy expert. Answer ONLY from the provided context. "
            f"You must respond entirely in {LANGUAGE_LABELS.get(original_language, original_language)}. "
            f"Never use the source language (English) in your answer unless for names or numbers."
        )
    else:
        system_prompt = "You answer only from the provided context and never use outside knowledge."
    
    answer_en = generate_text(
        prompt,
        system_prompt=system_prompt,
        temperature=0.0,
    )
    logger.debug("ask_service_raw_llm_response preview=%s", answer_en[:1500])

    if _is_unsupported_answer(answer_en):
        extractive_answer = _extractive_answer(question_en, retrieved_chunks)
        if extractive_answer:
            logger.info("ask_service_path=extractive_rewrite reason=llm_empty_or_unsupported")
            answer = _finalize_answer(extractive_answer, question_en, original_language)
            logger.debug("ask_service_final_answer preview=%s", answer[:1500])
            citations = make_citations(retrieved_chunks)
            logger.debug("ask_service_returned_citations=%s", citations)
            return AskResponse(
                question=validated_question,
                answer=answer,
                language=original_language,
                citations=citations,
            )

        logger.info("ask_service_path=fallback reason=llm_empty_or_unsupported_and_no_extractive_answer")
        fallback = SAFE_FALLBACKS.get(original_language, SAFE_FALLBACKS["en"])
        logger.debug("ask_service_final_answer preview=%s", fallback[:1500])
        return AskResponse(
            question=validated_question,
            answer=fallback,
            language=original_language,
            confidence=_calculate_confidence(retrieved_chunks),
            citations=make_citations(retrieved_chunks),
        )

    logger.info("ask_service_path=llm_answer")
    answer = _finalize_answer(answer_en, question_en, original_language)
    logger.debug("ask_service_final_answer preview=%s", answer[:1500])
    citations = make_citations(retrieved_chunks)
    logger.debug("ask_service_returned_citations=%s", citations)
    return AskResponse(
        question=validated_question,
        answer=answer,
        language=original_language,
        confidence=_calculate_confidence(retrieved_chunks),
        citations=citations,
    )


class QAService:
    """Backward-compatible wrapper for the QA flow."""

    def answer(self, question: str) -> AskResponse:
        return answer_question(question)
