from typing import Literal

from pydantic import BaseModel, Field

CustomerTier = Literal["Standard", "Premium", "Enterprise"]
ReplyTone = Literal["Professional", "Friendly", "Concise"]
Category = Literal[
    "Billing",
    "Technical",
    "Account Access",
    "Security",
    "Feature Request",
    "General",
]
Priority = Literal["P1 Critical", "P2 High", "P3 Normal", "P4 Low"]
Sentiment = Literal["Positive", "Neutral", "Frustrated", "Angry"]
RoutingTeam = Literal[
    "Billing Operations",
    "Technical Support",
    "Account Support",
    "Security Response",
    "Product Feedback",
    "Customer Support",
]


class TicketRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=300)
    message: str = Field(min_length=20, max_length=12_000)
    customer_tier: CustomerTier = "Standard"
    customer_context: str = Field(default="", max_length=4_000)
    policy_context: str = Field(default="", max_length=6_000)
    reply_tone: ReplyTone = "Professional"


class TicketAnalysis(BaseModel):
    category: Category
    priority: Priority
    sentiment: Sentiment
    confidence: float = Field(ge=0, le=1)
    summary: str
    routing_team: RoutingTeam
    tags: list[str] = Field(min_length=2, max_length=6)
    risk_flags: list[str]
    escalation_required: bool
    escalation_reason: str
    next_actions: list[str] = Field(min_length=1, max_length=6)
    draft_reply: str


class AutomationPayload(BaseModel):
    queue: RoutingTeam
    priority: Priority
    tags: list[str]
    requires_human_approval: bool = True
    escalation_required: bool
    next_actions: list[str]
    draft_reply: str


class AnalysisResult(BaseModel):
    ticket_id: str
    analysis: TicketAnalysis
    automation_payload: AutomationPayload

