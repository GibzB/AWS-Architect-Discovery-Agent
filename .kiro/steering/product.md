---
inclusion: always
---
# Product Context

## What this is
An agentic, omnichannel customer-engagement solution built on **AWS
Communication Developer Services (CDS)** for the AWS CDS Agentic AI Partner
Hackathon.

The product opens with a voice-driven AWS architecture discovery interview
(Amazon Nova Sonic on Bedrock AgentCore), generates a discovery report
(Amazon Nova Pro), and then continues the relationship as a **two-way,
multi-channel conversation**:

- **Amazon SES** delivers the full discovery report by email.
- **AWS End User Messaging (SMS, RCS-ready)** sends an interactive follow-up and
  receives the customer's free-text reply.
- An **agentic inbound handler** (Lambda + Amazon Bedrock) interprets the reply,
  takes an action (book a deep-dive, answer a question, escalate to a human),
  and responds on the same channel — picking up where the last message left off.

## Why it matters for the hackathon
The brief asks for conversational, two-way, omnichannel engagement where CDS is
the communications backbone, powered by agentic AI — explicitly *beyond* OTP and
rigid chatbots. This project uses CDS at runtime for real two-way dialogue, with
Bedrock providing the agentic reasoning.

## Design intent: Option B, built C-ready
- **Option B (now):** omnichannel two-way follow-up on top of the existing
  discovery agent. Channels implemented: SES + SMS, with RCS stubbed behind the
  same interface.
- **C-ready (next):** a channel abstraction layer and a generic
  conversation/journey state model so the same engine can drive a customer-facing
  vertical journey (e.g. healthcare, retail) by swapping prompts and a journey
  definition — not by rewriting plumbing. Adding WhatsApp (Meta prize) is one new
  adapter.

## Non-negotiables
- At least one AWS CDS service must be invoked at runtime in the code path.
- The CDS integration code must be real (actual boto3 calls); a sandbox/mock mode
  may stand in for un-provisioned AWS resources during development and demo, but
  the production code path calls CDS for real.
