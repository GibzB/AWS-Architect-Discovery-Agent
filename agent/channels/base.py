"""
Channel abstraction layer — base types.

Every outbound message in the system goes through a Channel adapter. This keeps
the engagement logic channel-agnostic: SES (email), AWS End User Messaging
(SMS / RCS) and, in future, End User Messaging Social (WhatsApp) are all
interchangeable implementations of the same `Channel` interface.

Adding a new channel = adding a new adapter class. No call site changes.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class Action:
    """A button-like choice offered to the customer in a message.

    Channels render this differently: SMS shows a numbered option, RCS shows a
    suggested-reply chip, email shows a labelled link/button.
    """

    id: str
    label: str


@dataclass
class OutboundMessage:
    """A channel-agnostic outbound message.

    Attributes:
        text: The plain-text body. Always required; used verbatim for SMS and as
            the fallback for richer channels.
        subject: Email subject line. Ignored by non-email channels.
        html: Optional HTML body for email. Falls back to `text` if absent.
        actions: Optional choices to present (rendered per channel).
    """

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
    # phone-like: keep last 4 digits
    digits = [c for c in recipient if c.isdigit()]
    if len(digits) >= 4:
        return "***" + "".join(digits[-4:])
    return "***"


class Channel(ABC):
    """Interface implemented by every channel adapter."""

    #: short channel name, e.g. "email", "sms", "rcs", "whatsapp"
    name: str = "base"

    @abstractmethod
    def send(self, recipient: str, message: OutboundMessage) -> SendResult:
        """Send `message` to `recipient` over this channel.

        Implementations must never raise on an ordinary send failure — they
        return a `SendResult` with ok=False and an error string, so a messaging
        problem can never crash the conversation. They may still raise on
        programmer error (e.g. an empty recipient).
        """
        raise NotImplementedError

    def _actions_as_text(self, message: OutboundMessage) -> str:
        """Render actions as numbered options appended to the text body.

        Shared helper for text-only channels (SMS) and fallbacks.
        """
        if not message.actions:
            return message.text
        lines = [message.text, ""]
        for i, action in enumerate(message.actions, start=1):
            lines.append(f"{i}. {action.label}")
        lines.append("")
        lines.append("Reply with a number or a short message.")
        return "\n".join(lines)
