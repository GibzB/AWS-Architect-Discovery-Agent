"""Discovery Agent — identifies gaps and asks intelligent questions."""

import json
import logging
from typing import Any

from packages.agent_sdk.base import BaseAgent, AgentContext, AgentOutput
from packages.prompts.discovery import DISCOVERY_SYSTEM_PROMPT, DISCOVERY_USER_PROMPT_TEMPLATE
from app.services.bedrock import bedrock

logger = logging.getLogger(__name__)


class DiscoveryAgent(BaseAgent):
    """Identifies missing information and generates adaptive questions."""

    name = "DiscoveryAgent"
    description = "Asks intelligent follow-up questions based on gaps in knowledge."
    available_tools = ["knowledge_base_search"]
    memory_access = ["read", "write"]

    async def execute(self, context: AgentContext) -> AgentOutput:
        """Run discovery: extract facts, identify gaps, generate questions."""
        try:
            result = await self._invoke_llm(context)
        except Exception as e:
            logger.warning(f"Bedrock failed, using fallback: {e}")
            result = self._fallback(context)

        # Prepare memory updates
        memory_updates: dict[str, Any] = {}

        # Extract facts from user's message
        facts_extracted = result.get("facts_extracted", [])
        if facts_extracted:
            existing_facts = context.memory.get("known_facts", [])
            new_facts = existing_facts + [
                {
                    "fact": f["fact"],
                    "source": "customer",
                    "confidence": f.get("confidence", 0.9),
                    "category": f.get("category", "general"),
                }
                for f in facts_extracted
            ]
            memory_updates["known_facts"] = new_facts

            # Also populate business/technical requirements from facts
            biz_reqs = list(context.memory.get("business_requirements", []))
            tech_reqs = list(context.memory.get("technical_requirements", []))
            for f in facts_extracted:
                cat = f.get("category", "")
                fact_text = f.get("fact", "")
                if cat == "business" and fact_text not in biz_reqs:
                    biz_reqs.append(fact_text)
                elif cat in ("technical", "operations") and fact_text not in tech_reqs:
                    tech_reqs.append(fact_text)
            memory_updates["business_requirements"] = biz_reqs
            memory_updates["technical_requirements"] = tech_reqs

        # Update remaining questions
        questions = result.get("questions", [])
        if questions:
            memory_updates["questions_remaining"] = questions

        # Update gaps
        gaps = result.get("gaps_remaining", [])
        if gaps:
            memory_updates["unknown_facts"] = gaps

        # Check if sufficient for architecture
        if result.get("sufficient_for_architecture"):
            memory_updates["status"] = "architecture"

        return AgentOutput(
            agent_name=self.name,
            success=True,
            data=result,
            memory_updates=memory_updates,
            reasoning=f"Extracted {len(facts_extracted)} facts, generated {len(questions)} questions.",
        )

    async def reason(self, context: AgentContext) -> dict[str, Any]:
        """Determine what information is missing."""
        memory = context.memory
        return {
            "known_count": len(memory.get("known_facts", [])),
            "unknown_count": len(memory.get("unknown_facts", [])),
            "has_business": any(
                f.get("category") == "business"
                for f in memory.get("known_facts", [])
                if isinstance(f, dict)
            ),
            "has_technical": any(
                f.get("category") == "technical"
                for f in memory.get("known_facts", [])
                if isinstance(f, dict)
            ),
        }

    async def plan(self, context: AgentContext) -> dict[str, Any]:
        """Plan which questions to ask."""
        return {"action": "generate_questions"}

    async def _invoke_llm(self, context: AgentContext) -> dict[str, Any]:
        """Use Bedrock to generate intelligent questions."""
        memory = context.memory
        known_facts = memory.get("known_facts", [])
        unknown_facts = memory.get("unknown_facts", [])
        biz_reqs = memory.get("business_requirements", [])
        tech_reqs = memory.get("technical_requirements", [])
        history = memory.get("conversation_history", [])
        customer = memory.get("customer", {})
        planner_ctx = context.planner_instructions

        # Get last user message
        user_messages = [m for m in history if m.get("role") == "user"]
        user_message = user_messages[-1]["content"] if user_messages else ""

        # Format recent history
        recent = history[-10:]
        recent_str = "\n".join(
            f"{m['role'].upper()}: {m['content'][:200]}" for m in recent
        )

        user_prompt = DISCOVERY_USER_PROMPT_TEMPLATE.format(
            customer_name=customer.get("name", "Unknown"),
            customer_industry=customer.get("industry", "Unknown"),
            known_facts=json.dumps([f.get("fact", f) if isinstance(f, dict) else f for f in known_facts], indent=2),
            unknown_facts=json.dumps(unknown_facts),
            business_requirements=json.dumps(biz_reqs),
            technical_requirements=json.dumps(tech_reqs),
            planner_context=json.dumps(planner_ctx),
            user_message=user_message,
            recent_history=recent_str or "No previous conversation.",
        )

        return await bedrock.invoke_json(DISCOVERY_SYSTEM_PROMPT, user_prompt)

    def _fallback(self, context: AgentContext) -> dict[str, Any]:
        """Rule-based fallback when Bedrock is unavailable."""
        memory = context.memory
        known_facts = memory.get("known_facts", [])
        fact_categories = set()
        for f in known_facts:
            if isinstance(f, dict):
                fact_categories.add(f.get("category", ""))

        questions = []
        if "business" not in fact_categories:
            questions.append({
                "question": "What does your company do, and who are your primary users? I'd also like to understand your team size and current growth stage.",
                "category": "business",
                "reason": "Need to understand business context for architecture decisions",
                "priority": "critical",
            })
        elif "technical" not in fact_categories:
            questions.append({
                "question": "What does your current technical stack look like? I'm interested in languages, frameworks, databases, and where you're hosting today.",
                "category": "technical",
                "reason": "Need to understand current state to recommend the right AWS services",
                "priority": "critical",
            })
        elif "compliance" not in fact_categories:
            questions.append({
                "question": "Are there any regulatory or compliance requirements — things like GDPR, HIPAA, PCI-DSS, or data residency rules I should design around?",
                "category": "compliance",
                "reason": "Compliance requirements significantly impact architecture choices",
                "priority": "important",
            })
        elif "operations" not in fact_categories:
            questions.append({
                "question": "What are your availability expectations? Specifically: what uptime do your users expect, and how much data loss is acceptable in a disaster scenario?",
                "category": "operations",
                "reason": "DR objectives drive multi-region and backup architecture decisions",
                "priority": "important",
            })
        else:
            questions.append({
                "question": "Is there anything else about your infrastructure needs, security concerns, or budget constraints I should factor into the architecture?",
                "category": "technical",
                "reason": "Catch remaining requirements before architecture design",
                "priority": "nice_to_have",
            })

        return {
            "facts_extracted": [],
            "questions": questions,
            "gaps_remaining": [c for c in ["business", "technical", "compliance", "operations"] if c not in fact_categories],
            "sufficient_for_architecture": len(fact_categories) >= 4,
            "response_to_customer": questions[0]["question"],
        }
