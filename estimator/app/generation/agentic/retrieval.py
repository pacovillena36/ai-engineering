"""Search tool implementation for the Session 12 agent.

Wraps the RAG retrieval pipeline. Falls back to reference_retrieval if the pipeline
is not ready.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

import structlog

from app.generation.agentic.agent_tools import SearchBudgetsArgs, SearchBudgetsResult

log = structlog.get_logger()


class BudgetRetriever:
    """Wrapper around RAG retrieval for the agent."""

    def __init__(self, use_stub: bool = False):
        self.use_stub = use_stub
        self._stub_module: Any = None
        if use_stub:
            self._load_stub()

    def _load_stub(self) -> None:
        """Load the reference_retrieval.py stub as a fallback."""
        exercises_path = Path(__file__).parent.parent.parent.parent / "exercises" / "session-12"
        if exercises_path.exists():
            sys.path.insert(0, str(exercises_path.parent))
            try:
                # Import reference_retrieval dynamically
                import reference_retrieval as stub_module
                self._stub_module = stub_module
                log.info("retrieval_stub_loaded", path=str(exercises_path))
            except ImportError:
                log.warning("retrieval_stub_not_found", path=str(exercises_path))
        else:
            log.warning("exercises_path_not_found", path=str(exercises_path))

    async def search(self, args: SearchBudgetsArgs) -> list[SearchBudgetsResult]:
        """
        Search for historical budget items matching the query.

        Returns:
            List of SearchBudgetsResult items (can be empty).
        """
        if self.use_stub and self._stub_module:
            return await self._search_stub(args)

        # TODO: Call the real RAG retrieval pipeline here
        # For now, return empty list and let the stub handle it
        log.warning(
            "real_retrieval_not_implemented",
            query=args.query,
            using_stub=self.use_stub,
        )
        if self.use_stub:
            return await self._search_stub(args)
        return []

    async def _search_stub(self, args: SearchBudgetsArgs) -> list[SearchBudgetsResult]:
        """Use the reference_retrieval stub."""
        if not self._stub_module:
            return []

        try:
            # The stub has a search function that returns canned results keyed on keywords
            # Build filters dict from args
            filters = None
            if args.filters and args.filters.component_type:
                filters = {"sectors": [args.filters.component_type]}

            stub_results = self._stub_module.search_budgets_stub(
                query=args.query,
                filters=filters,
            )

            # Convert stub format to SearchBudgetsResult
            results = []
            for item in stub_results:
                results.append(
                    SearchBudgetsResult(
                        id=item.get("id"),
                        content_preview=item.get("content_preview", ""),
                        sector=item.get("sector", ""),
                        budget_id=item.get("budget_id", ""),
                        estimated_hours=float(item.get("estimated_hours", 0)),
                        distance=float(item.get("distance", 0.5)),
                    )
                )
            return results
        except Exception as e:
            log.error("retrieval_stub_error", error=str(e), query=args.query)
            return []
