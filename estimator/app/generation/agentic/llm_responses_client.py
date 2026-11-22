"""Real LLM client using the Responses API (function calling with strict=True)."""

from __future__ import annotations

import time
from typing import Any

import litellm
import structlog

from app.generation.agentic.llm_client import AgentLLMClient, AgentLLMResponse

log = structlog.get_logger()


class ResponsesAPIClient:
    """LLM client using the Responses API for function calling with strict mode."""

    def __init__(
        self,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        primary_model: str = "gpt-5-mini",
        fallback_model: str | None = None,
    ):
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key

    async def create_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str = "gpt-5-mini",
        reasoning_effort: str = "medium",
        timeout_seconds: int = 60,
    ) -> AgentLLMResponse:
        """
        Call the LLM with function calling support via Responses API.

        Args:
            messages: Chat messages (can include previous_response_id for chaining)
            tools: Tool definitions with strict=True JSON Schema
            model: Model to use
            reasoning_effort: "low", "medium", "high"
            timeout_seconds: Request timeout

        Returns:
            AgentLLMResponse with output items and token usage
        """
        # Extract previous_response_id from last message if present
        previous_response_id = None
        if messages and isinstance(messages[-1], dict):
            previous_response_id = messages[-1].pop("previous_response_id", None)

        # Build kwargs
        kwargs = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "timeout": timeout_seconds,
        }

        # Add reasoning if supported by model
        if model in ("gpt-5", "gpt-4-reasoning") and reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort

        # Set up API keys
        if model.startswith("gpt") or model.startswith("o"):
            kwargs["api_key"] = self.openai_api_key
        elif model.startswith("claude"):
            kwargs["api_key"] = self.anthropic_api_key

        t0 = time.perf_counter()
        try:
            log.info(
                "llm_responses_call_started",
                model=model,
                has_tools=len(tools) > 0,
            )

            # Use litellm.completion for the Responses API
            response = litellm.completion(**kwargs)

            latency_ms = int((time.perf_counter() - t0) * 1000)

            # Parse response
            # The Responses API returns a response with:
            # - response.choices[0].message.content (can be text or function calls)
            # - response.usage.prompt_tokens, completion_tokens

            message = response.choices[0].message
            usage = response.usage

            # Extract output items from the message
            output_items: list[dict[str, Any]] = []

            # Handle content
            if hasattr(message, "content") and message.content:
                output_items.append({"type": "text", "text": message.content})

            # Handle tool calls
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tool_call in message.tool_calls:
                    output_items.append(
                        {
                            "type": "function_call",
                            "id": tool_call.id,
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,  # JSON string
                        }
                    )

            stop_reason = response.choices[0].finish_reason or "end_turn"

            log.info(
                "llm_responses_call_completed",
                model=model,
                latency_ms=latency_ms,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                tool_calls=len([i for i in output_items if i["type"] == "function_call"]),
            )

            return AgentLLMResponse(
                output=output_items,
                stop_reason=stop_reason,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
            )

        except Exception as e:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            log.error(
                "llm_responses_call_failed",
                error_type=type(e).__name__,
                error=str(e),
                latency_ms=latency_ms,
            )
            raise
