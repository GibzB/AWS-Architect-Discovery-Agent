"""AWS End User Messaging SMS channel adapter (AWS CDS — SMS)."""

from __future__ import annotations

import logging
import os

import boto3

from .base import Channel, OutboundMessage, SendResult, mask_recipient

log = logging.getLogger(__name__)

REGION = os.getenv("AWS_REGION_NAME", os.getenv("AWS_REGION", "us-east-1"))
MAX_SMS_CHARS = 1200


class SmsAdapter(Channel):
    """SMS via AWS End User Messaging (pinpoint-sms-voice-v2.send_text_message)."""

    name = "sms"

    def __init__(self, origination_identity: str | None = None, client=None):
        self.origination_identity = origination_identity or os.getenv("SMS_ORIGINATION_IDENTITY", "")
        self._client = client

    def _sms(self):
        if self._client is None:
            self._client = boto3.client("pinpoint-sms-voice-v2", region_name=REGION)
        return self._client

    def _body(self, message: OutboundMessage) -> str:
        text = self._actions_as_text(message)
        if len(text) > MAX_SMS_CHARS:
            text = text[: MAX_SMS_CHARS - 1] + "\u2026"
        return text

    def send(self, recipient: str, message: OutboundMessage) -> SendResult:
        if not recipient:
            raise ValueError("SMS send requires a destination phone number")
        masked = mask_recipient(recipient)

        if not self.origination_identity:
            log.error("[sms] SMS_ORIGINATION_IDENTITY not configured; cannot send to %s", masked)
            return SendResult(self.name, masked, None, sandbox=False, ok=False,
                              error="SMS_ORIGINATION_IDENTITY not configured")

        try:
            resp = self._sms().send_text_message(
                DestinationPhoneNumber=recipient,
                OriginationIdentity=self.origination_identity,
                MessageBody=self._body(message),
            )
            mid = resp.get("MessageId")
            log.info("[sms] sent to %s (MessageId=%s)", masked, mid)
            return SendResult(self.name, masked, mid, sandbox=False, ok=True)
        except Exception as exc:
            log.exception("[sms] send to %s failed: %s", masked, exc)
            return SendResult(self.name, masked, None, sandbox=False, ok=False, error=str(exc))
