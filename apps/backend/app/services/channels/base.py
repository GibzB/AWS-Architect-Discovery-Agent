"""Channel abstraction layer — base types."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class Action:
    """A button-like choice offered to the customer in a message.

    Channels render this differently: SMS shows a numbered option, RCS shows a
    suggested-reply chip, email shows a labelled item.
    """

    id: str
    label: str


@dataclass
class OutboundMessage:
    """A channel-agnostic outbound message."""

    text: str
    subject: str | None = None
    html: str | None = None
    actions: list[Action] = field(default_factory=list)


@dataclass
class SendResult:
    """Result of a send attempt.

    `sandbox` is True when the message was recorded instead of actually sent
    (SANDBOX_MODE or missing channel configuration).
    """

    channel: str
    recipient_masked: str
    message_id: str | None
    sandbox: bool
    ok: bool = True
    error: str | None = None


def mask_recipient(recipient: str) -> str:
    """Mask a phone number or email for safe logging (never log raw PII)."""
    if not recipient:
        return "(none)"
    if "@" in recipient:
        local, _, domain = recipient.partition("@")
        shown = local[:2] if len(local) > 2 else local[:1]
        return f"{shown}***@{domain}"
    digits = [c for c in recipient if c.isdigit()]
    if len(digits) >= 4:
        return "***" + "".join(digits[-4:])
    return "***"


class Channel(ABC):
    """Interface implemented by every channel adapter."""

    name: str = "base"

    @abstractmethod
    def send(self, recipient: str, message: OutboundMessage) -> SendResult:
        """Send `message` to `recipient` over this channel.

        Implementations never raise on an ordinary send failure — they return a
        SendResult with ok=False and an error, so a messaging problem can never
        crash a workshop. They may raise on programmer error (empty recipient).
        """
        raise NotImplementedError

    def _actions_as_text(self, message: OutboundMessage) -> str:
        """Render actions as numbered options appended to the text body."""
        if not message.actions:
            return message.text
        lines = [message.text, ""]
        for i, action in enumerate(message.actions, start=1):
            lines.append(f"{i}. {action.label}")
        lines.append("")
        lines.append("Reply with a number or a short message.")
        return "\n".join(lines)
