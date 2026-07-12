from __future__ import annotations

from pathlib import Path
from typing import Any

import tomllib
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
        extra="ignore"
    )

    # Groq API key might not have prefix, so map it explicitly or allow fallback
    # We will let pydantic handle `groq_api_key` without prefix by using Field if necessary,
    # but since it's defined in .env as GROQ_API_KEY, we should configure it.
    
    # We can just define an alias if needed, or use a property.
    # Actually, pydantic-settings allows overriding field env names.

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


# We need to map groq_api_key specifically because it lacks the prefix
from pydantic import Field

class AppSettings(Settings):
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")



def _load_streamlit_secrets() -> dict[str, Any]:
    secrets_path = PROJECT_ROOT / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return {}

    with secrets_path.open("rb") as secrets_file:
        raw_secrets = tomllib.load(secrets_file)

    return {
        "groq_api_key": raw_secrets.get("GROQ_API_KEY", ""),
        "chroma_db_dir": raw_secrets.get("POLICYLENS_CHROMA_DB_DIR", "vectorstore/chroma_db"),
        "embedding_model_name": raw_secrets.get(
            "POLICYLENS_EMBEDDING_MODEL_NAME",
            "sentence-transformers/all-MiniLM-L6-v2",
        ),
        "chunk_size": raw_secrets.get("POLICYLENS_CHUNK_SIZE", 800),
        "chunk_overlap": raw_secrets.get("POLICYLENS_CHUNK_OVERLAP", 120),
        "top_k": raw_secrets.get("POLICYLENS_TOP_K", 4),
        "supported_languages": raw_secrets.get("POLICYLENS_SUPPORTED_LANGUAGES", "en,hi,mr"),
        "app_title": raw_secrets.get("POLICYLENS_APP_TITLE", "PolicyLens"),
        "app_description": raw_secrets.get(
            "POLICYLENS_APP_DESCRIPTION",
            "PolicyLens is a multilingual policy Q&A starter app with placeholder routes for future RAG and contradiction-checking logic.",
        ),
    }


settings = AppSettings(**_load_streamlit_secrets())
