"""
Amazon SES channel adapter (AWS CDS — email).

Sends email via the Amazon SES v2 API (`sesv2.send_email`). This is a real
AWS Communication Developer Service call on the production path; in SANDBOX_MODE
the factory substitutes a recording adapter instead of constructing this one.
"""

from __future__ import annotations

import html as html_lib
import logging
import os

import boto3

from .base import Channel, OutboundMessage, SendResult, mask_recipient

log = logging.getLogger(__name__)

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


class SesAdapter(Channel):
    """Email via Amazon SES."""

    name = "email"

    def __init__(self, sender: str | None = None, client=None):
        # Verified SES "From" identity, supplied via environment / infra.
        self.sender = sender or os.environ.get("SES_SENDER_EMAIL", "")
        self._client = client

    def _ses(self):
        if self._client is None:
            self._client = boto3.client("sesv2", region_name=REGION)
        return self._client

    def _render_html(self, message: OutboundMessage) -> str:
        if message.html:
            return message.html
        # Minimal HTML fallback from the plain-text body.
        body = html_lib.escape(message.text).replace("\n", "<br>")
        action_html = ""
        if message.actions:
            items = "".join(
                f"<li>{html_lib.escape(a.label)}</li>" for a in message.actions
            )
            action_html = f"<ul>{items}</ul>"
        return (
            "<html><body style='font-family:system-ui,Arial,sans-serif'>"
            f"<div>{body}</div>{action_html}"
            "</body></html>"
        )

    def send(self, recipient: str, message: OutboundMessage) -> SendResult:
        if not recipient:
            raise ValueError("SES send requires a recipient email")
        masked = mask_recipient(recipient)

        if not self.sender:
            log.error("[ses] SES_SENDER_EMAIL not configured; cannot send to %s", masked)
            return SendResult(
                channel=self.name, recipient_masked=masked, message_id=None,
                sandbox=False, ok=False, error="SES_SENDER_EMAIL not configured",
            )

        subject = message.subject or "Your AWS discovery report"
        try:
            resp = self._ses().send_email(
                FromEmailAddress=self.sender,
                Destination={"ToAddresses": [recipient]},
                Content={
                    "Simple": {
                        "Subject": {"Data": subject},
                        "Body": {
                            "Text": {"Data": self._actions_as_text(message)},
                            "Html": {"Data": self._render_html(message)},
                        },
                    }
                },
            )
            message_id = resp.get("MessageId")
            log.info("[ses] sent to %s (MessageId=%s)", masked, message_id)
            return SendResult(
                channel=self.name, recipient_masked=masked,
                message_id=message_id, sandbox=False, ok=True,
            )
        except Exception as exc:  # never crash the conversation on a send error
            log.exception("[ses] send to %s failed: %s", masked, exc)
            return SendResult(
                channel=self.name, recipient_masked=masked, message_id=None,
                sandbox=False, ok=False, error=str(exc),
            )
