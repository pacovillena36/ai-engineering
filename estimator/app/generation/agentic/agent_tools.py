"""Tool schemas and definitions for Session 12 agent.

The two tools are:
1. search_budgets — retrieves historical budget items matching a component query
2. calculate_estimate — computes cost from components and their historical references

Both use strict JSON Schema (strict=True with the Responses API) and return
structured, validated results.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, field_validator


# --- Tool argument schemas (Pydantic) ----------------------------------------


class SearchBudgetsFilters(BaseModel):
    """Optional filters for the search_budgets tool."""

    component_type: str | None = Field(
        default=None,
        max_length=64,
        description="Narrow by component type (e.g., 'authentication', 'backend').",
    )
    date_range: dict[str, str] | None = Field(
        default=None,
        description='Narrow by date range: {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}.',
    )

    @field_validator("date_range", mode="before")
    @classmethod
    def validate_date_range(cls, v: Any) -> Any:
        if v is None:
            return None
        if not isinstance(v, dict):
            raise ValueError("date_range must be a dict or null")
        if "start" in v and "end" in v:
            # Basic ISO format check
            for key in ("start", "end"):
                if not v[key].count("-") == 2:
                    raise ValueError(f"{key} must be in YYYY-MM-DD format")
        return v


class SearchBudgetsArgs(BaseModel):
    """Arguments for search_budgets tool."""

    query: str = Field(
        min_length=1,
        max_length=500,
        description="Natural language description of the component to search for (e.g., 'OAuth2 authentication backend with JWT and rate limiting').",
    )
    filters: SearchBudgetsFilters | None = Field(
        default=None,
        description="Optional filters (component_type, date_range). Pass null if no filters.",
    )


class SearchBudgetsResult(BaseModel):
    """One historical budget item returned by search_budgets."""

    id: int = Field(description="Unique identifier of the historical record.")
    content_preview: str = Field(
        description="Short summary of the historical project component."
    )
    sector: str = Field(description="Industry or sector (e.g., 'finance', 'logistics').")
    budget_id: str = Field(description="Reference budget identifier.")
    estimated_hours: float = Field(
        ge=0, description="Historical engineer-hours for this component."
    )
    distance: float = Field(
        ge=0,
        le=1,
        description="Relevance score (0=exact match, 1=no match). Used by the agent to gauge confidence.",
    )


class ComponentEstimate(BaseModel):
    """One component in the calculate_estimate result."""

    name: str = Field(
        min_length=1, max_length=256, description="Name of the component."
    )
    reference_count: int = Field(
        ge=0, description="Number of historical references used."
    )
    estimated_hours: float = Field(
        ge=0, description="Estimated engineer-hours for this component (central + contingency)."
    )
    unbudgeted: bool = Field(
        description="True if no historical references were found (agent must search again)."
    )


class CalculateEstimateArgs(BaseModel):
    """Arguments for calculate_estimate tool."""

    components: list[dict[str, Any]] = Field(
        min_items=1,
        description="Array of components to cost. Each component has 'name' (string) and 'reference_amounts' (list of historical hours).",
    )

    @field_validator("components", mode="before")
    @classmethod
    def validate_components(cls, v: Any) -> Any:
        if not isinstance(v, list):
            raise ValueError("components must be a list")
        for idx, comp in enumerate(v):
            if not isinstance(comp, dict):
                raise ValueError(f"component[{idx}] must be a dict")
            if "name" not in comp:
                raise ValueError(f"component[{idx}] missing required field 'name'")
            if "reference_amounts" not in comp:
                raise ValueError(
                    f"component[{idx}] missing required field 'reference_amounts'"
                )
            if not isinstance(comp["reference_amounts"], list):
                raise ValueError(
                    f"component[{idx}]['reference_amounts'] must be a list"
                )
        return v


class CalculateEstimateResult(BaseModel):
    """Result from calculate_estimate tool."""

    components: list[ComponentEstimate] = Field(
        description="Per-component cost breakdown."
    )
    total_hours: float = Field(
        ge=0, description="Sum of all component estimated hours."
    )
    summary: str = Field(
        description="Human-readable summary of the calculation (used in agent trace)."
    )


# --- Tool definitions for the Responses API (strict JSON Schema) ----------------


def get_search_budgets_tool_definition() -> dict[str, Any]:
    """
    Tool definition for search_budgets with strict JSON Schema.

    When strict=True, all properties must be in 'required' and 'additionalProperties'
    must be false at every object level. Nullable fields use type: ["type", "null"].
    """
    return {
        "type": "function",
        "name": "search_budgets",
        "description": (
            "Retrieve historical budget items (with engineer-hours) for a component. "
            "Use this when the agent needs reference data to estimate cost. "
            "Query should be a natural-language description (e.g., 'OAuth2 backend with JWT'). "
            "Returns a list of historical records with estimated_hours in engineer-days. "
            "Do NOT use this to calculate totals — use calculate_estimate instead. "
            "If the query is too generic or no items match, returns empty list; consider narrowing or rephrasing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 500,
                    "description": (
                        "Natural language description of the component to find historical references for. "
                        "Example: 'OAuth2 authentication backend with JWT and rate limiting'. "
                        "Be specific about technology and requirements."
                    ),
                },
                "filters": {
                    "type": ["object", "null"],
                    "description": (
                        "Optional search filters. Pass null for no filters. "
                        "Available filters: component_type (string, e.g. 'authentication'), "
                        "date_range (object with 'start' and 'end' in YYYY-MM-DD format)."
                    ),
                    "properties": {
                        "component_type": {
                            "type": ["string", "null"],
                            "maxLength": 64,
                            "description": "Narrow by component type (e.g., 'authentication', 'backend'). Pass null to skip.",
                        },
                        "date_range": {
                            "type": ["object", "null"],
                            "description": "Narrow by date range. Pass null to skip.",
                            "properties": {
                                "start": {
                                    "type": "string",
                                    "pattern": r"^\d{4}-\d{2}-\d{2}$",
                                    "description": "Start date in YYYY-MM-DD format.",
                                },
                                "end": {
                                    "type": "string",
                                    "pattern": r"^\d{4}-\d{2}-\d{2}$",
                                    "description": "End date in YYYY-MM-DD format.",
                                },
                            },
                            "required": ["start", "end"],
                            "additionalProperties": False,
                        },
                    },
                    "required": ["component_type", "date_range"],
                    "additionalProperties": False,
                },
            },
            "required": ["query", "filters"],
            "additionalProperties": False,
        },
    }


def get_calculate_estimate_tool_definition() -> dict[str, Any]:
    """
    Tool definition for calculate_estimate with strict JSON Schema.

    Pure, deterministic function: takes a list of components and their historical
    references, returns a cost breakdown with contingency included.
    """
    return {
        "type": "function",
        "name": "calculate_estimate",
        "description": (
            "Calculate total cost (in engineer-hours) from components and their historical references. "
            "Use this AFTER gathering historical data with search_budgets. "
            "This tool is deterministic: same inputs → same output. No LLM call, no side effects. "
            "Returns component-level breakdown plus total. Do NOT use this to search for data — use search_budgets instead. "
            "If a component has no reference_amounts (empty list), it is marked 'unbudgeted'; agent must search again."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "components": {
                    "type": "array",
                    "minItems": 1,
                    "description": (
                        "Array of components to cost. "
                        "Each item is an object: {'name': string, 'reference_amounts': [list of historical hours]}. "
                        "Example: [{'name': 'Auth backend', 'reference_amounts': [420.0, 380.0]}, ...]"
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 256,
                                "description": "Name of the component.",
                            },
                            "reference_amounts": {
                                "type": "array",
                                "description": (
                                    "List of historical engineer-hour estimates for this component. "
                                    "Can be empty; if so, component is marked unbudgeted."
                                ),
                                "items": {"type": "number", "minimum": 0},
                            },
                        },
                        "required": ["name", "reference_amounts"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["components"],
            "additionalProperties": False,
        },
    }


def schema_to_json_string(schema: dict[str, Any]) -> str:
    """Serialize a tool definition to JSON string (for display in traces)."""
    return json.dumps(schema, indent=2)
