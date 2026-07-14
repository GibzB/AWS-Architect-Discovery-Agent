# Architecture — Atlas: AI Solutions Architect

## System Overview

Atlas is an autonomous AI Solutions Architect that conducts enterprise cloud discovery
workshops through voice and chat. It replaces weeks of manual pre-sales consulting with
a guided, multi-agent conversation that produces implementation-ready deliverables.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                                  │
│                                                                         │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │  React + TypeScript + Tailwind                                   │  │
│   │  • Chat Interface                                                │  │
│   │  • Voice Controls (Nova Sonic WebSocket)                         │  │
│   │  • Session Management                                            │  │
│   │  • Report Viewer                                                 │  │
│   │  • Architecture Diagram Viewer                                   │  │
│   └──────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                    WebSocket + REST (API Gateway)
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│                           API LAYER                                      │
│                                                                         │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │  FastAPI                                                         │  │
│   │  • POST /sessions          (create session)                      │  │
│   │  • POST /sessions/{id}/messages  (send message)                  │  │
│   │  • GET  /sessions/{id}     (get session state)                   │  │
│   │  • GET  /sessions/{id}/report    (get report)                    │  │
│   │  • GET  /sessions/{id}/diagram   (get diagram)                   │  │
│   │  • WS   /sessions/{id}/voice     (voice stream)                  │  │
│   └──────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│                       ORCHESTRATION LAYER                                │
│                                                                         │
│   ┌─────────────────────┐    ┌─────────────────────────────────────┐   │
│   │  Atlas               │    │  Planner                            │   │
│   │  (Conversation Mgr)  │───▶│  (Reasoning Engine)                 │   │
│   │                      │    │                                     │   │
│   │  • Stream responses  │    │  • Observe memory state             │   │
│   │  • Explain reasoning │    │  • Decide next agent                │   │
│   │  • Workshop flow     │    │  • Determine if done                │   │
│   │  • Never designs     │    │  • Never calls AWS                  │   │
│   └─────────────────────┘    └──────────────┬──────────────────────┘   │
│                                              │                          │
│                              ┌───────────────▼────────────────┐         │
│                              │        Tool Registry           │         │
│                              │  • KB Search                   │         │
│                              │  • Diagram Generator           │         │
│                              │  • Terraform Generator         │         │
│                              │  • Markdown Generator          │         │
│                              └───────────────┬────────────────┘         │
│                                              │                          │
└──────────────────────────────────────────────┼──────────────────────────┘
                                               │
┌──────────────────────────────────────────────▼──────────────────────────┐
│                         AGENT LAYER                                      │
│                                                                         │
│   ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐   │
│   │ Discovery Agent │  │ Architect Agent│  │ Review Agent           │   │
│   │                 │  │                │  │                        │   │
│   │ • Identify gaps │  │ • AWS services │  │ • Validate HA          │   │
│   │ • Ask questions │  │ • Decisions    │  │ • Validate Security    │   │
│   │ • Update memory │  │ • Diagrams     │  │ • Validate Networking  │   │
│   │ • Adaptive      │  │ • Risks        │  │ • Reject or Approve    │   │
│   └────────────────┘  └────────────────┘  └────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│                        DATA LAYER                                        │
│                                                                         │
│   ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐   │
│   │ DynamoDB        │  │ S3             │  │ Bedrock Knowledge Base │   │
│   │                 │  │                │  │                        │   │
│   │ • Sessions      │  │ • Reports      │  │ • Well-Architected     │   │
│   │ • Memory state  │  │ • Diagrams     │  │ • Landing Zones        │   │
│   │ • Conversations │  │ • Terraform    │  │ • Reference Archs      │   │
│   └────────────────┘  └────────────────┘  └────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
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
┌─────────┐     ┌─────────┐     ┌───────────┐     ┌───────────┐     ┌────────┐
│ Customer│     │  Atlas  │     │  Planner  │     │  Agent(s) │     │ Review │
└────┬────┘     └────┬────┘     └─────┬─────┘     └─────┬─────┘     └───┬────┘
     │               │                │                  │               │
     │  message      │                │                  │               │
     ├──────────────►│                │                  │               │
     │               │  observe       │                  │               │
     │               ├───────────────►│                  │               │
     │               │                │                  │               │
     │               │  plan          │                  │               │
     │               │◄───────────────┤                  │               │
     │               │                │                  │               │
     │               │  invoke agent  │                  │               │
     │               ├──────────────────────────────────►│               │
     │               │                │                  │               │
     │               │  agent output  │                  │               │
     │               │◄──────────────────────────────────┤               │
     │               │                │                  │               │
     │               │  (if architecture ready)          │  validate     │
     │               ├──────────────────────────────────────────────────►│
     │               │                │                  │               │
     │               │                │                  │  approved/    │
     │               │◄─────────────────────────────────────rejected     │
     │               │                │                  │               │
     │  response     │                │                  │               │
     │◄──────────────┤                │                  │               │
     │               │                │                  │               │
```

## Key Design Principles

### 1. Separation of Concerns
- **Planner** decides WHAT should happen (never calls AWS)
- **Orchestrator (Atlas)** executes the plan (never reasons about architecture)
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

### 4. Persistent Memory
- Single source of truth for session state
- All agents read from and write to the same memory structure
- Enables context continuity across the entire workshop

## Technology Stack

| Capability | Technology |
|-----------|-----------|
| Frontend | React + TypeScript + Tailwind CSS |
| Backend API | FastAPI (Python 3.12) |
| Voice | Amazon Nova Sonic (bidirectional WebSocket) |
| Text AI | Amazon Nova Pro / Lite |
| Agent Runtime | Amazon Bedrock AgentCore |
| Database | Amazon DynamoDB |
| Storage | Amazon S3 |
| Authentication | Amazon Cognito |
| API | API Gateway (REST + WebSocket) |
| IaC | Terraform |
| CI/CD | GitHub Actions |
| Monitoring | CloudWatch + X-Ray |
| Knowledge Base | Amazon Bedrock Knowledge Base |
| Secrets | AWS Secrets Manager |

## AWS Service Map

```
┌─────────────────────────────────────────────────────────┐
│                     AWS Account                          │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │ CloudFront  │  │ API Gateway │  │ Cognito      │   │
│  │ (Frontend)  │  │ (REST + WS) │  │ (Auth)       │   │
│  └──────┬──────┘  └──────┬──────┘  └──────────────┘   │
│         │                 │                             │
│  ┌──────▼──────┐  ┌──────▼──────┐                     │
│  │ S3          │  │ Bedrock     │                     │
│  │ (Static)    │  │ AgentCore   │                     │
│  └─────────────┘  │ Runtime     │                     │
│                    └──────┬──────┘                     │
│                           │                            │
│         ┌─────────────────┼─────────────────┐         │
│         │                 │                 │         │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐  │
│  │ Nova Sonic  │  │ Nova Pro    │  │ Knowledge   │  │
│  │ (Voice)     │  │ (Text/Plan) │  │ Base (RAG)  │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
│                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ DynamoDB    │  │ S3          │  │ Secrets Mgr │  │
│  │ (Sessions)  │  │ (Reports)   │  │ (API Keys)  │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
│                                                       │
│  ┌─────────────┐  ┌─────────────┐                    │
│  │ CloudWatch  │  │ X-Ray       │                    │
│  │ (Logs)      │  │ (Tracing)   │                    │
│  └─────────────┘  └─────────────┘                    │
│                                                       │
└───────────────────────────────────────────────────────┘
```

## Memory Schema

```json
{
  "session_id": "uuid",
  "created_at": "iso8601",
  "updated_at": "iso8601",
  "status": "discovery | architecture | review | complete",
  "customer": {
    "name": "",
    "industry": "",
    "company_size": "",
    "region": ""
  },
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
    "revision_count": 0
  },
  "questions_remaining": [],
  "deliverables": {
    "report_md": "",
    "diagram_url": "",
    "terraform_url": "",
    "json_output": {}
  },
  "agent_trace": []
}
```

## Deliverables Produced

1. Executive Summary
2. Architecture Decision Record (ADR)
3. Business Requirements Document
4. Functional Requirements
5. Non-Functional Requirements
6. Architecture Diagram (Mermaid)
7. AWS Service Mapping
8. Security Assessment
9. Cost Estimate
10. Risk Register
11. Assumptions Log
12. Migration Plan
13. Terraform Code
14. Markdown Report
15. JSON API Output
