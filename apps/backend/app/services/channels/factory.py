"""Channel factory + SANDBOX_MODE recording adapter."""

from __future__ import annotations

import logging
import os
import uuid
from importlib import import_module

from .base import Channel, OutboundMessage, SendResult, mask_recipient

log = logging.getLogger(__name__)

# Module-level outbox so a test / demo can inspect what would have been sent.
SANDBOX_OUTBOX: list[dict] = []


def sandbox_enabled() -> bool:
    return os.getenv("SANDBOX_MODE", "true").lower() in ("1", "true", "yes")


class RecordingChannel(Channel):
    """A no-send adapter used in SANDBOX_MODE. Records the intended message."""

    def __init__(self, name: str, reason: str = "SANDBOX_MODE"):
        self.name = name
        self.reason = reason

    def send(self, recipient: str, message: OutboundMessage) -> SendResult:
        masked = mask_recipient(recipient)
        body = self._actions_as_text(message)
        record = {
            "channel": self.name,
            "recipient_masked": masked,
            "subject": message.subject,
            "text": body,
            "actions": [a.id for a in message.actions],
            "reason": self.reason,
        }
        SANDBOX_OUTBOX.append(record)
        log.info("[sandbox:%s] would send to %s: %r", self.name, masked, body[:120])
        return SendResult(self.name, masked, f"sandbox-{uuid.uuid4()}", sandbox=True, ok=True)


# channel name -> (module, class, env var required for a real send)
_REAL_ADAPTERS: dict[str, tuple[str, str, str]] = {
    "email": ("ses_adapter", "SesAdapter", "SES_SENDER_EMAIL"),
    "sms": ("sms_adapter", "SmsAdapter", "SMS_ORIGINATION_IDENTITY"),
    "rcs": ("rcs_adapter", "RcsAdapter", "SMS_ORIGINATION_IDENTITY"),
}


def get_channel(name: str) -> Channel:
    """Resolve a channel name to an adapter instance (sandbox-aware)."""
    name = (name or "").lower()
    if name not in _REAL_ADAPTERS:
        raise ValueError(f"Unknown channel: {name!r}")

    module_name, class_name, required_env = _REAL_ADAPTERS[name]

    if sandbox_enabled():
        return RecordingChannel(name, reason="SANDBOX_MODE")

    if not os.getenv(required_env):
        log.warning("[factory] %s not configured for channel %r; recording instead of sending",
                    required_env, name)
        return RecordingChannel(name, reason=f"{required_env} not configured")

    module = import_module(f"{__package__}.{module_name}")
    return getattr(module, class_name)()
