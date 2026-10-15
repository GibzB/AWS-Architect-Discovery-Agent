"""
Channel abstraction layer for AWS Communication Developer Services.

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
