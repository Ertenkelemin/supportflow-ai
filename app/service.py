from __future__ import annotations

from uuid import uuid4

from app.analyzer import OllamaTicketAnalyzer
from app.config import get_settings
from app.models import AnalysisResult, AutomationPayload, TicketRequest


class SupportFlowService:
    def __init__(self) -> None:
        self.analyzer = OllamaTicketAnalyzer(get_settings())

    def analyze(self, ticket: TicketRequest) -> AnalysisResult:
        analysis = self.analyzer.analyze(ticket)
        payload = AutomationPayload(
            queue=analysis.routing_team,
            priority=analysis.priority,
            tags=analysis.tags,
            escalation_required=analysis.escalation_required,
            next_actions=analysis.next_actions,
            draft_reply=analysis.draft_reply,
        )
        return AnalysisResult(
            ticket_id=f"TKT-{uuid4().hex[:8].upper()}",
            analysis=analysis,
            automation_payload=payload,
        )

    @staticmethod
    def export_json(result: AnalysisResult) -> str:
        return result.model_dump_json(indent=2)


service = SupportFlowService()

