# Hackathon Submission — AWS Discovery Orchestrator

---

## About the Project (Project Story)

### Inspiration

As someone who works in the cloud solutions space, I've seen how the architecture discovery process is painfully slow. A solutions architect spends weeks scheduling meetings, interviewing stakeholders, researching services, and writing reports — all before a single resource is provisioned. I asked myself: what if an AI could conduct that entire discovery interview in real-time over voice, then instantly produce the report?

The Azure Discovery Orchestrator project (which I previously built) proved the concept works — but it relied on multiple Azure services stitched together (Speech SDK for STT/TTS, OpenAI for reasoning, Cosmos DB, etc.). When I discovered Amazon Bedrock AgentCore and Nova 2 Sonic, I realized I could build something far simpler and more elegant: a single model that handles the entire voice conversation natively, running on a fully serverless runtime with zero infrastructure to manage.

### What It Does

The AWS Discovery Orchestrator is a voice-powered AI agent that conducts architecture discovery workshops with clients. A user opens the web app, clicks "Start Discovery Session," and has a natural voice conversation with an AI architect that:

1. Asks structured questions about their business, technical needs, compliance requirements, and growth plans
2. Adapts follow-up questions based on answers
3. Generates a complete architecture recommendation report the moment the session ends

A typical 12-minute conversation replaces 20-40 hours of senior architect work and produces a professional report instantly.

### How I Built It

**Architecture:**
- **Amazon Nova 2 Sonic** handles the entire voice conversation — bidirectional audio streaming means no separate STT or TTS services needed
- **Amazon Nova Pro** generates the post-session report (architecture recommendations, AWS service breakdown, cost estimates, next steps)
- **Amazon Bedrock AgentCore Runtime** hosts the agent container serverlessly — scales to zero, no servers to manage
- **AWS Lambda + API Gateway** generates SigV4 presigned WebSocket URLs for secure browser-to-agent connections
- **Amazon DynamoDB** stores session transcripts and generated reports
- **Amazon S3 + CloudFront** serves the frontend globally with HTTPS
- **AWS CloudFormation** defines the entire infrastructure as code

**Tech stack:**
- Python 3.12 + FastAPI (agent backend)
- Vanilla HTML/CSS/JS (frontend — intentionally lightweight)
- Docker (ARM64 container for AgentCore)
- Single deploy script that stands up everything in one command

**Key design decision:** Instead of the multi-agent routing pattern (orchestrator → business agent → architect agent → security agent), I use Nova 2 Sonic's native conversational abilities with a comprehensive system prompt that covers all discovery phases. This eliminates inter-agent latency and produces a more natural conversation flow. Nova Pro then acts as the "report agent" post-session.

### Challenges

1. **AgentCore WebSocket proxy behavior** — The proxy only delivers server→client messages while handling a client frame. I had to implement a message queue pattern where Nova Sonic callbacks enqueue messages, and the main loop flushes them on each client frame.

2. **Nova 2 Sonic bidirectional stream protocol** — The event-based protocol (contentStart/textInput/audioInput/contentEnd) requires precise sequencing. Getting the session start → system prompt → greeting trigger → audio block open sequence right took careful study of the SDK.

3. **Transcript deduplication** — Nova Sonic sometimes echoes transcript events. I implemented a seen-set to suppress duplicates.

4. **Cold starts** — AgentCore containers take 30-60 seconds on first invocation. I documented this clearly and recommend a warm-up call before demos.

### What I Learned

- Bedrock AgentCore Runtime is a genuinely zero-ops way to deploy AI agents — no ECS clusters, no auto-scaling configs, no load balancers
- Nova 2 Sonic's native bidirectional voice eliminates an entire class of complexity (separate STT → LLM → TTS pipelines)
- The SigV4 presigned URL pattern for WebSocket auth is elegant and avoids putting credentials in the frontend
- CloudFormation custom resource types (`AWS::BedrockAgentCore::Runtime`) make IaC for new services straightforward

---

## Built With

- Amazon Bedrock (Nova 2 Sonic, Nova Pro)
- Amazon Bedrock AgentCore Runtime
- AWS Lambda
- Amazon API Gateway
- Amazon DynamoDB
- Amazon S3
- Amazon CloudFront
- AWS CloudFormation
- AWS IAM
- AWS WAF
- Python
- FastAPI
- Docker

---

## Links and Media

- **Demo URL:** *(CloudFront URL after deployment)*
- **GitHub / Repository URL:** https://github.com/GibzB/AWS-Architect-Discovery-Agent

---

## Video Demo Link

*(Record a 2-3 minute demo showing: clicking Start → having a brief voice conversation → seeing the transcript appear live → ending session → seeing the report generate)*

---

## Technology Partner: AWS

### How I Used AWS

The entire application runs exclusively on AWS services with a fully serverless architecture:

**Amazon Bedrock — Nova 2 Sonic** is the core of the system. It powers the real-time bidirectional voice conversation between the user and the AI architect. The model receives a system prompt that structures the discovery interview into 5 phases (business context, technical workloads, compliance, growth, recommendation) and conducts the entire conversation via streaming audio — no separate speech-to-text or text-to-speech services needed.

**Amazon Bedrock — Nova Pro** generates the post-session discovery report. After the voice conversation ends, the full transcript is sent to Nova Pro with a report-generation prompt. It produces a structured Markdown document with architecture recommendations, AWS service breakdown with cost estimates, security considerations, and concrete next steps.

**Amazon Bedrock AgentCore Runtime** hosts the agent as a serverless container. It manages scaling (including scale-to-zero), WebSocket proxying with SigV4 authentication, health checks, and container lifecycle — all without any ECS/EKS/EC2 infrastructure. The container runs a FastAPI server that bridges the browser WebSocket to the Nova 2 Sonic bidirectional stream.

**AWS Lambda + Amazon API Gateway** provide the presign API. A single Lambda function generates SigV4-presigned WebSocket URLs that allow the browser to securely connect to AgentCore without exposing AWS credentials client-side.

**Amazon DynamoDB** persists session data — transcripts and generated reports — with on-demand billing (zero cost when idle).

**Amazon S3 + Amazon CloudFront** serve the static frontend (HTML/JS/CSS) globally over HTTPS with Origin Access Control. A CloudFront Function handles optional HTTP Basic Auth for demo access.

**AWS WAF** (optional) adds rate limiting and AWS managed common rules for production protection.

**AWS CloudFormation** defines the entire infrastructure as code in two templates, deployable with a single shell script.

The result is a system that costs $0.08-0.25 per discovery session, scales to zero when not in use, and requires zero operational maintenance.
