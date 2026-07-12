from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, examples=["What is the leave policy?"])


class Citation(BaseModel):
    source_file: str
    page: int | None = None
    chunk_id: str
    snippet: str


class AskResponse(BaseModel):
    question: str
    answer: str
    language: str
    confidence: float | None = None
    citations: list[Citation] = Field(default_factory=list)


class ContradictRequest(BaseModel):
    doc1_id: str = Field(min_length=1, examples=["policy_a"])
    doc2_id: str = Field(min_length=1, examples=["policy_b"])
    topic: str = Field(min_length=1, examples=["leave policy"])


class ContradictionEvidence(BaseModel):
    doc: str
    page: int | None = None
    chunk_id: str
    snippet: str


class ContradictResponse(BaseModel):
    topic: str
    doc1: str
    doc2: str
    conflict: bool | None = None
    reasoning: str
    evidence: list[ContradictionEvidence] = Field(default_factory=list)


class IngestionSummary(BaseModel):
    documents: int
    chunks: int
    sources: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
