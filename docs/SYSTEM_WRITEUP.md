# AWS Discovery Orchestrator — System Writeup

## What It Is

The AWS Discovery Orchestrator is an AI-powered voice agent that conducts architecture discovery workshops with clients in real-time. It replaces the traditional multi-week pre-sales discovery process — where a solutions architect manually interviews stakeholders, documents requirements, and produces architecture recommendations — with a single 10-15 minute voice conversation that generates a professional discovery report instantly.

The system uses Amazon Nova 2 Sonic for natural, bidirectional voice conversation and Amazon Nova Pro for intelligent report generation, all running serverlessly on Amazon Bedrock AgentCore Runtime.

---

## The Problem It Solves

### Traditional Discovery Workflow

1. **Schedule meetings** — 1-2 weeks of calendar coordination
2. **Conduct interviews** — 2-4 hours of architect time per session
3. **Document findings** — 4-8 hours of manual note-taking and structuring
4. **Research services** — 2-4 hours mapping requirements to AWS services
5. **Write the report** — 8-16 hours producing the final deliverable
6. **Review and revise** — 2-4 additional hours

**Total: 2-4 weeks and 20-40 hours of senior architect time per engagement.**

### With AWS Discovery Orchestrator

1. **Client clicks "Start Discovery"** — immediate
2. **AI architect conducts the interview** — 10-15 minutes, voice-based
3. **Report generated automatically** — instant, on session end
4. **Client receives structured recommendations** — within seconds

**Total: 15 minutes of client time. Zero architect time for initial discovery.**

---

## Value Proposition

### For Solutions Architects / Pre-Sales Teams

- **10x throughput** — handle 10+ discoveries per day instead of 1-2 per week
- **Consistent quality** — every interview follows the same structured methodology
- **Always available** — clients can run a discovery at 2am on a Sunday
- **No scheduling overhead** — eliminates the back-and-forth of meeting coordination
- **Instant deliverables** — the report is ready before the call ends

### For Clients / Prospects

- **Immediate value** — get architecture recommendations in minutes, not weeks
- **Low commitment** — 15 minutes of conversation vs. multi-hour workshops
- **Natural interaction** — speak naturally instead of filling out intake forms
- **Professional output** — structured report with service recommendations, cost estimates, and next steps

### For the Business

- **Reduced cost per engagement** — from $2,000-5,000 (architect time) to $0.15-0.50 (AI costs)
- **Scalable lead qualification** — pre-qualify prospects before committing senior architects
- **Data capture** — every discovery session is transcribed and stored for analysis
- **Faster pipeline** — compress the sales cycle from weeks to days

---

## How It Works — Technical Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (Client)                         │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │ Mic Capture  │───►│  WebSocket   │───►│  Audio Playback   │  │
│  │ (16kHz PCM)  │    │  (base64)    │    │  (LPCM → Speaker) │  │
│  └─────────────┘    └──────┬───────┘    └───────────────────┘  │
└─────────────────────────────┼───────────────────────────────────┘
                              │ SigV4 Presigned WSS
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               Amazon Bedrock AgentCore Runtime                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    FastAPI Server                         │    │
│  │  ┌───────────┐     ┌──────────────┐     ┌───────────┐  │    │
│  │  │ WebSocket │────►│ Nova 2 Sonic │────►│  Report   │  │    │
│  │  │  Handler  │     │ (Bidi Voice) │     │ Generator │  │    │
│  │  └───────────┘     └──────────────┘     └─────┬─────┘  │    │
│  └─────────────────────────────────────────────────┼────────┘    │
└─────────────────────────────────────────────────────┼────────────┘
                                                      │
                              ┌────────────────────────┼─────────┐
                              ▼                        ▼         │
                    ┌──────────────┐          ┌──────────────┐   │
                    │  Nova Pro    │          │  DynamoDB    │   │
                    │ (Report Gen) │          │ (Sessions)   │   │
                    └──────────────┘          └──────────────┘   │
```

### Session Lifecycle

1. **Presign** — Frontend calls API Gateway → Lambda generates a SigV4-presigned WebSocket URL pointing to AgentCore
2. **Connect** — Browser opens WebSocket to AgentCore; sends `{"type": "start"}`
3. **Voice Loop** — Nova 2 Sonic runs a bidirectional audio stream:
   - System prompt instructs it to conduct a phased discovery interview
   - Client audio is streamed in; agent responses stream back as audio + transcript
   - The agent asks one question per turn across 5 phases (Business, Technical, Compliance, Growth, Recommendation)
4. **Hangup** — Client ends the session; triggers report generation
5. **Report** — Nova Pro receives the full transcript and generates:
   - A JSON digest (summary, recommended services, action items) for the UI cards
   - A full Markdown report (architecture, service breakdown, cost estimates, next steps)
6. **Persist** — Session transcript and report stored in DynamoDB

---

## Discovery Interview Phases

The AI architect follows a structured methodology:

| Phase | Focus | Example Questions |
|-------|-------|-------------------|
| 1. Business Context | Industry, size, drivers | "What industry are you in? What's driving your move to AWS?" |
| 2. Technical Workloads | Applications, data, integrations | "What are the primary applications that need to run on AWS?" |
| 3. Compliance & Security | Regulatory, data residency, identity | "Are there any compliance requirements like GDPR or HIPAA?" |
| 4. Growth & Future | Scale projections, new workloads | "What growth do you expect over the next 2-3 years?" |
| 5. Recommendation | Summary + architecture sketch | "Based on what you've told me, I'd recommend..." |

The agent adapts its questioning based on client answers — if something is unclear, it asks follow-up questions before moving on.

---

## AWS Services Cost Breakdown

### Per-Session Costs (estimated for a typical 12-minute discovery)

| Service | Usage per Session | Unit Price | Cost per Session |
|---------|-------------------|------------|------------------|
| **Nova 2 Sonic** (voice) | ~12 min audio (~720 audio-seconds) | ~$0.33/1M input tokens, $2.75/1M output tokens | ~$0.05 - $0.15 |
| **Nova Pro** (report) | ~3,000 input tokens + ~2,000 output | $0.80/1M input, $3.20/1M output | ~$0.009 |
| **AgentCore Runtime** | ~12 min active compute | Consumption-based (GB-seconds) | ~$0.02 - $0.05 |
| **DynamoDB** | 2-3 write operations | $1.25/million writes | ~$0.000003 |
| **API Gateway** | 1 presign request | $1.00/million requests | ~$0.000001 |
| **Lambda** | 1 invocation (128MB, <1s) | $0.20/million invocations | ~$0.0000002 |

**Total estimated cost per discovery session: $0.08 - $0.25**

### Monthly Infrastructure Costs (idle / low-traffic)

| Service | Cost When Idle | Notes |
|---------|----------------|-------|
| AgentCore Runtime | $0.00 | Scales to zero |
| DynamoDB | $0.00 | On-demand, pay per request |
| S3 (frontend) | ~$0.03 | ~1MB of static files |
| CloudFront | $0.00 | Free tier covers low traffic |
| API Gateway | $0.00 | Free tier: 1M requests/month |
| Lambda | $0.00 | Free tier: 1M invocations/month |
| WAF (optional) | ~$7.00 | Flat fee if enabled |

**Total idle cost: $0.03/month (or ~$7/month with WAF)**

### Volume Pricing Scenarios

| Sessions/Month | Est. Monthly Cost | Cost per Session | Equivalent Architect Hours Saved |
|----------------|-------------------|------------------|----------------------------------|
| 10 | $1 - $3 | ~$0.15 | 40-80 hours |
| 100 | $10 - $25 | ~$0.15 | 400-800 hours |
| 1,000 | $80 - $250 | ~$0.15 | 4,000-8,000 hours |
| 10,000 | $800 - $2,500 | ~$0.15 | 40,000-80,000 hours |

### Cost Comparison: AI vs. Human Architect

| Metric | Human Architect | AWS Discovery Orchestrator |
|--------|-----------------|---------------------------|
| Cost per discovery | $2,000 - $5,000 | $0.08 - $0.25 |
| Time to deliver report | 1-4 weeks | Instant |
| Availability | Business hours | 24/7/365 |
| Sessions per day | 1-2 | Unlimited |
| Consistency | Varies by person | Identical methodology every time |

---

## Security Model

- **SigV4 presigned URLs** — WebSocket connections are authenticated with short-lived (5-minute) AWS Signature V4 tokens
- **HTTP Basic Auth** — optional demo password protection on the CloudFront frontend
- **IAM least-privilege** — AgentCore role scoped to specific ECR repos, Bedrock models, and DynamoDB table
- **Private S3** — frontend bucket is not publicly accessible; served only through CloudFront OAC
- **AWS WAF** (optional) — rate limiting at 300 requests per 5 minutes per IP, plus AWS managed common rule set
- **No secrets in code** — all credentials managed through IAM roles and environment variables

---

## Deployment Model

The entire stack deploys with a single command:

```bash
./deploy.sh --profile my-aws-profile --password demo123 --waf
```

**Infrastructure as Code** — two CloudFormation stacks:
1. `bootstrap.yaml` — ECR repository (deploy once)
2. `template.yaml` — full application stack (AgentCore, API Gateway, Lambda, DynamoDB, S3, CloudFront, WAF)

**Container** — ARM64 Python 3.12 image with FastAPI, pushed to ECR, pulled by AgentCore Runtime.

**Zero-ops** — no servers to patch, no clusters to manage, no auto-scaling to configure. AgentCore handles all of it.

---

## Future Enhancements

1. **Bedrock Knowledge Base integration** — RAG-augment recommendations with AWS Well-Architected Framework, Landing Zone patterns, and service-specific documentation
2. **Multi-language support** — Nova 2 Sonic supports multiple languages; add language selection to the UI
3. **Session history** — dashboard showing past discovery sessions with search/filter
4. **PDF export** — generate downloadable PDF reports with architecture diagrams
5. **CRM integration** — push discovery results to Salesforce/HubSpot via EventBridge
6. **Custom prompts** — allow teams to customize the discovery flow for their specific practice areas (migration, modernization, data & analytics)
7. **Follow-up sessions** — resume a previous discovery to dive deeper into specific areas

---

## References

- [Amazon Nova Pricing](https://aws.amazon.com/nova/pricing/)
- [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)
- [Amazon Bedrock AgentCore Pricing](https://aws.amazon.com/bedrock/agentcore/pricing/)
- [Amazon Nova 2 Sonic Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-2-sonic.html)
- [AgentCore Runtime Blog Post](https://aws.amazon.com/blogs/machine-learning/securely-launch-and-scale-your-agents-and-tools-on-amazon-bedrock-agentcore-runtime/)
