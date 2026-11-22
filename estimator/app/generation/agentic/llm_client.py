"""LLM client abstraction for the Session 12 agent.

The agent loop only knows about this Protocol, not the real LLMWrapper.
This design makes the loop testeable without network or token cost.
"""

from __future__ import annotations

from typing import Any, Protocol


class AgentLLMResponse:
    """One response from the LLM during an agentic loop."""

    def __init__(
        self,
        output: list[dict[str, Any]],
        stop_reason: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ):
        self.output = output  # list of {"type": "text"/"function_call", ...}
        self.stop_reason = stop_reason  # "tool_calls", "end_turn", etc.
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def function_calls(self) -> list[dict[str, Any]]:
        """Extract all function_call items from the output."""
        return [item for item in self.output if item.get("type") == "function_call"]

    def text_content(self) -> str:
        """Extract text from the output (if any)."""
        texts = [item.get("text", "") for item in self.output if item.get("type") == "text"]
        return "".join(texts).strip()


class AgentLLMClient(Protocol):
    """Protocol (interface) for the LLM client used by the agent loop.

    The real client (wrapping the Responses API) implements this.
    Tests inject a double that returns canned function_call sequences.
    """

    async def create_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str = "gpt-5-mini",
        reasoning_effort: str = "medium",
        timeout_seconds: int = 60,
    ) -> AgentLLMResponse:
        """
        Call the LLM with the given messages and tools.

        Args:
            messages: List of {"role": "user"/"assistant", "content": ...} items
            tools: List of tool definitions (Responses API format with strict=True)
            model: Model identifier
            reasoning_effort: "low", "medium", "high"
            timeout_seconds: Request timeout

        Returns:
            AgentLLMResponse with output items and token counts.

        The returned output list contains items of type:
            - "text": {"type": "text", "text": "..."}
            - "function_call": {"type": "function_call", "id": "...", "name": "...", "arguments": "..."}
        """
        ...
