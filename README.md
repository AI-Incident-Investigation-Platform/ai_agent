# AI Incident Investigator — AI Backend

Python 3.14 backend scaffold for AI investigations. The main Backend owns users,
projects, and incidents; this service will run investigations through one
LangGraph agent. Project API and diagnostic tool contracts are available as
v0.2 drafts, not approved production interfaces.

## Project context

Start with [the documentation map](docs/00_START_HERE.md) and
[AI scope and architecture](docs/02_AI_SCOPE_AND_ARCHITECTURE.md).
[Decisions and conflicts](docs/04_DECISIONS_AND_CONFLICTS.md) separate current
team decisions from historical requirements. The [contract pack](docs/contracts/00_README.md)
contains draft JSON Schemas, OpenAPI candidates, a gRPC candidate, MCP tool
catalog, and examples. [Legacy specifications](docs/references/README.md) are
retained for background; their RabbitMQ requirement for Main Backend ↔ AI is
superseded. Repository instructions are in [AGENTS.md](AGENTS.md).

## Run locally

Install [uv](https://docs.astral.sh/uv/) and Python 3.14, then run:

```sh
uv sync
uv run uvicorn ai_agent.api.app:app --host 127.0.0.1 --port 8000
```

`GET http://127.0.0.1:8000/health` returns `{"status":"ok"}`. The response
includes `X-Request-ID`; a valid supplied ID is reused, otherwise one is
generated. Neither this endpoint nor application startup connects to llama.cpp.

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Copy `.env.example` to `.env` when changing local settings. The optional
`AI_AGENT_LLM_BASE_URL`, `AI_AGENT_LLM_MODEL`, and
`AI_AGENT_LLM_TIMEOUT_SECONDS` settings configure a local llama.cpp server's
OpenAI-compatible `/v1/chat/completions` endpoint. The model and server must be
provided separately. `AI_AGENT_LOG_LEVEL` controls application JSON logs.

## Current layout

```text
src/ai_agent/
  api/app.py                  FastAPI assembly and request correlation
  api/routes/health.py        Technical health route
  core/config.py              Environment settings
  core/logging.py             JSON log formatter and request context
  agent/state.py              Minimal graph state
  agent/graph.py              Compiled, no-op LangGraph skeleton
  llm/providers/llama_cpp.py  On-demand llama.cpp HTTP adapter
tests/unit/                  Configuration, graph, and LLM adapter tests
tests/integration/           HTTP health smoke test
```

The graph intentionally has no diagnostic nodes or tool calls. Future
investigation nodes belong under `agent/nodes`, with orchestration in
`application` and contract-owned data types in `domain`. MCP Streamable HTTP
client and potential server implementations will live under separate `mcp/client`
and `mcp/server` packages once tool contracts are defined. The MCP server is a
separate protocol surface from the internal FastAPI API. PostgreSQL checkpoint
storage will be wired at graph compilation through `persistence/checkpoints`
after persistence and recovery contracts are agreed. No database schema is
defined here.

Still to decide: REST or gRPC for the Main Backend boundary; MCP Server
ownership; admission and result recovery policies; service authentication;
and checkpoint storage ownership. The draft contracts describe candidate
investigation and tool schemas, but the current code does not implement them.
The existing `/health` is a technical liveness endpoint, not the draft
`/internal/v1/health` readiness response.
