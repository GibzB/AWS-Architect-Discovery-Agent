"""Amazon SES channel adapter (AWS CDS — email)."""

from __future__ import annotations

import html as html_lib
import logging
import os

import boto3

from .base import Channel, OutboundMessage, SendResult, mask_recipient

log = logging.getLogger(__name__)

REGION = os.getenv("AWS_REGION_NAME", os.getenv("AWS_REGION", "us-east-1"))


class SesAdapter(Channel):
    """Email via Amazon SES (sesv2.send_email)."""

    name = "email"

    def __init__(self, sender: str | None = None, client=None):
        self.sender = sender or os.getenv("SES_SENDER_EMAIL", "")
        self._client = client

    def _ses(self):
        if self._client is None:
            self._client = boto3.client("sesv2", region_name=REGION)
        return self._client

    def _render_html(self, message: OutboundMessage) -> str:
        if message.html:
            return message.html
        body = html_lib.escape(message.text).replace("\n", "<br>")
        action_html = ""
        if message.actions:
            items = "".join(f"<li>{html_lib.escape(a.label)}</li>" for a in message.actions)
            action_html = f"<ul>{items}</ul>"
        return (
            "<html><body style='font-family:system-ui,Arial,sans-serif'>"
            f"<div>{body}</div>{action_html}</body></html>"
        )

    def send(self, recipient: str, message: OutboundMessage) -> SendResult:
        if not recipient:
            raise ValueError("SES send requires a recipient email")
        masked = mask_recipient(recipient)

        if not self.sender:
            log.error("[ses] SES_SENDER_EMAIL not configured; cannot send to %s", masked)
            return SendResult(self.name, masked, None, sandbox=False, ok=False,
                              error="SES_SENDER_EMAIL not configured")

        subject = message.subject or "Your AWS discovery report"
        try:
            resp = self._ses().send_email(
                FromEmailAddress=self.sender,
                Destination={"ToAddresses": [recipient]},
                Content={"Simple": {
                    "Subject": {"Data": subject},
                    "Body": {
                        "Text": {"Data": self._actions_as_text(message)},
                        "Html": {"Data": self._render_html(message)},
                    },
                }},
            )
            mid = resp.get("MessageId")
            log.info("[ses] sent to %s (MessageId=%s)", masked, mid)
            return SendResult(self.name, masked, mid, sandbox=False, ok=True)
        except Exception as exc:
            log.exception("[ses] send to %s failed: %s", masked, exc)
            return SendResult(self.name, masked, None, sandbox=False, ok=False, error=str(exc))
