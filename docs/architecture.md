# Architecture — ASA (Autonomous Solutions Architect)

## System Overview

ASA is an autonomous AI Solutions Architect that conducts enterprise cloud discovery
workshops through voice and chat. It replaces weeks of manual pre-sales consulting with
a guided, multi-agent conversation that produces implementation-ready deliverables.

## High-Level Architecture

```
┌────────────────────────────────────┐
│            End User                │
│  Voice / Chat / Web Interface      │
└────────────────┬───────────────────┘
                 │
     Voice       │       Chat
         │               │
┌────────┴───────────────┴────────────────────────┐
│                                                  │
│  Amazon Nova Sonic              React + Tailwind │
│  (Speech-to-Speech AI)          Frontend UI      │
│                                                  │
└──────────────────────┬───────────────────────────┘
                       │
            Amazon API Gateway
          (REST + WebSocket APIs)
                       │
                       ▼
               FastAPI Backend
          Session & API Management
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
    ▼                  ▼                  ▼
Amazon Cognito      DynamoDB           Amazon S3
Authentication   Session Memory   Reports / Diagrams / PDFs
                       │
                       ▼
          Amazon Bedrock AgentCore
            Agent Runtime Layer
                       │
                       ▼
┌──────────────────────────────────────┐
│          Planner Agent               │
│  Observe → Reason → Plan            │
└──────────────────┬───────────────────┘
                   │
            Execution Plan
                   │
                   ▼
          Orchestrator Service
           (Execution Engine)
                   │
    ┌──────────┬───┼────────┬──────────────────┐
    ▼          ▼   ▼        ▼                  ▼
Discovery   Architect  Review       Tool Registry
Agent       Agent      Agent        Execute Tools
Gather      Design     Validate
Req'mts     AWS Arch   Architecture
                   │
    ┌──────────────┼────────────────────┐
    ▼              ▼                    ▼
Bedrock KB       Diagram Gen       Terraform Gen
AWS WAF/CAF      (Mermaid)         Infrastructure IaC
(RAG)
                   │
                   ▼
       Markdown / JSON Reports
```

## Autonomous Reasoning Loop

The system continuously executes:

```
Observe → Reason → Plan → Select Agent → Invoke Tools → Evaluate → Reflect → Repeat
```

The loop terminates when:
1. All required information has been gathered
2. Architecture has been designed
3. Review Agent has approved the design
4. Deliverables have been generated

## Agent Interaction Flow

```
User speaks/types
       │
       ▼
┌─────────────┐    ┌──────────────┐    ┌───────────────┐    ┌──────────────┐
│   ASA       │───▶│   Planner    │───▶│  Agent(s)     │───▶│   Review     │
│ (Interface) │    │   (Brain)    │    │  Discovery/   │    │   (QA Gate)  │
│             │◀───│              │◀───│   Architect   │◀───│              │
└─────────────┘    └──────────────┘    └───────────────┘    └──────────────┘
       │
       ▼
   Response to User
```

## Key Design Principles

### 1. Separation of Concerns
- **Planner** decides WHAT should happen (never calls AWS)
- **Orchestrator** executes the plan (never reasons about architecture)
- **Agents** perform specialized work within their domain
- **Tools** provide capabilities; agents request them through the orchestrator

### 2. Dynamic over Static
- No hardcoded sequential workflows
- Planner dynamically decides next steps based on memory state
- Discovery questions are generated based on gaps, not a questionnaire

### 3. Reflection Loop
- Every architecture recommendation passes through the Review Agent
- If inconsistencies are found, the recommendation loops back for revision
- No final report is generated until review passes

### 4. Auto-Chaining
- When Discovery has enough info → automatically chains to Architect
- When Architect produces design → automatically chains to Review
- Multiple agents can execute in a single user turn

## Technology Stack

| Capability | Technology |
|-----------|-----------|
| Frontend | React + TypeScript + Tailwind CSS |
| Backend API | FastAPI (Python) |
| Voice | Amazon Nova Sonic (bidirectional) |
| TTS Fallback | Amazon Polly |
| STT | Web Speech API (client-side) |
| Text AI | Amazon Nova Pro / Lite |
| Agent Runtime | Amazon Bedrock AgentCore |
| Database | Amazon DynamoDB |
| Storage | Amazon S3 |
| Authentication | Amazon Cognito |
| API | Amazon API Gateway (REST + WebSocket) |
| IaC | Terraform |
| CI/CD | GitHub Actions |
| Hosting | AWS Amplify |
| Knowledge Base | Amazon Bedrock Knowledge Base |

## AWS Service Map

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| Amplify Hosting | Frontend CDN + HTTPS | 5GB storage, 15GB/mo bandwidth |
| API Gateway | REST + WebSocket APIs | 1M calls/mo |
| DynamoDB | Session memory | 25GB storage, 25 WCU/RCU |
| S3 | Reports, diagrams | 5GB storage |
| Cognito | Authentication | 50k MAU |
| Bedrock (Nova Pro) | LLM reasoning | Pay per token |
| Bedrock (Nova Sonic) | Voice conversations | Pay per audio second |
| Polly | Text-to-Speech | 5M chars/mo (12 months) |
| Bedrock Knowledge Base | RAG search | Pay per query |

## Memory Schema

```json
{
  "session_id": "uuid",
  "status": "discovery | architecture | review | complete",
  "customer": { "name": "", "industry": "" },
  "business_requirements": [],
  "technical_requirements": [],
  "known_facts": [],
  "unknown_facts": [],
  "assumptions": [],
  "risks": [],
  "conversation_history": [],
  "architecture": {
    "services": [],
    "decisions": [],
    "diagram_mermaid": "",
    "cost_estimate": {}
  },
  "review": {
    "status": "pending | approved | rejected",
    "findings": [],
    "score": {},
    "revision_count": 0
  },
  "deliverables": {}
}
```

## Deliverables Produced

1. Executive Summary
2. Architecture Decision Records (ADR)
3. AWS Service Mapping with justification
4. Architecture Diagram (Mermaid)
5. Well-Architected Review Scores
6. Risk Register with mitigations
7. Cost Estimate
8. Terraform Code
9. Markdown Report
10. JSON API Output
