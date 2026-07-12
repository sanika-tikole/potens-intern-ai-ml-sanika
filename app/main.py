from __future__ import annotations

import logging

from fastapi import FastAPI

from app.config import settings
from app.routes.ask import router as ask_router
from app.routes.contradict import router as contradict_router
from app.routes.ingest import router as ingest_router
from app.services.retriever import inspect_chroma_state


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_title, description=settings.app_description)

    @app.on_event("startup")
    def log_startup_state() -> None:
        state = inspect_chroma_state()
        logger.info(
            "startup_chroma_state path=%s collection=%s path_exists=%s collection_exists=%s",
            state.get("path"),
            state.get("collection_name"),
            state.get("path_exists"),
            state.get("collection_exists"),
        )

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "message": "PolicyLens backend is running.",
            "health": "/health",
            "ask": "/ask",
            "contradict": "/contradict",
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(ask_router)
    app.include_router(contradict_router)
    app.include_router(ingest_router)
    return app


app = create_app()
