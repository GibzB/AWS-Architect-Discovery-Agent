"""
DynamoDB-backed session store.

Drop-in replacement for the in-memory MemoryStore with the same interface, so
the app works correctly on Lambda where each invocation may hit a different
container. Selected at runtime when SESSION_BACKEND=dynamodb (see store.py).

The whole session document is stored as a single item keyed by session_id. The
app's sessions are small (conversation + facts + architecture), well within the
400 KB item limit for a demo. Reads/writes are whole-item for simplicity and
correctness; concurrent writes to the same session are serialized by the
single-request-at-a-time nature of a conversation turn.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3

logger = logging.getLogger(__name__)

REGION = os.getenv("AWS_REGION_NAME", os.getenv("AWS_REGION", "us-east-1"))
TABLE = os.getenv("DYNAMODB_TABLE_NAME", "atlas-discovery-dev-sessions")
# Sessions auto-expire to avoid unbounded growth / stale PII (default 30 days).
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(30 * 24 * 3600)))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_dynamo(obj: Any) -> Any:
    """Recursively convert floats to Decimal (DynamoDB has no float type)."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_dynamo(v) for v in obj]
    return obj


def _from_dynamo(obj: Any) -> Any:
    """Recursively convert Decimal back to int/float for app/JSON use."""
    if isinstance(obj, Decimal):
        # Whole numbers -> int, else float
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    if isinstance(obj, dict):
        return {k: _from_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_dynamo(v) for v in obj]
    return obj


def _new_session_doc(session_id: str, customer_name: str, customer_industry: str) -> dict[str, Any]:
    """Identical shape to MemoryStore.create_session (single source of truth)."""
    return {
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
        "architecture": {"services": [], "decisions": [], "diagram_mermaid": "", "cost_estimate": {}},
        "review": {"status": "pending", "findings": [], "revision_count": 0},
        "questions_remaining": [],
        "deliverables": {"report_md": "", "diagram_url": "", "terraform_url": "", "json_output": {}},
        "agent_trace": [],
        "engagement": {},
    }


class DynamoSessionStore:
    """DynamoDB-backed store with the MemoryStore interface."""

    def __init__(self, table_name: str | None = None, resource=None):
        self.table_name = table_name or TABLE
        self._resource = resource

    def _table(self):
        if self._resource is None:
            self._resource = boto3.resource("dynamodb", region_name=REGION)
        return self._resource.Table(self.table_name)

    def _put(self, session: dict[str, Any]) -> None:
        item = dict(session)
        import time

        item["ttl"] = int(time.time()) + SESSION_TTL_SECONDS
        self._table().put_item(Item=_to_dynamo(item))

    def create_session(self, session_id: str, customer_name: str, customer_industry: str = "") -> dict[str, Any]:
        session = _new_session_doc(session_id, customer_name, customer_industry)
        self._put(session)
        logger.info("Session created (dynamo): %s", session_id)
        return session

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        try:
            resp = self._table().get_item(Key={"session_id": session_id})
        except Exception as exc:
            logger.error("[dynamo] get_session %s failed: %s", session_id, exc)
            return None
        item = resp.get("Item")
        if not item:
            return None
        item = _from_dynamo(item)
        item.pop("ttl", None)
        return item

    def update_session(self, session_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        session = self.get_session(session_id)
        if session is None:
            return None
        # Match MemoryStore semantics but tolerate new top-level keys too, so
        # features like `engagement` persist even on older documents.
        for key, value in updates.items():
            session[key] = value
        session["updated_at"] = _now()
        self._put(session)
        return session

    def add_message(self, session_id: str, role: str, content: str) -> None:
        session = self.get_session(session_id)
        if session is None:
            return
        session["conversation_history"].append({"role": role, "content": content, "timestamp": _now()})
        session["updated_at"] = _now()
        self._put(session)

    def add_fact(self, session_id: str, fact: str, source: str = "customer", confidence: float = 1.0) -> None:
        session = self.get_session(session_id)
        if session is None:
            return
        session["known_facts"].append(
            {"fact": fact, "source": source, "confidence": confidence, "added_at": _now()}
        )
        session["updated_at"] = _now()
        self._put(session)

    def add_trace(self, session_id: str, trace_entry: dict[str, Any]) -> None:
        session = self.get_session(session_id)
        if session is None:
            return
        trace_entry = dict(trace_entry)
        trace_entry["timestamp"] = _now()
        session["agent_trace"].append(trace_entry)
        self._put(session)

    def list_sessions(self) -> list[str]:
        try:
            resp = self._table().scan(ProjectionExpression="session_id")
            return [i["session_id"] for i in resp.get("Items", [])]
        except Exception as exc:
            logger.error("[dynamo] list_sessions failed: %s", exc)
            return []
