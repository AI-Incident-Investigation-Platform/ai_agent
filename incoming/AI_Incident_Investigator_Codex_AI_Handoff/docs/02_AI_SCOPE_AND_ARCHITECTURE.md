# AI Backend — текущая архитектура и границы реализации

## Функции AI Backend
AI слой — это **самостоятельный Python backend service**. Он предоставляет внутренний сервисный интерфейс к Main Backend, обрабатывает асинхронные investigation runs и размещает LangGraph agent loop, MCP Client, LLM runtime client, durable checkpoints, контроль лимитов, structured progress/results и evaluation. Это не браузерный API.

### Транспортная архитектура (логическая)
```text
Frontend REST/WS
      |
Main Backend (FastAPI, Юрий)
      |  authenticated internal calls: REST or gRPC [TBD]
      v
AI Backend (Олег)
   |-- internal transport adapter [TBD]
   |-- run registry + admission control + cancel
   |-- LangGraph ReAct single agent
   |     |-- local llama.cpp/llama-server, Qwen2.5-Coder-7B-Instruct GGUF candidate
   |     |-- MCP Client --> MCP Server [owner/location TBD]
   |     |                   |--> Elasticsearch / Prometheus / Tempo
   |     |                   |--> GitHub / Docker / Deployments / allowlisted health
   |     +-- PostgreSQL checkpoint store
   +-- event / final-result delivery to Main Backend [contract-defined]
Main Backend persists Incident, Investigation, RCA, Evidence, Review and replays events to WebSocket clients.
```

**Снятое требование:** RabbitMQ между Main Backend и AI Backend. Никаких Rabbit consumers или queue/exchange contracts для AI. RabbitMQ *может оставаться в demo e-commerce как диагностируемая система*.

## Логический LangGraph
`load_context/restore → agent_decision → [validate_tool_call → MCP read-only call → normalize_and_redact → evidence_and_hypotheses_update → checkpoint → agent_decision]* → RCA_validation → terminal_result`. Может завершиться `completed`, `inconclusive`, `failed`, `timed_out`, `canceled`. Модель не обязана использовать все инструменты и не должна вводить фиктивные этапы.

## Accepted constraints
- Single-agent LangGraph ReAct; лимиты **20 шагов / 40 tool calls / 1200 секунд**. Цифры настраиваются безопасно, сервер обязан соблюдать верхние пределы.
- До **трёх** гипотез со статусами и confidence, привязанные к фактически полученным Evidence.
- Evidence включает конкретный источник, project/scope, time window, source locator/excerpt, признак truncation, source_refs; root-cause claim должен ссылаться на фактические доказательства.
- Не раскрывать model chain-of-thought; можно отправлять краткие action summaries и результаты инструментов.
- Обработка невалидных LLM outputs — Pydantic validation, bounded repair, корректный `inconclusive`/`failed` при невозможности восстановления.
- Tools and results untrusted: prompt injection handling, no tools with arbitrary command execution, redaction and allowlists.
- Retry = новый run; Cancel = cooperative, с сохранением имеющейся полезной информации.
- Один concurrent run на executor в MVP. Политика перегрузки **не финализирована** (`429 Retry-After` предлагается).

## Internal contract, НЕ путать с решением о транспорте
В `contracts/05_INTERNAL_BACKEND_AI.md` описаны операции, например `Start`, `GetStatus`, `Cancel`, `PublishEvent`, `SubmitResult`, `GetIncidentContext`, optional `GetResult`. REST-кандидат: `POST /internal/v1/investigations` отдаёт **202 Accepted** после устойчивого принятия задания, а не RCA report. Event/result callbacks должны иметь идемпотентность и сохранение; конечное WebSocket событие Main Backend отправляет после сохранения результата.

**Transport-neutral first:** до решения команды можно реализовать DTO, доменную логику, протокол/интерфейсы адаптеров и тесты; не реализовывать «на всякий случай» и REST и gRPC целиком.

## Durable execution без брокера
- Ни request handler, ни `BackgroundTasks` без дополнительного устойчивого механизма **не могут быть единственным источником исполнения 20-минутной работы**.
- Нужен durable registry с idempotency (`investigation_id`, attempts, status, concurrency, leases/heartbeat или иной согласованный аналог), checkpoint store и recovery logic.
- При рестарте workers: восстановить runs, если безопасно, или записать терминальное failure; не оставлять «вечный running».
- Прогресс: уникальный `event_id`, монотонный `sequence` per run, bounded event payloads. При ошибке internal callback — bounded retries и повтор с тем же ID. Final callback dedupe/atomic persistence — Main Backend.
- AI владеет собственным execution state/checkpoints. Конкретные схемы/ownership PostgreSQL ещё требуют решения.

## MCP tools MVP
`search_logs`, `query_prometheus`, `get_trace`, `get_service_health`, `get_container_status`, `get_container_events`, `get_recent_deployments`, `github_search_code`, `github_get_file`, `github_get_commit`, `github_compare_commits`, `github_get_blame`, `http_health_check`, `get_incident_context`.
Phase 2: `search_docs`, `search_similar_incidents`. **Авторитетный список и input/output schemas**: `contracts/mcp/tool-catalog.json` и `contracts/schemas/mcp-results.schema.json`.

## Local development, proposed
- AI service inside Docker Compose; `llama-server` on host macOS with Apple Metal; from container connect via configurable `host.docker.internal` (verify on actual host).
- GGUF initial candidate Qwen2.5-Coder-7B-Instruct, possible Q4_K_M; do not claim performance before benchmark on available hardware.
- Integration tests use fake deterministic model and fake MCP transports; live demo with actual logs/metrics/traces is separately tested.

## Out of scope for this repository
User JWT/email OTP/RBAC storage, user CRUD, UI screens, browser WS fanout, Main Backend's Incident lifecycle, general-purpose MCP server if its ownership remains with Юрий, and e-commerce microservices. Integration adapters/tools may be co-owned **only after explicit team decision**.
