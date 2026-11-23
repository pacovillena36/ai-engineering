# Session 12 Agent Demo Script

## Overview

`run_agent_s12.py` is an end-to-end demonstration of the Session 12 manual agent loop. It:

1. Loads a transcript
2. Instantiates an `EstimationAgent` with configurable LLM and retrieval backend
3. Runs the loop (while loop, not Responses API automation)
4. Captures a structured trace (Pydantic models)
5. Saves the trace as JSON and human-readable text

## Usage

```bash
cd estimator
uv run python scripts/run_agent_s12.py <transcript_path> [options]
```

### Arguments

| Argument | Type | Default | Notes |
|---|---|---|---|
| `transcript_path` | positional | — | Path to .txt file (plain text transcript) |
| `--model` | string | `gpt-5-mini` | LLM model: real model or `mock` for scripted test |
| `--stub` | flag | False | Use `reference_retrieval.py` stub instead of RAG pipeline |
| `--output` | path | None | Base path for trace output (without extension) |

### Examples

#### Mock mode (scripted, no tokens spent)
```bash
uv run python scripts/run_agent_s12.py \
    exercises/session-12/sample_transcript_simple.txt \
    --model mock \
    --stub
```

Output to stdout (human-readable trace).

#### Mock mode with file output
```bash
uv run python scripts/run_agent_s12.py \
    exercises/session-12/sample_transcript_complex.txt \
    --model mock \
    --stub \
    --output outputs/trace_simple
```

Produces:
- `outputs/trace_simple.txt` (human-readable)
- `outputs/trace_simple.json` (machine-readable)

#### Real LLM (requires API key)
```bash
export OPENAI_API_KEY=sk-...
uv run python scripts/run_agent_s12.py \
    exercises/session-12/sample_transcript_complex.txt \
    --model gpt-5-mini \
    --stub \
    --output outputs/trace_real
```

## Mock Mode Details

When `--model mock`, the script uses `MockLLMClient` with a **hardcoded scripted sequence**:

1. **Step 1**: `search_budgets(query='authentication backend', filters=None)`
2. **Step 2**: `calculate_estimate(components=[{'name': 'Auth backend', 'reference_amounts': [420.0, 380.0]}])`
3. **Final**: Text response ("Estimation complete. Total effort: ~400 engineer-hours.")

This sequence is **independent of the transcript** — it's a fixed demo sequence for testing the loop mechanics without token cost.

## Real LLM Mode

When `--model gpt-5-mini` (or any real model):
- Requires `OPENAI_API_KEY` environment variable set
- Respects `--stub` flag for retrieval (uses reference corpus if `--stub`, else RAG pipeline)
- Incurs API costs (charged per token)

## Output Format

### Trace Text (`.txt`)
Human-readable format:

```
================================================================================
AGENT EXECUTION TRACE
================================================================================
Execution ID: f75877e8-4f1b-4bf0-8901-f579ccde616f
Model: mock
Tools Schema Version: v1
Started: 2026-11-23T15:59:44.471647
Finished: 2026-11-23T15:59:44.471647
Total Duration: 0ms
Total Tokens: 200 in / 100 out
Steps: 2
Termination: success

--- STEP 1 ---
Action: search_budgets({'query': 'authentication backend', 'filters': None})
Observation: Found 0 historical references for query 'authentication backend'
Duration: 0ms | Tokens: 100in/50out

--- STEP 2 ---
Action: calculate_estimate({'components': [...]})
Observation: total=460.0h across 1 components
Duration: 0ms | Tokens: 100in/50out

--- FINAL ESTIMATE ---
{'summary': 'Estimation complete...', 'step_count': 2}
================================================================================
```

### Trace JSON (`.json`)
Machine-readable format (Pydantic model serialization):

```json
{
  "execution_id": "f75877e8-4f1b-4bf0-8901-f579ccde616f",
  "model": "mock",
  "tools_schema_version": "v1",
  "started_at": "2026-11-23T15:59:44.471647",
  "finished_at": "2026-11-23T15:59:44.471647",
  "total_duration_ms": 0,
  "total_input_tokens": 100,
  "total_output_tokens": 50,
  "step_count": 2,
  "steps": [
    {
      "step_number": 1,
      "tool_name": "search_budgets",
      "duration_ms": 0,
      "input_tokens": 100,
      "output_tokens": 50,
      "reasoning": null,
      "action_arguments": {
        "query": "authentication backend",
        "filters": null
      },
      "observation": "Found 0 historical references...",
      "tool_error": null
    },
    ...
  ],
  "termination_reason": "success",
  "final_estimate": {...},
  "error_message": null
}
```

This format is ideal for:
- Parsing in test suites
- Comparing executions programmatically
- Storing in audit trails
- Integration with dashboards

## Transcript Format

Transcripts are plain UTF-8 text files. The script validates:
- Minimum 20 characters (empty transcripts rejected)
- Maximum 500 KB (guard against abuse)
- No special encoding required

Example (`sample_transcript_simple.txt`):
```
Reunión de descubrimiento — Proyecto "Backend de autenticación"
Cliente: Marta Ledesma (CTO, NeoPagos)
Consultor: equipo de estimación
Fecha: reunión inicial

[00:00:10] Consultor: Gracias por el tiempo, Marta. Cuéntanos qué necesitáis...
[00:00:22] Marta: Vamos al grano. Somos una fintech y necesitamos construir...
```

## Debugging

Enable structured logging:

```python
# If you edit the script:
import structlog
# Already configured in the script; output goes to console
```

Log level defaults to INFO. Filtered output:

```bash
uv run python scripts/run_agent_s12.py ... 2>&1 | grep -E "agent_|retrieval_"
```

## Implementation Notes

- **No network required** with `--model mock`
- **LLM calls are async** but wrapped to work synchronously from the CLI (`asyncio.run()`)
- **Retrieval fallback**: if RAG pipeline is not ready, `--stub` uses the safety-net corpus
- **Trace capture is automatic**: no need to manually wire up logging
