"""Markdown Report Generator — produces the final discovery report."""

import json
from typing import Any
from datetime import datetime, timezone


def generate_report(session: dict[str, Any]) -> str:
    """Generate a full markdown report from session memory."""
    customer = session.get("customer", {})
    arch = session.get("architecture", {})
    review = session.get("review", {})
    risks = session.get("risks", [])
    known_facts = session.get("known_facts", [])
    biz_reqs = session.get("business_requirements", [])
    tech_reqs = session.get("technical_requirements", [])
    assumptions = session.get("assumptions", [])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    sections = []

    # Title
    sections.append(f"""# Cloud Discovery Report
## {customer.get('name', 'Customer')} — {customer.get('industry', 'Technology')}

**Generated:** {now}
**Status:** {'✅ Approved' if review.get('status') == 'approved' else '⏳ Pending'}
**AI Solutions Architect:** Atlas

---""")

    # Executive Summary
    services = arch.get("services", [])
    svc_names = [s.get("service", "") for s in services]
    sections.append(f"""## Executive Summary

This report presents the recommended AWS cloud architecture for {customer.get('name', 'the customer')},
a {customer.get('industry', '')} organisation. The architecture was designed through an autonomous
discovery workshop conducted by Atlas, validating requirements across business, technical,
compliance, and operational dimensions.

**Key Services:** {', '.join(svc_names[:8])}
**Estimated Monthly Cost:** ${arch.get('cost_estimate', {}).get('monthly_low', 'N/A')} — ${arch.get('cost_estimate', {}).get('monthly_high', 'N/A')} USD
""")

    # Business Requirements
    sections.append("## Business Requirements\n")
    if biz_reqs:
        for req in biz_reqs:
            sections.append(f"- {req}")
    else:
        sections.append("_No formal business requirements recorded. See discovered facts._")
    sections.append("")

    # Technical Requirements
    sections.append("## Technical Requirements\n")
    if tech_reqs:
        for req in tech_reqs:
            sections.append(f"- {req}")
    else:
        sections.append("_No formal technical requirements recorded. See discovered facts._")
    sections.append("")

    # Discovered Facts
    sections.append("## Discovered Facts\n")
    sections.append("| Fact | Category | Confidence |")
    sections.append("|------|----------|------------|")
    for f in known_facts:
        if isinstance(f, dict):
            sections.append(f"| {f.get('fact', '')} | {f.get('category', 'general')} | {f.get('confidence', 1.0):.0%} |")
        else:
            sections.append(f"| {f} | general | 100% |")
    sections.append("")

    # Architecture Decisions
    sections.append("## Architecture Decisions\n")
    decisions = arch.get("decisions", [])
    for i, dec in enumerate(decisions, 1):
        sections.append(f"""### ADR-{i:03d}: {dec.get('decision', 'Decision')}

**Rationale:** {dec.get('rationale', '')}
**Trade-offs:** {dec.get('trade_offs', '')}
**Reversibility:** {dec.get('reversibility', 'medium')}
""")

    # AWS Service Mapping
    sections.append("## AWS Service Mapping\n")
    sections.append("| Service | Purpose | Justification |")
    sections.append("|---------|---------|---------------|")
    for svc in services:
        sections.append(f"| {svc.get('service', '')} | {svc.get('purpose', '')} | {svc.get('justification', '')} |")
    sections.append("")

    # Architecture Diagram
    diagram = arch.get("diagram_mermaid", "")
    if diagram:
        sections.append(f"""## Architecture Diagram

```mermaid
{diagram}
```
""")

    # Non-Functional Requirements
    nfr = arch.get("non_functional", {})
    if nfr:
        sections.append(f"""## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Availability | {nfr.get('availability_target', 'N/A')} |
| RTO | {nfr.get('rto', 'N/A')} |
| RPO | {nfr.get('rpo', 'N/A')} |
| Regions | {', '.join(nfr.get('regions', []))} |
| Multi-Region | {'Yes' if nfr.get('multi_region') else 'No'} |
""")

    # Cost Estimate
    cost = arch.get("cost_estimate", {})
    if cost:
        sections.append(f"""## Cost Estimate

| Metric | Value |
|--------|-------|
| Monthly Low | ${cost.get('monthly_low', 'N/A')} |
| Monthly High | ${cost.get('monthly_high', 'N/A')} |
| Currency | {cost.get('currency', 'USD')} |

**Assumptions:**
""")
        for a in cost.get("assumptions", []):
            sections.append(f"- {a}")
        sections.append("")

    # Risk Register
    sections.append("## Risk Register\n")
    if risks:
        sections.append("| Risk | Impact | Likelihood | Mitigation |")
        sections.append("|------|--------|-----------|------------|")
        for risk in risks:
            if isinstance(risk, dict):
                sections.append(f"| {risk.get('risk', '')} | {risk.get('impact', '')} | {risk.get('likelihood', '')} | {risk.get('mitigation', '')} |")
    else:
        sections.append("_No risks identified._")
    sections.append("")

    # Assumptions
    if assumptions:
        sections.append("## Assumptions\n")
        for a in assumptions:
            sections.append(f"- {a}")
        sections.append("")

    # Review Results
    if review.get("score"):
        sections.append("## Well-Architected Review\n")
        sections.append("| Pillar | Score |")
        sections.append("|--------|-------|")
        for pillar, score in review["score"].items():
            label = pillar.replace("_", " ").title()
            emoji = "✅" if score >= 7 else "⚠️" if score >= 5 else "❌"
            sections.append(f"| {label} | {emoji} {score}/10 |")
        sections.append("")

    if review.get("findings"):
        sections.append("### Findings\n")
        for finding in review["findings"]:
            if isinstance(finding, dict):
                severity = finding.get("severity", "info").upper()
                sections.append(f"- **[{severity}]** {finding.get('finding', '')} → {finding.get('recommendation', '')}")
        sections.append("")

    # Footer
    sections.append("""---

*This report was generated autonomously by Atlas, an AI Solutions Architect powered by
Amazon Bedrock. All recommendations should be validated by qualified AWS architects before
implementation.*
""")

    return "\n".join(sections)
