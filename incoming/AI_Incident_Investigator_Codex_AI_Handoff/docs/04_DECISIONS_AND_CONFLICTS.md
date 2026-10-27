# Принятые решения, устаревшие материалы, открытые вопросы

Дата актуализации handoff: **2026-10-20**. Эта таблица предотвращает важную ошибку: старые PDF/MD/спецификации утверждали RabbitMQ между Backend ↔ AI, но команда **позже отменила эту архитектуру**.

## Подтверждено последними договорённостями
| Тема | Состояние |
|---|---|
| Backend ↔ AI | **Прямое межсервисное взаимодействие без RabbitMQ**. Логический API контракт уже подготовлен в v0.2. |
| Форма AI-компонента | **Отдельный AI Backend**, а не просто скрипт AI Worker; он управляет агентом и отвечает Main Backend. |
| Frontend | Только Main Backend REST/WS, без прямых вызовов AI. |
| Agent | LangGraph, **один ReAct агент**, MCP Client, read-only operations. |
| Local LLM | `llama.cpp/llama-server`, no Ollama, initial Qwen2.5-Coder-7B-Instruct candidate. |
| Budgets | ≤20 steps, ≤40 calls, ≤20 minutes, 1 active executor in initial config. |
| Data / output | PG checkpoints, evidence-backed RCA, up to 3 hypotheses; `inconclusive` on weak data; human review; controlled Cancel/Retry. |
| Browser login | Email + password + **OTP at each new password login**. Implemented on Main Backend side. |
| Current contract pack | `docs/contracts/` **v0.2-draft**, NOT v1 final. |

## Открытые решения — НЕ додумывать
- **REST vs gRPC** Main Backend ↔ AI (both examples are transport candidates).
- **MCP Server ownership**: Backend owned / AI owned / separately deployed; who implements individual tools and where permissions enforced.
- Durable busy-run policy without queue (candidate reject `429 Retry-After` vs durable waiting).
- Reliable delivery of final result when callback lost; GET result candidate and durable callback outbox.
- Internal service authorization mechanism (not browser JWT / OTP).
- PostgreSQL checkpoint schema/database access ownership and migrations.
- Auto-start investigation policy after alert (manual/automatic conditions).
- MVP priorities of advanced Service Map / Logs Explorer / Traces backend APIs.
- Fields of integration configs, detailed MCP security and provider-specific fields, event/Evidence retention.

For **complete** decisions table consult `contracts/10_OPEN_DECISIONS.md` and readiness audit `contracts/13_BACKEND_READINESS_AUDIT.md`. If an answer requires deciding one of these, **ask the owning teammate** or produce a clearly-labeled proposal/ADR — never silently codify a guess.

## Explicit supersessions
1. `references/legacy_specs/00_PROJECT_OVERVIEW.md`, `02_AI_REPOSITORY.md` and Backend/Infra counterparts mention a RabbitMQ consumer, `investigation.requested` exchange, acknowledgement and queue orchestration. **All of that is superseded FOR MAIN BACKEND ↔ AI**. Do not implement those old instructions.
2. Earlier AI spec states MCP Server is strictly Backend-owned. **Location/owner has since become undecided**. Current `contracts/06_MCP_CONTRACTS.md` is authoritative about interface, not final owner.
3. `references/legacy_specs/` and first UI drafts predate obligatory email OTP. Canonical login behavior is `contracts/12_AUTH_EMAIL_OTP.md`; this belongs to Main Backend/Frontend.
4. Old project spec was authored before current v0.2 contract definitions. If field names differ, canonical JSON Schema/OpenAPI takes priority until v1 sign-off.
5. Avoid assuming every proposed endpoint and enum in draft v0.2 is already implemented in a repository; Codex must inspect code, then gap-list.

## ADR discipline
When an open question is resolved, add an ADR and update this file + contract schemas, regenerate mocks/tests as needed, record whether it was approved by Олег/Юрий and date. Do not invent approvals.
