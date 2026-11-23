#!/usr/bin/env python3
"""
Demo script to run the Session 12 agent on a transcript.

Usage:
    uv run python scripts/run_agent_s12.py \
        estimator/exercises/session-12/sample_transcript_simple.txt \
        --model gpt-5-mini \
        --stub

The --stub flag uses the reference_retrieval fallback instead of the RAG pipeline.
The --output flag specifies where to save the trace (default: stdout).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()


async def main():
    parser = argparse.ArgumentParser(
        description="Run the Session 12 agent on a transcript."
    )
    parser.add_argument(
        "transcript_path",
        type=Path,
        help="Path to the transcript file (plain text).",
    )
    parser.add_argument(
        "--model",
        default="gpt-5-mini",
        help="LLM model to use (default: gpt-5-mini).",
    )
    parser.add_argument(
        "--stub",
        action="store_true",
        help="Use reference_retrieval stub instead of RAG pipeline.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to save the trace (default: stdout).",
    )

    args = parser.parse_args()

    # Read transcript
    if not args.transcript_path.exists():
        print(f"Error: {args.transcript_path} not found", file=sys.stderr)
        sys.exit(1)

    transcript = args.transcript_path.read_text(encoding="utf-8")
    log.info("transcript_loaded", path=str(args.transcript_path), length=len(transcript))

    # Import after logging setup
    from app.generation.agentic.agent_loop import EstimationAgent
    from app.generation.agentic.agent_trace import format_trace_for_console
    from app.generation.agentic.llm_double import MockLLMClient
    from app.generation.agentic.llm_responses_client import ResponsesAPIClient
    from app.generation.agentic.tools_impl import AgentTools

    # Set up tools
    tools = AgentTools(use_stub_retrieval=args.stub)

    # Create tool callables that can be awaited
    async def search_budgets_wrapped(search_args):
        return await tools.search_budgets(search_args)

    async def calculate_estimate_wrapped(calc_args):
        # calculate_estimate is sync but we wrap it as async for consistency
        return tools.calculate_estimate(calc_args)

    # Set up LLM client
    if args.model == "mock":
        # For testing: use a mock client with predefined responses
        llm_client = MockLLMClient()
        llm_client.add_response(
            [
                {
                    "type": "function_call",
                    "id": "call_1",
                    "name": "search_budgets",
                    "arguments": json.dumps({"query": "authentication backend", "filters": None}),
                }
            ]
        )
        llm_client.add_response(
            [
                {
                    "type": "function_call",
                    "id": "call_2",
                    "name": "calculate_estimate",
                    "arguments": json.dumps(
                        {
                            "components": [
                                {
                                    "name": "Authentication backend",
                                    "reference_amounts": [420.0, 380.0],
                                }
                            ]
                        }
                    ),
                }
            ]
        )
        llm_client.add_final_text("Estimation complete. Total effort: ~400 engineer-hours.")
    else:
        # Real LLM client
        import os

        openai_key = os.getenv("OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        llm_client = ResponsesAPIClient(
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
            primary_model=args.model,
        )

    # Create and run agent
    agent = EstimationAgent(
        llm_client=llm_client,
        search_budgets_fn=search_budgets_wrapped,
        calculate_estimate_fn=calculate_estimate_wrapped,
        model=args.model,
    )

    log.info("agent_running", model=args.model, stub=args.stub)
    execution = await agent.run(transcript)
    log.info(
        "agent_finished",
        reason=execution.termination_reason,
        steps=execution.step_count,
        tokens_in=execution.total_input_tokens,
        tokens_out=execution.total_output_tokens,
    )

    # Format and output trace
    trace_text = format_trace_for_console(execution)
    trace_dict = execution.to_dict()

    if args.output:
        # Save both text and JSON
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.with_suffix(".txt").write_text(trace_text, encoding="utf-8")
        args.output.with_suffix(".json").write_text(
            json.dumps(trace_dict, indent=2), encoding="utf-8"
        )
        log.info("trace_saved", text=str(args.output.with_suffix(".txt")), json=str(args.output.with_suffix(".json")))
    else:
        # Print to stdout
        print(trace_text)


if __name__ == "__main__":
    asyncio.run(main())
