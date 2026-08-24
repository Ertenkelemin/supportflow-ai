import json

from app.models import TicketAnalysis, TicketRequest
from app.service import SupportFlowService
from tests.test_analyzer import VALID_ANALYSIS


def test_service_builds_integration_payload(monkeypatch) -> None:
    service = SupportFlowService()
    analysis = TicketAnalysis.model_validate(VALID_ANALYSIS)
    monkeypatch.setattr(service.analyzer, "analyze", lambda ticket: analysis)

    result = service.analyze(
        TicketRequest(subject="Duplicate charge", message="I was charged twice yesterday.")
    )

    assert result.ticket_id.startswith("TKT-")
    assert result.automation_payload.queue == "Billing Operations"
    assert result.automation_payload.requires_human_approval is True


def test_json_export_contains_analysis_and_payload(monkeypatch) -> None:
    service = SupportFlowService()
    analysis = TicketAnalysis.model_validate(VALID_ANALYSIS)
    monkeypatch.setattr(service.analyzer, "analyze", lambda ticket: analysis)
    result = service.analyze(
        TicketRequest(subject="Duplicate charge", message="I was charged twice yesterday.")
    )

    exported = json.loads(service.export_json(result))
    assert exported["analysis"]["category"] == "Billing"
    assert exported["automation_payload"]["escalation_required"] is True

