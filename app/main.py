from __future__ import annotations

from fastapi import FastAPI

from app.config import settings
from app.routes.ask import router as ask_router
from app.routes.contradict import router as contradict_router
from app.routes.ingest import router as ingest_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_title, description=settings.app_description)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(ask_router)
    app.include_router(contradict_router)
    app.include_router(ingest_router)
    return app


app = create_app()
