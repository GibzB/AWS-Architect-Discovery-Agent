"""
Conversation state — generic, journey-agnostic persistence.

A ConversationState tracks an ongoing engagement with a customer across channels,
keyed by the customer's identity (not by session or channel). This is the
C-ready seam: the same model drives the discovery follow-up journey today and any
other vertical journey later — only `journey`, `stage`, and `context` change.

Stored in DynamoDB. Contact data is treated as PII: never logged raw, kept to a
minimum, and expired via TTL.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import asdict, dataclass, field

import boto3

log = logging.getLogger(__name__)

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
# Reuse the sessions table by default; conversation items use a distinct PK space.
STATE_TABLE = os.environ.get("CONVERSATION_TABLE", os.environ.get("DYNAMODB_TABLE", "aws-discovery-sessions"))
# Default TTL: 30 days. Keep customer contact data only as long as needed.
STATE_TTL_SECONDS = int(os.environ.get("CONVERSATION_TTL_SECONDS", str(30 * 24 * 3600)))


def make_conversation_id(channel: str, address: str) -> str:
    """Normalize a (channel, address) pair into a stable conversation key.

    e.g. ("sms", "+14155550123") -> "sms:+14155550123"
         ("email", "A@Example.com") -> "email:a@example.com"
    """
    return f"{channel.lower()}:{address.strip().lower()}"


@dataclass
class ConversationState:
    conversation_id: str
    session_id: str = ""
    journey: str = "discovery_followup"
    stage: str = "new"
    channels: dict = field(default_factory=dict)      # {"email": "...", "sms": "+1..."}
    context: dict = field(default_factory=dict)        # report summary, cost notes, etc.
    pending_actions: list = field(default_factory=list)  # [{"id":..., "label":...}]
    history: list = field(default_factory=list)        # [{"role","channel","text"}]
    ttl: int = 0

    def record_turn(self, role: str, channel: str, text: str, max_history: int = 20):
        self.history.append({"role": role, "channel": channel, "text": text})
        if len(self.history) > max_history:
            self.history = self.history[-max_history:]


class ConversationStore:
    """DynamoDB-backed persistence for ConversationState.

    In SANDBOX_MODE (no real table), falls back to an in-memory dict so the full
    flow runs locally without AWS.
    """

    def __init__(self, table_name: str | None = None, resource=None):
        self.table_name = table_name or STATE_TABLE
        self._resource = resource
        self._mem: dict[str, dict] = {}
        self._sandbox = os.environ.get("SANDBOX_MODE", "true").lower() in ("1", "true", "yes")

    def _table(self):
        if self._resource is None:
            self._resource = boto3.resource("dynamodb", region_name=REGION)
        return self._resource.Table(self.table_name)

    def load(self, conversation_id: str) -> ConversationState | None:
        if self._sandbox:
            item = self._mem.get(conversation_id)
            return ConversationState(**item) if item else None
        try:
            resp = self._table().get_item(Key={"session_id": conversation_id})
            item = resp.get("Item")
            if not item:
                return None
            # Strip storage-only attributes not on the dataclass.
            item.pop("record_type", None)
            return ConversationState(**item)
        except Exception as exc:
            log.warning("[state] load %s failed: %s", conversation_id, exc)
            return None

    def save(self, state: ConversationState) -> None:
        state.ttl = int(time.time()) + STATE_TTL_SECONDS
        data = asdict(state)
        if self._sandbox:
            self._mem[state.conversation_id] = data
            log.info("[state] (sandbox) saved %s stage=%s", state.conversation_id, state.stage)
            return
        try:
            # The sessions table PK is `session_id`; store the conversation under it.
            item = dict(data)
            item["session_id"] = state.conversation_id
            item["record_type"] = "conversation"
            self._table().put_item(Item=item)
            log.info("[state] saved %s stage=%s", state.conversation_id, state.stage)
        except Exception as exc:
            log.warning("[state] save %s failed: %s", state.conversation_id, exc)
