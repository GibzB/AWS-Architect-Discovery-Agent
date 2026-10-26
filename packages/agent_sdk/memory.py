"""Session Memory — single source of truth for all agent state."""

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SessionMemory:
    """The shared memory structure for a discovery workshop session."""

    session_id: str
    status: str = "discovery"  # discovery | architecture | review | complete
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    # Customer profile
    customer: dict[str, Any] = field(default_factory=lambda: {
        "name": "",
        "industry": "",
        "company_size": "",
        "region": "",
    })

    # Requirements
    business_requirements: list[str] = field(default_factory=list)
    technical_requirements: list[str] = field(default_factory=list)

    # Knowledge state
    known_facts: list[dict[str, Any]] = field(default_factory=list)
    unknown_facts: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    risks: list[dict[str, Any]] = field(default_factory=list)

    # Conversation
    conversation_history: list[dict[str, str]] = field(default_factory=list)

    # Architecture
    architecture: dict[str, Any] = field(default_factory=lambda: {
        "services": [],
        "decisions": [],
        "diagram_mermaid": "",
        "cost_estimate": {},
    })

    # Review
    review: dict[str, Any] = field(default_factory=lambda: {
        "status": "pending",
        "findings": [],
        "revision_count": 0,
    })

    # Remaining questions
    questions_remaining: list[dict[str, Any]] = field(default_factory=list)

    # Final deliverables
    deliverables: dict[str, Any] = field(default_factory=lambda: {
        "report_md": "",
        "diagram_url": "",
        "terraform_url": "",
        "json_output": {},
    })

    # Agent execution trace
    agent_trace: list[dict[str, Any]] = field(default_factory=list)

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = _now()

    def add_fact(self, fact: str, source: str = "customer", confidence: float = 1.0) -> None:
        """Add a known fact."""
        self.known_facts.append({
            "fact": fact,
            "source": source,
            "confidence": confidence,
            "added_at": _now(),
        })
        self.touch()

    def add_message(self, role: str, content: str) -> None:
        """Append a message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": _now(),
        })
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary (for DynamoDB storage)."""
        return {
            "session_id": self.session_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "customer": self.customer,
            "business_requirements": self.business_requirements,
            "technical_requirements": self.technical_requirements,
            "known_facts": self.known_facts,
            "unknown_facts": self.unknown_facts,
            "assumptions": self.assumptions,
            "risks": self.risks,
            "conversation_history": self.conversation_history,
            "architecture": self.architecture,
            "review": self.review,
            "questions_remaining": self.questions_remaining,
            "deliverables": self.deliverables,
            "agent_trace": self.agent_trace,
        }
