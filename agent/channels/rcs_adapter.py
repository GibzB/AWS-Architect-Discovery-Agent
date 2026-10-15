"""
AWS End User Messaging RCS channel adapter (AWS CDS — RCS).

RCS (Rich Communication Services) supports rich cards and suggested replies, but
requires an approved RCS agent, which has onboarding lead time. This adapter is a
documented stub: it implements the `Channel` interface so RCS is a drop-in once an
RCS agent is provisioned, and until then it degrades to an SMS-style text send via
the same `pinpoint-sms-voice-v2` client.

When a brand's RCS agent is available, `send` can be upgraded to deliver a rich
card payload; the call site and the rest of the system do not change.
"""

from __future__ import annotations

import logging
import os

import boto3

from .base import Channel, OutboundMessage, SendResult, mask_recipient

log = logging.getLogger(__name__)

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


class RcsAdapter(Channel):
    """RCS via AWS End User Messaging (stub: text fallback until an RCS agent exists)."""

    name = "rcs"

    def __init__(self, origination_identity: str | None = None, client=None):
        # An RCS agent id / phone pool once provisioned; reuses the SMS identity
        # as a fallback origination for the text-mode send.
        self.origination_identity = origination_identity or os.environ.get(
            "RCS_AGENT_ID", os.environ.get("SMS_ORIGINATION_IDENTITY", "")
        )
        self._client = client

    def _sms(self):
        if self._client is None:
            self._client = boto3.client("pinpoint-sms-voice-v2", region_name=REGION)
        return self._client

    def send(self, recipient: str, message: OutboundMessage) -> SendResult:
        if not recipient:
            raise ValueError("RCS send requires a destination phone number")
        masked = mask_recipient(recipient)

        if not self.origination_identity:
            log.error("[rcs] no RCS_AGENT_ID / SMS identity configured for %s", masked)
            return SendResult(
                channel=self.name, recipient_masked=masked, message_id=None,
                sandbox=False, ok=False, error="RCS/SMS identity not configured",
            )

        # STUB: deliver as text until a brand RCS agent is approved. Upgrading to
        # a rich card payload here is the only change needed later.
        log.info("[rcs] (stub) delivering as text fallback to %s", masked)
        try:
            resp = self._sms().send_text_message(
                DestinationPhoneNumber=recipient,
                OriginationIdentity=self.origination_identity,
                MessageBody=self._actions_as_text(message),
            )
            return SendResult(
                channel=self.name, recipient_masked=masked,
                message_id=resp.get("MessageId"), sandbox=False, ok=True,
            )
        except Exception as exc:
            log.exception("[rcs] send to %s failed: %s", masked, exc)
            return SendResult(
                channel=self.name, recipient_masked=masked, message_id=None,
                sandbox=False, ok=False, error=str(exc),
            )
