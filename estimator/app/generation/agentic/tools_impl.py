"""Implementation of the two agent tools: search_budgets and calculate_estimate."""

from __future__ import annotations

import statistics
from typing import Any

import structlog

from app.generation.agentic.agent_tools import (
    CalculateEstimateArgs,
    CalculateEstimateResult,
    ComponentEstimate,
    SearchBudgetsArgs,
    SearchBudgetsResult,
)
from app.generation.agentic.retrieval import BudgetRetriever

log = structlog.get_logger()

# Contingency buffer applied to central estimate
CONTINGENCY_FACTOR = 0.15


class AgentTools:
    """Container for agent tool implementations."""

    def __init__(self, use_stub_retrieval: bool = False):
        self.retriever = BudgetRetriever(use_stub=use_stub_retrieval)

    async def search_budgets(self, args: SearchBudgetsArgs) -> dict[str, Any]:
        """
        Tool: search_budgets.

        Retrieves historical budget items matching the query.
        """
        results = await self.retriever.search(args)

        # Format as dict for JSON serialization
        return {
            "items": [
                {
                    "id": r.id,
                    "content_preview": r.content_preview,
                    "sector": r.sector,
                    "budget_id": r.budget_id,
                    "estimated_hours": r.estimated_hours,
                    "distance": r.distance,
                }
                for r in results
            ],
            "summary": f"Found {len(results)} historical references for query '{args.query}'",
        }

    def calculate_estimate(self, args: CalculateEstimateArgs) -> dict[str, Any]:
        """
        Tool: calculate_estimate (pure, deterministic, no LLM call).

        Computes cost breakdown from components and their historical references.
        """
        components = args.components
        breakdown: list[dict[str, Any]] = []
        total_hours = 0.0

        for component in components:
            name = component.get("name", "unknown")
            refs = component.get("reference_amounts", [])

            # Choose central estimate (median is robust to outliers)
            if refs:
                central = statistics.median(refs)
                hours = round(central * (1 + CONTINGENCY_FACTOR), 1)
                unbudgeted = False
            else:
                hours = 0.0
                unbudgeted = True

            total_hours += hours
            breakdown.append(
                {
                    "name": name,
                    "reference_count": len(refs),
                    "estimated_hours": hours,
                    "unbudgeted": unbudgeted,
                }
            )

        total_hours = round(total_hours, 1)
        summary = f"total={total_hours}h across {len(breakdown)} components"

        return {
            "components": breakdown,
            "total_hours": total_hours,
            "summary": summary,
        }
