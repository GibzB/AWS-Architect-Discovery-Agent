# AWS Discovery Orchestrator

An AI-powered conversational engine that runs AWS architecture discovery
workshops — replacing weeks of manual pre-sales work with a guided, multi-agent
voice dialogue that produces a professional discovery report.

Powered by **Amazon Bedrock AgentCore Runtime** + **Amazon Nova 2 Sonic** (bidirectional voice)
+ **Amazon Nova Pro** (report generation).

## How It Works

1. Customer opens the web UI and starts a voice session.
2. Nova 2 Sonic conducts a real-time voice conversation guided by the Orchestrator prompt.
3. The discovery interview covers: business context, technical workloads, compliance, and growth.
4. On hangup, Nova Pro generates a structured discovery report (architecture recommendations, service breakdown, next steps).
5. The report is stored in DynamoDB and presented in the UI.

## Architecture

Fully serverless — zero cost when idle.

```
Browser (WebSocket) ──► FastAPI / AgentCore Runtime ──► Nova 2 Sonic (bidirectional voice)
                                    │
                                    └──► Nova Pro (report generation)
                                    │
                                    └──► DynamoDB (session + report storage)
                                    │
                                    └──► Bedrock Knowledge Base (RAG - Well-Architected, Landing Zones)
```

| Component | AWS Service |
|-----------|------------|
| Voice conversation | Amazon Nova 2 Sonic (`amazon.nova-2-sonic-v1:0`) |
| Report generation | Amazon Nova Pro (`amazon.nova-pro-v1:0`) |
| Agent runtime | Amazon Bedrock AgentCore Runtime |
| RAG knowledge base | Amazon Bedrock Knowledge Base |
| Session storage | Amazon DynamoDB |
| Frontend hosting | Amazon S3 + CloudFront |
| Presign API | API Gateway + Lambda |
| IaC | AWS CloudFormation |

## Project Structure

```
aws-discovery-orchestrator/
├── agent/
│   ├── server.py            # FastAPI WebSocket server (runs in AgentCore)
│   ├── nova_sonic.py        # Nova 2 Sonic bidirectional stream client
│   ├── report.py            # Post-session report generation via Nova Pro
│   ├── prompts/             # System prompts for the discovery agent
│   │   ├── orchestrator.py  # Main discovery interview prompt
│   │   └── report.py        # Report generation prompt
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── infra/
│   ├── bootstrap.yaml       # CFN: ECR repository (first-time setup)
│   └── template.yaml        # CFN: full stack (AgentCore, API GW, CloudFront, DDB)
├── knowledgebase/           # RAG documents (Well-Architected, Landing Zones)
│   ├── well_architected/
│   ├── landing_zones/
│   └── migration/
├── deploy.sh                # One-command deploy script
├── ARCHITECTURE.md
└── DEPLOYMENT.md
```

## Prerequisites

- AWS CLI configured with a profile
- Docker with buildx support (or use `--prebuilt`)
- `jq` installed
- Amazon Bedrock model access enabled for Nova 2 Sonic and Nova Pro in your region

## Quick Start

```bash
./deploy.sh --profile <your-aws-profile> --password <demo-password>
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for full instructions.

## Local Development

```bash
cd agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-local.txt
cp .env.example .env  # edit with your values
uvicorn local_server:app --reload --port 8000
```

Then open `frontend/index.html` in your browser.

## Cost

All services are pay-per-use with no idle cost.

| Service | Pricing |
|---------|---------|
| Nova 2 Sonic | Per audio second |
| Nova Pro (report) | Per token |
| AgentCore Runtime | Per invocation |
| DynamoDB | Per request (on-demand) |
| Bedrock Knowledge Base | Per query |
| WAF (optional) | ~$7/month flat + $0.60/M requests |

## License

MIT
