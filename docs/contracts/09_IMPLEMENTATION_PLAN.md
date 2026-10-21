# 09. Параллельная разработка, тестирование и приёмка контрактов

## 1. Точный порядок работ

| Этап | Юрий / Main Backend | Олег / AI Backend | Расул / Frontend | Даниил / Infra |
|---|---|---|---|---|
| **A. Контракты** | OpenAPI main/callbacks, домен, auth, RBAC | OpenAPI AI REST candidate, events, MCP schemas | typed client, mock WS | service URLs, Docker DNS, secrets |
| **B. Локальные моки** | Mock AI commands, mock MCP if backend owns server | Mock Main callbacks/context, fake sources without hardcoded RCA | mock REST + WS fixtures | Compose profiles, test data paths |
| **C. Вертикальный срез** | Ingest → Incident → Start AI → persist event/report | accept → LangGraph → MCP → callback | Incident list/detail + live feed + RCA | monitoring and tracing, local llama.cpp |
| **D. Надёжность** | replay + idempotency, cancel/retry, RBAC | checkpoints, retries, failure/inconclusive, cleanup | reconnect, 403/429/empty states | restarts, unavailable services |
| **E. Оценка** | real evidence provenance, review/audit | 10–15 reproducible fault scenarios | end-to-end UI | real OTEL/Prometheus/Tempo/ELK |

## 2. Contract test obligations

**Main Backend (provider):** OpenAPI schema validation on every operation; 401/403 project boundary; 409 invalid transition; 202 async start; UUIDs/UTC; WS sequence/catch-up; callback dedup.

**AI Backend (provider):** validates `StartAIRequest`; 202 fast; identical Idempotency-Key does not produce second run; cancellation cooperative; status readable; callback retry on 502/timeout, events ordered.

**MCP Server (provider):** `tools/list` inputSchema exactly matches catalog; bounded outputs and timeouts; reject cross-project, unsupported/unsafe operations; no secrets leaks.

**Frontend:** generated TS types; REST mock fixtures pass schema; reducer dedups WebSocket; retry creates new run; Viewer cannot trigger actions; `inconclusive` UI honest.

**Infra:** test that `main-backend` can call AI by DNS/service auth, AI can call back, no public exposure of `/internal/v1` or `/mcp`, native macOS llama.cpp URL via host bridge works, configured stack is feasible for 16 GB hosts.

## 3. E2E demo, который должен пройти

1. В демонстрационном e-commerce вводится контролируемая ошибка `payment-service` (например, утечка пула PostgreSQL).
2. Реальные метрики/логи/трейсы меняются; Alertmanager отправляет webhook.
3. Backend создаёт/дедуплицирует Incident, создаёт run, вызывает AI напрямую.
4. AI исполняет реальные read-only MCP Tools, формирует гипотезы и доказательства с source refs.
5. Frontend через WebSocket показывает Tool Started/Completed, Hypothesis Updated, Evidence Added; при разрыве делает replay.
6. AI возвращает Report с причинной цепочкой и ссылками, при нехватке данных честно `inconclusive`.
7. Пользователь Review — `confirmed/rejected/corrected`; resolved статус НЕ появляется автоматически.
8. Интеграция отключается, повторяем сценарий: нет ложного Evidence, UI показывает partial/unavailable.
9. Retry старого investigation создаёт новый ID, история первой попытки сохранена.

## 4. Договор об изменениях

- `main-backend.openapi.yaml` — owner Юрий, review Расул и Олег.
- `ai-backend-rest-candidate.openapi.yaml` — owner Олег, review Юрий.
- `schemas/ai-events.schema.json`, `schemas/ai-result-callback.schema.json`, `mcp/tool-catalog.json` — shared owner Олег + Юрий.
- Изменение wire fields/enum не сливать без совместного CI contract test (backend provider, AI mock, frontend generated types).
- Репозитории остаются **четырьмя**; источник истины схем хранить через Git submodule/subtree/CI-published artifact — организационная деталь открыта. Не заводить пятый runtime-сервис ради контрактов.

## 5. Что нельзя выдавать за готовую реализацию

1. HTTP `202` **не означает**, что расследование завершилось или AI уже стартовал.
2. «Обнаружена причина» без реальных source_refs **не считается** результатом.
3. REST-кандидат **не означает**, что команда уже выбрала REST вместо gRPC.
4. Нельзя считать макет Service Map доказательством автообнаружения.
5. Факт того, что в макете редактируются лимиты AI, не означает, что Backend должен открыть их для пользовательского PATCH.
6. Нельзя показывать фиктивные «live» сообщения вместо реального stream при интеграционном тесте.

## Дополнение v0.2: Auth OTP в разработке и CI

1. Backend и Frontend использовать только новый двухэтапный auth, в том числе в mocked Swagger examples.
2. Контрактные тесты: login 202 без JWT, verify 200 + токены, resend 202 + old OTP invalid, expired 410, throttling 429, concurrency/race.
3. Infra предоставить mock mail sender (Mailpit или аналог), SMTP/API provider credentials только в secrets, не в git.
4. На всех 9 экранах требуется auth guard; отдельно разработать Login и Verify email UI.
