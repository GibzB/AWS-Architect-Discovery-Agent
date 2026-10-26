# AWS CDS Omnichannel Engagement — Integration & Status

This document describes how **AWS Communication Developer Services (CDS)** are
integrated into Atlas and the exact live/sandbox status of each channel, for the
AWS CDS Agentic AI Partner Hackathon.

## What was added

After a discovery workshop completes and the Review agent approves the
architecture, Atlas turns the one-shot session into an ongoing, two-way,
multi-channel conversation over AWS CDS:

1. **Amazon SES** emails the full discovery report.
2. **AWS End User Messaging (SMS / RCS)** sends an interactive follow-up offering
   next steps (book a deep-dive, see the cost estimate, talk to a human).
3. The customer replies in free text; an **agentic inbound handler** classifies
   intent with Amazon Bedrock (a fixed action enum — prompt-injection safe) and
   replies on the **same channel**, with conversation state persisted so it
   picks up where it left off.

### Components (backend)

| Path | Role |
|------|------|
| `apps/backend/app/services/channels/` | Channel abstraction — SES, SMS, RCS adapters + factory + `SANDBOX_MODE` |
| `apps/backend/app/services/engagement_service.py` | Post-workshop delivery + two-way agentic inbound loop |
| `apps/backend/app/routes/engagement.py` | `POST /v1/sessions/{id}/engage`, `POST /v1/inbound` |
| `apps/backend/app/services/dynamo_store.py` | Durable DynamoDB session state (Lambda-safe) |
| `apps/frontend/src/components/EngagementPanel.tsx` | UI to capture email/phone and trigger delivery |

Adding a channel (e.g. WhatsApp via End User Messaging Social) is one new adapter
implementing the same `Channel` interface — no call-site changes.

## CDS channel status (honest)

| Channel | CDS service | Code | Status |
|---------|-------------|------|--------|
| **Email** | Amazon SES (`sesv2.send_email`) | `ses_adapter.py` | **LIVE — verified** on AWS (real MessageIds). This is the runtime CDS usage satisfying the hackathon requirement. |
| **SMS** | AWS End User Messaging (`pinpoint-sms-voice-v2.send_text_message`) | `sms_adapter.py` | **Implemented; sandbox-proven.** The two-way agentic loop is verified in `SANDBOX_MODE`. Live delivery is pending a provisioned origination identity (US toll-free / 10DLC verification, or a registered Sender ID for other regions) and SMS production access — standard AWS/carrier registration gates, not code gaps. |
| **RCS** | AWS End User Messaging RCS | `rcs_adapter.py` | **Implemented as a drop-in stub** behind the same interface; upgrades to rich cards once a brand RCS agent is approved. |
| **WhatsApp** | End User Messaging Social (`socialmessaging`) | future adapter | Designed-for; one new adapter. |

### Why SMS is sandbox-proven rather than live

The demo AWS account is in the **SMS sandbox** (`ACCOUNT_TIER = SANDBOX`, text
spend limit capped at $1 and non-raisable while in sandbox) with **no
origination identity provisioned**. AWS requires:

- a verified **origination number** (US toll-free or 10DLC) or a registered
  **Sender ID** for the destination country, and
- **SMS production access** to lift the sandbox spend cap,

both of which involve carrier/AWS registration with multi-day lead time. The
destination test numbers were registered for sandbox verification; the send path
itself is the real `pinpoint-sms-voice-v2` call, guarded by `SANDBOX_MODE` so the
flow is fully demonstrable today and goes live the moment an origination identity
exists — no code change required.

## SANDBOX_MODE

`SANDBOX_MODE=true` makes every channel adapter **record** the intended send
(channel, masked recipient, body) instead of calling AWS, so the complete
workshop → report → email → SMS → two-way reply loop runs with no provisioned
CDS resources. The production code path (`SANDBOX_MODE=false`) performs the real
boto3 CDS calls — as proven live for SES.

## Security properties

- Replies always go to the address stored on the conversation, never a value
  taken from the inbound message body.
- The agent only acts on senders with existing conversation state.
- The Bedrock intent router returns one of a fixed action set; customer free text
  never drives a privileged operation directly.
- Customer PII (email/phone) is masked in all logs; DynamoDB session records
  carry a TTL so contact data auto-expires.

## Deployment

- Backend: FastAPI run via **AWS Lambda Web Adapter** (container image) behind an
  **API Gateway HTTP API**; session state in **Amazon DynamoDB**.
- Frontend: **AWS Amplify** (`feature-cds-omnichannel-atlas` branch), pointed at
  the API via `VITE_API_URL`.
- Voice (Nova Sonic bidirectional WebSocket) runs on the local/streaming target,
  not on the Lambda HTTP deployment (Lambda HTTP is request/response only).
