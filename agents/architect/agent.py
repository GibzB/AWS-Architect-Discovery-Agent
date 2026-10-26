"""Architect Agent — designs AWS architecture from requirements."""

import json
import logging
from typing import Any

from packages.agent_sdk.base import BaseAgent, AgentContext, AgentOutput
from packages.prompts.architect import ARCHITECT_SYSTEM_PROMPT, ARCHITECT_USER_PROMPT_TEMPLATE
from app.services.bedrock import bedrock

logger = logging.getLogger(__name__)


class ArchitectAgent(BaseAgent):
    """Designs complete AWS architectures based on discovered requirements."""

    name = "ArchitectAgent"
    description = "Produces AWS architecture with justification, diagrams, and cost estimates."
    available_tools = ["knowledge_base_search", "diagram_generator", "terraform_generator"]
    memory_access = ["read", "write"]

    async def execute(self, context: AgentContext) -> AgentOutput:
        """Generate or revise architecture."""
        try:
            result = await self._invoke_llm(context)
        except Exception as e:
            logger.error(f"Architect Agent Bedrock call failed: {e}")
            return AgentOutput(
                agent_name=self.name,
                success=False,
                data={"error": str(e)},
                reasoning="Failed to generate architecture — Bedrock unavailable.",
            )

        # Build memory updates
        memory_updates: dict[str, Any] = {
            "architecture": {
                "services": result.get("services", []),
                "decisions": result.get("decisions", []),
                "diagram_mermaid": result.get("diagram_mermaid", ""),
                "cost_estimate": result.get("cost_estimate", {}),
                "non_functional": result.get("non_functional", {}),
            },
            "risks": result.get("risks", []),
            "status": "review",
            "review": {
                "status": "pending",
                "findings": [],
                "revision_count": context.memory.get("review", {}).get("revision_count", 0),
            },
        }

        return AgentOutput(
            agent_name=self.name,
            success=True,
            data=result,
            memory_updates=memory_updates,
            reasoning=f"Generated architecture with {len(result.get('services', []))} services.",
        )

    async def reason(self, context: AgentContext) -> dict[str, Any]:
        """Check if we have enough info to design."""
        memory = context.memory
        return {
            "fact_count": len(memory.get("known_facts", [])),
            "has_previous_architecture": bool(memory.get("architecture", {}).get("services")),
            "is_revision": memory.get("review", {}).get("status") == "rejected",
        }

    async def plan(self, context: AgentContext) -> dict[str, Any]:
        """Plan the architecture generation."""
        return {"action": "generate_architecture"}

    async def _invoke_llm(self, context: AgentContext) -> dict[str, Any]:
        """Use Bedrock to design architecture."""
        memory = context.memory
        customer = memory.get("customer", {})
        known_facts = memory.get("known_facts", [])
        biz_reqs = memory.get("business_requirements", [])
        tech_reqs = memory.get("technical_requirements", [])
        review = memory.get("review", {})
        prev_arch = memory.get("architecture", {})
        planner_ctx = context.planner_instructions

        # Extract compliance-related facts
        compliance_facts = [
            f.get("fact", f) if isinstance(f, dict) else f
            for f in known_facts
            if isinstance(f, dict) and f.get("category") == "compliance"
        ]

        # Previous architecture (if revision)
        prev_arch_str = ""
        if prev_arch.get("services"):
            prev_arch_str = json.dumps(prev_arch, indent=2)

        # Review feedback (if rejected)
        review_feedback = ""
        if review.get("status") == "rejected":
            review_feedback = json.dumps(review.get("findings", []), indent=2)

        user_prompt = ARCHITECT_USER_PROMPT_TEMPLATE.format(
            customer_name=customer.get("name", "Unknown"),
            customer_industry=customer.get("industry", "Unknown"),
            business_requirements=json.dumps(biz_reqs, indent=2),
            technical_requirements=json.dumps(tech_reqs, indent=2),
            known_facts=json.dumps(
                [f.get("fact", f) if isinstance(f, dict) else f for f in known_facts],
                indent=2,
            ),
            compliance_facts=json.dumps(compliance_facts),
            planner_context=json.dumps(planner_ctx),
            previous_architecture=prev_arch_str or "None — this is the first design.",
            review_feedback=review_feedback or "None — first submission.",
        )

        return await bedrock.invoke_json(
            ARCHITECT_SYSTEM_PROMPT, user_prompt, max_tokens=8192, temperature=0.3
        )
