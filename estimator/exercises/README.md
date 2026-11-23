# Exercises — Session Support Materials

This directory contains pre-made and reference materials for each session of the **Master en AI Engineering**.

## Session 12 — Manual Agent Loop

Located in `session-12/`:

| File | Purpose |
|---|---|
| `sample_transcript_simple.txt` | Simple 1-component use case for quick testing |
| `sample_transcript_complex.txt` | Multi-component realistic scenario (target for evaluation) |
| `reference_retrieval.py` | Safety-net stub: canned corpus for testing without RAG pipeline |
| `calculate_estimate_skeleton.py` | Starter skeleton for the deterministic cost calculation tool |

### Quick Start

```bash
# Run the agent on the simple transcript with mock model (no tokens spent)
cd ../..
uv run python scripts/run_agent_s12.py \
    exercises/session-12/sample_transcript_simple.txt \
    --model mock \
    --stub \
    --output outputs/trace_simple

# Run on complex transcript
uv run python scripts/run_agent_s12.py \
    exercises/session-12/sample_transcript_complex.txt \
    --model mock \
    --stub \
    --output outputs/trace_complex

# Run with real model (requires OPENAI_API_KEY)
export OPENAI_API_KEY=sk-...
uv run python scripts/run_agent_s12.py \
    exercises/session-12/sample_transcript_complex.txt \
    --model gpt-5-mini \
    --stub \
    --output outputs/trace_real
```

### How to Use the Materials

1. **`reference_retrieval.py`**: 
   - Standalone stub with keyword-matched corpus
   - Use with `--stub` flag to bypass RAG pipeline
   - For testing the agent loop logic without infrastructure

2. **`calculate_estimate_skeleton.py`**:
   - Pure deterministic function (median + 15% contingency)
   - No LLM calls, no side effects
   - Fully implemented; use as reference

3. **Transcripts**:
   - Simple: single component ("OAuth backend"), straightforward dialogue
   - Complex: multi-turn meeting with multiple requirements

### Outputs

The agent produces:
- **`trace_*.txt`**: Human-readable execution trace
- **`trace_*.json`**: Machine-readable Pydantic objects (audit trail)

Each trace includes:
- Step-by-step reasoning, action, and observation
- Tool arguments (after validation)
- Execution metrics (duration, tokens)
- Termination reason and final estimate
