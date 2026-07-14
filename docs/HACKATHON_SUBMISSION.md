# Hackathon Submission — Atlas: AI Solutions Architect

## What is Atlas?

Atlas is an autonomous AI Solutions Architect that conducts enterprise cloud discovery
workshops through natural voice and chat conversations. It replaces weeks of manual
pre-sales consulting with a guided, multi-agent dialogue that produces
implementation-ready deliverables.

**Atlas is not a chatbot.** It is an autonomous reasoning system that drives the
conversation, plans dynamically, coordinates specialist agents, reflects on its own
work, and produces complete architectural recommendations.

---

## Problem

Enterprise cloud discovery workshops require:
- Experienced Solutions Architects (scarce, expensive)
- Multiple sessions spanning weeks
- Manual documentation and architecture design
- No automated validation against best practices

**Cost:** $50,000–$150,000+ per engagement in billable hours.

---

## Solution

Atlas conducts the entire workshop autonomously:

1. **Discovery** — Asks adaptive questions to understand the business
2. **Architecture** — Designs a complete AWS solution with justification
3. **Review** — Validates against the Well-Architected Framework
4. **Deliverables** — Produces reports, diagrams, and Terraform code

Total time: **15–30 minutes** instead of weeks.

---

## What Makes This Agentic

### Autonomous Reasoning Loop
```
Observe → Reason → Plan → Select Agent → Invoke Tools → Evaluate → Reflect → Repeat
```

### Multi-Agent Collaboration
| Agent | Role |
|-------|------|
| Planner | Decides what happens next (never acts) |
| Discovery | Identifies gaps, asks questions (never designs) |
| Architect | Designs AWS solutions (never asks questions) |
| Review | Validates and can reject (forces revision) |

### Dynamic Planning
- No hardcoded questionnaire
- Questions adapt based on what's already known
- Planner dynamically routes between agents

### Reflection Loop
- Review Agent can REJECT architecture
- Rejection triggers the Architect to revise
- Loop continues until validation passes
- **This is the key differentiator** — the system validates its own output

### Tool Registry
Agents request capabilities through a registry:
- Knowledge Base Search (RAG)
- Diagram Generator (Mermaid)
- Terraform Generator
- Markdown Report Generator

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   React + Tailwind                    │
└───────────────────────┬──────────────────────────────┘
                        │ REST + WebSocket
┌───────────────────────▼──────────────────────────────┐
│                     FastAPI                           │
│  ┌─────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │  Atlas  │→ │  Planner │→ │  Agent Registry  │   │
│  └─────────┘  └──────────┘  └────────┬─────────┘   │
│                                       │             │
│       ┌───────────┬──────────┬────────┘             │
│       ▼           ▼          ▼                      │
│  ┌──────────┐ ┌────────┐ ┌────────┐                │
│  │Discovery │ │Architect│ │ Review │                │
│  └──────────┘ └────────┘ └────────┘                │
└──────────────────────────────────────────────────────┘
          │              │              │
    ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
    │  Bedrock  │ │ DynamoDB  │ │    S3     │
    │ Nova Pro  │ │ (Sessions)│ │ (Reports) │
    └───────────┘ └───────────┘ └───────────┘
```

---

## AWS Services Used

| Service | Purpose |
|---------|---------|
| Amazon Bedrock (Nova Pro) | LLM reasoning for all agents |
| Amazon Bedrock (Nova Sonic) | Bidirectional voice |
| Amazon Bedrock Knowledge Base | RAG over Well-Architected docs |
| Amazon DynamoDB | Session memory persistence |
| Amazon S3 | Report storage, frontend hosting |
| Amazon Cognito | Authentication |
| Amazon Polly | Text-to-Speech for voice mode |
| Amazon CloudFront | Frontend CDN |
| AWS Secrets Manager | API key storage |

---

## Deliverables Produced

1. ✅ Executive Summary
2. ✅ Architecture Decisions (ADRs)
3. ✅ AWS Service Mapping with justification
4. ✅ Architecture Diagram (Mermaid)
5. ✅ Well-Architected Review Scores
6. ✅ Risk Register with mitigations
7. ✅ Cost Estimate
8. ✅ Terraform Code
9. ✅ Markdown Report
10. ✅ JSON API Output

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript + Tailwind CSS |
| Backend | FastAPI (Python 3.10+) |
| AI | Amazon Bedrock (Nova Pro, Nova Sonic, Polly) |
| Database | Amazon DynamoDB |
| Storage | Amazon S3 |
| Auth | Amazon Cognito |
| IaC | Terraform |
| CI/CD | GitHub Actions |

---

## Running Locally

```bash
# Backend
cd apps/backend
source .venv/bin/activate
export AWS_PROFILE=K1-Kitstek-Billy
uvicorn app.main:app --reload --port 8000

# Frontend
cd apps/frontend
npm run dev
```

Open http://localhost:5173

---

## Demo Scenario

**Input:** "We're a healthcare SaaS company with 50,000 users. We require HIPAA compliance, 99.99% availability, and disaster recovery."

**Atlas:**
1. Conducts adaptive discovery (asks about PHI, encryption needs, RPO/RTO)
2. Identifies compliance gaps
3. Generates multi-region architecture with HIPAA-compliant services
4. Review Agent rejects (single-region insufficient for stated RTO)
5. Architect revises to multi-region
6. Review approves
7. Full report + Terraform + diagram generated

**Duration:** ~3 minutes for complete end-to-end demonstration.

---

## What's Next

- Full Nova Sonic bidirectional voice (requires Python 3.12+ runtime)
- Step Functions orchestration for production workloads
- EventBridge for async agent events
- Bedrock Knowledge Base with AWS reference architectures
- PDF report generation
- Multi-cloud architecture support

---

## Team

Built with ❤️ using Amazon Bedrock, AgentCore patterns, and autonomous AI principles.
