from __future__ import annotations

from dataclasses import asdict, is_dataclass
from collections.abc import Iterable
from typing import Any

from app.schemas.api_models import Citation, ContradictionEvidence


def _normalize_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _to_page_number(value: object) -> int | None:
    try:
        page_number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return page_number if page_number > 0 else None


def _truncate_snippet(text: str, max_snippet_chars: int) -> str:
    compact = " ".join(_normalize_text(text).split())
    if len(compact) <= max_snippet_chars:
        return compact
    return compact[: max_snippet_chars - 3].rstrip() + "..."


def make_citation(chunk: dict[str, Any], max_snippet_chars: int = 220) -> dict[str, Any] | None:
    chunk_id = _normalize_text(chunk.get("chunk_id"))
    if not chunk_id:
        return None

    return {
        "source_file": _normalize_text(chunk.get("source_file", "unknown")) or "unknown",
        "page": _to_page_number(chunk.get("page_no", chunk.get("page"))),
        "chunk_id": chunk_id,
        "snippet": _truncate_snippet(chunk.get("text", ""), max_snippet_chars),
    }


def make_citations(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen_chunk_ids: set[str] = set()
    for chunk in chunks:
        citation = make_citation(chunk)
        if citation is None:
            continue
        chunk_id = citation["chunk_id"]
        if chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)
        citations.append(citation)
    return citations


def _chunk_to_dict(chunk: Any) -> dict[str, Any]:
    if isinstance(chunk, dict):
        return chunk
    if is_dataclass(chunk):
        return asdict(chunk)
    if hasattr(chunk, "model_dump"):
        return chunk.model_dump()  # type: ignore[no-any-return]
    if hasattr(chunk, "dict"):
        return chunk.dict()  # type: ignore[no-any-return]
    return {
        key: getattr(chunk, key)
        for key in ("source_file", "page", "page_no", "chunk_id", "text", "doc_id", "score", "distance")
        if hasattr(chunk, key)
    }


def build_citations(chunks: Iterable[Any]) -> list[Citation]:
    citations: list[Citation] = []
    seen_chunk_ids: set[str] = set()
    for chunk in chunks:
        chunk_dict = _chunk_to_dict(chunk)
        citation = make_citation(chunk_dict)
        if citation is None:
            continue
        chunk_id = citation["chunk_id"]
        if chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)
        citations.append(Citation(**citation))
    return citations


def build_contradiction_evidence(chunks: Iterable[Any]) -> list[ContradictionEvidence]:
    evidence: list[ContradictionEvidence] = []
    seen_chunk_ids: set[str] = set()
    for chunk in chunks:
        chunk_dict = _chunk_to_dict(chunk)
        citation = make_citation(chunk_dict)
        if citation is None:
            continue
        chunk_id = citation["chunk_id"]
        if chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)
        evidence.append(
            ContradictionEvidence(
                doc=citation["source_file"],
                page=citation["page"],
                chunk_id=chunk_id,
                snippet=citation["snippet"],
            )
        )
    return evidence
