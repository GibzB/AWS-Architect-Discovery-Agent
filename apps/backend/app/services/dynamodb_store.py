"""DynamoDB session store — persistent storage for sessions."""

import json
import logging
from typing import Any
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


class _DecimalEncoder(json.JSONEncoder):
    """Handle Decimal types from DynamoDB."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def _convert_floats_to_decimal(obj):
    """Convert floats to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_floats_to_decimal(v) for v in obj]
    return obj


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DynamoDBStore:
    """DynamoDB-backed session store. Falls back to in-memory if DynamoDB unavailable."""

    def __init__(self):
        self._table = None
        self._fallback: dict[str, dict[str, Any]] = {}
        self._use_dynamo = True

    @property
    def table(self):
        if self._table is None:
            try:
                dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
                self._table = dynamodb.Table(settings.dynamodb_table)
                # Test connection
                self._table.table_status
                logger.info(f"Connected to DynamoDB table: {settings.dynamodb_table}")
            except Exception as e:
                logger.warning(f"DynamoDB unavailable ({e}), using in-memory fallback")
                self._use_dynamo = False
        return self._table

    def create_session(self, session_id: str, customer_name: str, customer_industry: str = "") -> dict[str, Any]:
        """Create a new session."""
        session = {
            "session_id": session_id,
            "status": "discovery",
            "created_at": _now(),
            "updated_at": _now(),
            "customer": {"name": customer_name, "industry": customer_industry, "company_size": "", "region": ""},
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
        }

        if self._use_dynamo:
            try:
                self.table.put_item(Item=_convert_floats_to_decimal(session))
            except Exception as e:
                logger.warning(f"DynamoDB put_item failed: {e}")
                self._fallback[session_id] = session
        else:
            self._fallback[session_id] = session

        return session

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve a session."""
        if self._use_dynamo:
            try:
                response = self.table.get_item(Key={"session_id": session_id})
                item = response.get("Item")
                if item:
                    return json.loads(json.dumps(item, cls=_DecimalEncoder))
                return None
            except Exception as e:
                logger.warning(f"DynamoDB get_item failed: {e}")
                return self._fallback.get(session_id)
        return self._fallback.get(session_id)

    def update_session(self, session_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update session fields."""
        session = self.get_session(session_id)
        if session is None:
            return None

        for key, value in updates.items():
            if key in session:
                session[key] = value
        session["updated_at"] = _now()

        if self._use_dynamo:
            try:
                self.table.put_item(Item=_convert_floats_to_decimal(session))
            except Exception as e:
                logger.warning(f"DynamoDB update failed: {e}")
                self._fallback[session_id] = session
        else:
            self._fallback[session_id] = session

        return session

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to conversation history."""
        session = self.get_session(session_id)
        if session:
            session["conversation_history"].append({"role": role, "content": content, "timestamp": _now()})
            session["updated_at"] = _now()
            if self._use_dynamo:
                try:
                    self.table.put_item(Item=_convert_floats_to_decimal(session))
                except Exception:
                    self._fallback[session_id] = session
            else:
                self._fallback[session_id] = session

    def add_trace(self, session_id: str, trace_entry: dict[str, Any]) -> None:
        """Add an agent trace entry."""
        session = self.get_session(session_id)
        if session:
            trace_entry["timestamp"] = _now()
            session["agent_trace"].append(trace_entry)
            if self._use_dynamo:
                try:
                    self.table.put_item(Item=_convert_floats_to_decimal(session))
                except Exception:
                    self._fallback[session_id] = session
            else:
                self._fallback[session_id] = session


# Singleton — automatically uses DynamoDB if available, falls back to in-memory
dynamodb_store = DynamoDBStore()
