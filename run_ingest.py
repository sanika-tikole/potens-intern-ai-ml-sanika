from __future__ import annotations

from app.config import settings
from app.services.ingest import IngestionService


if __name__ == "__main__":
    settings.ensure_directories()
    summary = IngestionService(settings).ingest_all()
    print(summary)
