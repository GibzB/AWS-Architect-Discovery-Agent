# AWS CDS Agentic Omnichannel Engagement

An agentic, omnichannel customer-engagement solution built on **AWS Communication
Developer Services (CDS)**. A voice-driven AWS architecture discovery session
turns into an ongoing, two-way conversation across **email, SMS, and RCS** — the
customer gets their report, replies in their own words, and an AI agent picks up
right where the last message left off.

Built for the **AWS CDS Agentic AI Partner Hackathon**.

> CDS is the communications backbone (Amazon SES + AWS End User Messaging);
> Amazon Bedrock (Nova Sonic + Nova Pro) is the agentic brain.

## Why this fits the hackathon

The brief asks for conversational, two-way, omnichannel engagement where CDS is
the backbone and agentic AI does the reasoning — explicitly *beyond* OTP and
rigid chatbots. This project:

- **Uses AWS CDS at runtime** — Amazon SES sends the report; AWS End User
  Messaging (SMS, RCS-ready) sends the interactive follow-up and receives the
  customer's reply.
- **Is genuinely two-way and agentic** — an inbound reply is classified by
  Amazon Bedrock and drives a real action (book a deep-dive, answer a question,
  escalate to a human), with the agent remembering context across channels.
- **Is omnichannel by design** — a channel abstraction layer makes SES / SMS /
  RCS interchangeable, and adding **WhatsApp** (Meta prize) is one new adapter.

## How it works

```
1. Customer has a voice discovery session (Nova Sonic on AgentCore).
2. Nova Pro generates a structured discovery report.
3. Amazon SES  → emails the full report.
4. End User Messaging (SMS/RCS) → sends an interactive follow-up with next steps.
5. Customer replies in free text.
6. Inbound Lambda → Amazon Bedrock classifies intent → takes an action →
   replies on the SAME channel. Conversation state persists in DynamoDB.
```

See the full diagram in [`docs/architecture-diagram.md`](docs/architecture-diagram.md)
and the design in [`docs/DESIGN_CDS.md`](docs/DESIGN_CDS.md).

## AWS CDS services used

| CDS service | Where | boto3 | Call |
|-------------|-------|-------|------|
| **Amazon SES** | report delivery | `sesv2` | `send_email` |
| **AWS End User Messaging (SMS)** | follow-up + two-way | `pinpoint-sms-voice-v2` | `send_text_message` |
| **AWS End User Messaging (RCS)** | rich follow-up (stub, drop-in) | `pinpoint-sms-voice-v2` | `send_text_message` |
| **AWS End User Messaging Social (WhatsApp)** | future adapter (Meta prize) | `socialmessaging` | `send_whatsapp_message` |

Supporting AWS services: Amazon Bedrock (Nova Sonic + Nova Pro) on **AgentCore
Runtime**, AWS Lambda, Amazon SNS (inbound routing), Amazon DynamoDB, Amazon S3 +
CloudFront, AWS CloudFormation.

## Project structure

```
agent/
  channels/            # Channel abstraction layer (CDS adapters)
    base.py            #   Channel interface + message types
    ses_adapter.py     #   Amazon SES (email)
    sms_adapter.py     #   End User Messaging (SMS)
    rcs_adapter.py     #   End User Messaging (RCS) — stub, same interface
    factory.py         #   adapter resolution + SANDBOX_MODE
  engagement/          # Agentic omnichannel engagement
    orchestrator.py    #   post-call: email report + send follow-up
    intent.py          #   Bedrock intent router (fixed action enum)
    actions.py         #   action handlers (book / cost / human / answer)
    inbound.py         #   two-way inbound handler + SNS/EUM parsing
    state.py           #   ConversationState + DynamoDB (journey-agnostic)
  prompts/             # Nova Sonic discovery prompt + intent-router prompt
  server.py            # AgentCore WebSocket server (wires in engagement)
  local_server.py      # local dev server
infra/
  template.yaml        # CloudFormation: AgentCore, CDS, SNS inbound, DynamoDB...
  inbound_lambda.py    # production inbound handler (reuses agent/engagement)
  bootstrap.yaml       # ECR bootstrap
docs/                  # design, sprint plan, architecture, submission
.kiro/                 # Scrum/DevSecOps steering + security guard hooks
deploy.sh              # one-command deploy
```

## Quick start

```bash
# Sandbox (default): deploys and runs without SES/SMS provisioning.
./deploy.sh --profile <aws-profile> --password <demo-password>

# Live CDS: once a verified SES sender + an SMS origination identity exist.
./deploy.sh --profile <aws-profile> --password <demo-password> \
  --live --ses-sender no-reply@your-domain.com \
  --sms-identity <phone-number-id-or-pool> \
  --demo-email you@your-domain.com --demo-phone +1XXXXXXXXXX
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for CDS provisioning (SES verification, End
User Messaging number, two-way SNS wiring) and the inbound Lambda packaging note.

## Local development

```bash
cd agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-local.txt
cp .env.example .env   # SANDBOX_MODE=true by default — no CDS needed
uvicorn local_server:app --reload --port 8000
```

In `SANDBOX_MODE`, the channel adapters record what they *would* send (visible in
logs and the `SANDBOX_OUTBOX`) so the whole voice → report → email → SMS →
two-way reply loop runs with no provisioned CDS resources.

## GitHub Codespaces (cloud dev — no local Docker needed)

The repo ships a `.devcontainer`, so a Codespace comes up with Docker, the AWS
CLI, Python 3.12, and `jq` ready — ideal for running the full `./deploy.sh`
(which builds an ARM64 container) without installing Docker locally.

```bash
# From the repo on GitHub: Code → Codespaces → Create codespace on
# feature/cds-agentic-messaging
# Then, inside the Codespace terminal:
aws configure                      # or set AWS_* env vars
./deploy.sh --profile <aws-profile> --password <demo-password>
```

To edit from a local editor instead of the browser, connect over SSH with the
GitHub CLI:

```bash
gh codespace ssh                   # interactive shell
gh codespace ssh --config          # prints an SSH host entry for Remote-SSH editors
```

Any editor with Remote-SSH support can then attach to that host. The deploy
itself is plain shell, so it runs the same in the browser terminal or over SSH.

## Development process

This project was built Scrum / DevSecOps style following an adapted
[Kiro-SDLC-Scrum skill](https://github.com/timwukp/Kiro-SDLC-Scrum-best-practics).
The sprint plan, backlog, and threat model are in
[`docs/SPRINT_PLAN.md`](docs/SPRINT_PLAN.md); deterministic security guard hooks
(credential / PII / prompt-security) live in [`.kiro/`](.kiro).

## License

MIT — see [LICENSE](LICENSE).
