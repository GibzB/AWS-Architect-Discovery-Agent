# Atlas Demo Script

**Duration:** 5 minutes
**Goal:** Demonstrate autonomous reasoning, planning, reflection, and deliverable generation.

---

## Setup (before demo)

```bash
# Terminal 1: Backend
cd apps/backend && source .venv/bin/activate
export AWS_PROFILE=K1-Kitstek-Billy
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd apps/frontend && npm run dev
```

Open http://localhost:5173

---

## Scene 1: Introduction (30s)

> "This is Atlas — an autonomous AI Solutions Architect. It doesn't just answer questions.
> It drives the entire cloud discovery workshop: deciding what to ask, when to design,
> and validating its own work."

**Action:** Enter organisation name "FinanceFlow" and industry "Fintech". Click "Start Discovery Workshop".

Atlas introduces itself.

---

## Scene 2: Discovery (1.5 min)

**User says:**
> "We're a fintech startup with 50,000 active users. We process payments and need to expand into Europe."

**What to point out:**
- Atlas extracts facts automatically (facts counter increases in sidebar)
- Atlas asks targeted follow-up questions (not a questionnaire)
- The Planner routes to the Discovery Agent

**User says:**
> "We need PCI-DSS compliance, 99.99% uptime, disaster recovery with 1-hour RTO, and we use Python microservices on containers."

**What to point out:**
- Multiple facts extracted in one turn
- Atlas acknowledges compliance requirements
- Sidebar shows progress toward architecture phase

---

## Scene 3: Architecture (1 min)

**User says:**
> "That covers everything. Please design the architecture."

**What to point out:**
- Planner decides Discovery is complete → routes to Architect Agent
- Architecture is generated with specific AWS services
- Each service has justification and alternatives considered
- Mermaid diagram is produced
- Status changes to "Review"

---

## Scene 4: Review & Reflection (1 min)

**What to point out:**
- Review Agent automatically validates the architecture
- Well-Architected scores appear in the sidebar
- **If rejected:** "The review identified a single point of failure. The Architect is revising."
  - This is the reflection loop — the key differentiator
- **When approved:** Status changes to "Complete"

---

## Scene 5: Deliverables (1 min)

**Action:** Click the "Report" tab.

**What to point out:**
- Full report generated: executive summary, services, risks, decisions
- Click "Terraform" tab → production-ready IaC code
- Click "Diagram" tab → architecture diagram
- All produced autonomously without human intervention

---

## Key Talking Points

1. **"This is not a chatbot."** Atlas decides what to do next. It doesn't wait for instructions.
2. **"Dynamic, not scripted."** The questions adapt based on what's already known.
3. **"Multi-agent collaboration."** Four specialists work together: Planner, Discovery, Architect, Review.
4. **"Self-validating."** The Review Agent can reject and force revision — demonstrating reflection.
5. **"Production-ready output."** Not just advice — Terraform code, Mermaid diagrams, risk registers.

---

## Fallback Scenarios

**If Bedrock is slow:** The system has rule-based fallbacks. Discovery will still ask sensible questions.

**If review rejects:** This is a FEATURE. Say: "Watch — Atlas detected an issue and is fixing it autonomously."

**If voice doesn't work in browser:** Fall back to chat. Voice requires Chrome with microphone permissions.

---

## One-liner for Judges

> "Atlas is an autonomous AI Solutions Architect that conducts cloud discovery workshops,
> coordinates specialist agents, validates its own recommendations through a reflection loop,
> and produces implementation-ready deliverables — all without human intervention."
