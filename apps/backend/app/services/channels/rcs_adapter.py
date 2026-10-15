"""
AWS End User Messaging RCS channel adapter (AWS CDS — RCS).

Stub behind the Channel interface: RCS needs an approved brand agent (onboarding
lead time), so until one exists this degrades to an SMS-style text send via the
same pinpoint-sms-voice-v2 client. When an RCS agent is available, `send` is the
single place to upgrade to a rich-card payload — call sites don't change.
"""

from __future__ import annotations

import logging
import os

import boto3

from .base import Channel, OutboundMessage, SendResult, mask_recipient

log = logging.getLogger(__name__)

REGION = os.getenv("AWS_REGION_NAME", os.getenv("AWS_REGION", "us-east-1"))


class RcsAdapter(Channel):
    """RCS via AWS End User Messaging (stub: text fallback until an agent exists)."""

    name = "rcs"

    def __init__(self, origination_identity: str | None = None, client=None):
        self.origination_identity = origination_identity or os.getenv(
            "RCS_AGENT_ID", os.getenv("SMS_ORIGINATION_IDENTITY", "")
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
            return SendResult(self.name, masked, None, sandbox=False, ok=False,
                              error="RCS/SMS identity not configured")

        log.info("[rcs] (stub) delivering as text fallback to %s", masked)
        try:
            resp = self._sms().send_text_message(
                DestinationPhoneNumber=recipient,
                OriginationIdentity=self.origination_identity,
                MessageBody=self._actions_as_text(message),
            )
            return SendResult(self.name, masked, resp.get("MessageId"), sandbox=False, ok=True)
        except Exception as exc:
            log.exception("[rcs] send to %s failed: %s", masked, exc)
            return SendResult(self.name, masked, None, sandbox=False, ok=False, error=str(exc))
