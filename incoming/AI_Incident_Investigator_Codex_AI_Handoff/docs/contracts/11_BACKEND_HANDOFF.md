# 11. Юрию: Backend handoff — что реализовать и в каком порядке

> Это точка входа для владельца Main Backend. Полное описание API — `02_ENDPOINT_MAP.md`, OpenAPI — `openapi/main-backend.openapi.yaml`, объектная модель — `03_DOMAIN_MODELS.md`. **Внутреннее дробление Backend на микросервисы выбираешь сам.**

## 1. Основной P0 для сквозного MVP

| Шаг | Ресурсы/контракты | Готовность |
|---|---|---|
| 1 | **Email/password + mandatory email OTP** (`/auth/login` → 202 challenge; `/auth/otp/verify` → 200 JWT; `/auth/otp/resend` → 202), `/auth/refresh`, `/logout`, `/users/me`, RBAC, `Problem` errors | JWT не получить до OTP; пользователь не видит чужих проектов |
| 2 | `/projects`, `/environments`, `/services`, integrations basic | можно привязать сервисы и источники |
| 3 | `/ingest/alertmanager`, `/ingest/alerts`, `/ingest/deployments` | реальный alert создаёт/dedup Incident |
| 4 | `/incidents`, `/incidents/{id}`, `/overview` | Incidents / Dashboard работают по реальным данным |
| 5 | `POST /incidents/{id}/investigations` + прямой вызов AI | `202` + устойчивый pending/running, без RabbitMQ |
| 6 | `/internal/v1/ai/events`, `/internal/v1/ai/results` | AI callbacks валидируются, дедуплицируются, сохраняются |
| 7 | `/investigations/{id}/events`, WebSocket /ws/v1/events | UI получает tool/hypothesis/evidence updates и replay |
| 8 | `/investigations/{id}/hypotheses`, `/evidence`, `/report`, incident `/timeline` | полный Evidence-backed RCA |
| 9 | `/investigations/{id}/cancel`, `/retry`, `/incidents/{id}/reviews`, status | отмена, повтор и человеческая проверка работают корректно |

## 2. P1 после сквозного сценария

Service Map topology, full Logs & Metrics explorer, full Tempo waterfall, admin user management, advanced integration update, settings UI. В Figma они отрисованы, но это **не причина блокировать RCA MVP**. Базовые API для источников/ссылок и настройка интеграций нужны и в P0.

## 3. Права и ошибки

RBAC: Admin управляет, Developer расследует/ревьюит, Viewer только читает. Выделить service authorization для AI и ingestion auth для webhook. Не путать пользователю разрешённый project scope с UUID из клиента. 401/403/404/409/422/429/5xx, единый RFC7807 `Problem`.

## 4. Backend ↔ AI, Transport TBD

Пока команда не выбрала REST/gRPC, реализовать узкий adapter `AIInvestigationClient` с операциями `start`, `get_status`, `get_result`, `cancel`, не привязывая доменную логику к HTTP-клиенту. Моки реализуются по `StartAIRequest`, `StartAIAck`, `InvestigationEvent`, `AIResultCallback`. В REST-кандидате callback endpoints — Main Backend; в gRPC-кандидате их замещают RPC.

**Без RabbitMQ.** Нужны согласованный admission control (один активный run в AI executor), idempotency, timeout, durable result reconciliation. Отдельно решить, чей MCP Server. Никогда не смешивать MCP tools с вызовом Start investigation.

## 5. DoD и блокирующие проверки

- `GET /api/v1/incidents` возвращает строгий `IncidentsPage`; ресурсы не протекают между проектами.
- `POST /.../investigations` возвращает новый `Investigation.id`, не ждёт RCA и сохраняет relation к Incident.
- Одно событие с тем же `event_id` и `(investigation_id,sequence)` сохраняется только один раз.
- WebSocket replay и REST `/events` гарантируют отсутствие потери событий при reconnect.
- RCA `completed/inconclusive` не означает `incident.resolved`.
- Повторное выполнение `retry` создаёт новый investigation ID и сохраняет прошлый audit.
- При отключённом Elasticsearch/Tempo информация остаётся честной, root cause не выдумывается.
- Все контрактные JSON/примерные payload проходят CI validation.

## 6. Что передать Олегу перед независимой AI-разработкой

1. URL/протокол internal AI client + service identity strategy.
2. Утверждённые `StartAIRequest`, Event Envelope, RCA result schema.
3. Решение кто предоставляет MCP Server и кто создаёт source deep-links.
4. Способ получения initial IncidentContext и integration auth scopes.
5. Процедура отмены, конечный статус и reconciliation при сбое callback.

### Открытые обсуждения

Все вопросы, которые нельзя замолчать: `10_OPEN_DECISIONS.md`. Не считать проектные дефолты обязательными до ADR.

## С чего начать Backend сейчас (обновление 20.10.2026)

**Прочитать в первую очередь `12_AUTH_EMAIL_OTP.md` и `13_BACKEND_READINESS_AUDIT.md`.** Схемы `LoginChallenge`, `OtpVerifyRequest`, `OtpResendRequest`, `OtpResendResponse` и OpenAPI уже обновлены. Потребуется согласовать пароль/приглашения для Admin-created users, provider исходящих писем и JSON vs HttpOnly cookie для refresh — текущий JSON RefreshToken контракт не надо копировать в браузер до этого решения.
