# 04. Frontend REST / WebSocket: карта «экран → данные»

**Единственный внешний API:** `https://<main-backend>/api/v1/*`. Браузер не обращается напрямую к AI Backend, MCP Server, Elasticsearch, Docker и Prometheus.

**Новый обязательный auth flow:** до открытия приложений пользователь проходит `Login (email+password) → Verify Email OTP (6 цифр) → /users/me`. Это два дополнительных auth screen, **не отрисованных на девяти Figma B экранах**. См. `12_AUTH_EMAIL_OTP.md`. Не выдавать JWT на `/auth/login`.

## 1. Все девять экранов Figma B

| Экран | REST запросы | Реактивность / действия | Приоритет |
|---|---|---|---|
| **Overview** | `GET /overview`, `GET /incidents`, `GET /services/{id}/health` | новые incidents и статусы по WS; переход к деталям | P0, health P1 |
| **Incidents** | `GET /incidents` с `project_id/environment_id/service_id/severity/status/search/from/to/sort/cursor` | pagination, переход на detail | P0 |
| **Live investigations** | `GET /investigations`, `GET /investigations/{id}`, `GET /investigations/{id}/events` | realtime, Cancel, Retry с RBAC | P0 |
| **Service map** | `GET /projects/{id}/topology`, `GET /services/{id}/health` | read-only graph; no fabricated links | P1 |
| **Logs & metrics** | `POST /telemetry/logs/search`, `POST /telemetry/metrics/query` | bounded search, time selector, deep links | P1 |
| **Traces** | `GET /telemetry/traces`, `GET /telemetry/traces/{id}` | waterfall; deep-link Tempo | P1 |
| **Integrations** | `GET/POST /integrations`, `GET/PATCH/DELETE /integrations/{id}`, `POST /integrations/{id}/test` | admin operations; no secret returned | P0 basic / P1 edit |
| **Settings** | `GET /settings`, `GET /users/me`, `GET /users` | read-only AI budget in MVP; admin users roles | P1 |
| **Incident Detail** | `GET /incidents/{id}`, `/timeline`, `/investigations`, `/reviews`, plus run's events/hypotheses/evidence/report | real-time activity, cancel, retry, human review | P0 |

### Incident Detail — 6 вкладок

| Вкладка | Основная загрузка | Правила |
|---|---|---|
| `Overview` | incident + latest run + latest RCA summary | root cause nullable, no fake success |
| `Live investigation` | investigation + `/events?after_sequence=…` | tool started/completed/failed, budget, elapsed time |
| `Hypotheses` | `/investigations/{id}/hypotheses` | максимум 3, `pending/supported/rejected` |
| `Evidence` | `/investigations/{id}/evidence` + `/evidence/{id}` | excerpt + source URL; redact secrets |
| `Timeline` | `/incidents/{id}/timeline` | times from sources, causality tagging |
| `RCA report` | `/investigations/{id}/report` + `POST /incidents/{id}/reviews` | review explicitly tied to run, no auto resolve |

## 2. Обычные запросы

**GET** list: `GET /api/v1/incidents?project_id=…&status=open&limit=25&sort=-detected_at&cursor=…`.

**Response:**

```json
{
  "items": [{ "id": "11111111-1111-4111-8111-111111111111", "title": "Payment failures", "status": "open", "severity": "critical" }],
  "next_cursor": null
}
```

Запись в примере урезана для читаемости; реальные обязательные поля и типы — OpenAPI. Следующая страница только по `next_cursor` (не считать порядковый номер страницы курсором).

**Start:** `POST /api/v1/incidents/{incident_id}/investigations` с `Idempotency-Key`; `202` возвращает `Investigation`, Header `Location: /api/v1/investigations/{id}`.

**Cancel:** `POST /api/v1/investigations/{id}/cancel` → `202`, статус cancel_requested; не показывать canceled до фактического завершения.

**Retry:** `POST /api/v1/investigations/{id}/retry` → `202`, новая investigation ID; прошлые события остаются.

**Review:** `POST /api/v1/incidents/{id}/reviews` с `investigation_id`, `decision`, `comment`, опционально `corrected_root_cause` → `201`.

**Evidence:** excerpt только безопасный фрагмент; исходные ссылки можно открывать по разрешённым URL, не брать непосредственно из неподтверждённого HTML.

## 3. WebSocket (контракт для frontend)

**Адрес:** `wss://<main-backend>/ws/v1/events`. Auth: защищённая session cookie либо краткоживущий WebSocket ticket (выбор в `10_OPEN_DECISIONS.md`). Никогда не передавать долгоживущий JWT в query string или неограниченным токеном в URL.

Client → Server подписка:

```json
{"action":"subscribe","subscription_id":"sub-1","investigation_id":"22222222-2222-4222-8222-222222222222","after_sequence":12}
```

Server → Client подтверждение:

```json
{"type":"subscription.ack","subscription_id":"sub-1","investigation_id":"22222222-2222-4222-8222-222222222222","last_sequence":12}
```

Server → Client событие агента (**тот же payload, что persisted Event**):

```json
{
  "schema_version":"1.0",
  "event_id":"33333333-3333-4333-8333-333333333333",
  "investigation_id":"22222222-2222-4222-8222-222222222222",
  "incident_id":"11111111-1111-4111-8111-111111111111",
  "sequence":13,
  "type":"tool.completed",
  "occurred_at":"2026-10-19T14:39:10Z",
  "data":{
    "tool_call_id":"44444444-4444-4444-8444-444444444444",
    "tool_name":"search_logs",
    "output_summary":"Found 124 DB pool timeouts",
    "duration_ms":310
  }
}
```

### Правила WebSocket

1. Первый connect: загрузить run и `/events`; открыть WS; подписаться **с последним успешно применённым sequence**.
2. При reconnect: запросить REST `/events?after_sequence=<last_applied>` и затем возобновить subscription. Допускать дубли: reducer dedup по `(investigation_id, sequence)` и `event_id`.
3. События приходят с последовательной нумерацией **внутри одного run**, без гарантии порядка между разными расследованиями.
4. Backend должен предотвращать чтение чужих project/run при subscribe, а также перепроверять access после изменения прав.
5. При дырке в sequence клиент не теряет события, а запускает backfill.
6. Ошибка WS не считается ошибкой расследования; UI показывает connection status.
7. События `tool.*` показывают **операционный summary**, не скрытые рассуждения LLM.

## 4. Состояния и UI guard

`loading`, `empty`, `forbidden`, `not_found`, `source_unavailable`, `rate_limited`, `partial`, `run_failed`, `run_inconclusive`. Viewer не видит доступных к запуску и Review действий. RBAC подтверждается **сервером**, frontend guard — только UX.

## 5. Прямые ссылки на источники

В моделях `Evidence.source.url`, `TraceSummary.source_url`, `Deployment.source_url`: полный URL с верифицированным host allowlist, HTTPS там где доступно; никакого HTML или JS. Внешние источники требуют отдельного user-login, UI не добавляет сервисные секреты в ссылки.

## 6. Схемы WebSocket (дополнение)

`schemas/websocket.schema.json` различает `SubscribeInvestigation`, `SubscribeProject`, `Unsubscribe`, `SubscriptionAck`, `SubscriptionError`, `IncidentCreated`, `IncidentUpdated`, `Heartbeat` и тот же `InvestigationEvent`. Для live Dashboard проектная подписка обязательна; для полного event replay используются нумерованные InvestigationEvent в REST и WS. `Project` events имеют `event_id` для dedup, но не общий sequence, поэтому после переподключения Dashboard повторно запрашивает `/overview` и `/incidents`.
