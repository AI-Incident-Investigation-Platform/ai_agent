# 13. Готовность API-пакета к передаче Backend — честный аудит v0.2

## Итог

**Передавать Юрию для старта разработки: ДА. Считать весь проект production-ready / frozen-contract v1: НЕТ.**

Это один сквозной *контрактный baseline*, который покрывает 9 страниц Figma B, core Incident/Investigation/Events/Hypotheses/Evidence/RCA, source ingestion, service-to-service AI, MCP diagnostics и **обязательный email OTP**. Для параллельной работы над основными модулями его достаточно. Для полностью независимой реализации без вопросов осталось несколько архитектурных развилок и схемных пробелов.

## Покрыто документами и схемами

| Подсистема | Статус | Что передаём |
|---|---|---|
| Login + OTP + RBAC | **Прописано v0.2**, UI ещё не нарисован | `12_AUTH_EMAIL_OTP.md`, OpenAPI и `schemas/email-otp.schema.json` |
| Projects / Environments / Services / Deployments | Маршруты, модели и базовые проверки готовы к реализации | 02, 03 и Main OpenAPI |
| Incidents / lifecycle | Маршруты и DTO готовы к ревью | 02, 03, Main OpenAPI |
| Investigations / retry / cancel | Взаимодействия предложены, transport open | 04, 05, REST- и gRPC-кандидаты |
| Agent progress → WebSocket → Frontend | Event schemas, replay и idempotency описаны | 04, 05, schemas/ai-events и websocket |
| Hypotheses / Evidence / RCA / Human Review | Основные DTO описаны | 03, 04, schemas/domain |
| MCP diagnostics | 16 инструментов (14 MVP, 2 P2), inputSchemas; полная output типизация по отдельным инструментам не завершена | 06, mcp/tool-catalog.json |
| Ingestion alerts + deployments | JSON Schema и OpenAPI | 07, schemas/alertmanager-webhook.schema.json |
| Frontend экраны Figma B | Карта к API, есть P0/P1 | 04 |
| Security / monitoring / integration | Основные политики зафиксированы | 08, 09 |

## Блокирующие для согласования интерфейсов между участниками

| Priority | Что остаётся | Какое решение нужно |
|---|---|---|
| BLOCKER | **REST или gRPC для Main Backend ↔ AI** | Зафиксировать один wire transport; пока есть кандидат обоих |
| BLOCKER | **Граница MCP Server / AI MCP Client и владельцы инструментов** | Распределить реализацию и service identity |
| BLOCKER | **Подлинный session transport для браузера** | Refresh через HttpOnly cookie (рекомендуется) или JSON + хранение, CSRF, WS auth; после решения синхронно обновить OpenAPI |
| BLOCKER | **Пользовательское приглашение / установка и восстановление пароля** | Registration/signup отключён? Admin invite, email verification, password reset и user activation не специфицированы |
| BLOCKER | **Email provider / delivery и окружения** | SMTP либо API-провайдер, секреты, local Mailpit/mock, разрешённые адреса, поведение при сбое |
| HIGH | **Admission control без очереди** | Один активный run и reject 429 или собственное durable pending-состояние; persistent retries после рестарта |
| HIGH | **Полный MCP outputSchema, разные типы ошибок инструментов** | Типизировать результат каждого tool (inputSchemas уже есть), контрактные тесты |
| HIGH | **Источник истины и версионирование DTO** | Разместить canonical specs и generator client/server; policy change review |
| HIGH | **Операционная схема деплоя и observability hard limits** | Конкретные URL, auth service identity, budgets, mTLS/TLS и алерты |
| MEDIUM | **Incidents human display ID / service health topology** | Утвердить формат `INC-123` и P1 для дополнительной визуализации |
| MEDIUM | **Limits email OTP** | Подтвердить 6 digits, 5m TTL, 5 tries, resend 60s/3, absolute 15m либо изменить ADR |

## Что у Юрия есть для начала прямо сейчас

**Можно реализовать параллельно:**

- SQLAlchemy/Alembic модели core сущностей и юнит-тесты бизнес-правил.
- `/auth/login` → challenge, `/auth/otp/verify` → tokens, `/auth/otp/resend` и RBAC через временный mock mailer (после согласования D-06).
- Project/Environment/Service CRUD, Incident CRUD и Dashboard summary.
- Alertmanager webhook + dedup и deployments ingestion.
- Investigation events/result persist, uniqueness by `event_id`/sequence, REST `/events`, WebSocket relay, read-only evidence/rca endpoints.
- Mock AI adapter на согласованных DTO, ещё без выбора gRPC/REST реализации.
- Контрактные тесты API, OTP и проектных ACL.

**Не надо блокировать разработку** полной типизацией всех MCP outputSchemas или красивыми P1 Telemetry Explorer и trace graph; это можно довести после первых сквозных RCA.

## Отдельно про «всё ли написано?»

`v0.2` — полноценная **карта и рабочие черновики API-контрактов** всего продукта, но **не** исчерпывающий архитектурный дизайн и не завершённая спецификация миграций БД/SMTP/деплоймента/внутренней микросервисной топологии. Эти части не стоит выдавать за согласованные, потому что некоторые решения команда ещё не приняла. В `10_OPEN_DECISIONS.md` указаны точные блокеры.
