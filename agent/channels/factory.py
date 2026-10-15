"""
Channel factory + SANDBOX_MODE recording adapter.

`get_channel(name)` returns the adapter for a channel. When SANDBOX_MODE is on
(or a channel's required configuration is missing), it returns a RecordingChannel
that logs and stores the intended send instead of calling AWS — so the whole flow
is runnable before SES identities / SMS numbers / RCS agents are provisioned.

The real adapters still contain the real boto3 CDS calls; only the sandbox
substitution happens here, at the edge.
"""

from __future__ import annotations

import logging
import os
import uuid

from .base import Channel, OutboundMessage, SendResult, mask_recipient

log = logging.getLogger(__name__)

# Module-level outbox so a test / demo can inspect what would have been sent.
SANDBOX_OUTBOX: list[dict] = []


def sandbox_enabled() -> bool:
    return os.environ.get("SANDBOX_MODE", "true").lower() in ("1", "true", "yes")


class RecordingChannel(Channel):
    """A no-send adapter used in SANDBOX_MODE. Records the intended message."""

    def __init__(self, name: str, reason: str = "SANDBOX_MODE"):
        self.name = name
        self.reason = reason

    def send(self, recipient: str, message: OutboundMessage) -> SendResult:
        masked = mask_recipient(recipient)
        record = {
            "channel": self.name,
            "recipient_masked": masked,
            "subject": message.subject,
            "text": self._actions_as_text(message),
            "actions": [a.id for a in message.actions],
            "reason": self.reason,
        }
        SANDBOX_OUTBOX.append(record)
        log.info("[sandbox:%s] would send to %s: %r", self.name, masked, record["text"][:120])
        return SendResult(
            channel=self.name, recipient_masked=masked,
            message_id=f"sandbox-{uuid.uuid4()}", sandbox=True, ok=True,
        )


# channel name -> (adapter module, class, env var that must be set for a real send)
_REAL_ADAPTERS = {
    "email": ("ses_adapter", "SesAdapter", "SES_SENDER_EMAIL"),
    "sms": ("sms_adapter", "SmsAdapter", "SMS_ORIGINATION_IDENTITY"),
    "rcs": ("rcs_adapter", "RcsAdapter", "SMS_ORIGINATION_IDENTITY"),
}


def get_channel(name: str) -> Channel:
    """Resolve a channel name to an adapter instance.

    Returns a RecordingChannel when SANDBOX_MODE is enabled or the channel's
    required configuration is absent; otherwise the real CDS adapter.
    """
    name = (name or "").lower()
    if name not in _REAL_ADAPTERS:
        raise ValueError(f"Unknown channel: {name!r}")

    module_name, class_name, required_env = _REAL_ADAPTERS[name]

    if sandbox_enabled():
        return RecordingChannel(name, reason="SANDBOX_MODE")

    if not os.environ.get(required_env):
        log.warning(
            "[factory] %s not configured for channel %r; recording instead of sending",
            required_env, name,
        )
        return RecordingChannel(name, reason=f"{required_env} not configured")

    # Import lazily so sandbox/demo runs don't require boto3 clients to construct.
    from importlib import import_module

    module = import_module(f"{__package__}.{module_name}")
    adapter_cls = getattr(module, class_name)
    return adapter_cls()
