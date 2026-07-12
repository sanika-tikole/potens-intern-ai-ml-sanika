from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.api_models import AskRequest, AskResponse
from app.services.qa_service import answer_question

router = APIRouter(prefix="", tags=["ask"])
logger = logging.getLogger(__name__)


@router.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest) -> AskResponse:
    try:
        logger.info("/ask request received question=%s", payload.question)
        return answer_question(payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to answer question.") from exc
