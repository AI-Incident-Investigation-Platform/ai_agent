# 07. External API: Alertmanager, generic alerts и deployment events

## 1. Что умеет Main Backend

| Метод | URL | Кто вызывает | Назначение |
|---|---|---|---|
| `POST` | `/api/v1/ingest/alerts` | внешний мониторинг / webhook bridge | нормализованный alert |
| `POST` | `/api/v1/ingest/alertmanager` | Alertmanager | native webhook, adapter → `AlertIngest` |
| `POST` | `/api/v1/ingest/deployments` | любой CD/provider | запись факта deployment, без чтения CI pipeline |

Не отправлять браузерный JWT для этих запросов: у каждого источника свои credentials, `X-Ingest-Key` в примере OpenAPI — один из возможных способов (лучше подпись HMAC/mTLS для deployment environment). Секреты лежат в env/secret store; per source/project permissions.

## 2. Generic Alert payload

```json
{
  "source": "prometheus-alertmanager",
  "source_event_id": "alert-prod-payment-high5xx-2026-10-19T14:35Z",
  "project_id": "55555555-5555-4555-8555-555555555555",
  "environment_id": "66666666-6666-4666-8666-666666666666",
  "service_ids": ["77777777-7777-4777-8777-777777777777"],
  "severity": "critical",
  "title": "Payment error rate > 10%",
  "description": "HTTP 5xx above threshold",
  "started_at": "2026-10-19T14:35:00Z",
  "labels": {"alertname":"High5xxRate", "service":"payment-service"}
}
```

Response `202`: `{"accepted":true,"deduplicated":false,"resource_id":"11111111-1111-4111-8111-111111111111"}`. Повтор source_event_id с тем же scope не создаёт второй Incident. Одновременные `firing/resolved` в Alertmanager требуют правил grouping/window correlation (решить с Юрием).

## 3. Native Alertmanager webhook (пример входа)

```json
{
  "receiver":"investigator",
  "status":"firing",
  "groupKey":"{service=payment-service}",
  "alerts":[{"status":"firing","labels":{"alertname":"High5xxRate","service":"payment-service","severity":"critical"},"annotations":{"summary":"Error rate is high"},"startsAt":"2026-10-19T14:35:00Z","endsAt":"0001-01-01T00:00:00Z","fingerprint":"a1b2c3"}]
}
```

Adapter сопоставляет `service` с настроенными `Service.external_names` в нужном Project/Environment. При неоднозначности создаёт alert в карантине/возвращает controlled error, **не угадывает** проект по одному имени. Оригинальный Alertmanager payload не отправляется целиком в LLM.

## 4. Deployment ingestion

```json
{
  "source_event_id": "deploy-20261019-294",
  "project_id": "55555555-5555-4555-8555-555555555555",
  "environment_id": "66666666-6666-4666-8666-666666666666",
  "service_id": "77777777-7777-4777-8777-777777777777",
  "version": "2.4.1",
  "commit_sha": "23f5ab341bb1",
  "deployed_at": "2026-10-19T14:15:00Z",
  "status": "succeeded",
  "source": "external-cd",
  "source_url": "https://github.com/example/ecommerce/actions/runs/100"
}
```

Registry хранит только событие deployment и ссылку. **GitHub Actions API / logs/CI runs не является обязательной диагностической интеграцией.** Deployment может приходить из Jenkins, GitHub, GitLab, Argo, ручного API.

## 5. Webhook безопасность

Валидировать HMAC/signed token/service identity, limit body size, rate limit, timestamp skew/replay, source-event dedup, input fields/labels allowlist, mapping to project env, explicit 401/403/422/409/429. Повторные одинаковые payload должны безопасно возвращать ACK. Непонятный сервис ≠ создавать случайный project. Сохранять raw webhook только ограниченно с redaction/audit для отладки.

## 6. Машинная схема нативного Alertmanager

`schemas/alertmanager-webhook.schema.json` типизирует `receiver/status/groupKey/alerts[]`, и OpenAPI описывает requestBody native webhook, который может включать **несколько алертов**. Ответ `AlertmanagerAck` содержит `accepted_count`, `deduplicated_count`, `incident_ids[]` — **а не один resource_id**, поскольку native webhook принимает batch.
