import io
import json

import pytest

from app.analyzer import AnalysisError, OllamaTicketAnalyzer
from app.config import Settings
from app.models import TicketRequest

VALID_ANALYSIS = {
    "category": "Billing",
    "priority": "P2 High",
    "sentiment": "Angry",
    "confidence": 0.94,
    "summary": "Premium customer reports a duplicate charge and missing plan access.",
    "routing_team": "Billing Operations",
    "tags": ["duplicate-charge", "plan-access", "chargeback-risk"],
    "risk_flags": ["Customer threatens a chargeback."],
    "escalation_required": True,
    "escalation_reason": "Chargeback threats require human review.",
    "next_actions": ["Verify both transaction IDs.", "Check entitlement sync status."],
    "draft_reply": "I understand the urgency and have escalated this for review.",
}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_analyzer_parses_structured_response(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        payload = json.loads(request.data)
        assert payload["model"] == "qwen3:8b"
        assert payload["format"]["title"] == "TicketAnalysis"
        body = {"message": {"content": json.dumps(VALID_ANALYSIS)}}
        return FakeResponse(json.dumps(body).encode())

    monkeypatch.setattr("app.analyzer.urlopen", fake_urlopen)
    analyzer = OllamaTicketAnalyzer(Settings())
    ticket = TicketRequest(subject="Duplicate charge", message="I was charged twice yesterday.")

    result = analyzer.analyze(ticket)

    assert result.category == "Billing"
    assert result.escalation_required is True
    assert result.confidence == 0.94


def test_analyzer_rejects_invalid_output(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse(b'{"message":{"content":"invalid"}}')

    monkeypatch.setattr("app.analyzer.urlopen", fake_urlopen)
    analyzer = OllamaTicketAnalyzer(Settings())

    with pytest.raises(AnalysisError, match="invalid ticket analysis"):
        analyzer.analyze(
            TicketRequest(subject="Access issue", message="I cannot access my paid account.")
        )


def test_analyzer_retries_unsafe_reply(monkeypatch) -> None:
    calls = 0

    def fake_urlopen(request, timeout):
        nonlocal calls
        calls += 1
        analysis = dict(VALID_ANALYSIS)
        analysis["draft_reply"] = (
            "We will resolve this as soon as possible."
            if calls == 1
            else "Our billing team will review the transactions before confirming the outcome."
        )
        body = {"message": {"content": json.dumps(analysis)}}
        return FakeResponse(json.dumps(body).encode())

    monkeypatch.setattr("app.analyzer.urlopen", fake_urlopen)
    analyzer = OllamaTicketAnalyzer(Settings())
    result = analyzer.analyze(
        TicketRequest(subject="Duplicate charge", message="I was charged twice yesterday.")
    )

    assert calls == 2
    assert "before confirming" in result.draft_reply


def test_analyzer_uses_safe_fallback_after_two_unsafe_replies(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        analysis = dict(VALID_ANALYSIS)
        analysis["draft_reply"] = "We will resolve this as soon as possible."
        body = {"message": {"content": json.dumps(analysis)}}
        return FakeResponse(json.dumps(body).encode())

    monkeypatch.setattr("app.analyzer.urlopen", fake_urlopen)
    analyzer = OllamaTicketAnalyzer(Settings())
    result = analyzer.analyze(
        TicketRequest(subject="Duplicate charge", message="I was charged twice yesterday.")
    )

    assert "before any outcome can be confirmed" in result.draft_reply
    assert "human escalation" in result.draft_reply
    assert analyzer._has_unsafe_commitment(result.draft_reply) is False


def test_json_can_be_extracted_from_code_fence() -> None:
    content = f"```json\n{json.dumps(VALID_ANALYSIS)}\n```"
    extracted = OllamaTicketAnalyzer._extract_json(content)
    assert json.loads(extracted)["priority"] == "P2 High"


@pytest.mark.parametrize(
    "reply",
    [
        "We will resolve this as soon as possible.",
        "We will provide an update shortly.",
        "Thank you for waiting while we resolve this matter.",
    ],
)
def test_unsafe_commitments_are_detected(reply: str) -> None:
    assert OllamaTicketAnalyzer._has_unsafe_commitment(reply) is True
