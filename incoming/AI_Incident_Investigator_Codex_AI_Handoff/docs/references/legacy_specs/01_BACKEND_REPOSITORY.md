# incident-investigator-backend — техническое задание

**Ответственный:** Юрий Бурцев (основной Backend Engineer).  
**Поддержка:** Даниил Митин — отдельные несложные Backend-задачи по согласованию.  
**Статус:** требования и интерфейсные ожидания; **не** навязываем внутреннее деление микросервисов.  
**Смежные репозитории:** `incident-investigator-ai`, `incident-investigator-frontend`, `incident-investigator-infra`.  
**Общий контекст:** `00_PROJECT_OVERVIEW.md`.

## 1. Задача Backend в продукте

Предоставить устойчивую прикладную платформу для регистрации инцидентов, хранения и выдачи данных, управления пользователями и интеграциями, асинхронного запуска AI-расследований, обработки их результатов и realtime-отображения. **Backend не выполняет ReAct/LLM-рассуждения:** за это отвечает AI-репозиторий.

**Принцип ответственности:** Backend управляет инцидентами и доступом к данным; AI-компонент владеет логикой расследования. Backend предоставляет диагностические возможности AI через **MCP Server**.

## 2. Технологии

- Python, **FastAPI**, Uvicorn.
- **Pydantic v2**, `pydantic-settings`.
- **SQLAlchemy 2**, `asyncpg`, **Alembic** с PostgreSQL.
- **Dishka** (DI).
- **RabbitMQ** для асинхронных заданий расследования и выбранных событий.
- **DragonflyDB** для кэша.
- `prometheus-client`, OpenTelemetry instrumentation для собственного мониторинга.
- **MCP Python SDK / FastMCP** или эквивалентная реализация MCP Server через **Streamable HTTP**.
- Контейнеризация Docker; сборка и тесты в GitHub Actions.

Показанные ранее минимальные версии пакетов являются ориентиром; Юрий фиксирует совместимый lockfile. Никаких обязательных дополнительных технологий не вводим до обоснования.

## 3. Что Backend обязан реализовать в MVP

### 3.1. Projects / Environments / Services

- CRUD и получение каталога доступных пользователю проектов.
- В каждом проекте несколько окружений (`production`, `staging`, `development`, другие конфигурируемые).
- Управление сервисами и их идентификаторами в источниках телеметрии (`service.name`, label `service` и т. п.); ручной ввод достаточен.
- Соответствие Service ↔ Project ↔ Environment, перечень подключённых репозиториев и observability-интеграций.
- Сведения о deployments/version/commit SHA в разрезе сервисов и окружений.
- Не навязывать сложную `Organization → Tenant` модель и автоматическое service discovery: эти функции не утверждены для MVP.

### 3.2. Incident Management

- Создание инцидента из внешнего webhook/alert и вручную.
- Нормализация источника, названия, описания, severity, времени начала, окружения, affected services, ссылок на исходный alert.
- Severity: `Critical`, `High`, `Medium`, `Low` (сопоставление внешнего регистра в адаптерах).
- Статусы инцидента: `Open`, `Investigating`, `Awaiting Review`, `Resolved`.
- Поиск/фильтрация/сортировка/пагинация по Project, Service, Severity, Status, интервалу времени, ID/названию.
- Базовая корреляция/дедупликация повторяющихся alerts, чтобы пачка оповещений не порождала каскад повторных расследований.
- Возможность одного инцидента затрагивать несколько сервисов. Отдельно сохранять исходно проблемный сервис и сервисы, выявленные в расследовании.
- Ссылки и идентификаторы реальных источников. Не создавать фиктивную телеметрию.

### 3.3. Investigation Orchestration

- API для **Start / Get Status / Cancel / Retry**. Запуск расследования асинхронный: HTTP быстро возвращает идентификаторы и текущий статус.
- Для каждого запуска — собственный уникальный `investigation_id`. Один Incident может иметь несколько последовательных запусков (например, Retry), старые результаты остаются.
- Публикация задания в RabbitMQ с минимальным набором IDs и версией схемы; авторитетный контекст доступен AI через Backend.
- Раздельное хранение статуса Incident и статуса AI Run: **расследование завершено ≠ проблема устранена**.
- Уметь сохранять промежуточные события AI, Evidence, Hypotheses и финальный RCA.
- Состояния AI-исполнения предусматривают `queued/running/completed/inconclusive/failed/timed_out/cancelled`; точные машинные enum/переходы определим в Contract-First спецификации.
- Обработка повторной доставки RabbitMQ, идемпотентность сообщений, подтверждения (ack), стратегия retries, dead-letter при устойчивой ошибке.
- Cancel должен останавливать дальнейшую работу AI Worker **кооперативно** (механизм сигнала предстоит согласовать). Retry — отдельный запуск; не переиспользовать старый ID.
- Избежать дублирующего сохранения событий при повторной доставке и после рестартов.

### 3.4. Incident Evidence / Hypotheses / RCA / Review

- Принимать структурированные результаты от AI и валидировать Pydantic-схемами.
- Хранить до трёх гипотез со статусом `pending/supported/rejected`, qualitative confidence `High/Medium/Low`, explanation, references на Evidence.
- Evidence: тип источника, excerpt/summary, временная метка/диапазон, сервис, адрес источника и стабильные IDs (`trace_id`, commit SHA, document/log ID и др.).
- RCA Report: incident summary, severity, symptoms, affected services, root cause или explicit unknown, causal chain, timeline, hypotheses, evidence refs, recommended fix, prevention, confidence, completed/partial status.
- **Human review** после расследования: пользователь подтверждает/отклоняет/корректирует Root Cause; сохранить автора/время/результат, не подменять исходный вывод AI.
- Не копировать все сырые логи/метрики/трассы в PostgreSQL; сохранять существенные выдержки и ссылки на первоисточники.
- Поддержать изоляцию данных между разрешёнными проектами.

### 3.5. REST API для Frontend

**Функциональные ресурсы** (реальные пути и JSON — в отдельном OpenAPI-контракте):

| Ресурс | Операции |
|---|---|
| Auth | Login/token и получение профиля/прав |
| Projects / Environments / Services | List, details, create/update, настройки |
| Integrations | List, create/update/delete, test connection, статус |
| Incidents | List/filter/page, detail, manual create, review/status |
| Investigations | Start, status, events history, cancel, retry |
| Evidence / Hypotheses | List/get по incident/investigation |
| RCA | Get structured report, версия/review |
| Deployments | Приём event, list последних релизов по service/env |

**Важно:** это перечень capabilities, не утверждённые маршруты. Все методы возвращают машиночитаемые ошибки и учитывают RBAC/Project Access. Проставлять корреляционные ID в логах и ответах.

### 3.6. Realtime через WebSocket

- WebSocket только между **Backend ↔ Frontend**; AI не соединяется с браузером напрямую.
- Транслировать run status, tool start/complete/failure, краткую цель действия, гипотезы, Evidence, RCA ready и Cancel/Retry.
- Привязка потоков к `incident_id` и `investigation_id`, проверка JWT/прав на каждый доступ.
- Порядковые номера событий, сохранение истории, восстановление пропущенных после разрыва соединения; UI не должен полагаться на безусловную доставку WebSocket.
- Лимит на размер payload, нормализация/маскирование сырых tool outputs.
- **Точный путь доставки AI-событий в Backend** (RabbitMQ event topic, REST ingestion и т. п.) оставить предметом согласования API-контрактов: пока нет решения, не придумывать его.

## 4. MCP Server: основная граница Backend ↔ AI

**Цель:** предоставить AI Agent через Streamable HTTP стандартизованные read-only диагностические инструменты и защищённые адаптеры к источникам.

### 4.1. MVP-каталог инструментов

| Tool (рабочее название) | Backend интеграция | Назначение |
|---|---|---|
| `search_logs`, `get_error_logs` | Elasticsearch | Фильтрация логов, ошибки, time window, request/trace IDs |
| `query_prometheus`, готовые metric helpers | Prometheus | Guarded PromQL для ошибок, latency, БД, контейнеров |
| `get_trace`, trace search/helper | Tempo | Span tree, errors, duration, межсервисные зависимости |
| `search_code`, `read_file` | GitHub | Read-only поиск и чтение исходников |
| `git_log`, `git_diff`, `git_blame`, `get_commit` | GitHub | Контекст commit/deployment, история/сравнения |
| `get_container_status`, `get_container_events` | Docker diagnostic adapter | Restarts, OOMKilled, health, lifecycle |
| `get_recent_deployments` | Backend deployment history | Rollout time, version и commit по service/environment |
| `check_external_api`, `check_external_service_health` | Safe outbound HTTP | Проверка allowlisted зависимости |

Названия — **проектные предложения**, не согласованная schema. Для каждого инструмента нужны: description, входные типы/ограничения, JSON Schema, результат/ссылки на source, ошибки, timeout и тесты.

### 4.2. Правила выполнения

- Все инструменты **read-only**, без shell, прямого SQL, изменения GitHub, Docker или конфигураций.
- **Credentials** никогда не попадают в tool output, prompts или frontend.
- Auth AI Worker → MCP Server, project/environment scope и authorization для каждого вызова. `project_id`, присланный клиентом, **не считается доказательством доступа**.
- Elasticsearch DSL и PromQL: ограничивать опасные запросы, объём результата, timeout, cardinality; исторические интервалы по данным retention, а не один глобальный «последний час».
- GitHub: доступ только к авторизованным репозиториям/refs; ограничивать пути, размеры файлов и API квоты.
- Docker: не подключать LLM/Worker напрямую к всесильному Docker Socket; ограниченный прокси/адаптер, права исключительно диагностики.
- External API: allowlist адресов/доменов, GET/HEAD, блокировка private/metadata SSRF и redirect bypass, timeout/rate limits.
- Логи/README/исходный код — недоверенные данные. Проводить redaction и отделять источник данных от инструкций агента.
- MCP tool errors — структурированные, различать auth, permission, invalid args, timeout, rate-limit, unavailable, partial result.
- Tool Call audit: кто/какой run/какой tool/когда/результат и latency, без сохранения секретов.

### 4.3. Параллельная разработка

Юрий предоставляет **mock MCP Server** или фикстуры ответов по согласованным схемам. Олег строит MCP Client/LangGraph против этих контрактов. Контрактные тесты должны одинаково проходить на mock и реальном Server. **Не реализовывать tool payload в одиночку без согласования с AI.**

## 5. Integration Management / Deployment Events

- Экран Backend API для настройки и проверки Elasticsearch, Prometheus, Tempo, GitHub и безопасного Docker diagnostic endpoint.
- Изолировать конфигурацию источников по Project/Environment, отделять общедоступные метаданные от секретов; не возвращать токены после сохранения.
- Универсальный API для Deployment Events: service, environment, timestamp, version/commit, status, issuer/source. Не внедрять обязательный анализ GitHub Actions/CI pipeline.
- При необходимости нормализация внешних alert-событий Alertmanager, Grafana Alerting, Sentry. Не считать все входящие webhook доверенными.
- Кэш DragonflyDB для безопасных к повторному вычислению данных, явная стратегия TTL/invalidation. Никаких инцидентов только в кэше.

## 6. Пользователи и безопасность

**Утверждён RBAC**:

- `Admin`: пользователи, проекты, интеграции, настройки.
- `Developer`: разрешённые инциденты, запуск/Cancel/Retry, RCA/evidence, human review.
- `Viewer`: просмотр разрешённых проектов/инцидентов/отчётов, без мутаций.

Требования:

- JWT для HTTP/WebSocket; проверка роли + проектных прав **на Backend**, не только через кнопки Frontend.
- Аутентификация сервисов для AI ↔ Backend/MCP, защита от неавторизованных tool calls.
- Секреты в переменных окружения/защищённом хранилище и при необходимости шифрование at-rest; политика хранения будет уточнена.
- Маскировка секретов в логах, событиях, Evidence и перед передачей локальной LLM.
- Audit действий пользователей и критических фоновых операций.
- Не требовать SaaS, tenants или SSO в MVP; отдельная модель `Organization` не утверждалась.

## 7. Backend observability и устойчивость

- Prometheus endpoint и метрики: HTTP RPS/errors/latency, время создания инцидента, очередь/lag/повторы, WS connections, MCP tool calls errors/latency, database pool.
- Structured JSON logging c `request_id`, `correlation_id`, `incident_id`, `investigation_id`; OpenTelemetry traces для внутренних вызовов.
- Healthcheck/liveness/readiness, orderly shutdown, timeouts внешних зависимостей, retries с ограничениями.
- Поддержка внешнего размещения DB/broker/MCP/AI (в MVP единый Compose network).
- Документация env vars, миграции, bootstrap пользователя, минимальные инструкции локального запуска.

## 8. Чего Backend делать не должен

- Выбирать LLM, строить гипотезы или формировать текст RCA вместо AI.
- Выполнять произвольный код из ответов LLM, запускать SQL в PostgreSQL расследуемого приложения.
- Придумывать новый формат tool результатов без согласования MCP schemas.
- Самостоятельно анализировать GitHub Actions workflows и нести задачи CI/CD самого проекта (они у Infra).
- Жёстко привязываться к тестовому e-commerce и именам его сервисов.
- Создавать обязательный «knowledge-service» для Qdrant до второго этапа.

## 9. Реализация по вехам

1. **Каркас:** зависимости, настройки, Dockerfile, DB migrations, basic health, structured logs, CI.
2. **Вертикальный путь:** минимальные Project/Service и Incident API, webhook/manual incident, RabbitMQ task, хранение investigation lifecycle.
3. **MCP:** mock contracts, MCP Server, работающие `search_logs` + `query_prometheus` с тестовыми источниками и безопасными ограничениями.
4. **Realtime и отчёт:** события AI, WebSocket с replay, evidence/hypotheses/RCA storage, Incident Detail API.
5. **Остальные integrations:** Tempo, GitHub, Docker, deployments и целевые демонстрационные fault scenarios.
6. **Стабилизация:** RBAC, failure/retry/cancel/idempotency, contract/e2e tests, метрики и документация.

Вехи могут идти параллельно; приоритет — **работающий сквозной поток**, а не завершение всех REST endpoints отдельно от агента.

## 10. Критерии приёмки

- [ ] Инцидент появляется после валидного webhook; повторное уведомление не создаёт неконтролируемых дублей.
- [ ] Пользователь с правами может запустить investigation; задача уходит в RabbitMQ; HTTP не ждёт завершения AI.
- [ ] AI с отдельного контейнера может вызвать MCP-инструменты по Streamable HTTP, получая только данные разрешённого проекта.
- [ ] Реальные запросы в Elasticsearch/Prometheus выполняются с ограничениями и создают корректные Evidence source references.
- [ ] События agent run переживают refresh/disconnect WebSocket, отображаются в истории в правильном порядке.
- [ ] Hypotheses, RCA и review сохраняются в PostgreSQL; предыдущие расследования сохраняются после Retry.
- [ ] Cancel достигает Worker, а дубликат команды/сообщения не создаёт некорректного состояния.
- [ ] JWT/RBAC и project access работают для REST, WebSocket и MCP, в том числе при негативных тестах.
- [ ] Нет прямого Docker Socket/SQL/shell и утечек credentials в HTTP/WS/MCP ответах.
- [ ] `docker compose` + GitHub Actions поднимают и тестируют backend в составе общей системы.

## 11. Обязательные будущие API-контракты

Вместе с Олегом и Расулом согласовать **до независимой реализации**: REST OpenAPI; WebSocket event schema/replay; RabbitMQ request/cancel/status и idempotency; форматы AI progress/hypotheses/evidence/RCA; MCP JSON Schemas и унифицированные ошибки; JWT/permissions; env contracts. Версионировать схемы, поддержать mocks/contract tests. **Этот файл — ТЗ, не окончательный OpenAPI или MCP contract.**
