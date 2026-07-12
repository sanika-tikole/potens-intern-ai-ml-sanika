from __future__ import annotations

from pathlib import Path
from typing import Iterable
from importlib import import_module

from app.config import Settings, settings
from app.services.retriever import ChromaRetriever
from app.utils.chunking import ChunkRecord, chunk_text


class IngestionService:
    """Load raw policy files, chunk them, and persist embeddings to ChromaDB."""

    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings
        self.retriever = ChromaRetriever(app_settings)

    def ingest_all(self) -> dict[str, object]:
        self.settings.ensure_directories()
        chromadb = import_module("chromadb")
        client = chromadb.PersistentClient(path=str(self.settings.vectorstore_dir))
        try:
            client.delete_collection(self.settings.chroma_collection_name)
        except Exception:
            pass
        collection = client.get_or_create_collection(name=self.settings.chroma_collection_name)

        sources = self._iter_sources(self.settings.raw_docs_dir)
        records: list[ChunkRecord] = []
        for source_path in sources:
            records.extend(self._extract_and_chunk(source_path))

        if records:
            embeddings = self.retriever.embedding_model.encode(
                [record.text for record in records],
                normalize_embeddings=True,
            ).tolist()
            collection.add(
                ids=[record.chunk_id for record in records],
                documents=[record.text for record in records],
                embeddings=embeddings,
                metadatas=[
                    {
                        "source_file": record.source_file,
                        "doc_id": record.doc_id,
                        "page": record.page if record.page is not None else -1,
                        "chunk_id": record.chunk_id,
                        "source_type": record.source_type,
                    }
                    for record in records
                ],
            )

        return {
            "documents": len({record.doc_id for record in records}),
            "chunks": len(records),
            "sources": sorted({record.source_file for record in records}),
            "details": {"collection": self.settings.chroma_collection_name},
        }

    def _iter_sources(self, raw_docs_dir: Path) -> Iterable[Path]:
        if not raw_docs_dir.exists():
            return []
        candidates = [path for path in raw_docs_dir.iterdir() if path.suffix.lower() in {".pdf", ".docx", ".txt"}]
        return sorted(candidates)

    def _extract_and_chunk(self, path: Path) -> list[ChunkRecord]:
        doc_id = path.stem
        source_file = path.name
        if path.suffix.lower() == ".pdf":
            return self._extract_pdf(path, doc_id=doc_id, source_file=source_file)
        if path.suffix.lower() == ".docx":
            return self._extract_docx(path, doc_id=doc_id, source_file=source_file)
        return self._extract_txt(path, doc_id=doc_id, source_file=source_file)

    def _extract_pdf(self, path: Path, *, doc_id: str, source_file: str) -> list[ChunkRecord]:
        fitz = import_module("fitz")
        chunks: list[ChunkRecord] = []
        with fitz.open(path) as pdf_document:
            for page_index in range(pdf_document.page_count):
                page = pdf_document.load_page(page_index)
                text = page.get_text("text")
                chunks.extend(
                    chunk_text(
                        text,
                        source_file=source_file,
                        doc_id=doc_id,
                        page=page_index + 1,
                        source_type="pdf",
                    )
                )
        return chunks

    def _extract_docx(self, path: Path, *, doc_id: str, source_file: str) -> list[ChunkRecord]:
        Document = import_module("docx").Document
        document = Document(path)
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        text = "\n".join(paragraphs)
        return chunk_text(text, source_file=source_file, doc_id=doc_id, page=None, source_type="docx")

    def _extract_txt(self, path: Path, *, doc_id: str, source_file: str) -> list[ChunkRecord]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return chunk_text(text, source_file=source_file, doc_id=doc_id, page=None, source_type="txt")
