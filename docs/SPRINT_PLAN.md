# Sprint Plan — CDS Agentic Omnichannel Engagement

This project is built Scrum / DevSecOps style, following an adapted version of the
[Kiro-SDLC-Scrum best-practices skill](https://github.com/timwukp/Kiro-SDLC-Scrum-best-practics).
The security guardrails for the sprint are enforced deterministically by the
Pre-Tool-Use hooks in [`.kiro/hooks/`](../.kiro/hooks); the sprint framework
itself lives in [`.kiro/steering/scrum-devsecops.md`](../.kiro/steering/scrum-devsecops.md).

## Sprint Goal

> Turn the voice-only AWS Discovery Orchestrator into an **agentic, omnichannel
> customer-engagement solution with AWS Communication Developer Services (CDS)
> as the communications backbone** — so that a discovery session continues as a
> real two-way conversation across email and messaging, and the project
> satisfies the hackathon's "at least one CDS service, used at runtime" bar.

Success is measured by: (1) at least one CDS service invoked on the real code
path; (2) a two-way inbound reply handled by an agentic (Bedrock) handler; and
(3) a demo that runs end-to-end in `SANDBOX_MODE` without provisioned AWS
resources.

## Why this is valuable (the "Why")

The hackathon explicitly asks for conversational, two-way, omnichannel
engagement that goes *beyond* OTP and rigid chatbots, with CDS as the backbone
and agentic AI doing the reasoning. The existing app has the agentic core
(Bedrock AgentCore + Nova) but no CDS and no two-way channel. This sprint closes
that gap while keeping the distinctive voice-discovery opener.

## Product Backlog (prioritized)

Priority key: **P0** = required for eligibility, **P1** = required for a strong
submission, **P2** = stretch / Meta-WhatsApp-prize path.

| # | PBI | Priority | Type |
|---|-----|----------|------|
| PBI-1 | Channel abstraction layer: `send(channel, recipient, message)` with SES + SMS adapters, RCS stub, `SANDBOX_MODE` toggle. | P0 | Feature |
| PBI-2 | Post-call orchestration: on report completion, email the report via SES and send an interactive SMS/RCS follow-up; persist conversation state in DynamoDB. | P0 | Feature |
| PBI-3 | Two-way inbound handler: inbound message → Bedrock intent routing → action (book / answer / escalate) → reply on the same channel. | P0 | Feature |
| PBI-4 | Security story: treat customer phone/email as PII end-to-end — mask in logs, never persist more than needed, validate/normalize inbound sender identity before acting. | P1 | Security |
| PBI-5 | Security story: inbound webhook trust — verify the message source (SNS signature / EUM event shape) so the agent only acts on genuine CDS events. | P1 | Security |
| PBI-6 | Infrastructure: CloudFormation for SES identity, SMS phone-pool/number params, inbound SNS topic + Lambda, least-privilege IAM for `sesv2` + `sms-voice-v2`. | P1 | Infra |
| PBI-7 | Submission docs: README, ARCHITECTURE, DEPLOYMENT, HACKATHON_SUBMISSION rewritten around CDS; architecture diagram; runtime/demo instructions; detectable LICENSE. | P1 | Docs |
| PBI-8 | C-ready seam: generic conversation/journey state model + intent router decoupled from the discovery prompt, so a customer-facing vertical journey is a config swap. | P1 | Feature |
| PBI-9 | WhatsApp adapter (`socialmessaging`) behind the same interface — Meta WhatsApp prize path. | P2 | Feature |

## Threat model (security shift-left, done before building)

New external surfaces introduced this sprint and their mitigations:

| Surface | Risk (STRIDE) | Mitigation |
|---------|---------------|------------|
| Inbound messaging webhook (Lambda) | Spoofing — attacker posts fake inbound events to trigger agent actions | Verify SNS signature / EUM event shape; only act on recognized senders with existing conversation state (PBI-5). |
| Conversation state keyed by phone/email | Information disclosure — PII leak via logs or over-broad storage | Mask PII in logs (last 4 only); store minimum fields; DynamoDB encrypted at rest; TTL on records (PBI-4). |
| Agentic action on free-text reply | Tampering / prompt injection via the customer's message | Constrain the intent router to a fixed enum of actions; never let message text drive privileged operations directly. |
| Outbound send | Repudiation / abuse — unbounded sends, wrong recipient | Send only to the recipient on record for the session; `SANDBOX_MODE` for non-prod; fail-safe (a send error never crashes the session). |
| Credentials / secrets | Elevation — leaked AWS keys | Env vars / Secrets Manager only; credential + PII guard hooks block hardcoding at write time. |

## Definition of Done (per PBI)

- [ ] Code written and self-reviewed against `.kiro/steering/tech.md`.
- [ ] Security hooks pass (no hardcoded credentials or PII).
- [ ] `python -m py_compile` passes for changed modules; imports resolve.
- [ ] Behavior verified where runnable (`SANDBOX_MODE` smoke test).
- [ ] Docs updated when deployment / architecture / submission narrative changes.

## Sprint board (status)

| PBI | Status |
|-----|--------|
| PBI-1 Channel layer | In progress |
| PBI-2 Post-call orchestration | To do |
| PBI-3 Inbound handler | To do |
| PBI-4 PII handling | To do (woven through PBI-1..3) |
| PBI-5 Webhook trust | To do (part of PBI-3/PBI-6) |
| PBI-6 Infrastructure | To do |
| PBI-7 Submission docs | To do |
| PBI-8 C-ready seam | To do (woven through PBI-1..3) |
| PBI-9 WhatsApp (stretch) | Backlog |

## Retrospective notes

- Adapting the Kiro-SDLC-Scrum skill revealed its guard hooks were hardcoded for
  a Singapore banking context (region lock to `ap-southeast-1`, Java standards,
  Aurora/Flyway DB guards). Those were dropped; the credential / PII /
  prompt-security guards were kept and ported to Python + international E.164 /
  `us-east-1`. Lesson captured in `.kiro/steering/scrum-devsecops.md`.
