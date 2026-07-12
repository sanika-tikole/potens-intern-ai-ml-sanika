from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.schemas.api_models import IngestionSummary

router = APIRouter(prefix="", tags=["ingest"])


def _create_ingestion_service():
    from app.services.ingest import IngestionService

    return IngestionService(settings)


@router.post("/ingest", response_model=IngestionSummary)
def ingest_documents() -> IngestionSummary:
    service = _create_ingestion_service()
    return IngestionSummary(**service.ingest_all())