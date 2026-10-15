# Hackathon Submission — AWS CDS Agentic Omnichannel Engagement

**AWS CDS Agentic AI Partner Hackathon**

---

## Elevator pitch

A conversation that starts as a voice discovery call and continues as a real
two-way dialogue across email, SMS, and RCS — powered by AWS Communication
Developer Services as the backbone and Amazon Bedrock as the agentic brain. The
customer gets their report, replies in their own words, and an AI agent picks up
exactly where the last message left off, taking real actions on their behalf.

---

## About the project

### Inspiration

Pre-sales architecture discovery is slow, and worse, it goes cold the moment the
call ends. The customer gets a PDF days later and the thread dies. The hackathon
brief captures the fix perfectly: engagement should be conversational, two-way,
and omnichannel — reaching customers in the channel they prefer and picking up
where the last conversation left off. We took an existing voice-discovery agent
and made AWS CDS its communications backbone so the relationship continues after
the call, on the customer's terms.

### What it does

1. **Voice discovery** — the customer has a natural voice conversation with an AI
   architect (Amazon Nova Sonic on Bedrock AgentCore).
2. **Report** — Amazon Nova Pro generates a structured discovery report.
3. **Email (Amazon SES)** — the full report is emailed instantly.
4. **Interactive follow-up (AWS End User Messaging — SMS/RCS)** — a message
   offers next steps: book a deep-dive, see the cost estimate, or talk to a human.
5. **Two-way, agentic** — the customer replies in free text. The reply is
   classified by Amazon Bedrock and drives a real action; the agent responds on
   the same channel and remembers the context for the next turn.

This is the omnichannel journey the brief describes: a conversation that starts
in one channel (voice), delivers in another (email), and completes an action in
another (SMS/RCS) — without the customer leaving the messaging experience.

### How AWS CDS is used at runtime

| CDS service | Runtime role | Code |
|-------------|-------------|------|
| **Amazon SES** | Emails the discovery report | `agent/channels/ses_adapter.py` → `sesv2.send_email` |
| **AWS End User Messaging (SMS)** | Sends the interactive follow-up and receives the two-way reply | `agent/channels/sms_adapter.py` → `pinpoint-sms-voice-v2.send_text_message` |
| **AWS End User Messaging (RCS)** | Rich-card follow-up, drop-in behind the same interface | `agent/channels/rcs_adapter.py` |
| **AWS End User Messaging Social (WhatsApp)** | Future adapter (Meta prize path) | `socialmessaging.send_whatsapp_message` |

Inbound replies are delivered by End User Messaging to an Amazon SNS topic and
processed by a Lambda (`infra/inbound_lambda.py`) that runs one agentic turn:
verify → classify (Bedrock) → act → reply over CDS.

### Agentic AI (Amazon Bedrock)

- **Nova Sonic** runs the real-time bidirectional voice discovery interview.
- **Nova Pro** generates the report, classifies inbound intent into a fixed
  action set, and answers follow-up questions grounded in the report.
- **Bedrock AgentCore Runtime** hosts the agent serverlessly.

The intent router is deliberately constrained to a fixed action enum
(`book_deepdive`, `cost_estimate`, `talk_to_human`, `ask_question`, `unknown`),
so a customer's free-text reply can never drive a privileged operation directly —
agentic flexibility with a bounded, safe action surface.

### How we built it

- **Channel abstraction layer** (`agent/channels/`) — every outbound message goes
  through one `send(recipient, message)` interface. SES, SMS, RCS (and future
  WhatsApp) are interchangeable adapters. Adding a channel is one new class.
- **Journey-agnostic conversation state** (`agent/engagement/state.py`) — stored
  in DynamoDB, keyed by customer identity so context survives across channels.
  This is also what makes the solution a *repeatable offering*: a different
  vertical journey (healthcare, retail, logistics) is a prompt + journey-config
  swap, not a rewrite.
- **SANDBOX_MODE** — the whole flow is runnable with no provisioned CDS
  resources, so judges and demos can exercise voice → report → email → SMS →
  two-way reply end-to-end; the real boto3 CDS calls remain on the production
  path.
- **Process** — built Scrum / DevSecOps style (adapted
  [Kiro-SDLC-Scrum skill](https://github.com/timwukp/Kiro-SDLC-Scrum-best-practics)):
  sprint plan + backlog + STRIDE threat model in `docs/SPRINT_PLAN.md`, and
  deterministic credential/PII/prompt-security guard hooks in `.kiro/`.

### Challenges

- **Two-way trust.** Inbound webhooks are an attack surface. We only act on
  senders with existing conversation state, always reply to the stored address
  (never a value from the message body), and verify the event shape.
- **Provisioning lead time.** SES verification, an EUM number, and RCS agent
  approval all take time. `SANDBOX_MODE` and the adapter seam let us build and
  demo the complete flow in parallel with provisioning.
- **Portability of the security tooling.** The DevSecOps skill we adopted was
  tuned for a Singapore banking context; we ported the useful guard hooks to our
  Python/`us-east-1`/CDS stack and dropped the banking-specific ones.

### What we learned

- CDS turns a one-shot AI interaction into a durable, multi-channel relationship
  with very little plumbing once a channel abstraction is in place.
- Constraining an agent to a fixed action enum is a simple, strong defense that
  keeps the experience conversational without opening a prompt-injection hole.

---

## Meta WhatsApp prize

The channel abstraction makes WhatsApp (AWS End User Messaging Social) a single
additional adapter implementing the same `Channel` interface
(`socialmessaging.send_whatsapp_message`), with inbound handled by the same
SNS → Lambda → Bedrock path. The journey — report delivery, interactive
follow-up, two-way agentic replies — runs on WhatsApp with no changes to the
engagement logic. See [`docs/DESIGN_CDS.md`](DESIGN_CDS.md) §3 and §8.

---

## Built with

Amazon Bedrock (Nova Sonic, Nova Pro) · Amazon Bedrock AgentCore Runtime ·
**Amazon SES** · **AWS End User Messaging (SMS/RCS)** · Amazon SNS · AWS Lambda ·
Amazon API Gateway · Amazon DynamoDB · Amazon S3 · Amazon CloudFront · AWS
CloudFormation · AWS IAM · Python · FastAPI · Docker

---

## Links and media

- **Repository:** https://github.com/GibzB/AWS-Architect-Discovery-Agent
  (branch `feature/cds-agentic-messaging`)
- **Architecture diagram:** [`docs/architecture-diagram.md`](architecture-diagram.md)
- **Design:** [`docs/DESIGN_CDS.md`](DESIGN_CDS.md)
- **Sprint plan / process:** [`docs/SPRINT_PLAN.md`](SPRINT_PLAN.md)
- **Demo URL:** *(CloudFront URL after deployment)*
- **Demo video:** *(record ~3 min — see script below)*

### Suggested 3-minute demo script

1. Start a voice discovery session; have a short conversation; end it.
2. Show the report appear, then the SES email and the SMS follow-up (in
   `SANDBOX_MODE`, show the `[sandbox] would send ...` log lines, or show the
   real email/SMS if deployed live).
3. Reply to the SMS with "1" → show the agent book a deep-dive and reply back.
4. Reply with a free-text question → show the agent answer from the report.
5. Point at the architecture diagram and name the CDS services doing the work.

---

## How to interact with it

- **Deployed:** open the CloudFront URL, log in (`demo` / your password), start a
  session. Live CDS sends to your `--demo-email` / `--demo-phone`.
- **Local (no AWS CDS needed):** run `uvicorn local_server:app` in `SANDBOX_MODE`
  (see README) and watch the recorded sends in the logs.
