"""Report Service — generates all deliverables when workshop is complete."""

import logging
from typing import Any

from tools.markdown.generator import generate_report as generate_markdown_report
from tools.terraform.generator import generate_terraform
from tools.diagram.generator import generate_mermaid_diagram

logger = logging.getLogger(__name__)


class ReportService:
    """Generates final deliverables from a completed session."""

    def generate_all(self, session: dict[str, Any]) -> dict[str, Any]:
        """Generate all deliverables — report, terraform, diagram."""
        report_md = generate_markdown_report(session)
        terraform_code = generate_terraform(session)
        diagram = generate_mermaid_diagram(session)

        return {
            "session_id": session["session_id"],
            "generated_at": session.get("updated_at", ""),
            "report_markdown": report_md,
            "executive_summary": self._extract_summary(session),
            "architecture_decisions": session.get("architecture", {}).get("decisions", []),
            "services": session.get("architecture", {}).get("services", []),
            "risks": session.get("risks", []),
            "cost_estimate": session.get("architecture", {}).get("cost_estimate", {}),
            "diagram_mermaid": diagram,
            "terraform_snippet": terraform_code,
            "review_score": session.get("review", {}).get("score", {}),
            "review_findings": session.get("review", {}).get("findings", []),
            "business_requirements": session.get("business_requirements", []),
            "technical_requirements": session.get("technical_requirements", []),
            "known_facts": session.get("known_facts", []),
        }

    def _extract_summary(self, session: dict[str, Any]) -> str:
        """Build executive summary text."""
        customer = session.get("customer", {})
        arch = session.get("architecture", {})
        services = arch.get("services", [])
        svc_names = [s.get("service", "") for s in services[:6]]

        return (
            f"Architecture recommendation for {customer.get('name', 'customer')} "
            f"({customer.get('industry', 'technology')}). "
            f"Proposed services: {', '.join(svc_names)}. "
            f"Estimated cost: ${arch.get('cost_estimate', {}).get('monthly_low', '?')}–"
            f"${arch.get('cost_estimate', {}).get('monthly_high', '?')}/month."
        )


report_service = ReportService()
