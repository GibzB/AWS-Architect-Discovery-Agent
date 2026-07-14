"""Base Agent contract — all agents implement this interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    """Context passed to every agent invocation."""

    session_id: str
    memory: dict[str, Any]
    planner_instructions: dict[str, Any] = field(default_factory=dict)
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    tools_available: list[str] = field(default_factory=list)


@dataclass
class AgentOutput:
    """Standard output from any agent."""

    agent_name: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    memory_updates: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    next_action: str | None = None


class BaseAgent(ABC):
    """All ASA agents implement this lifecycle."""

    name: str
    description: str
    available_tools: list[str]
    memory_access: list[str]  # "read", "write"

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentOutput:
        """Main entry point. Runs the full agent lifecycle."""
        ...

    @abstractmethod
    async def reason(self, context: AgentContext) -> dict[str, Any]:
        """Analyse memory state and determine what to do."""
        ...

    @abstractmethod
    async def plan(self, context: AgentContext) -> dict[str, Any]:
        """Produce a concrete action plan."""
        ...

    async def invoke_tools(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Request tools through the orchestrator. Override if tools needed."""
        return {}

    async def reflect(self, results: dict[str, Any]) -> dict[str, Any]:
        """Evaluate results and decide if more work is needed."""
        return {"complete": True}
