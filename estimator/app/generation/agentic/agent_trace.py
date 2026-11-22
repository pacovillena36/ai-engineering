"""Structured trace for Session 12 agent execution.

Each step captures reasoning, action, and observation for auditability and cost analysis.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentStep(BaseModel):
    """One iteration of the agent loop: reasoning → action → observation."""

    step_number: int = Field(description="Iteration number (1-indexed)")
    tool_name: str = Field(description="Name of the tool called (search_budgets, calculate_estimate)")
    duration_ms: int = Field(description="Execution time in milliseconds")
    input_tokens: int = Field(default=0, description="Tokens consumed by the LLM call")
    output_tokens: int = Field(default=0, description="Tokens produced by the LLM call")
    reasoning: Optional[str] = Field(
        default=None,
        description="Agent reasoning (extracted from reasoning_effort output if available; TODO if not)",
    )
    action_arguments: dict[str, Any] = Field(
        default_factory=dict, description="Arguments passed to the tool (after validation)"
    )
    observation: str = Field(description="Tool result or error (human-readable summary for trace)")
    tool_error: Optional[str] = Field(
        default=None,
        description="If tool execution failed, the error message. Sent back to agent as 'error' observation.",
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict (for JSON output or logging)."""
        return {
            "step_number": self.step_number,
            "tool_name": self.tool_name,
            "duration_ms": self.duration_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "reasoning": self.reasoning,
            "action_arguments": self.action_arguments,
            "observation": self.observation,
            "tool_error": self.tool_error,
        }


class AgentExecution(BaseModel):
    """Complete trace of one agent execution."""

    execution_id: str = Field(description="Unique identifier for this execution")
    model: str = Field(description="LLM model used")
    tools_schema_version: str = Field(
        default="v1", description="Version of the tool schemas (for iterative improvement)"
    )
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = Field(default=None)
    steps: list[AgentStep] = Field(default_factory=list)
    termination_reason: str = Field(
        default="", description="How the agent exited: 'success', 'max_iterations', 'max_tool_calls', 'error'"
    )
    final_estimate: Optional[dict[str, Any]] = Field(
        default=None, description="The final structured estimate (if successful)"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error that caused termination (if applicable)"
    )

    @property
    def total_duration_ms(self) -> int:
        """Total execution time in milliseconds."""
        if self.finished_at and self.started_at:
            if isinstance(self.finished_at, (int, float)) and isinstance(self.started_at, (int, float)):
                # Both are timestamps
                delta_seconds = self.finished_at - self.started_at
            else:
                # Both are datetime objects
                delta = self.finished_at - self.started_at
                delta_seconds = delta.total_seconds()
            return int(delta_seconds * 1000)
        return 0

    @property
    def total_input_tokens(self) -> int:
        """Sum of all input tokens across all steps."""
        return sum(step.input_tokens for step in self.steps)

    @property
    def total_output_tokens(self) -> int:
        """Sum of all output tokens across all steps."""
        return sum(step.output_tokens for step in self.steps)

    @property
    def step_count(self) -> int:
        """Number of steps executed."""
        return len(self.steps)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "execution_id": self.execution_id,
            "model": self.model,
            "tools_schema_version": self.tools_schema_version,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "total_duration_ms": self.total_duration_ms,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "step_count": self.step_count,
            "steps": [step.to_dict() for step in self.steps],
            "termination_reason": self.termination_reason,
            "final_estimate": self.final_estimate,
            "error_message": self.error_message,
        }


def format_trace_for_console(execution: AgentExecution) -> str:
    """Format the trace as human-readable output for console/file."""
    lines = [
        "=" * 80,
        f"AGENT EXECUTION TRACE",
        f"{'=' * 80}",
        f"Execution ID: {execution.execution_id}",
        f"Model: {execution.model}",
        f"Tools Schema Version: {execution.tools_schema_version}",
        f"Started: {execution.started_at.isoformat()}",
        f"Finished: {execution.finished_at.isoformat() if execution.finished_at else 'N/A'}",
        f"Total Duration: {execution.total_duration_ms}ms",
        f"Total Tokens: {execution.total_input_tokens} in / {execution.total_output_tokens} out",
        f"Steps: {execution.step_count}",
        f"Termination: {execution.termination_reason}",
        "",
    ]

    for step in execution.steps:
        lines.append(f"--- STEP {step.step_number} ---")
        if step.reasoning:
            lines.append(f"Reasoning: {step.reasoning}")
        lines.append(f"Action: {step.tool_name}({step.action_arguments})")
        lines.append(f"Observation: {step.observation}")
        if step.tool_error:
            lines.append(f"Error: {step.tool_error}")
        lines.append(f"Duration: {step.duration_ms}ms | Tokens: {step.input_tokens}in/{step.output_tokens}out")
        lines.append("")

    if execution.final_estimate:
        lines.append(f"--- FINAL ESTIMATE ---")
        lines.append(str(execution.final_estimate))
        lines.append("")

    if execution.error_message:
        lines.append(f"ERROR: {execution.error_message}")

    lines.append("=" * 80)
    return "\n".join(lines)
