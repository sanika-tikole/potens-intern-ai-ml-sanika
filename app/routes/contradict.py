from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException, status

from app.schemas.api_models import ContradictRequest, ContradictResponse
from app.services.contradiction_service import check_contradiction as run_contradiction_check

router = APIRouter(prefix="", tags=["contradict"])


@router.post("/contradict", response_model=ContradictResponse)
def check_contradiction(payload: ContradictRequest) -> ContradictResponse:
    try:
        return run_contradiction_check(payload.doc1_id, payload.doc2_id, payload.topic)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to check contradiction.",
        ) from exc
