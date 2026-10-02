import io
import json

from docx import Document
from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _upload(data, name="paper.docx"):
    return {"file": (name, data, DOCX)}


def test_analyze_then_render(paper_bytes, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    res = client.post("/api/analyze", files=_upload(paper_bytes))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ai_used"] is False and body["warnings"]
    labels = [{"index": b["index"], "label": b["label"]} for b in body["blocks"]]
    labels[1]["label"] = "author"  # user correction

    res = client.post(
        "/api/render",
        files=_upload(paper_bytes, "My Paper!.docx"),
        data={"labels": json.dumps(labels), "options": json.dumps({"paper_type": "professional"})},
    )
    assert res.status_code == 200, res.text
    assert res.headers["content-type"] == DOCX
    assert 'filename="My Paper (APA).docx"' in res.headers["content-disposition"]
    assert Document(io.BytesIO(res.content)).paragraphs


def test_rejects_non_docx():
    res = client.post("/api/analyze", files=_upload(b"not a zip", "paper.doc"))
    assert res.status_code == 400
    assert ".docx" in res.json()["detail"]


def test_render_rejects_mismatched_labels(paper_bytes):
    res = client.post("/api/render", files=_upload(paper_bytes),
                      data={"labels": json.dumps([{"index": 0, "label": "title"}])})
    assert res.status_code == 409


def test_rate_limit(paper_bytes, monkeypatch):
    monkeypatch.setattr(main, "analyze_limiter", main.RateLimiter(1, 3600))
    headers = {"x-forwarded-for": "203.0.113.9"}
    assert client.post("/api/analyze", files=_upload(paper_bytes), headers=headers).status_code == 200
    assert client.post("/api/analyze", files=_upload(paper_bytes), headers=headers).status_code == 429
