"""
Two-way inbound handler.

Processes an inbound customer message (an SMS/RCS reply delivered via AWS End
User Messaging -> SNS, or any channel event normalized to the same shape) and
drives one agentic turn:

    verify -> normalize sender -> load state -> classify intent
           -> dispatch action -> reply on the SAME channel -> persist state

Security properties (see docs/SPRINT_PLAN.md threat model):
- The reply is always sent to the address stored on the conversation, never to a
  value taken from the message body.
- The agent only acts on a sender that already has conversation state.
- The intent router returns a fixed action enum; message text never drives a
  privileged operation directly.
"""

from __future__ import annotations

import logging

from channels import OutboundMessage, get_channel, mask_recipient

from .actions import dispatch
from .intent import classify_intent
from .state import ConversationStore, make_conversation_id

log = logging.getLogger(__name__)


class InboundMessage:
    """Normalized inbound event: which channel, who from, what they said."""

    def __init__(self, channel: str, sender: str, text: str):
        self.channel = (channel or "").lower()
        self.sender = (sender or "").strip()
        self.text = text or ""


def process_inbound(msg: InboundMessage, store: ConversationStore | None = None) -> dict:
    """Handle one inbound message. Returns a result dict for logging / tests."""
    store = store or ConversationStore()
    masked = mask_recipient(msg.sender)

    if not msg.channel or not msg.sender:
        log.warning("[inbound] rejected: missing channel/sender")
        return {"ok": False, "reason": "missing channel or sender"}

    conversation_id = make_conversation_id(msg.channel, msg.sender)
    state = store.load(conversation_id)

    if state is None:
        # No prior conversation for this sender — do not act on unsolicited input.
        log.info("[inbound] no conversation state for %s; ignoring", masked)
        return {"ok": False, "reason": "no conversation state", "sender": masked}

    # Classify (agentic) then dispatch to a bounded action handler.
    intent = classify_intent(msg.text)
    state.record_turn("user", msg.channel, msg.text)
    reply_text = dispatch(intent, state)
    state.record_turn("agent", msg.channel, reply_text)

    # Reply on the SAME channel, to the address on record (never the message body).
    reply_to = state.channels.get(msg.channel, msg.sender)
    send_result = get_channel(msg.channel).send(reply_to, OutboundMessage(text=reply_text))

    store.save(state)

    log.info(
        "[inbound] %s action=%s stage=%s replied(ok=%s,sandbox=%s)",
        masked, intent["action"], state.stage, send_result.ok, send_result.sandbox,
    )
    return {
        "ok": True,
        "sender": masked,
        "action": intent["action"],
        "confidence": intent["confidence"],
        "stage": state.stage,
        "reply_sent": send_result.ok,
        "sandbox": send_result.sandbox,
    }


# ── Event parsing (AWS End User Messaging via SNS) ──

def parse_sns_eum_event(event: dict) -> list[InboundMessage]:
    """Parse an SNS-delivered AWS End User Messaging inbound event into
    normalized InboundMessages.

    AWS End User Messaging publishes inbound SMS/RCS to an SNS topic; the SNS
    record's Message is a JSON string containing the origination number and body.
    This parser is defensive: unknown shapes yield no messages rather than raising.
    """
    import json

    messages: list[InboundMessage] = []
    for record in event.get("Records", []):
        sns = record.get("Sns", {})
        raw = sns.get("Message", "")
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            log.warning("[inbound] could not parse SNS message payload")
            continue

        # EUM inbound fields vary by channel; map the common ones defensively.
        sender = (
            payload.get("originationNumber")
            or payload.get("OriginationNumber")
            or payload.get("from")
            or ""
        )
        text = (
            payload.get("messageBody")
            or payload.get("MessageBody")
            or payload.get("body")
            or ""
        )
        channel = (payload.get("messageType") or payload.get("channel") or "sms").lower()
        if channel not in ("sms", "rcs"):
            channel = "sms"
        if sender and text:
            messages.append(InboundMessage(channel=channel, sender=sender, text=text))
    return messages
