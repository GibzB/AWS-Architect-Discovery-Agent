"""Review Agent — validates architecture against requirements and best practices."""

import json
import logging
from typing import Any

from packages.agent_sdk.base import BaseAgent, AgentContext, AgentOutput
from packages.prompts.review import REVIEW_SYSTEM_PROMPT, REVIEW_USER_PROMPT_TEMPLATE
from app.services.bedrock import bedrock

logger = logging.getLogger(__name__)


class ReviewAgent(BaseAgent):
    """Validates architecture and approves or rejects with findings."""

    name = "ReviewAgent"
    description = "Independent validation against Well-Architected Framework."
    available_tools = ["knowledge_base_search"]
    memory_access = ["read", "write"]

    async def execute(self, context: AgentContext) -> AgentOutput:
        """Validate the current architecture."""
        try:
            result = await self._invoke_llm(context)
        except Exception as e:
            logger.error(f"Review Agent Bedrock call failed: {e}")
            return AgentOutput(
                agent_name=self.name,
                success=False,
                data={"error": str(e)},
                reasoning="Failed to review architecture — Bedrock unavailable.",
            )

        status = result.get("status", "rejected")
        current_revision = context.memory.get("review", {}).get("revision_count", 0)

        memory_updates: dict[str, Any] = {
            "review": {
                "status": status,
                "findings": result.get("findings", []),
                "score": result.get("score", {}),
                "revision_count": current_revision + (1 if status == "rejected" else 0),
            },
        }

        # If approved, move to complete
        if status == "approved":
            memory_updates["status"] = "complete"

        # If rejected, back to architecture phase
        if status == "rejected":
            memory_updates["status"] = "architecture"

        return AgentOutput(
            agent_name=self.name,
            success=True,
            data=result,
            memory_updates=memory_updates,
            reasoning=f"Review {status}. {len(result.get('findings', []))} findings.",
        )

    async def reason(self, context: AgentContext) -> dict[str, Any]:
        """Check what needs validation."""
        memory = context.memory
        arch = memory.get("architecture", {})
        return {
            "has_architecture": bool(arch.get("services")),
            "service_count": len(arch.get("services", [])),
            "revision_count": memory.get("review", {}).get("revision_count", 0),
        }

    async def plan(self, context: AgentContext) -> dict[str, Any]:
        """Plan the review."""
        return {"action": "validate_architecture"}

    async def _invoke_llm(self, context: AgentContext) -> dict[str, Any]:
        """Use Bedrock to validate architecture."""
        memory = context.memory
        customer = memory.get("customer", {})
        known_facts = memory.get("known_facts", [])
        biz_reqs = memory.get("business_requirements", [])
        tech_reqs = memory.get("technical_requirements", [])
        arch = memory.get("architecture", {})
        review = memory.get("review", {})

        # Compliance facts
        compliance_facts = [
            f.get("fact", f) if isinstance(f, dict) else f
            for f in known_facts
            if isinstance(f, dict) and f.get("category") == "compliance"
        ]

        user_prompt = REVIEW_USER_PROMPT_TEMPLATE.format(
            customer_name=customer.get("name", "Unknown"),
            customer_industry=customer.get("industry", "Unknown"),
            business_requirements=json.dumps(biz_reqs, indent=2),
            technical_requirements=json.dumps(tech_reqs, indent=2),
            compliance_facts=json.dumps(compliance_facts),
            architecture_services=json.dumps(arch.get("services", []), indent=2),
            architecture_decisions=json.dumps(arch.get("decisions", []), indent=2),
            non_functional=json.dumps(arch.get("non_functional", {}), indent=2),
            revision_count=review.get("revision_count", 0),
            previous_findings=json.dumps(review.get("findings", []), indent=2),
        )

        return await bedrock.invoke_json(
            REVIEW_SYSTEM_PROMPT, user_prompt, max_tokens=4096, temperature=0.2
        )
