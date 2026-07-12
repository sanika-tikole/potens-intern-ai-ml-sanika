from __future__ import annotations

from typing import Any

QA_UNSUPPORTED_RESPONSE = "I could not find enough supporting information in the documents."

ANSWER_PROMPT = """You are PolicyLens, a careful document question answering assistant.
Answer only from the provided context. Do not use outside knowledge.
If the answer is unsupported, respond exactly with:
{unsupported_response}
You MUST answer in {target_language}. {language_instruction}
Question in English: {question_en}
Original question: {question_original}

Context:
{context}

Return a concise, natural-sounding answer in 1-3 sentences.
Do not copy lines verbatim from the context.
Do not quote the document line by line or reproduce section headers.
Paraphrase the policy into a clean sentence while keeping the meaning exact.
If the answer is unsupported, return the exact fallback sentence and nothing else.
Always respond entirely in {target_language}. Do not mix languages."""

CONTRADICTION_PROMPT = """You are PolicyLens, a careful policy analyst.
Compare the two document excerpts on the requested topic.
Use only the provided evidence.
Decide whether the documents conflict, do not conflict, or whether the evidence is insufficient.
Write the reasoning in {target_language}.
Topic in English: {topic_en}
Original topic: {topic_original}

Document 1 evidence:
{doc1_context}

Document 2 evidence:
{doc2_context}

Return a short judgment first, then explain the evidence for each document clearly.
"""

SAFE_FALLBACKS = {
    "en": QA_UNSUPPORTED_RESPONSE,
    "hi": "मुझे सुरक्षित रूप से उत्तर देने के लिए पर्याप्त संदर्भ नहीं मिला।",
    "mr": "मला सुरक्षितपणे उत्तर देण्यासाठी पुरेसा संदर्भ मिळाला नाही।",
}

SAFE_CONTRADICTION_FALLBACKS = {
    "en": "The evidence is insufficient to confidently determine whether the documents conflict on this topic.",
    "hi": "इस विषय पर दस्तावेजों में टकराव है या नहीं, यह तय करने के लिए पर्याप्त प्रमाण नहीं हैं।",
    "mr": "या विषयावर दस्तऐवजांमध्ये विरोध आहे का हे ठरवण्यासाठी पुरेसा पुरावा नाही।",
}


def _normalize_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _format_chunk(index: int, chunk: dict[str, Any]) -> str:
    source_file = _normalize_text(chunk.get("source_file", "unknown"))
    doc_id = _normalize_text(chunk.get("doc_id", "unknown"))
    page_no = chunk.get("page_no")
    chunk_id = _normalize_text(chunk.get("chunk_id", "unknown"))
    text = _normalize_text(chunk.get("text", ""))
    score = chunk.get("score")
    distance = chunk.get("distance")
    metadata_bits = [f"doc_id={doc_id}", f"source_file={source_file}", f"chunk_id={chunk_id}"]
    if page_no is not None:
        metadata_bits.insert(2, f"page_no={page_no}")
    if score is not None:
        metadata_bits.append(f"score={score}")
    if distance is not None:
        metadata_bits.append(f"distance={distance}")
    header = f"[{index}] " + " | ".join(metadata_bits)
    return f"{header}\n{text}".strip()


def _build_context_block(context_chunks: list[dict[str, Any]]) -> str:
    if not context_chunks:
        return "No supporting excerpts were retrieved."
    return "\n\n".join(_format_chunk(index, chunk) for index, chunk in enumerate(context_chunks, start=1))


def build_qa_prompt(question: str, context_chunks: list[dict], target_language: str = "English", original_language: str = "en") -> str:
    context = _build_context_block(context_chunks)
    
    # Language-specific instructions
    language_map = {
        "en": "English",
        "hi": "Hindi",
        "mr": "Marathi",
    }
    
    target_lang_name = language_map.get(target_language, target_language)
    
    # Devanagari script languages need explicit instruction
    language_instruction = ""
    if target_language in {"hi", "mr"}:
        script_name = "Devanagari" if target_language == "hi" else "Devanagari"
        language_instruction = f"Write EVERY word in {script_name} script. No English words except names/numbers/policy codes."
    
    return ANSWER_PROMPT.format(
        unsupported_response=QA_UNSUPPORTED_RESPONSE,
        target_language=target_lang_name,
        language_instruction=language_instruction,
        question_en=question,
        question_original=question,
        context=context,
    )


def build_contradiction_prompt(topic: str, doc1_chunks: list[dict], doc2_chunks: list[dict], target_language: str = "English", original_language: str = "en") -> str:
    doc1_context = _build_context_block(doc1_chunks)
    doc2_context = _build_context_block(doc2_chunks)
    
    # Language-specific instructions
    language_map = {
        "en": "English",
        "hi": "Hindi",
        "mr": "Marathi",
    }
    
    target_lang_name = language_map.get(target_language, target_language)
    
    # Devanagari script languages need explicit instruction
    language_instruction = ""
    if target_language in {"hi", "mr"}:
        script_name = "Devanagari" if target_language == "hi" else "Devanagari"
        language_instruction = f" Write your reasoning ENTIRELY in {script_name} script, using {target_lang_name} language."
    
    contradiction_prompt = (
        f"""You are an expert document comparison and policy analysis assistant.

Your task is to compare two retrieved document excerpts for a specific topic and determine whether they conflict.

Important:
Base your answer ONLY on the provided evidence.
Do not use outside knowledge.
Do not assume facts that are not present in the retrieved text.

Definition of a conflict:

A conflict exists when the two documents define different rules, requirements, thresholds, values, timelines, responsibilities, permissions, restrictions, eligibility criteria, procedures, or expected actions for the same topic.

A conflict does NOT require one document to explicitly say "the opposite."

If following Document A would cause a person to behave differently than following Document B for the same situation, treat it as a conflict.

Examples of potential conflicts include (not exhaustive):

- Different numerical values
- Different deadlines
- Different notice periods
- Different eligibility requirements
- Different approval authorities
- Different mandatory documents
- Different reimbursement limits
- Different attendance requirements
- Different responsibilities
- Different procedures
- Different penalties
- Different exceptions

Do NOT classify documents as conflicting simply because:
- wording is different
- sentence structure differs
- formatting changes
- additional explanation is included
while the actual rule remains the same.

If there is insufficient evidence in the retrieved excerpts to compare the topic, return:

conflict = null

and explain that there is insufficient evidence.

For every decision:

1. Identify the rule from Document A.
2. Identify the rule from Document B.
3. Compare them objectively.
4. Explain why they are the same or different.
5. Support every conclusion using only the retrieved evidence.

Topic: {topic}

DOCUMENT 1:
{doc1_context}

DOCUMENT 2:
{doc2_context}

Provide your judgment in this format:

CONFLICT = [TRUE / FALSE / NULL]

REASONING:
- Rule in Document 1: [specific rule or "Not found"]
- Rule in Document 2: [specific rule or "Not found"]
- Differences: [specific differences or "No differences" or "Unclear"]
- Conclusion: [Explain why TRUE, FALSE, or NULL]

EVIDENCE:
- From Document 1: [exact quote]
- From Document 2: [exact quote]

{language_instruction}You MUST respond entirely in {target_lang_name}."""
    )
    
    return contradiction_prompt
