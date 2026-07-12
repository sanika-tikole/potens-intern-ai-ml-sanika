from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Pydantic settings container for import-safe app configuration."""

    project_root: Path = PROJECT_ROOT
    groq_api_key: str = ""
    chroma_db_dir: str = "vectorstore/chroma_db"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 4
    use_embeddings: bool = False
    supported_languages: str = "en,hi,mr"
    app_title: str = "PolicyLens"
    app_description: str = (
        "PolicyLens is a multilingual policy Q&A starter app with placeholder routes "
        "for future RAG and contradiction-checking logic."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="POLICYLENS_",
        extra="ignore",
    )

    @property
    def get_supported_languages(self) -> list[str]:
        return [lang.strip() for lang in self.supported_languages.split(",") if lang.strip()]

    @property
    def raw_docs_dir(self) -> Path:
        return self.project_root / "data" / "raw_docs"

    @property
    def vectorstore_dir(self) -> Path:
        vectorstore_path = Path(self.chroma_db_dir)
        if vectorstore_path.is_absolute():
            return vectorstore_path
        return self.project_root / vectorstore_path

    @property
    def chroma_collection_name(self) -> str:
        return "policylens_chunks"

    def ensure_directories(self) -> None:
        self.raw_docs_dir.mkdir(parents=True, exist_ok=True)
        self.vectorstore_dir.mkdir(parents=True, exist_ok=True)


class AppSettings(Settings):
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")


settings = AppSettings()
