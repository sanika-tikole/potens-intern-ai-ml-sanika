from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from typing import Any

from app.config import Settings, settings
from app.utils.errors import RetrievalError


DEFAULT_COLLECTION_NAME = "policylens_chunks"
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievedChunk:
    text: str
    source_file: str
    doc_id: str
    page: int | None
    chunk_id: str
    source_type: str = "unknown"
    score: float = 0.0
    distance: float | None = None

    @property
    def page_no(self) -> int | None:
        return self.page


def _resolve_vectorstore_path() -> Path:
    vectorstore_path = Path(settings.chroma_db_dir)
    if not vectorstore_path.is_absolute():
        vectorstore_path = settings.project_root / vectorstore_path
    return vectorstore_path


def inspect_chroma_state() -> dict[str, Any]:
    vectorstore_path = _resolve_vectorstore_path()
    path_exists = vectorstore_path.exists()
    collection_exists: bool | None = None

    logger.info(
        "chroma_startup_state path=%s collection=%s path_exists=%s",
        vectorstore_path,
        DEFAULT_COLLECTION_NAME,
        path_exists,
    )

    if not path_exists:
        return {
            "path": str(vectorstore_path),
            "path_exists": False,
            "collection_name": DEFAULT_COLLECTION_NAME,
            "collection_exists": False,
        }

    try:
        chromadb = import_module("chromadb")
        client = chromadb.PersistentClient(path=str(vectorstore_path))
        collections = client.list_collections()
        collection_exists = any(getattr(item, "name", None) == DEFAULT_COLLECTION_NAME for item in collections)
    except Exception as exc:
        logger.warning(
            "chroma_startup_state_check_failed path=%s collection=%s reason=%s",
            vectorstore_path,
            DEFAULT_COLLECTION_NAME,
            exc,
        )
        collection_exists = None

    logger.info(
        "chroma_startup_state path=%s collection=%s path_exists=%s collection_exists=%s",
        vectorstore_path,
        DEFAULT_COLLECTION_NAME,
        path_exists,
        collection_exists,
    )
    return {
        "path": str(vectorstore_path),
        "path_exists": path_exists,
        "collection_name": DEFAULT_COLLECTION_NAME,
        "collection_exists": collection_exists,
    }


@lru_cache(maxsize=4)
def _embedding_model(model_name: str):
    try:
        sentence_transformers = import_module("sentence_transformers")
    except Exception:
        return None
    try:
        return sentence_transformers.SentenceTransformer(model_name)
    except Exception:
        return None


def _encode_query(query: str) -> list[float] | None:
    model = _embedding_model(settings.embedding_model_name)
    if model is None:
        return None
    try:
        encoded = model.encode([query], normalize_embeddings=True)
        return encoded[0].tolist()
    except Exception:
        return None


def _to_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _distance_to_score(distance: float | None) -> float:
    if distance is None:
        return 0.0
    return max(0.0, 1.0 - distance)


def _get_collection():
    try:
        chromadb = import_module("chromadb")
    except Exception:
        logger.warning("retriever_path=unavailable reason=chromadb_missing")
        return None

    vectorstore_path = _resolve_vectorstore_path()
    logger.info(
        "retriever_chroma_lookup path=%s collection=%s path_exists=%s",
        vectorstore_path,
        DEFAULT_COLLECTION_NAME,
        vectorstore_path.exists(),
    )
    if not vectorstore_path.exists():
        logger.warning("retriever_path=unavailable vectorstore_path=%s reason=missing_directory", vectorstore_path)
        return None

    try:
        client = chromadb.PersistentClient(path=str(vectorstore_path))
        collections = client.list_collections()
        collection_exists = any(getattr(item, "name", None) == DEFAULT_COLLECTION_NAME for item in collections)
        logger.info(
            "retriever_collection_check path=%s collection=%s exists=%s",
            vectorstore_path,
            DEFAULT_COLLECTION_NAME,
            collection_exists,
        )
        if not collection_exists:
            raise RetrievalError(
                f"Chroma collection '{DEFAULT_COLLECTION_NAME}' was not found at '{vectorstore_path}'. Run ingestion first."
            )
        collection = client.get_collection(name=DEFAULT_COLLECTION_NAME)
        logger.debug(
            "retriever_collection_loaded path=%s collection=%s",
            vectorstore_path,
            DEFAULT_COLLECTION_NAME,
        )
        return collection
    except Exception as exc:
        if isinstance(exc, RetrievalError):
            raise
        logger.exception(
            "retriever_path=unavailable vectorstore_path=%s collection=%s reason=collection_load_failed",
            vectorstore_path,
            DEFAULT_COLLECTION_NAME,
        )
        raise RetrievalError(
            f"Failed to load Chroma collection '{DEFAULT_COLLECTION_NAME}' from '{vectorstore_path}': {exc}"
        ) from exc


def retrieve(query: str, top_k: int = 4, doc_id: str | None = None) -> list[dict[str, Any]]:
    if not query or not query.strip():
        return []

    logger.info("retriever_query query=%r top_k=%d doc_id=%s", query, top_k, doc_id)

    collection = _get_collection()
    if collection is None:
        logger.info("retriever_result_count=0 reason=no_collection")
        return []

    query_embedding = _encode_query(query)
    if query_embedding is None:
        logger.info("retriever_result_count=0 reason=query_embedding_unavailable")
        return []

    where: dict[str, Any] | None = None
    if doc_id:
        where = {"doc_id": {"$eq": doc_id}}

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=max(1, int(top_k)),
            where=where,
        )
    except Exception as exc:
        logger.exception("retriever_query_failed query=%r top_k=%d doc_id=%s", query, top_k, doc_id)
        raise RetrievalError(f"Vector search failed: {exc}") from exc

    ids = results.get("ids", [[]])[0] if results else []
    documents = results.get("documents", [[]])[0] if results else []
    metadatas = results.get("metadatas", [[]])[0] if results else []
    distances = results.get("distances", [[]])[0] if results else []

    chunks: list[dict[str, Any]] = []
    for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
        metadata = metadata or {}
        numeric_distance = _to_float(distance)
        page_no = _to_int(metadata.get("page_no", metadata.get("page")))
        chunk = {
            "doc_id": str(metadata.get("doc_id", doc_id or "unknown")),
            "source_file": str(metadata.get("source_file", "unknown")),
            "page_no": page_no,
            "chunk_id": str(metadata.get("chunk_id", chunk_id)),
            "text": str(text or ""),
            "score": _distance_to_score(numeric_distance),
            "distance": numeric_distance,
        }
        if "source_type" in metadata:
            chunk["source_type"] = str(metadata.get("source_type", "unknown"))
        chunks.append(chunk)

    logger.info("retriever_result_count=%d", len(chunks))
    for index, chunk in enumerate(chunks, start=1):
        logger.debug(
            "retriever_chunk_%d source_file=%s doc_id=%s chunk_id=%s page_no=%s preview=%s",
            index,
            chunk.get("source_file"),
            chunk.get("doc_id"),
            chunk.get("chunk_id"),
            chunk.get("page_no"),
            str(chunk.get("text", ""))[:200].replace("\n", " "),
        )

    return chunks


class ChromaRetriever:
    """Backwards-compatible wrapper around the module-level retrieve helper."""

    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings
        self.embedding_model = _embedding_model(self.settings.embedding_model_name)

    def query(
        self,
        question: str,
        *,
        top_k: int | None = None,
        doc_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        doc_id = doc_ids[0] if doc_ids else None
        chunk_dicts = retrieve(question, top_k=top_k or 4, doc_id=doc_id)
        chunks: list[RetrievedChunk] = []
        for chunk in chunk_dicts:
            chunks.append(
                RetrievedChunk(
                    text=str(chunk.get("text", "")),
                    source_file=str(chunk.get("source_file", "unknown")),
                    doc_id=str(chunk.get("doc_id", "unknown")),
                    page=chunk.get("page_no"),
                    chunk_id=str(chunk.get("chunk_id", "unknown")),
                    source_type=str(chunk.get("source_type", "unknown")),
                    score=float(chunk.get("score", 0.0) or 0.0),
                    distance=_to_float(chunk.get("distance")),
                )
            )
        return chunks
