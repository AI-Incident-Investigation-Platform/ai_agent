# Начни здесь — источники, приоритеты и область задачи

## Цель передачи
Сохранить достаточный контекст о **всём AI Incident Investigator**, чтобы Codex мог независимо проектировать и реализовывать **AI Backend** и не ломать интеграцию с Main Backend, Frontend и Infra. Это НЕ дамп переписки и НЕ свидетельство реализации описанных функций.

## Приоритет источников при конфликтах
1. Последние **явно согласованные решения команды**, зафиксированные ниже / в `04_DECISIONS_AND_CONFLICTS.md`.
2. `docs/contracts/` — актуальные спецификации **v0.2-draft**. Транспортные кандидаты (`ai-backend-rest-candidate` и `.proto`) не равны принятому решению.
3. `docs/01_PROJECT_BRIEF.md`, `02_AI_SCOPE_AND_ARCHITECTURE.md`, `03_AI_DELIVERY_PLAN.md` — адаптация контекста под работу AI-репозитория.
4. `docs/references/legacy_specs/` — более ранняя документация, полезная для требований к функциональности, но в ней ошибочно указан **RabbitMQ между Backend и AI**.
5. `docs/references/frontend_ui/` — UX-потребности экрана; детали API должны проверяться по OpenAPI/JSON Schema.

## Прочитай обязательно при первой сессии
- `../AGENTS.md`.
- `01_PROJECT_BRIEF.md`.
- `02_AI_SCOPE_AND_ARCHITECTURE.md`.
- `04_DECISIONS_AND_CONFLICTS.md`.
- `contracts/05_INTERNAL_BACKEND_AI.md`.
- `contracts/06_MCP_CONTRACTS.md`.
- `contracts/10_OPEN_DECISIONS.md`.

## Под задачу
| Работа | Открыть дополнительно |
|---|---|
| DTO запуска, event и результата | `contracts/schemas/ai-start-request.schema.json`, `ai-events.schema.json`, `ai-result-callback.schema.json`, `rca-report.schema.json`, `contracts/examples/` |
| REST integration | `contracts/openapi/ai-backend-rest-candidate.openapi.yaml` (**кандидат**) |
| gRPC integration | `contracts/proto/ai-backend-candidate.proto` (**кандидат**) |
| MCP Client | `contracts/mcp/tool-catalog.json`, `contracts/schemas/mcp-results.schema.json` |
| Domain / reviewer links | `contracts/03_DOMAIN_MODELS.md`, `contracts/04_FRONTEND_API_AND_WS.md` |
| Service-to-service auth | `contracts/08_SECURITY_AND_ERRORS.md`, `contracts/10_OPEN_DECISIONS.md` |
| Infra and local LLM | `02_AI_SCOPE_AND_ARCHITECTURE.md`, `references/legacy_specs/04_INFRA_REPOSITORY.md` (историческое) |
| Общая UI картина | `references/frontend_ui/10_INCIDENT_DETAIL.md`, `04_LIVE_INVESTIGATIONS.md` |

## Требования к ответам Codex
Всегда отделяй: **подтверждено** / **предлагается** / **требует решения** / **реализовано и протестировано**. Если бизнес/транспортное решение не принято, сначала реализуй нейтральный интерфейс/контрактные тесты либо задай конкретный вопрос, а не подменяй решение команды.
