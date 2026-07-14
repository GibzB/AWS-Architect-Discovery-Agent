# Agent Contracts

Every agent in the Atlas system implements a uniform contract. This document
defines the interface, responsibilities, and boundaries for each agent.

## Base Agent Contract

```python
class BaseAgent:
    """All agents implement this lifecycle."""

    name: str
    description: str
    available_tools: list[str]
    memory_access: list[str]  # read, write, or both
    decision_criteria: dict
    success_criteria: dict
    escalation_criteria: dict

    async def execute(self, context: AgentContext) -> AgentOutput:
        """Main entry point. Runs the full agent lifecycle."""
        ...

    async def reason(self, context: AgentContext) -> Reasoning:
        """Analyse memory state and determine what to do."""
        ...

    async def plan(self, context: AgentContext) -> Plan:
        """Produce a concrete action plan."""
        ...

    async def invoke_tools(self, plan: Plan) -> ToolResults:
        """Request tools through the orchestrator."""
        ...

    async def reflect(self, results: ToolResults) -> Reflection:
        """Evaluate results and decide if more work is needed."""
        ...
```

---

## Planner Agent

| Field | Value |
|-------|-------|
| **Name** | `PlannerAgent` |
| **Role** | Decides WHAT should happen next |
| **Inputs** | Session memory (full read access) |
| **Outputs** | `PlannerDecision` — next agent, reason, priority |
| **Available Tools** | None (reasoning only) |
| **Memory Access** | Read-only |
| **Decision Criteria** | Evaluates known_facts vs unknown_facts, checks if architecture exists, checks review status |
| **Success Criteria** | A valid next-step decision is produced |
| **Escalation Criteria** | Circular loop detected (same decision 3+ times) |

### Output Schema

```json
{
  "next_agent": "DiscoveryAgent | ArchitectAgent | ReviewAgent | null",
  "reason": "string — why this agent was selected",
  "priority": "high | medium | low",
  "context_for_agent": {
    "focus_area": "string",
    "specific_questions": []
  },
  "workshop_complete": false
}
```

### Rules
- Never calls AWS services
- Never generates architecture
- Never asks the customer questions directly
- Only produces planning decisions

---

## Discovery Agent

| Field | Value |
|-------|-------|
| **Name** | `DiscoveryAgent` |
| **Role** | Identifies missing information and generates questions |
| **Inputs** | Session memory, planner context (focus area) |
| **Outputs** | `DiscoveryOutput` — questions to ask, facts discovered |
| **Available Tools** | Knowledge Base Search |
| **Memory Access** | Read + Write (updates known_facts, unknown_facts) |
| **Decision Criteria** | Compares required info vs known_facts, identifies gaps |
| **Success Criteria** | At least one new fact added to memory OR a targeted question generated |
| **Escalation Criteria** | Customer unable/unwilling to answer after 2 attempts |

### Output Schema

```json
{
  "questions": [
    {
      "question": "string",
      "category": "business | technical | compliance | operations",
      "reason": "string — why this question matters",
      "priority": "critical | important | nice_to_have"
    }
  ],
  "facts_discovered": [
    {
      "fact": "string",
      "source": "customer | inferred | knowledge_base",
      "confidence": 0.0-1.0
    }
  ],
  "gaps_remaining": ["string"]
}
```

### Rules
- Never generates architecture
- Never makes assumptions without flagging them
- Questions must be adaptive (based on previous answers)
- Must explain WHY it needs each piece of information

---

## Architect Agent

| Field | Value |
|-------|-------|
| **Name** | `ArchitectAgent` |
| **Role** | Designs AWS architecture based on requirements |
| **Inputs** | Session memory (requirements, known_facts, constraints) |
| **Outputs** | `ArchitectureOutput` — services, decisions, diagram, risks |
| **Available Tools** | Knowledge Base Search, Diagram Generator, Terraform Generator |
| **Memory Access** | Read + Write (writes architecture decisions) |
| **Decision Criteria** | Sufficient requirements exist to produce a viable architecture |
| **Success Criteria** | Architecture covers all stated requirements with justification |
| **Escalation Criteria** | Contradictory requirements detected, insufficient info to proceed |

### Output Schema

```json
{
  "services": [
    {
      "service": "string",
      "purpose": "string",
      "justification": "string",
      "alternatives_considered": ["string"]
    }
  ],
  "decisions": [
    {
      "decision": "string",
      "rationale": "string",
      "trade_offs": "string",
      "reversibility": "high | medium | low"
    }
  ],
  "diagram_mermaid": "string",
  "risks": [
    {
      "risk": "string",
      "impact": "high | medium | low",
      "likelihood": "high | medium | low",
      "mitigation": "string"
    }
  ],
  "cost_estimate": {
    "monthly_low": 0,
    "monthly_high": 0,
    "assumptions": ["string"]
  },
  "non_functional": {
    "availability_target": "string",
    "rto": "string",
    "rpo": "string",
    "regions": ["string"]
  }
}
```

### Rules
- Only designs when the Planner sends it
- Must justify every service choice
- Must identify risks and trade-offs
- Must produce a Mermaid diagram
- Never asks the customer questions directly

---

## Review Agent

| Field | Value |
|-------|-------|
| **Name** | `ReviewAgent` |
| **Role** | Validates architecture against requirements and best practices |
| **Inputs** | Architecture output, session memory, Well-Architected Framework |
| **Outputs** | `ReviewOutput` — approved or rejected with findings |
| **Available Tools** | Knowledge Base Search (Well-Architected, security best practices) |
| **Memory Access** | Read + Write (writes review findings) |
| **Decision Criteria** | Architecture must satisfy: HA, security, networking, scalability, cost, compliance |
| **Success Criteria** | All validation checks pass OR clear rejection with specific remediation |
| **Escalation Criteria** | Architecture fails review 3+ times on the same criteria |

### Output Schema

```json
{
  "status": "approved | rejected",
  "findings": [
    {
      "category": "availability | security | networking | scalability | cost | compliance",
      "severity": "critical | major | minor",
      "finding": "string",
      "recommendation": "string",
      "well_architected_pillar": "string"
    }
  ],
  "score": {
    "availability": 0-10,
    "security": 0-10,
    "performance": 0-10,
    "cost_optimization": 0-10,
    "operational_excellence": 0-10,
    "sustainability": 0-10
  },
  "approval_conditions": ["string"],
  "revision_instructions": "string (if rejected)"
}
```

### Rules
- Independent from the Architect Agent (no shared state beyond memory)
- Must reference Well-Architected Framework pillars
- Rejection must include specific, actionable remediation
- Cannot approve an architecture that violates stated requirements
- Must detect: single points of failure, missing encryption, inadequate DR, compliance gaps

---

## Tool Registry Contract

Tools are requested through the orchestrator. Agents never call external services directly.

```python
class BaseTool:
    name: str
    description: str
    input_schema: dict
    output_schema: dict

    async def execute(self, params: dict) -> ToolOutput:
        ...
```

### Available Tools

| Tool | Used By | Purpose |
|------|---------|---------|
| `knowledge_base_search` | Discovery, Architect, Review | RAG over AWS docs |
| `diagram_generator` | Architect | Produce Mermaid diagrams |
| `terraform_generator` | Architect | Generate Terraform code |
| `markdown_generator` | Orchestrator | Produce final report |
| `cost_estimator` | Architect | Estimate monthly AWS cost |

---

## Agent Lifecycle

```
┌──────────┐
│  START   │
└────┬─────┘
     │
     ▼
┌──────────┐     ┌──────────┐     ┌──────────────┐
│  REASON  │────►│   PLAN   │────►│ INVOKE TOOLS │
└──────────┘     └──────────┘     └──────┬───────┘
     ▲                                    │
     │                                    ▼
     │                            ┌──────────────┐
     └────────────────────────────│   REFLECT    │
              (if incomplete)     └──────┬───────┘
                                         │
                                         ▼
                                  ┌──────────────┐
                                  │   OUTPUT     │
                                  └──────────────┘
```

Each agent may loop through Reason → Plan → Invoke → Reflect multiple times
before producing its final output.
