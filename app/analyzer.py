from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from app.config import Settings
from app.models import TicketAnalysis, TicketRequest


class AnalysisError(RuntimeError):
    """Raised when a support ticket cannot be analyzed safely."""


class OllamaTicketAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze(self, ticket: TicketRequest) -> TicketAnalysis:
        last_analysis: TicketAnalysis | None = None
        for attempt in range(2):
            system_prompt = self._system_prompt()
            if attempt:
                system_prompt += (
                    " SAFETY RETRY: The previous reply contained an unsupported commitment. "
                    "Rewrite the full analysis and use cautious language about review, verification, "
                    "and possible outcomes. Do not use guarantees or promise a resolution."
                )
            analysis = self._request_analysis(ticket, system_prompt)
            last_analysis = analysis
            if not self._has_unsafe_commitment(analysis.draft_reply):
                return analysis
        assert last_analysis is not None
        return last_analysis.model_copy(
            update={"draft_reply": self._safe_fallback_reply(ticket, last_analysis)}
        )

    def _request_analysis(self, ticket: TicketRequest, system_prompt: str) -> TicketAnalysis:
        payload = {
            "model": self.settings.ollama_model,
            "stream": False,
            "think": False,
            "keep_alive": "10m",
            "format": TicketAnalysis.model_json_schema(),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self._ticket_prompt(ticket)},
            ],
            "options": {"temperature": 0.1, "num_ctx": 8192},
        }
        request = Request(
            f"{self.settings.ollama_base_url.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.settings.ollama_timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["message"]["content"]
            return TicketAnalysis.model_validate_json(self._extract_json(content))
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise AnalysisError(f"Ollama is unavailable: {error}") from error
        except (KeyError, TypeError, json.JSONDecodeError, ValidationError) as error:
            raise AnalysisError("The model returned an invalid ticket analysis. Please retry.") from error

    @staticmethod
    def _extract_json(content: str) -> str:
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            raise json.JSONDecodeError("No JSON object found", text, 0)
        return text[start : end + 1]

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are a senior customer support operations specialist. Analyze and route the "
            "ticket using only the supplied facts. Return only JSON matching the schema. Never "
            "promise a refund, credit, deadline, security outcome, or product change unless the "
            "policy context explicitly allows it. Match the reply language to the customer's "
            "message and follow the requested tone. Draft a helpful reply but keep human approval "
            "required. Security incidents, suspected fraud, legal threats, chargebacks, data loss, "
            "and widespread outages require escalation. Avoid phrases such as 'we will resolve', "
            "'we will ensure', 'we will refund', 'guarantee', and 'as soon as possible'. Keep "
            "the words 'resolve' and 'resolution' out of the customer reply; describe review, "
            "verification, and next steps instead. Keep summaries and actions concise."
        )

    @staticmethod
    def _has_unsafe_commitment(reply: str) -> bool:
        patterns = (
            r"\b(?:we|i) will (?:resolve|fix|refund|credit|guarantee|ensure|activate)\b",
            r"\bas soon as possible\b",
            r"\bguarantee(?:d|s)?\b",
            r"\bwill definitely\b",
            r"\bwill provide an update (?:shortly|soon)\b",
            r"\bwhile we (?:resolve|fix)\b",
            r"\bwill be (?:resolved|fixed|refunded)\b",
            r"\bresolve(?:d|s)?\b",
            r"\bresolution\b",
        )
        return any(re.search(pattern, reply, flags=re.IGNORECASE) for pattern in patterns)

    @staticmethod
    def _safe_fallback_reply(ticket: TicketRequest, analysis: TicketAnalysis) -> str:
        escalated = analysis.escalation_required
        if re.search(r"[А-Яа-яЁё]", ticket.message):
            escalation_text = (
                " Обращение также отмечено для обязательной проверки специалистом."
                if escalated
                else ""
            )
            return (
                "Спасибо, что сообщили о проблеме. Обращение направлено в соответствующую "
                "команду для проверки доступной информации. Перед подтверждением результата "
                "специалисту необходимо проверить данные аккаунта и связанные операции. "
                "Пожалуйста, приложите необходимые идентификаторы, но не отправляйте полные "
                f"платёжные реквизиты.{escalation_text} Ответ будет предоставлен в рамках этого тикета."
            )
        escalation_text = (
            " The case has also been flagged for required human escalation." if escalated else ""
        )
        return (
            "Thank you for reporting this issue. The ticket has been routed to the appropriate "
            "team to review the available information. Account details and related transactions "
            "must be verified before any outcome can be confirmed. Please provide relevant "
            "reference or transaction IDs, but do not share full payment card details."
            f"{escalation_text} A specialist will respond through this ticket."
        )

    @staticmethod
    def _ticket_prompt(ticket: TicketRequest) -> str:
        customer_context = ticket.customer_context.strip() or "No customer history supplied."
        policy_context = ticket.policy_context.strip() or (
            "No policy context supplied. Ask for missing information and avoid firm commitments."
        )
        return (
            f"Customer tier: {ticket.customer_tier}\n"
            f"Preferred reply tone: {ticket.reply_tone}\n"
            f"Customer context: {customer_context}\n"
            f"Support policy context: {policy_context}\n\n"
            f"Ticket subject: {ticket.subject.strip()}\n"
            f"Ticket message:\n{ticket.message.strip()}"
        )
