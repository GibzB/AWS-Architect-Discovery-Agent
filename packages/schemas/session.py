"""Pydantic models for session and API schemas."""

from pydantic import BaseModel, Field
from typing import Any
from enum import Enum


class SessionStatus(str, Enum):
    DISCOVERY = "discovery"
    ARCHITECTURE = "architecture"
    REVIEW = "review"
    COMPLETE = "complete"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CreateSessionRequest(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_industry: str | None = None
    mode: str = Field(default="chat", pattern="^(chat|voice)$")


class CreateSessionResponse(BaseModel):
    session_id: str
    status: SessionStatus
    created_at: str
    websocket_url: str | None = None


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    role: str = Field(default="user", pattern="^(user)$")


class AgentTrace(BaseModel):
    planner_decision: str = ""
    agent_invoked: str = ""
    tools_used: list[str] = []
    reasoning: str = ""


class MessageMetadata(BaseModel):
    facts_gathered: int = 0
    questions_remaining: int = 0
    review_status: ReviewStatus | None = None


class SendMessageResponse(BaseModel):
    message_id: str
    content: str
    role: str = "assistant"
    agent_trace: AgentTrace = Field(default_factory=AgentTrace)
    session_status: SessionStatus = SessionStatus.DISCOVERY
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)


class SessionResponse(BaseModel):
    session_id: str
    status: SessionStatus
    created_at: str
    updated_at: str
    customer: dict[str, Any] = {}
    facts_count: int = 0
    questions_remaining: int = 0
    architecture_ready: bool = False
    review_status: ReviewStatus | None = None
    conversation_length: int = 0


class ReportResponse(BaseModel):
    session_id: str
    generated_at: str
    report_markdown: str = ""
    executive_summary: str = ""
    architecture_decisions: list[dict[str, Any]] = []
    services: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []
    cost_estimate: dict[str, Any] = {}
    diagram_mermaid: str = ""
    terraform_snippet: str = ""


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error: ErrorDetail
