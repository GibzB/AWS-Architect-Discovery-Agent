"""In-memory session store — will be replaced by DynamoDB in Phase 3."""

import logging
from typing import Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    """Dict-backed session store. Interface matches future DynamoDB implementation."""

    def __init__(self):
        self._sessions: dict[str, dict[str, Any]] = {}

    def create_session(self, session_id: str, customer_name: str, customer_industry: str = "") -> dict[str, Any]:
        """Create a new session with empty memory."""
        session = {
            "session_id": session_id,
            "status": "discovery",
            "created_at": _now(),
            "updated_at": _now(),
            "customer": {
                "name": customer_name,
                "industry": customer_industry,
                "company_size": "",
                "region": "",
            },
            "business_requirements": [],
            "technical_requirements": [],
            "known_facts": [],
            "unknown_facts": [],
            "assumptions": [],
            "risks": [],
            "conversation_history": [],
            "architecture": {
                "services": [],
                "decisions": [],
                "diagram_mermaid": "",
                "cost_estimate": {},
            },
            "review": {
                "status": "pending",
                "findings": [],
                "revision_count": 0,
            },
            "questions_remaining": [],
            "deliverables": {
                "report_md": "",
                "diagram_url": "",
                "terraform_url": "",
                "json_output": {},
            },
            "agent_trace": [],
            # AWS CDS omnichannel engagement state (populated after report delivery)
            "engagement": {},
        }
        self._sessions[session_id] = session
        logger.info(f"Session created: {session_id}")
        return session

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve a session by ID."""
        return self._sessions.get(session_id)

    def update_session(self, session_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Partial update of session fields."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        for key, value in updates.items():
            if key in session:
                session[key] = value
        session["updated_at"] = _now()
        return session

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to conversation history."""
        session = self._sessions.get(session_id)
        if session:
            session["conversation_history"].append({
                "role": role,
                "content": content,
                "timestamp": _now(),
            })
            session["updated_at"] = _now()

    def add_fact(self, session_id: str, fact: str, source: str = "customer", confidence: float = 1.0) -> None:
        """Add a known fact to the session."""
        session = self._sessions.get(session_id)
        if session:
            session["known_facts"].append({
                "fact": fact,
                "source": source,
                "confidence": confidence,
                "added_at": _now(),
            })
            session["updated_at"] = _now()

    def add_trace(self, session_id: str, trace_entry: dict[str, Any]) -> None:
        """Add an agent trace entry."""
        session = self._sessions.get(session_id)
        if session:
            trace_entry["timestamp"] = _now()
            session["agent_trace"].append(trace_entry)

    def list_sessions(self) -> list[str]:
        """List all session IDs."""
        return list(self._sessions.keys())


# ──────────────────────────────────────────────────────────────
# Backend selection
#   SESSION_BACKEND=dynamodb  -> durable DynamoDB store (Lambda-safe)
#   otherwise                 -> in-memory (local dev / tests)
# Both expose the identical interface.
# ──────────────────────────────────────────────────────────────
import os as _os


def _make_store():
    if _os.getenv("SESSION_BACKEND", "memory").lower() == "dynamodb":
        try:
            from app.services.dynamo_store import DynamoSessionStore

            logger.info("Session backend: DynamoDB")
            return DynamoSessionStore()
        except Exception as exc:  # fall back rather than crash the app
            logger.error("DynamoDB store init failed (%s); falling back to in-memory", exc)
    logger.info("Session backend: in-memory")
    return MemoryStore()


# Singleton
memory_store = _make_store()
