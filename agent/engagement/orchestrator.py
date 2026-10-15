"""
Post-call engagement orchestrator.

When a discovery session ends and the report is ready, this module turns the
one-shot voice call into an ongoing omnichannel conversation over AWS CDS:

  1. Email the full discovery report via Amazon SES.
  2. Send an interactive SMS/RCS follow-up offering next-step actions.
  3. Persist ConversationState so an inbound reply picks up where this left off.

Channels are resolved through the channel abstraction layer, so SANDBOX_MODE and
future channels (WhatsApp) work with no change here.
"""

from __future__ import annotations

import logging
import os

from channels import Action, OutboundMessage, get_channel

from .state import ConversationState, ConversationStore, make_conversation_id

log = logging.getLogger(__name__)

# The fixed next-step actions offered after a discovery call.
FOLLOW_UP_ACTIONS = [
    Action("book_deepdive", "Book a deep-dive with an architect"),
    Action("cost_estimate", "See the cost estimate"),
    Action("talk_to_human", "Talk to a human"),
]


def _report_html(report_md: str) -> str:
    """Very small Markdown-ish to HTML wrap for the email body.

    Keeps the report readable in an email client without pulling a Markdown
    dependency. Headings and line breaks are the common cases in our reports.
    """
    import html as html_lib

    lines = []
    for raw in report_md.splitlines():
        line = html_lib.escape(raw)
        stripped = raw.lstrip("#").strip()
        if raw.startswith("### "):
            lines.append(f"<h3>{html_lib.escape(stripped)}</h3>")
        elif raw.startswith("## "):
            lines.append(f"<h2>{html_lib.escape(stripped)}</h2>")
        elif raw.startswith("# "):
            lines.append(f"<h1>{html_lib.escape(stripped)}</h1>")
        elif not raw.strip():
            lines.append("<br>")
        else:
            lines.append(f"<div>{line}</div>")
    body = "\n".join(lines)
    return (
        "<html><body style='font-family:system-ui,Arial,sans-serif;max-width:680px;margin:auto'>"
        f"{body}"
        "</body></html>"
    )


def run_post_call_engagement(
    session_id: str,
    report: dict,
    digest: dict | None = None,
    *,
    email: str | None = None,
    phone: str | None = None,
    follow_up_channel: str | None = None,
    store: ConversationStore | None = None,
) -> dict:
    """Deliver the report and open the follow-up conversation.

    Recipients default to the DEMO_EMAIL / DEMO_PHONE environment variables so a
    sandbox demo runs without a real customer identity. The follow-up channel
    defaults to SMS (set FOLLOW_UP_CHANNEL=rcs to prefer RCS).

    Returns a summary dict of what was sent (for logging / the UI).
    """
    email = email or os.environ.get("DEMO_EMAIL", "")
    phone = phone or os.environ.get("DEMO_PHONE", "")
    follow_up_channel = (follow_up_channel or os.environ.get("FOLLOW_UP_CHANNEL", "sms")).lower()
    store = store or ConversationStore()

    report_md = report.get("report_md", "")
    summary = report.get("summary") or (digest or {}).get("summary") or "Your AWS discovery report is ready."

    results = {"email": None, "follow_up": None, "conversation_id": None}

    # 1) Email the full report via SES.
    if email:
        email_msg = OutboundMessage(
            text=f"Thanks for your discovery session. Your report is attached below.\n\n{report_md}",
            subject="Your AWS architecture discovery report",
            html=_report_html(report_md),
        )
        res = get_channel("email").send(email, email_msg)
        results["email"] = {"ok": res.ok, "sandbox": res.sandbox, "to": res.recipient_masked}
    else:
        log.info("[engagement] no email recipient; skipping report email")

    # 2) Send the interactive follow-up over SMS/RCS.
    conversation_id = None
    if phone:
        follow_up_msg = OutboundMessage(
            text=f"{summary}\n\nWhat would you like to do next?",
            actions=FOLLOW_UP_ACTIONS,
        )
        res = get_channel(follow_up_channel).send(phone, follow_up_msg)
        results["follow_up"] = {
            "channel": follow_up_channel, "ok": res.ok,
            "sandbox": res.sandbox, "to": res.recipient_masked,
        }

        # 3) Persist conversation state so an inbound reply has context.
        conversation_id = make_conversation_id(follow_up_channel, phone)
        state = ConversationState(
            conversation_id=conversation_id,
            session_id=session_id,
            journey="discovery_followup",
            stage="awaiting_choice",
            channels={k: v for k, v in (("email", email), ("sms", phone)) if v},
            context={
                "report_summary": summary,
                "report_md": report_md,
            },
            pending_actions=[{"id": a.id, "label": a.label} for a in FOLLOW_UP_ACTIONS],
        )
        state.record_turn("agent", follow_up_channel, follow_up_msg.text)
        store.save(state)
        results["conversation_id"] = conversation_id
    else:
        log.info("[engagement] no phone recipient; skipping follow-up message")

    log.info("[engagement] post-call engagement complete: %s", results)
    return results
