# AWS Discovery Orchestrator — Architecture

Fully serverless architecture on AWS. No EC2 instances, no ECS clusters, no
persistent servers to manage.

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
