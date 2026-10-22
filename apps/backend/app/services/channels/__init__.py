"""
Channel abstraction layer for AWS Communication Developer Services (CDS).

Every outbound message in Atlas goes through a Channel adapter, keeping the
engagement logic channel-agnostic: Amazon SES (email), AWS End User Messaging
(SMS / RCS) and, in future, End User Messaging Social (WhatsApp) are all
interchangeable implementations of the same interface.

Public API:
    get_channel(name) -> Channel     # resolve an adapter (sandbox-aware)
    OutboundMessage, Action          # channel-agnostic message types
    SendResult                       # send outcome
    SANDBOX_OUTBOX                   # recorded sends in SANDBOX_MODE
"""

from .base import Action, Channel, OutboundMessage, SendResult, mask_recipient
from .factory import SANDBOX_OUTBOX, get_channel, sandbox_enabled

__all__ = [
    "Action",
    "Channel",
    "OutboundMessage",
    "SendResult",
    "mask_recipient",
    "get_channel",
    "sandbox_enabled",
    "SANDBOX_OUTBOX",
]
