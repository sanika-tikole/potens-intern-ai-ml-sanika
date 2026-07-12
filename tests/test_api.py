from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_endpoint_returns_grounded_response(monkeypatch) -> None:
    from app.schemas.api_models import AskResponse, Citation
    import app.routes.ask as ask_route

    def fake_answer_question(question: str) -> AskResponse:
        return AskResponse(
            question=question,
            answer="Grounded answer",
            language="en",
            citations=[Citation(source_file="policy.pdf", page=1, chunk_id="chunk-1", snippet="Relevant policy text")],
        )

    monkeypatch.setattr(ask_route, "answer_question", fake_answer_question)

    client = TestClient(create_app())
    response = client.post("/ask", json={"question": "What is the leave policy for interns?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["question"] == "What is the leave policy for interns?"
    assert payload["answer"] == "Grounded answer"
    assert payload["language"] == "en"
    assert payload["citations"][0]["source_file"] == "policy.pdf"


def test_contradict_endpoint_returns_evidence(monkeypatch) -> None:
    from app.schemas.api_models import ContradictResponse, ContradictionEvidence
    import app.routes.contradict as contradict_route

    def fake_check_contradiction(doc1_id: str, doc2_id: str, topic: str) -> ContradictResponse:
        return ContradictResponse(
            topic=topic,
            doc1=doc1_id,
            doc2=doc2_id,
            conflict=True,
            reasoning="The documents conflict on this topic.",
            evidence=[
                ContradictionEvidence(doc=doc1_id, page=1, chunk_id="chunk-1", snippet="Doc 1 says X"),
                ContradictionEvidence(doc=doc2_id, page=1, chunk_id="chunk-2", snippet="Doc 2 says Y"),
            ],
        )

    monkeypatch.setattr(contradict_route, "run_contradiction_check", fake_check_contradiction)

    client = TestClient(create_app())
    response = client.post(
        "/contradict",
        json={"doc1_id": "policy_a", "doc2_id": "policy_b", "topic": "leave"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["conflict"] is True
    assert payload["doc1"] == "policy_a"
    assert len(payload["evidence"]) == 2


def test_extractive_answer_prefers_complete_sentence() -> None:
    from app.services.qa_service import _extractive_answer, _finalize_answer

    chunks = [
        {
            "text": "LEAVE FOR INTERNS 5.1 Interns are eligible for leave only as permitted by the applicable leave policy or",
        },
        {
            "text": "9. INTERNSHIP LEAVE 9.1 Interns are eligible for 1 paid leave day per month. 9.2 Any additional leave requires approval from both the mentor and HR and may be treated as unpaid depending on internship terms.",
        },
    ]

    answer = _extractive_answer("What is the leave policy for interns?", chunks)

    assert _finalize_answer(answer, "What is the leave policy for interns?", "en") == "Interns are eligible for 1 paid leave day per month."
