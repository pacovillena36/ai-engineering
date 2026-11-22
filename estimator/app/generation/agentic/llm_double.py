"""Test double for the LLM client — returns canned function_call sequences."""

from __future__ import annotations

from typing import Any

from app.generation.agentic.llm_client import AgentLLMClient, AgentLLMResponse


class MockLLMClient:
    """
    Test double that returns scripted function_call sequences.

    Usage:
        double = MockLLMClient()
        double.add_response(
            [
                {"type": "function_call", "id": "call_1", "name": "search_budgets", "arguments": '{"query": "auth"}'}
            ]
        )
        response = await double.create_response(...)
    """

    def __init__(self):
        self.responses: list[list[dict[str, Any]]] = []
        self.call_index = 0

    def add_response(
        self, output: list[dict[str, Any]], input_tokens: int = 100, output_tokens: int = 50
    ) -> MockLLMClient:
        """Queue a response. Returns self for chaining."""
        self.responses.append(output)
        return self

    def add_final_text(self, text: str) -> MockLLMClient:
        """Queue a final text response (no function calls). Returns self for chaining."""
        self.responses.append([{"type": "text", "text": text}])
        return self

    async def create_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str = "gpt-5-mini",
        reasoning_effort: str = "medium",
        timeout_seconds: int = 60,
    ) -> AgentLLMResponse:
        """Return the next queued response."""
        if self.call_index >= len(self.responses):
            # Fallback: return empty (agent finishes)
            return AgentLLMResponse(output=[], stop_reason="end_turn")

        output = self.responses[self.call_index]
        self.call_index += 1

        return AgentLLMResponse(
            output=output,
            stop_reason="tool_calls" if output and output[0].get("type") == "function_call" else "end_turn",
            input_tokens=100,
            output_tokens=50,
        )
