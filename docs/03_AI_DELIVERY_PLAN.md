# AI Backend — реалистичный порядок работ для Codex

**Внимание:** ниже предложен implementation plan. Это не утверждение о том, что что-либо уже реализовано. Сначала Codex должен прочитать текущий репозиторий и зафиксировать gaps.

## Фаза 0. Repo audit и фиксация допущений
- Проверить tree, deps/lockfiles, runtime Python, package layout, tests/CI, Docker, существующий `.env.example`, миграции, `git status`.
- Составить карту существующего кода: что работает, что mock/TODO, какие контракты соблюдены, какие отсутствуют.
- Отметить open decisions из `04_DECISIONS_AND_CONFLICTS.md`: RPC transport, MCP Server owner, executor policy, database ownership, service auth.
- Не добавлять новый framework или сервис только потому, что он популярный.

## Фаза 1. Domain DTO и контракты
- Pydantic v2 DTO для Start/Get/Cancel/Events/Result, RCA, Evidence, Hypothesis, budgets, error envelope. Source: `contracts/schemas/` и `contracts/05_INTERNAL_BACKEND_AI.md`.
- Contract tests/JSON Schema validation для **примеров** `contracts/examples/`.
- Преобразование external wire DTO ↔ internal domain state отдельно от agent logic.
- Дедуп/идемпотентность по IDs + sequence (правила в контракте), статусные переходы и Retry new ID.

## Фаза 2. Single-agent LangGraph loop
- Minimal controlled graph с deterministic fake LLM + fake MCP, чтобы проверять переходы, budget, hypothesis, evidence, invalid output, `inconclusive`.
- Реальная LLM abstraction через `llama.cpp/llama-server` с configurable base URL/model/timeout; benchmark later.
- Structured response parse and evidence validation; не принимать ссылку/факт без реально полученного tool result.

## Фаза 3. MCP Client и tools
- Streamable HTTP MCP client, discovery (`tools/list`) и типизированные wrappers (`tools/call`) по текущему catalog.
- Validate incoming LLM tool arguments, apply scope and bounded timeouts; support explicit `empty`, `partial`, `truncated`, `error` outputs.
- Secrets redaction, prompt injection resistance, no unrestricted shell/SQL/Docker or open HTTP.
- Endpoint auth implementation ждёт согласования межсервисной идентификации.

## Фаза 4. Durable run execution
- PostgreSQL LangGraph checkpoints, coherent durable run registry/admission control/recovery, cancellation and timeout.
- One active per executor; busy strategy needs team agreement, candidate `429 Retry-After`.
- Testing: crash/restart, duplicate Start, duplicate callback, out-of-order event, cancel vs complete, deadline, tool/model unavailable.

## Фаза 5. Integration Main Backend
- Реализовать **один выбранный** REST/gRPC adapter после согласования. До этого — transport-neutral service and contract tests/mocks.
- Emit validated progress/events/result to Main Backend, idempotent callback/retry; no direct browser WS.
- Correlation IDs / OTel spans, controlled structured logs, secret safe outputs.

## Фаза 6. Demo and evidence-based evaluation
- 6 e-commerce fault scenarios: PG pool exhaustion, bad deploy, latency cascade, OOM restart, RabbitMQ consumer lag/failure, DragonflyDB outage. Это **инциденты демо-приложения**, не транспорт AI backend.
- Evals: can reproduce scenario, agent sources grounded, valid schema, correctly distinguishes root cause/symptom, doesn't invent evidence, arrives to final/`inconclusive` within budget.
- Не выдавать единичный demo run за метрику качества; проводить повторные измерения и фиксировать false positive/negative.

## Вероятная структура кода (КАНДИДАТ — адаптировать к существующей)
```
src/incident_investigator_ai/
  api/              # selected internal REST/gRPC adapter, after decision
  contracts/        # typed wire schemas / validation
  domain/           # incident context, evidence, RCA, run state
  agent/            # LangGraph graph/nodes/state and prompts
  llm/              # llama-server client
  mcp/              # streamable HTTP client and wrappers
  runtime/          # durable execution, budget, cancel, checkpointing
  delivery/         # progress/result callbacks to Main Backend
  observability/    # logs/metrics/traces
  config/           # environment-driven settings
 tests/
```

## Definition of done на каждую работу
- Схема и поведение следуют утверждённому contract; где он draft — это явно указано.
- Unit/contract tests проходят локально; ошибки и крайние случаи покрыты.
- Logs/events не раскрывают credentials и сырые приватные данные.
- Нет выдуманных Evidence/Source references и самовольных production side effects.
- README/config/example обновлены; результаты реального запуска сообщаются **только если действительно проверены**.
