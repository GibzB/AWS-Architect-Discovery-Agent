---
inclusion: always
---
# Scrum + DevSecOps Sprint Framework (Hackathon-Adapted)

Adapted from the Kiro-SDLC-Scrum best-practices skill
(https://github.com/timwukp/Kiro-SDLC-Scrum-best-practics), trimmed for a
single-team hackathon build on a Python / FastAPI / AWS CDS stack in
`us-east-1`. The Singapore-banking-specific guardrails (MAS TRM / PDPA
cross-border region lock, Aurora/Flyway DB guards, Java coding standards) are
intentionally omitted because they do not apply to this project.

## Three Pillars of Empiricism
| Pillar | Application in this project |
|--------|-----------------------------|
| Transparency | Sprint plan, backlog, and Definition of Done live in `docs/SPRINT_PLAN.md`. Security hook results are visible on every write. |
| Inspection | Each task is verified (syntax check, hook scan, sandbox smoke test) before it is marked done. |
| Adaptation | Scope and backlog adjust as integration realities surface (e.g. RCS onboarding lead time). |

## Sprint Planning — Three Topics
- **Why** — the Sprint Goal (see `docs/SPRINT_PLAN.md`), including security outcomes.
- **What** — the prioritized backlog of Product Backlog Items (PBIs), including security stories.
- **How** — each PBI decomposed into tasks of roughly one unit of work or less.

## Security Shift-Left (DevSecOps)
- Threat-model each new external surface (inbound messaging webhook, two-way
  reply handling) before building it.
- Treat customer PII (phone numbers, email addresses) as sensitive at every
  layer: never log raw values, never hardcode them, store only what is needed.
- Secrets live in AWS Secrets Manager or environment variables, never in source.
- Deterministic Pre-Tool-Use hooks (credential guard, PII guard, prompt-security
  guard) enforce these rules at write time — see `.kiro/hooks/`.

## Definition of Done
A backlog item is **not** Done until:
- [ ] Code written and self-reviewed against the standards in `tech.md`.
- [ ] Security hooks pass (no hardcoded credentials or PII).
- [ ] Python modules compile (`python -m py_compile`) and imports resolve.
- [ ] Behavior verified where runnable (sandbox-mode smoke test for channel
      send + inbound intent routing).
- [ ] Docs updated when the change affects deployment, architecture, or the
      hackathon submission narrative.

## Core Rule
Steering **instructs**; hooks **enforce**. Any guardrail that must be 100%
reliable is a Pre-Tool-Use shell-command hook, not prose.
