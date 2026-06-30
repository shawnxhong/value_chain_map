# VCM backend

Layer-2 (industry structure & value chain) map engine. See `../plan/` for the full plan and `../docs/value_chain_map_design.md` for the design baseline.

## Local dev

```bash
cd backend
uv venv
uv pip install -e ".[dev]"        # add ".[parse]" where you run ingestion
uv run uvicorn vcm.main:app --reload
# health: http://localhost:8000/api/health
```

Run tests:

```bash
uv run pytest
```

## Config

Settings load from `VCM_*` environment variables or an `.env` file (see `vcm/config.py`). Anthropic credentials are **not** held in config — the SDK reads `ANTHROPIC_API_KEY` or an `ant` profile at call time.

## Layout

`vcm/` packages map 1:1 to the design modules: `ingestion · parsing · extraction · verification · resolution · evidence · graph · analytics · review · financials · eval · llm · api · models · db`. Most are stubs at the scaffold stage; see each package docstring.
