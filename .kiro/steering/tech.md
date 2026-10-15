---
inclusion: always
---
# Tech Standards

## Stack
- **Language:** Python 3.12.
- **Web/async:** FastAPI + Starlette WebSockets (agent runtime), boto3 for AWS.
- **AI:** Amazon Bedrock — Nova Sonic (voice), Nova Pro (report + intent routing).
- **Runtime:** Amazon Bedrock AgentCore Runtime (container).
- **CDS:** Amazon SES (`sesv2`), AWS End User Messaging SMS/RCS
  (`pinpoint-sms-voice-v2`). WhatsApp (`socialmessaging`) is a future adapter.
- **State:** Amazon DynamoDB (on-demand).
- **IaC:** AWS CloudFormation.
- **Region:** `us-east-1` (Nova Sonic + CDS availability). This project is not
  bound to any single-region data-residency rule.

## Coding standards
- Follow the style already present in `agent/` — module docstrings, type hints,
  `logging` (never `print`), small focused functions.
- All AWS access through boto3 clients created per-call or cached per-module;
  never hardcode account IDs, ARNs, numbers, or regions — read them from
  environment variables.
- **Secrets:** never hardcoded. Use environment variables or AWS Secrets Manager.
- **PII:** customer phone numbers and email addresses are sensitive. Never log
  raw PII — mask it (e.g. show last 4 digits). Never hardcode real contact data;
  use `example.com` / placeholder numbers in samples and tests.
- **CDS calls must be real.** When a required AWS resource is not yet provisioned,
  guard the call behind `SANDBOX_MODE` (env var) that records the intended send
  instead of performing it — but keep the real boto3 call on the production path.
- Fail safe: a messaging send failure must never crash the discovery session; log
  and degrade gracefully.

## Channel abstraction (C-ready)
- Every outbound message goes through `send(channel, recipient, message)` on a
  channel adapter. Adapters: `SesAdapter`, `SmsAdapter`, `RcsAdapter` (stub),
  future `WhatsAppAdapter`. New channels are new adapters, not new call sites.

## Verification
- `python -m py_compile` must pass for every changed module.
- Exercise the channel layer and inbound intent routing in `SANDBOX_MODE` before
  marking a task done.
