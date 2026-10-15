# Design — CDS Omnichannel Agentic Engagement (Option B, C-ready)

This document specifies how AWS Communication Developer Services (CDS) are added
to the Discovery Orchestrator as a two-way, omnichannel engagement layer, and how
the design is kept ready to grow into a customer-facing vertical journey (the
"Option C" pivot) without rewriting plumbing.

## 1. Goals and non-goals

**Goals**
- Use at least one CDS service at runtime, on the real code path.
- Continue the conversation after the voice call across email + messaging.
- Handle the customer's free-text reply with an agentic (Bedrock) handler.
- Keep channels interchangeable so WhatsApp/RCS are additive, not forked.
- Run end-to-end in `SANDBOX_MODE` for development and demo.

**Non-goals (this sprint)**
- Production WhatsApp onboarding (Meta Business verification lead time) — the
  adapter seam is designed for it, but WhatsApp is a P2 stretch.
- Replacing the voice opener — it stays as the first touch.

## 2. Component overview

```
agent/
  channels/                 # NEW — channel abstraction layer (C-ready seam)
    __init__.py
    base.py                 # Channel ABC: send(recipient, message) + Message types
    ses_adapter.py          # Amazon SES (sesv2)         — email
    sms_adapter.py          # AWS End User Messaging SMS  (pinpoint-sms-voice-v2)
    rcs_adapter.py          # AWS End User Messaging RCS  — stub behind same ABC
    factory.py              # resolve channel name -> adapter; SANDBOX_MODE switch
  engagement/               # NEW — conversation state + agentic follow-up
    __init__.py
    state.py                # ConversationState model + DynamoDB persistence
    orchestrator.py         # post-call: email report + send follow-up
    intent.py               # Bedrock intent router (free text -> action enum)
    actions.py              # action handlers: book / answer / escalate
  prompts/
    intent_router.py        # NEW — intent-classification prompt (separate from discovery)
  server.py                 # extended: on_done triggers engagement.orchestrator
infra/
  inbound.py                # NEW — inbound Lambda (webhook) source, deployed via CFN
```

## 3. Channel abstraction layer (PBI-1, C-ready)

A single interface so every outbound message is channel-agnostic:

```python
class Channel(ABC):
    name: str
    @abstractmethod
    def send(self, recipient: str, message: OutboundMessage) -> SendResult: ...
```

- `OutboundMessage` carries `text`, optional `subject` (email), and optional
  `actions` (list of button-like choices). Each adapter renders the message the
  way its channel supports: SES → HTML email, SMS → text + numbered options,
  RCS → rich card with suggested replies (when available), else text fallback.
- `factory.get_channel(name)` returns the adapter. When `SANDBOX_MODE=true` (or a
  channel's required config is missing), the factory returns a **recording**
  adapter that logs the intended send and stores it, instead of calling AWS —
  but the real adapters hold the real boto3 calls, so the production path uses
  CDS for real.
- **Adding WhatsApp or a new channel = one new adapter class.** No call site
  changes. This is the primary C-ready seam.

### CDS API mapping

| Channel | AWS CDS service | boto3 client | Key call |
|---------|-----------------|--------------|----------|
| Email | Amazon SES | `sesv2` | `send_email` |
| SMS | AWS End User Messaging | `pinpoint-sms-voice-v2` | `send_text_message` |
| RCS | AWS End User Messaging RCS | `pinpoint-sms-voice-v2` | `send_text_message` / RCS content (stub) |
| WhatsApp (P2) | AWS End User Messaging Social | `socialmessaging` | `send_whatsapp_message` |

## 4. Conversation state model (PBI-8, C-ready)

Generic — not hardcoded to "discovery follow-up" — so a different vertical journey
reuses it unchanged.

```
ConversationState (DynamoDB item)
  conversation_id   : str   (PK)  = normalized customer identity (e.g. "sms:+1555...")
  session_id        : str          link back to the discovery session
  channels          : map          last-used address per channel {email, sms, ...}
  journey           : str          journey name (default "discovery_followup")
  stage             : str          where the journey is (e.g. "awaiting_choice")
  context           : map          free-form journey context (report summary, etc.)
  pending_actions   : list         offered actions the customer can pick
  history           : list         recent turns (role, channel, text) — PII masked in logs
  ttl               : number       auto-expire (privacy; PBI-4)
```

Stored in the existing DynamoDB table (new item shape, keyed by
`conversation_id`) or a sibling table. Encrypted at rest; TTL set so contact data
does not linger.

## 5. Post-call orchestration (PBI-2)

On `server.py` `on_done()` after the report is generated:

1. Build/attach `ConversationState` keyed by the customer's identity (collected
   during the session, or a demo recipient in sandbox).
2. `SesAdapter.send` → email the full report (HTML rendered from the report
   Markdown).
3. `SmsAdapter.send` (RCS when available) → short follow-up with actions:
   "1 Book a deep-dive · 2 See cost estimate · 3 Talk to a human".
4. Persist `pending_actions` and `stage="awaiting_choice"`.
5. Fail-safe: any send error is logged (PII masked) and never crashes the session.

## 6. Two-way inbound handler (PBI-3, PBI-5)

An inbound message (SMS/RCS reply, or an inbound email) is delivered to a Lambda:

```
Customer reply ──► EUM/SNS ──► Inbound Lambda
    1. Verify event authenticity (SNS signature / EUM event shape).  [PBI-5]
    2. Normalize sender -> conversation_id; load ConversationState.
    3. Bedrock intent router (intent.py): free text -> fixed action enum
       {book_deepdive, cost_estimate, talk_to_human, ask_question, unknown}.
    4. actions.py executes the action:
         - book_deepdive  -> record booking intent, confirm with a slot prompt
         - cost_estimate  -> summarize cost section from report context
         - talk_to_human  -> flag for handoff, acknowledge
         - ask_question   -> answer from report context via Bedrock
         - unknown        -> re-present the options
    5. Reply on the SAME channel via the channel layer; update state.
```

Security:
- The intent router is constrained to a **fixed action enum** — the customer's
  free text never drives a privileged operation directly (prompt-injection
  containment).
- The agent only acts on a sender that matches existing conversation state.
- Reply recipient is always the stored address for the session, never a value
  taken from the message body.

## 7. SANDBOX_MODE

`SANDBOX_MODE=true` (default when CDS resources are not configured):
- Outbound: adapters record the intended send (channel, masked recipient, body)
  to logs and to an in-memory/DynamoDB "outbox" instead of calling AWS.
- Inbound: a local test entrypoint feeds a sample inbound payload to the handler
  so the full intent→action→reply loop can be exercised without a live number.
- This makes the demo and local development fully runnable before SES identity /
  SMS number / RCS agent provisioning completes, while the real boto3 calls
  remain on the production path.

## 8. C-pivot (Option C) readiness summary

| C requirement | How this design already supports it |
|---------------|-------------------------------------|
| Start a journey in a messaging channel (not voice) | Inbound handler + channel layer are channel-agnostic; a journey can begin from an inbound message. |
| Switch channels mid-journey | `ConversationState.channels` holds every address; any step can send on any channel. |
| Remember context across channels | State keyed by customer identity, not by session/channel. |
| New vertical (healthcare, retail) | Swap `journey` + prompts; plumbing unchanged. |
| Add WhatsApp (Meta prize) | One new adapter implementing `Channel`. |
