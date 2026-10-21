# AI Incident Investigator — единая карта API и контрактов

**Версия:** `0.2.0-draft` · **Дата:** 20 октября 2026 · **Владельцы согласования:** Юрий (Main Backend), Олег (AI Backend), Расул (Frontend), Даниил (Infra).

> Это **рабочий проект точных интерфейсов**, подготовленный на основе согласованной архитектуры и Figma B. Он намеренно конкретный для разработки и тестов, но **не выдаёт новые решения за принятые командой**. Перед фиксацией версии `1.0` Олег и Юрий должны закрыть вопросы из `10_OPEN_DECISIONS.md`.

**Новая договорённость v0.2:** обязательный шестизначный email OTP при каждом новом входе по email+паролю. `POST /auth/login` теперь возвращает только OTP challenge с HTTP 202; access/refresh tokens выдаёт исключительно `POST /auth/otp/verify`. См. `12_AUTH_EMAIL_OTP.md`.

## Что реализуем

Продукт принимает алерт, регистрирует Incident, **асинхронно** вызывает отдельный AI Backend без RabbitMQ, а тот запускает LangGraph Single-Agent ReAct, читает технические источники через MCP-инструменты, передаёт события и RCA в Main Backend. Main Backend сохраняет данные, транслирует WebSocket-события во Frontend и даёт человеку подтвердить, исправить или отвергнуть результат AI. Автоматического лечения production нет.

## Пакет документов

| Файл | Кому | Назначение |
|---|---|---|
| `12_AUTH_EMAIL_OTP.md` | Юрий, Расул, Даниил | полный двухэтапный email OTP, security, ограничения и тесты |
| `13_BACKEND_READINESS_AUDIT.md` | Юрий, Олег | что готово / что ещё блокирует frozen v1 |
| `01_ARCHITECTURE.md` | все | границы сервисов, последовательности, ответственность |
| `02_ENDPOINT_MAP.md` | Юрий, Расул, Олег | **полная карта операций** Backend/AI и каталог MCP |
| `03_DOMAIN_MODELS.md` | все | типы, ID, статусы, связи, RCA, гипотезы, Evidence |
| `04_FRONTEND_API_AND_WS.md` | Расул, Юрий | экран → API, REST, WebSocket, reconnect |
| `05_INTERNAL_BACKEND_AI.md` | Олег, Юрий | прямые асинхронные команды, callbacks, cancel/retry, отказоустойчивость |
| `06_MCP_CONTRACTS.md` | Олег, Юрий, Даниил | MCP Streamable HTTP, названия инструментов, security, ошибки |
| `07_INGESTION.md` | Юрий, Даниил | webhook Alertmanager, generic alerts, deployments, dedup |
| `08_SECURITY_AND_ERRORS.md` | Юрий, Расул, Олег | RBAC, HTTP ошибки, токены, лимиты, секреты |
| `09_IMPLEMENTATION_PLAN.md` | все | контрактные тесты, моки, приёмка, параллельная работа |
| `10_OPEN_DECISIONS.md` | Олег, Юрий | что надо формально утвердить |
| `openapi/main-backend.openapi.yaml` | Юрий, Расул | OpenAPI 3.1 Main Backend REST + входящие API + callbacks |
| `openapi/ai-backend-rest-candidate.openapi.yaml` | Юрий, Олег | **кандидат** на REST-интерфейс Backend↔AI; gRPC остаётся возможным |
| `schemas/*.schema.json` (включая `email-otp.schema.json`) | все | валидируемые JSON Schema 2020-12 |
| `mcp/tool-catalog.json` | Юрий, Олег | 16 формальных имен и inputSchemas (14 MVP, 2 P2) |
| `examples/` | все | тестовые сценарии, сообщения и curl |

## Самое важное отличие от предыдущих документов

**RabbitMQ в схеме связи Main Backend ↔ AI не существует.** Старые спецификации четырёх репозиториев были составлены ДО изменения решения; во всех случаях, когда там написано «публикует в RabbitMQ», актуальным считать `05_INTERNAL_BACKEND_AI.md`.

**Не путать:** транспорт REST/gRPC между Python-сервисами и MCP Streamable HTTP для агентных инструментов — разные слои. **Размещение MCP Server окончательно не согласовано**, но семантика инструментов здесь описана независимо от владельца сервера.

## Использование

1. Сначала прочитать `01`, `03`, `05`, `10` вместе.
2. Подключить файл `openapi/main-backend.openapi.yaml` в Swagger Editor / Stoplight; генерировать клиентские типы для Frontend.
3. Подключить `openapi/ai-backend-rest-candidate.openapi.yaml` для REST-прототипа или согласовать gRPC-схему, сохраняя DTO и семантику.
4. Использовать JSON Schema для моков, валидации событий и тестов.
5. Заменить тестовые хосты и примерные данные конфигурацией; никогда не зашивать Figma-значения в API.

**Точки версии:** `draft` → `approved-v1` → несовместимые изменения только в `/v2` или со схемной миграцией.

- `11_BACKEND_HANDOFF.md` — сжатый пошаговый план лично для Main Backend.
- `proto/ai-backend-candidate.proto` — **альтернативный gRPC-кандидат**, не принятое решение.
