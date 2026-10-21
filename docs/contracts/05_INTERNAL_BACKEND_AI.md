# 05. Контракт Main Backend ↔ AI Backend (без очереди)

## 1. Что утверждено, что — предложение

**Утверждено командой:** прямое backend-to-backend взаимодействие, **RabbitMQ не нужен**, AI слой — самостоятельный Python Backend + LangGraph + MCP взаимодействие.

**Не утверждено:** REST или gRPC. Нижеследующий wire protocol — **REST-кандидат**. Все DTO/status semantics пригодны и для gRPC. В `openapi/ai-backend-rest-candidate.openapi.yaml` записан конкретный REST маршрут, который можно сразу мокать, **но не считать выбранным транспортом**.

## 2. Команды и внутренние ручки

| Инициатор | Метод / REST candidate | Результат | Какой RPC может заменить |
|---|---|---|---|
| Main → AI | `POST /internal/v1/investigations` | `202 StartAIAck` | `AIInvestigationService.Start` |
| Main → AI | `GET /internal/v1/investigations/{id}` | `200 Investigation` | `AIInvestigationService.GetStatus` |
| Main → AI | `POST /internal/v1/investigations/{id}/cancel` | `202 CancelAck` | `AIInvestigationService.Cancel` |
| Main → AI | `GET /internal/v1/health` | `200 AIHealth` | gRPC Health Checking |
| AI → Main | `POST /internal/v1/ai/events` | `202 CallbackAck` | `IncidentEventSink.PublishEvent` |
| AI → Main | `POST /internal/v1/ai/results` | `202 CallbackAck` | `IncidentEventSink.SubmitResult` |
| AI → Main | `GET /internal/v1/ai/incidents/{id}/context` | `200 IncidentContext` | `IncidentContextService.Get` |

**Никакие callbacks не принимают `callback_url` от пользователя или из AI request payload.** AI сервис использует только заранее настроенный `MAIN_BACKEND_INTERNAL_URL`, иначе возникает SSRF/утечка data в чужую сеть.

## 3. Запуск (request + response)

```http
POST /internal/v1/investigations HTTP/1.1
Authorization: Bearer <service-token>
Idempotency-Key: 2f8b3c24c9ca4443b94d387e1332c670
Content-Type: application/json
```

```json
{
  "schema_version":"1.0",
  "investigation_id":"22222222-2222-4222-8222-222222222222",
  "incident_id":"11111111-1111-4111-8111-111111111111",
  "project_id":"55555555-5555-4555-8555-555555555555",
  "environment_id":"66666666-6666-4666-8666-666666666666",
  "service_ids":["77777777-7777-4777-8777-777777777777"],
  "detected_at":"2026-10-19T14:35:00Z",
  "window":{"from":"2026-10-19T14:05:00Z","to":"2026-10-19T14:40:00Z"},
  "alert_summary":"payment-service HTTP 500 spike",
  "budget":{"max_steps":20,"max_tool_calls":40,"timeout_seconds":1200}
}
```

**Ответ `202 Accepted` (не RCA):**

```json
{"investigation_id":"22222222-2222-4222-8222-222222222222","status":"pending","accepted_at":"2026-10-19T14:40:01Z"}
```

AI должен устойчиво зарегистрировать выполнение до возврата `202`. **Не исполнять LLM синхронно в обработчике HTTP**. `FastAPI BackgroundTasks` без устойчивой модели исполнения — недостаточная гарантия для 20-минутного run. Конкретный механизм исполнения (dedicated task runner в AI, durable registry/leases) — выбор AI владельца с согласованием, **но без брокера**.

## 4. Admission control при одном активном run

В MVP ограничение **одна активная работа на executor**. Пока не выбрана политика накопления pending requests, безопасный кандидат: AI отвечает `429` и `Retry-After` при занятости, Main Backend делает bounded retry/повторную попытку и сохраняет единый run ID. `202` для реально принятого run; никаких висящих соединений на 20 минут. При перезапуске сервиса незавершённые persistent runs необходимо восстановить/пометить сбой — без потери истории.

Обе стороны обязаны согласовать точный backoff, deadline и владельца ожидающего состояния до релиза (см. `10_OPEN_DECISIONS.md`).

## 5. Progress callbacks

AI публикует `InvestigationEvent` по `POST /internal/v1/ai/events`. Строгая структура — `schemas/ai-events.schema.json`.

- `event_id` UUID — дедуп повторной доставки.
- `sequence` int, увеличивается на один **в рамках investigation_id**.
- Main Backend сохраняет событие в transaction + проверяет ID/authorization + обновляет проекцию run.
- HTTP `202` подтверждает успешное сохранение либо признанный дубликат; ответ `{accepted:true,deduplicated:true|false}`.
- При `5xx`/network timeout AI повторяет с backoff, **с тем же event_id и sequence**; ошибки валидации `422` не повторять слепо.
- Callback summary — санитизированный; сырые prompts/credentials/полные логи не отправлять.

## 6. Итоговый RCA callback

`POST /internal/v1/ai/results` с `AIResultCallback`, `$defs` в `schemas/ai-result-callback.schema.json`.

`status = completed|inconclusive|failed|timed_out|canceled`.

- `completed`/`inconclusive`: `report` должен быть `RCAReport` (nullable `root_cause` в inconclusive), hypotheses/evidence/timeline arrays.
- `failed`/`timed_out`/`canceled`: `report=null` допустим, evidence/hypotheses могут быть частичными; ошибка передаётся полем `error`.
- Main Backend валидирует связи id, права исходного service, лимит трёх гипотез, ссылки и маскирование.
- **Атомарность:** результат, hypotheses, evidence, timeline, terminal status в одной транзакции; duplicate callback не создаёт дублей.
- Backend переводит incident в `awaiting_review` при completed/inconclusive, но **не в resolved**.
- Для восстановления после сбоя Main Backend может запросить `GET /internal/v1/investigations/{id}` и при необходимости запросить result повторно (метод уточнить).

## 7. Cancel / Retry

- Cancel — запрос, не мгновенная гарантия остановки. Кооперативно останавливаем LangGraph перед новым tool call, сохраняем checkpoint и шлём `investigation.canceled` + финальный result. Не обрывать running LLM stream без обработки последствий.
- Retry создаётся **Main Backend**, получает новый `investigation_id`, `attempt+1`, `parent_investigation_id`; вызывает обычный Start. AI не переиспользует старый идентификатор/результат.
- При одновременных командах cancel/complete побеждает первая зафиксированная терминальная запись по правилам optimistic locking. Terminal → terminal запрещён.

## 8. Idempotency и отказы

| Ситуация | Что должен сделать сервис |
|---|---|
| Timeout вызова Start | Main Backend повторяет с тем же ID + Idempotency-Key; AI возвращает существующий status |
| AI занят | согласованный `429` с Retry-After, Main Backend не теряет run |
| Callback повторился | ACK deduplicated, без двойных Evidence/Timeline |
| Callback out-of-order | хранить/буферизовать, воспроизвести sorted by sequence; не перепутать состояния |
| Frontend disconnected | run продолжается, replay с REST |
| AI рестарт | прочесть durable state/checkpoints, возобновить безопасно либо отметить failed |
| MCP недоступен | partial Evidence + `inconclusive` либо controlled failed; не фальсифицировать результат |
| Отмена, пока API недоступен | Main Backend принимает command only с устойчивым состоянием и ретраями, UI видит cancel_requested |

## 9. Если выберете gRPC

Оставляем **ровно эти операции и бизнес-модели**, переносим service calls в `.proto`: `Start`, `GetStatus`, `Cancel`, `PublishEvent`, `SubmitResult`, `GetIncidentContext`. JWT/service identity — в metadata, deadline/trace IDs — в headers/metadata. **Не делаем одновременно независимые REST и gRPC реализации по умолчанию**; выбираем единый source of truth, генерируем клиентов, делаем contract tests. MCP Streamable HTTP от этого выбора не меняется.

## 10. Страховочный readback итогов

Предложен также `GET /internal/v1/investigations/{investigation_id}/result` → `200 AIResultCallback` для terminal run, `409` до завершения. Это позволит Main Backend запросить итог при потере HTTP callback; **на утверждении**, но схема уже есть в REST-кандидате.

## 11. Дополнительные поля StartAIRequest

`attempt` (>=1) и `parent_investigation_id` (nullable UUID) позволяют AI однозначно различать исходный run и Retry. `Idempotency-Key` передаётся в headers/metadata; вторая попытка не переиспользует старый ID. **Терминальное событие `investigation.completed` клиенту WebSocket транслировать только после того, как результат RCA надёжно сохранён Main Backend**, даже если callbacks пришли в обратном порядке.
