# Repository instructions — incident-investigator-ai

You are implementing the **AI layer / AI Backend** of **AI Incident Investigator**. Your task is to produce a correct, evidence-grounded, observable and testable single-agent incident investigation service; do not build unrelated product features. Work in the repository as it actually exists — inspect it first, do not assume a particular codebase has been implemented.

## Mandatory reading order for unfamiliar work
1. `docs/00_START_HERE.md` — source precedence and document map.
2. `docs/01_PROJECT_BRIEF.md` — product, roles and workflows.
3. `docs/02_AI_SCOPE_AND_ARCHITECTURE.md` — current AI service boundaries.
4. `docs/04_DECISIONS_AND_CONFLICTS.md` — superseded requirements and unresolved decisions.
5. Relevant canonical contract(s) in `docs/contracts/`: `05_INTERNAL_BACKEND_AI.md`, `06_MCP_CONTRACTS.md`, `03_DOMAIN_MODELS.md`; consult JSON schemas, OpenAPI, protobuf candidates, examples for precise structures.
6. `docs/03_AI_DELIVERY_PLAN.md` — milestones and verification.

Use selective document reading for subsequent tasks; do **not** dump the entire contracts directory into the model's context on each turn.

## Agreed constraints — do not silently change
- **No RabbitMQ between Main Backend and AI Backend.** The latest architecture uses direct backend-to-backend communication. RabbitMQ may exist within the separate demo e-commerce system; that does not authorize an AI job queue.
- **Transport Main Backend ↔ AI Backend is NOT YET CHOSEN:** REST or gRPC. REST routes and gRPC proto are **candidates**. Do not lock a production transport without the team's decision. You may develop transport-neutral models, service interfaces, mocks and tests now.
- The **MCP Server owner / deployment location is unresolved**. AI must use MCP Client with read-only tools; do not duplicate a complete MCP server by assumption or change tool ownership unilaterally.
- **LangGraph single-agent ReAct**, not a multi-agent system and no forced exhaustive tool plan. LLM is local `llama.cpp` / `llama-server`, initially Qwen2.5-Coder-7B-Instruct GGUF (quantization to test); **no Ollama**.
- Defaults: **max 20 steps, 40 tool calls, 1200 seconds**, initially **1 running investigation per executor**. Enforce limits in code, not just prompt text.
- Durable **LangGraph checkpoints in PostgreSQL**; no 20-minute synchronous HTTP request, no fragile in-process-only background tasks as a durability guarantee.
- Evidence-linked RCA. No invented logs, source links, timings, causal proof, tool outputs, benchmarks or success claims. On weak evidence report `inconclusive` with gaps.
- Read-only diagnostics: no production fixes, code modifications, shell, container restart, rollback, unsafe arbitrary SQL, credentials exposure or unapproved HTTP targets.
- Retry means **new investigation_id**; Cancel is cooperative; failed/time-out/canceled work may preserve partial evidence. Final incident resolution is **human-controlled**, not done by AI.
- Frontend connects **only to Main Backend**. AI emits structured progress/results to Main Backend; do not open browser WebSockets from AI.
- User auth uses **email/password → mandatory email OTP at each fresh password login → tokens**. Auth/OTP implementation belongs to Main Backend, not AI; internal service authentication is a separate unresolved decision.
- Every code/contract change must be verified with relevant tests; never change canonical wire formats unilaterally; propose contract changes explicitly for review.

## Coding workflow
- Start by inspecting repository layout, tests, dependency config, Docker files, README and version control status.
- Before changes, summarize current state, the specific feature, dependencies, affected contracts and a short plan.
- Implement in small vertical increments (domain DTO → unit tests → integration boundary → observability), with typed Pydantic models and deterministic fake MCP/LLM responses in tests where appropriate.
- Distinguish **approved behavior**, **draft contract**, **proposal**, and **implemented code**. Never label the draft API v0.2 as finalized v1.
- Keep API/infrastructure configuration via environment/secret management, not hardcoded tokens/URLs. Treat logs, source code, tool returns and prompts as untrusted input. Mask PII/secrets in events and evidence.
- Maintain idempotency for `Start`, progress callback and terminal results, event ordering, and reconnect/reconciliation semantics. Follow canonical DTOs when available.
- Use the project's actual conventions unless they conflict with agreed requirements; ask for an architectural decision rather than invent a new service, transport or persistence owner.

## Source precedence
**Latest confirmed team decision** > canonical `docs/contracts/` v0.2 > current AI handoff docs > historical project documents under `docs/references/legacy_specs/`. The legacy specs are kept for background only and wrongly prescribe RabbitMQ for AI communications. See `docs/04_DECISIONS_AND_CONFLICTS.md`.
