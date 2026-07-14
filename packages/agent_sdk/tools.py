"""Tool Registry — base class for all tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolOutput:
    """Standard output from any tool invocation."""

    tool_name: str
    success: bool
    data: Any = None
    error: str | None = None


class BaseTool(ABC):
    """All tools implement this interface."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> ToolOutput:
        """Execute the tool with given parameters."""
        ...


class ToolRegistry:
    """Registry of available tools. Agents request tools through this."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool by name."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Retrieve a registered tool."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    async def invoke(self, name: str, params: dict[str, Any]) -> ToolOutput:
        """Invoke a tool by name."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolOutput(tool_name=name, success=False, error=f"Tool '{name}' not found")
        return await tool.execute(params)
