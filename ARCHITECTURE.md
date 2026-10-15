# AWS CDS Agentic Omnichannel Engagement — Architecture

Fully serverless architecture on AWS. No EC2 instances, no ECS clusters, no
persistent servers to manage. **AWS Communication Developer Services (CDS)** are
the communications backbone; Amazon Bedrock provides the agentic reasoning.

See [`docs/architecture-diagram.md`](docs/architecture-diagram.md) for the
diagram and [`docs/DESIGN_CDS.md`](docs/DESIGN_CDS.md) for the component design.

## AWS Communication Developer Services (CDS)

- **Amazon SES** (`sesv2.send_email`) — delivers the full discovery report by
  email.
- **AWS End User Messaging — SMS** (`pinpoint-sms-voice-v2.send_text_message`) —
  sends the interactive post-call follow-up and carries the two-way reply.
- **AWS End User Messaging — RCS** — rich-card follow-up; implemented as a
  drop-in stub behind the same channel interface until a brand RCS agent is
  approved.
- **AWS End User Messaging Social — WhatsApp** (`socialmessaging`) — future
  adapter behind the same interface (Meta WhatsApp prize path).

CDS calls run on the real code path; `SANDBOX_MODE` only controls whether a send
hits AWS or is recorded for local development and demos.

## AWS Services

### Voice & AI

- **Amazon Nova 2 Sonic** (Bedrock) — real-time bidirectional voice streaming for the discovery interview
- **Amazon Nova Pro** (Bedrock) — generates the post-session discovery report (architecture recommendations, service breakdown, cost estimates)

### Compute & Runtime

- **Amazon Bedrock AgentCore Runtime** — hosts the agent container (FastAPI + WebSocket server) with managed scaling, SigV4 auth, and WebSocket proxy

### Knowledge Base (RAG)

- **Amazon Bedrock Knowledge Base** — indexes AWS Well-Architected Framework, Landing Zone patterns, and migration guides for RAG-augmented responses
- **Amazon S3** — stores the source documents for the knowledge base

### API & Networking

- **Amazon API Gateway** (HTTP API) — single POST /presign endpoint that generates SigV4 presigned WebSocket URLs for the frontend
- **AWS Lambda** (Python 3.12) — presign URL generator, inline in CloudFormation

### Frontend & CDN

- **Amazon S3** — hosts static frontend assets (HTML, JS, CSS)
- **Amazon CloudFront** — HTTPS CDN with Origin Access Control, serves the frontend globally
- **CloudFront Functions** — HTTP Basic Auth for demo access control

### Storage

- **Amazon DynamoDB** — session records table (conversation transcripts, reports, metadata)

### Container & Deployment

- **Amazon ECR** — stores the agent Docker image (ARM64)
- **AWS CloudFormation** — all infrastructure defined as IaC (two stacks: bootstrap + main)

### Security

- **AWS IAM** — roles for AgentCore Runtime and presign Lambda
- **SigV4 presigned URLs** — secures WebSocket connections to AgentCore
- **AWS WAF** (optional) — rate limiting (300 req/5min per IP) and AWS managed common rule set

## Data Flow

```
1. User clicks "Start Discovery" → frontend requests presigned WSS URL from API Gateway
2. Lambda generates SigV4 presigned URL for AgentCore WebSocket endpoint
3. Frontend opens WebSocket to AgentCore Runtime
4. AgentCore sends first message → triggers Nova 2 Sonic greeting
5. Bidirectional voice loop:
   - User speaks → audio streamed to Nova 2 Sonic
   - Nova 2 Sonic responds with next discovery question
   - Transcript appears in real-time
6. User clicks "End Session" → triggers report generation
7. Nova Pro receives full transcript → generates structured report
8. Report stored in DynamoDB, displayed in frontend
```

## Omnichannel Engagement Flow (AWS CDS)

```
Post-call (outbound):
  9.  Amazon SES emails the full report.
  10. End User Messaging (SMS/RCS) sends an interactive follow-up
      ("Book a deep-dive / See cost estimate / Talk to a human").
  11. ConversationState persisted in DynamoDB, keyed by customer identity.

Two-way (inbound):
  12. Customer replies in free text.
  13. End User Messaging publishes the inbound message to an SNS topic.
  14. Inbound Lambda verifies the event, loads ConversationState by sender.
  15. Amazon Bedrock classifies the reply into a FIXED action enum.
  16. The matching action runs (book / cost / human / answer-from-report).
  17. The agent replies on the SAME channel, to the stored address, and
      updates ConversationState — ready for the next turn.
```

## Channel Abstraction + Engagement Design

- **`agent/channels/`** — every outbound message goes through
  `send(recipient, OutboundMessage)` on a `Channel` adapter. SES, SMS, RCS (and
  future WhatsApp) are interchangeable implementations. A `SANDBOX_MODE`
  recording adapter stands in when CDS is not provisioned. Adding a channel is
  one new adapter class — no call-site changes.
- **`agent/engagement/`** — post-call orchestration, a journey-agnostic
  `ConversationState` (so the same engine can drive other verticals), the
  Bedrock intent router (constrained to a fixed action enum to contain
  prompt-injection in customer replies), and the inbound handler.

### Security properties

- Replies are always sent to the address stored on the conversation, never to a
  value taken from the inbound message body.
- The agent only acts on senders that already have conversation state.
- The intent router returns one of a fixed set of actions; customer text never
  drives a privileged operation directly.
- Customer PII (phone/email) is masked in logs; conversation records carry a
  DynamoDB TTL so contact data auto-expires.

## Agent Design

Unlike the Azure version's multi-agent routing pattern, this implementation uses
a single Nova 2 Sonic session with a comprehensive system prompt that covers all
discovery phases. The voice model handles the full conversation flow natively.

Post-session, Nova Pro acts as the "report agent" — consolidating the transcript
into a structured architecture recommendation document.

### Discovery Phases (embedded in system prompt)

1. **Introduction** — greet, explain process
2. **Business Context** — industry, size, drivers
3. **Technical Workloads** — applications, data, integrations
4. **Compliance & Security** — regulatory, residency, identity
5. **Growth & Future** — scale projections, new workloads
6. **Recommendation** — summarise and suggest AWS architecture
