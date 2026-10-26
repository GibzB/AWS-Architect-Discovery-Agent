# Atlas — AI Solutions Architect

> An autonomous AI Solutions Architect that conducts enterprise cloud discovery
> workshops through natural voice and chat conversations, producing
> implementation-ready deliverables.

Atlas replaces weeks of manual pre-sales consulting with a guided, multi-agent
voice dialogue that behaves like a Principal Solutions Architect from AWS
Professional Services.

## What Makes Atlas Agentic

Atlas is **not a chatbot**. It is an autonomous reasoning system that:

- **Drives the conversation** — decides what to ask, not just responds
- **Plans dynamically** — no hardcoded questionnaire; adapts to each customer
- **Coordinates specialists** — routes work to Discovery, Architect, and Review agents
- **Reflects on its own work** — Review Agent can reject and force revision
- **Produces deliverables** — architecture diagrams, Terraform, reports

### Autonomous Loop

```
Observe → Reason → Plan → Select Agent → Invoke Tools → Evaluate → Reflect → Repeat
```

The loop continues until customer objectives are satisfied and the Review Agent
approves the architecture.

## Architecture

```
Customer
    │
    ▼
┌─────────┐     ┌─────────┐     ┌───────────────┐
│  Atlas  │────▶│ Planner │────▶│ Tool Registry │
│  (Conv) │     │ (Brain) │     └───────┬───────┘
└─────────┘     └─────────┘             │
                                        ▼
                    ┌───────────────────────────────────┐
                    │                                   │
              ┌─────▼─────┐  ┌──────▼──────┐  ┌───────▼───────┐
              │ Discovery  │  │  Architect  │  │    Review     │
              │   Agent    │  │    Agent    │  │    Agent      │
              └────────────┘  └─────────────┘  └───────────────┘
                                        │
                                        ▼
                              ┌────────────────────┐
                              │    Deliverables    │
                              │  • Report (MD)     │
                              │  • Diagram         │
                              │  • Terraform       │
                              │  • JSON Output     │
                              └────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript + Tailwind CSS |
| Backend | FastAPI (Python 3.12) |
| Voice | Amazon Nova Sonic |
| AI/LLM | Amazon Nova Pro / Lite |
| Runtime | Amazon Bedrock AgentCore |
| Database | Amazon DynamoDB |
| Storage | Amazon S3 |
| Auth | Amazon Cognito |
| IaC | Terraform |
| CI/CD | GitHub Actions |
| RAG | Amazon Bedrock Knowledge Base |

## Project Structure

```
atlas-discovery/
├── apps/
│   ├── backend/          # FastAPI application
│   └── frontend/         # React + TypeScript UI
├── packages/
│   ├── agent_sdk/        # Base agent classes and contracts
│   ├── shared/           # Shared utilities
│   ├── prompts/          # System prompts for all agents
│   └── schemas/          # Pydantic request/response models
├── agents/
│   ├── planner/          # Decides what happens next
│   ├── discovery/        # Asks adaptive questions
│   ├── architect/        # Designs AWS architecture
│   └── review/           # Validates and approves/rejects
├── tools/
│   ├── rag/              # Knowledge Base search
│   ├── diagram/          # Mermaid diagram generator
│   ├── terraform/        # Terraform code generator
│   └── markdown/         # Report generator
├── memory/               # Session memory management
├── infra/
│   └── terraform/        # AWS infrastructure
├── docs/
│   ├── architecture.md   # System architecture
│   ├── agent-contracts.md # Agent interfaces
│   └── api.md            # REST/WebSocket API spec
├── tests/
├── .github/workflows/    # CI/CD
├── scripts/
│   └── bootstrap.sh      # Project setup script
└── Makefile
```

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd aws-architect-discovery-agent

# Bootstrap everything
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh

# Start development
make backend    # FastAPI on :8000
make frontend   # React on :5173
```

## Development Phases

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Architecture & Contracts | ✅ Complete |
| 2 | Project Skeleton | ✅ Complete |
| 3 | Infrastructure (Terraform) | ✅ Complete |
| 4 | Backend API + Orchestrator | ✅ Complete |
| 5 | Agent Framework (Planner, Discovery, Architect, Review) | ✅ Complete |
| 6 | Voice (Nova Sonic / Polly) | ✅ Complete |
| 7 | Frontend | ✅ Complete |
| 8 | Testing | ✅ Complete |
| 9 | Deployment | ✅ Complete |
| 10 | Optimisation | ✅ Complete |

## Key Design Decisions

1. **Planner ≠ Orchestrator** — Planner reasons, Atlas executes. Strict separation.
2. **Dynamic over static** — No hardcoded question sequences.
3. **Reflection loop** — Architecture must pass Review Agent before report generation.
4. **Tool registry** — Agents never call AWS directly; they request tools.
5. **Persistent memory** — Single session state object, all agents read/write.

## License

MIT
