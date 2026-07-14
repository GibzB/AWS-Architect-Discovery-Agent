"""Planner Agent — the brain that decides what happens next."""

import json
import logging
from typing import Any

from packages.agent_sdk.base import BaseAgent, AgentContext, AgentOutput
from packages.prompts.planner import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT_TEMPLATE
from app.services.bedrock import bedrock

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """Decides which agent should execute next based on session memory state."""

    name = "PlannerAgent"
    description = "Decides what happens next. Never calls AWS. Never designs."
    available_tools: list[str] = []
    memory_access = ["read"]

    async def execute(self, context: AgentContext) -> AgentOutput:
        """Run the planner decision loop."""
        try:
            decision = await self._invoke_llm(context)
        except Exception as e:
            logger.warning(f"Bedrock call failed, falling back to rules: {e}")
            decision = self._rule_based_fallback(context)

        return AgentOutput(
            agent_name=self.name,
            success=True,
            data=decision,
            reasoning=decision.get("reason", ""),
        )

    async def reason(self, context: AgentContext) -> dict[str, Any]:
        """Analyse memory state."""
        memory = context.memory
        return {
            "fact_count": len(memory.get("known_facts", [])),
            "has_architecture": bool(memory.get("architecture", {}).get("services")),
            "review_status": memory.get("review", {}).get("status", "pending"),
            "revision_count": memory.get("review", {}).get("revision_count", 0),
        }

    async def plan(self, context: AgentContext) -> dict[str, Any]:
        """Produce planning decision."""
        return await self.execute(context)

    async def _invoke_llm(self, context: AgentContext) -> dict[str, Any]:
        """Use Bedrock to reason about what should happen next."""
        memory = context.memory
        known_facts = memory.get("known_facts", [])
        unknown_facts = memory.get("unknown_facts", [])
        biz_reqs = memory.get("business_requirements", [])
        tech_reqs = memory.get("technical_requirements", [])
        arch_services = memory.get("architecture", {}).get("services", [])
        review_status = memory.get("review", {}).get("status", "pending")
        revision_count = memory.get("review", {}).get("revision_count", 0)
        history = memory.get("conversation_history", [])
        last_message = history[-1]["content"] if history else ""

        user_prompt = PLANNER_USER_PROMPT_TEMPLATE.format(
            status=memory.get("status", "discovery"),
            fact_count=len(known_facts),
            known_facts=json.dumps([f.get("fact", f) if isinstance(f, dict) else f for f in known_facts[:10]]),
            unknown_facts=json.dumps(unknown_facts[:10]),
            biz_req_count=len(biz_reqs),
            business_requirements=json.dumps(biz_reqs[:10]),
            tech_req_count=len(tech_reqs),
            technical_requirements=json.dumps(tech_reqs[:10]),
            architecture_services=json.dumps([s.get("service", "") for s in arch_services]) if arch_services else "None",
            review_status=review_status,
            revision_count=revision_count,
            last_message=last_message[:500],
            conversation_length=len(history),
        )

        result = await bedrock.invoke_json(PLANNER_SYSTEM_PROMPT, user_prompt)
        return result

    def _rule_based_fallback(self, context: AgentContext) -> dict[str, Any]:
        """Deterministic fallback when Bedrock is unavailable."""
        memory = context.memory
        known_facts = memory.get("known_facts", [])
        arch_services = memory.get("architecture", {}).get("services", [])
        review_status = memory.get("review", {}).get("status", "pending")
        revision_count = memory.get("review", {}).get("revision_count", 0)

        # Rule 1: Not enough facts → Discovery
        if len(known_facts) < 5:
            return {
                "next_agent": "DiscoveryAgent",
                "reason": f"Only {len(known_facts)} facts known. Need more information.",
                "priority": "high",
                "context_for_agent": {
                    "focus_area": "Gather core requirements",
                    "specific_instructions": "Ask about business context, workloads, and compliance.",
                },
                "workshop_complete": False,
            }

        # Rule 2: Enough facts but no architecture → Architect
        if not arch_services:
            return {
                "next_agent": "ArchitectAgent",
                "reason": "Sufficient facts gathered. Ready to design architecture.",
                "priority": "high",
                "context_for_agent": {
                    "focus_area": "Design complete AWS architecture",
                    "specific_instructions": "Cover all stated requirements.",
                },
                "workshop_complete": False,
            }

        # Rule 3: Architecture exists but rejected → Architect (revise)
        if review_status == "rejected" and revision_count < 3:
            return {
                "next_agent": "ArchitectAgent",
                "reason": "Architecture rejected by Review. Revision required.",
                "priority": "high",
                "context_for_agent": {
                    "focus_area": "Revise architecture based on review feedback",
                    "specific_instructions": "Address all critical and major findings.",
                },
                "workshop_complete": False,
            }

        # Rule 4: Architecture exists, not yet reviewed → Review
        if review_status == "pending":
            return {
                "next_agent": "ReviewAgent",
                "reason": "Architecture ready for validation.",
                "priority": "high",
                "context_for_agent": {
                    "focus_area": "Validate against Well-Architected Framework",
                    "specific_instructions": "Check HA, security, networking, scalability.",
                },
                "workshop_complete": False,
            }

        # Rule 5: Approved → Complete
        if review_status == "approved":
            return {
                "next_agent": None,
                "reason": "Architecture approved. Workshop complete.",
                "priority": "low",
                "context_for_agent": {},
                "workshop_complete": True,
            }

        # Default: more discovery
        return {
            "next_agent": "DiscoveryAgent",
            "reason": "Defaulting to discovery for more context.",
            "priority": "medium",
            "context_for_agent": {
                "focus_area": "General discovery",
                "specific_instructions": "Identify any remaining gaps.",
            },
            "workshop_complete": False,
        }
