# incident-investigator-infra — техническое задание

**Ответственный:** Даниил Митин — Backend/Data + DevOps/Infrastructure.  
**Дополнительно:** по согласованию с Юрием — ограниченные несложные задачи Backend.  
**Репозиторий:** независимый GitHub repo, объединяющий Backend, AI, Frontend и инфраструктурные зависимости.  
**Контекст:** `00_PROJECT_OVERVIEW.md`.

## 1. Назначение

Обеспечить **воспроизводимый запуск, мониторинг, тестирование и интеграцию** AI Incident Investigator, который команда параллельно разрабатывает в четырёх разных репозиториях.

Владелец infra НЕ пишет LangGraph или Incident Management вместо Олега/Юрия. Он отвечает за инфраструктуру, телеметрию самого Investigator и demo-приложения, CI/CD и надёжное соединение контейнеров.

## 2. Состав и зависимости

| Компонент | Для чего | MVP/этап |
|---|---|---|
| Docker Engine / Docker Compose | Контейнеры, сервисная сеть, profiles, healthchecks | MVP |
| Backend image(s) | FastAPI, REST/WebSocket, MCP Server | MVP (поступает из Backend repo) |
| AI Worker image | LangGraph, MCP Client, RabbitMQ consumer | MVP (из AI repo) |
| Frontend image | UI | MVP (из Frontend repo) |
| PostgreSQL | Доменные данные и LangGraph checkpoints | MVP |
| RabbitMQ | Очередь investigations | MVP |
| DragonflyDB | Redis-compatible кэш (это **не Redis Server**) | MVP |
| Elasticsearch | Индексация/поиск логов подключённого demo | MVP |
| Kibana | Просмотр логов и deep links | MVP |
| Filebeat/Elastic Agent | Доставка контейнерных JSON logs в Elasticsearch | MVP |
| Prometheus | Мониторинг приложений и Investigator | MVP |
| Grafana | Dashboards/metrics/traces | MVP |
| OpenTelemetry Collector | Приём/маршрутизация OpenTelemetry | MVP |
| Grafana Tempo | Distributed traces | MVP |
| Exporters (cAdvisor, postgres/rabbitmq etc. по надобности) | Контейнерные/DB/broker/cache метрики | По целевым сценариям |
| Qdrant | Docs RAG и Incident Memory | Этап 2 |
| `llama-server` | Локальная LLM | **Нативно macOS**, не в Docker на Mac |

Logstash **не обязателен**, если agent/filebeat → Elasticsearch достаточно. Не внедрять Kafka и Loki в базовую конфигурацию (не являются нашим выбором для MVP).

## 3. Физическая схема локальной разработки

```text
                  MacBook Pro M2 Pro (16 GB)

  macOS host:
    llama.cpp / llama-server + GGUF model + Metal
                        ▲
                        │ HTTP via host.docker.internal
  Docker Compose network │
       ┌──────────────────┴────────────────────────────┐
       │  AI Worker ── MCP HTTP ──► Backend / MCP Server│
       │     ▲                         │ REST / WS      │
       │     │ RabbitMQ                ▼                │
       │  RabbitMQ                   Frontend           │
       │     │                                            │
       │  PostgreSQL · DragonflyDB                        │
       └──────────────────────────────────────────────────┘

  Отдельными profiles/на Mac mini/стенде:
     Elasticsearch · Kibana · Prometheus · Grafana
     OpenTelemetry Collector · Tempo · exporters
     demo e-commerce (во внешнем репозитории)
```

**Главный риск:** 16 GB RAM не предназначены для одновременного безусловного запуска квантизованной 7B-модели + ELK + Tempo + всего e-commerce. Нельзя считать такую композицию гарантированно работоспособной без измерений. Предусмотреть выборочное поднятие, распределение по MacBook/Mac mini и возможность подключаться к удалённым источникам.

### llama.cpp на Apple Silicon

- `llama.cpp` и Qwen2.5-Coder-7B-Instruct GGUF запускаем **на macOS нативно** с Metal.
- `llama-server` использует порт/адрес, доступные **из AI Docker-контейнера**, а не только из localhost контейнера; ограничить экспозицию в сеть.
- AI Worker получает URL через env; локальный вариант `http://host.docker.internal:<PORT>`.
- Не помещать llama.cpp в обычный Linux Docker на Mac как «тот же GPU-ускоренный runtime»: Metal там не будет работать аналогично нативному процессу.
- Документировать как минимум запуск/остановку модели, тип GGUF/quant, настройки контекста, тест доступности health, фактическое потребление RAM/скорость.
- Имя и параметры модели должны быть конфигурируемы; Qwen2.5-Coder-7B-Instruct — кандидат, качество Tool Calling/Structured Output проверяет Олег.

## 4. Docker Compose: что сделать

- **Главный интеграционный `compose`** запускает собранные образы Backend, AI, Frontend и обязательные хранилища/очереди.
- Дополнительные профили или конфигурации: `core`, `observability`, `demo`, `evaluation` (названия рабочие). Не требуют включать ELK при каждом AI unit test.
- Общая внутренняя Docker network; service discovery через Compose DNS (`backend`, `rabbitmq`, `postgres` и т. п. — реальные имена выберем вместе).
- MCP Server доступен AI по **внутреннему** Streamable HTTP endpoint. Не публиковать его в интернет по умолчанию.
- Healthchecks, readiness, restart policy, корректный shutdown для RabbitMQ consumers и PostgreSQL migrations.
- Volumes для PostgreSQL/Elasticsearch/RabbitMQ и иных persistent stores, скрипты safe reset/demo cleanup, без удаления пользовательских данных автоматически.
- Конфигурация через `.env.example`; секреты не коммитить. Для работы на нескольких машинах URL/порты задавать внешними переменными.
- Образы из трёх независимых репозиториев: локально соседние `build.context` **или** versioned images в container registry. Не требовать копирования исходников в infra repo.
- Отдельная инструкция «bootstrap from clean machine»; фиксация версий/commit SHA образов для воспроизводимой демонстрации.

## 5. Observability подключённого приложения

### 5.1. Логи: Elasticsearch + Kibana

- Принимать **структурированные JSON** логи тестового e-commerce и самого Investigator.
- Сбор через Filebeat/Elastic Agent, индексы/retention и поля для фильтрации.
- Минимальный стандарт корреляции: `timestamp`, `service.name`, `environment`, `severity`, `request_id`, `trace_id`, `correlation_id`, `incident_id`/`investigation_id` для Investigator.
- Межсервисная передача context IDs по HTTP и **RabbitMQ** должна быть проверена end-to-end.
- MCP tools Backend должны находить реальные ошибки через Elasticsearch; Kibana link должен открывать соответствующий source в доступном для пользователя интерфейсе.
- Не подменять данные scripted логами только для ответа AI.

### 5.2. Метрики: Prometheus + Grafana

- Точки сбора `prometheus-client` и exporters; scrape config/labels для service/env.
- HTTP request count, status codes, duration/latency, error rate.
- CPU, memory, container restarts, host status, диски/сеть при наличии exporters.
- PostgreSQL: соединения, pool usage (из instrumentation клиента/приложения, если нужен), transactions/locks/slow query indicators. Учесть, что exporter Postgres сам по себе не раскрывает все метрики connection pool приложения.
- DragonflyDB: cache health/latency, error/fallback, memory, если экспорт поддерживается.
- RabbitMQ: backlog/queue depth, consumers, processing latency, redeliveries.
- Разумные scrape intervals/retention и достаточный набор правил alerts для демонстрации.
- Grafana dashboards для e-commerce, Backend/AI, RabbitMQ/DB, не превращать UI продукта в обязательную замену Grafana.

### 5.3. Tracing: OpenTelemetry + Tempo

- Инструментировать критические HTTP вызовы и сообщения RabbitMQ в demo e-commerce; использовать OTel SDK/auto instrumentation, collector и Tempo.
- Сквозные `trace_id`/spans между gateway/order/payment/inventory и broker consumers.
- Статусы spans, ошибки, latency, `service.name`, ресурсные метаданные.
- Убедиться, что trace и связанные логи можно соединить по IDs, а Backend MCP `get_trace` возвращает настоящую трассировку.
- Для самого Investigator — span/run MCP/LLM/tool events через OTel, traces в Tempo.

## 6. Инциденты и реальные алерты

- Нужен работающий путь: Prometheus alert rule → Alertmanager webhook → Backend Incident API → RabbitMQ → AI Worker.
- Инфраструктура предоставляет доступность Alertmanager/внешних alert ingestion endpoints, которые согласует Юрий.
- Fault injection реализуется в **отдельном e-commerce репозитории другим разработчиком**. Infra помогает подключить demo к сетям/observability и запускает сценарии тестирования, но не берёт на себя всё его бизнес-приложение.
- Поддержать ручную проверку каждого утверждённого сценария с известной первопричиной.
- Обязательно изолировать injection от реальных production данных: только demo/staging, с автоостановкой неисправностей на стороне testbed.

### Первая шестёрка сценариев

1. PostgreSQL connection pool exhaustion — логи timeout, connection/pool metrics, traces.
2. Bad deployment — версия/commit/event, изменение поведения приложения.
3. High downstream latency — HTTP latency, downstream span, каскад таймаутов.
4. OOM/container restarts — OOMKilled/container event, memory trends.
5. RabbitMQ consumer failure — queue backlog/consumer count, логи обработки.
6. DragonflyDB failure — ошибки кэша, latency/fallback, клиентские логи.

Цель — 10–15 reproducible ground truth scenarios для тестирования AI (за метрики качества модели отвечает Олег).

## 7. Мониторинг самого Investigator

| Что измеряем | Где смотреть |
|---|---|
| HTTP/API latency/errors, WS connections | Prometheus/Grafana |
| RabbitMQ queue depth, inflight runs, retries | Prometheus/Grafana |
| AI run durations/completion/failures | Prometheus/Grafana |
| LangGraph nodes / tool/LLM call traces | OpenTelemetry/Tempo |
| MCP tool latency/errors/rate limits | Prometheus + Tempo |
| Token usage при достоверной доступности | Metrics, без выдуманных значений |
| Incident/Investigation activity history | PostgreSQL через Backend UI |

Не вводим **LangSmith как обязательный компонент**. Особая осторожность с traces/logs: не писать в них секреты, токены, сырые чувствительные данные.

## 8. GitHub Actions CI/CD

Каждый репозиторий отвечает за свои job'ы; Даниил помогает выровнять CI conventions и владеет интеграционными workflow в infra.

### Обязательный минимум по каждому репозиторию

- **Lint** (Python/TypeScript инструменты владельца репозитория).
- **Type checking** (где применимо).
- **Tests** (unit и подходящие contract tests).
- **Docker build** и базовая проверка образа.

### Integration CI в infra

- Зафиксировать версии Backend/AI/Frontend images (Git SHA, digest или version tag).
- Поднять минимальный Compose stack, дождаться health/readiness.
- Проверить API ↔ RabbitMQ ↔ AI Worker ↔ MCP Server; использовать mock llama-server/источники в быстрых CI тестах, чтобы не требовать Apple GPU в GitHub Actions.
- Прогнать contract tests REST/MCP/WebSocket/event схем; проверку runtime конфигурации и отсутствие секретов в образах.
- Не пытаться запускать полный Elastic/Tempo e-commerce и дорогие AI evaluation сценарии на каждый commit: для них отдельный integration/nightly/manual workflow.
- Опциональное деплой-обновление demo стенда после успешной проверки, но **не включать автоматические необратимые действия без решения команды**.

## 9. Межрепозиторная совместимость и контракты

Контрактная спецификация будет создана отдельно. Infra должна обеспечивать:

- env names and documented config for all three components;
- Docker DNS names / ports / MCP URL / llama-server URL;
- версии и совместимость контейнерных image tags;
- readiness/liveness endpoints;
- схема переменных DB/RabbitMQ/Dragonfly/Tempo/Prometheus/Elastic/GitHub;
- bootstrap/migration sequence и стартовые права;
- transport security и запрет случайной публикации sensitive endpoints;
- CI contract suite с mocks и простым e2e.

**Важный момент:** MVP разрабатывается в четырёх **разных** GitHub-репозиториях. `infra` — интегратор, но не монорепозиторий, куда переносится код остальных участников.

## 10. Безопасность и эксплуатация

- Никаких токенов, `.env`, приватных ключей или пользовательских dump в Git.
- Docker Socket привилегирован: не монтировать его прямо в контейнер AI и не отдавать LLM. Если Backend должен диагностировать Docker, предоставить минимально разрешённый read-only diagnostic proxy/adaptor с проверкой прав.
- RabbitMQ/PostgreSQL/MCP/Prometheus/Elastic по умолчанию доступны только через предназначенные сети/порты; публиковать наружу только необходимые Dev UI/API endpoints.
- Secrets в безопасных переменных/manager; документация для rotation и локальных dev credentials. Redaction в telemetry.
- Сетевые сегменты по назначению, ограничение access to Elasticsearch/Tempo/GitHub и SSRF-protected external check endpoint.
- Backup/restore для PostgreSQL, зафиксировать поведение при падении Worker и приём повторных сообщений.
- Ресурсные лимиты контейнеров, диск/retention, очистка demo data без удаления реальных данных.
- TLS, reverse proxy, публичное размещение и SaaS **не описываем как обязательные для текущей локальной MVP конфигурации**. При внешнем deployment — обязательное отдельное решение по безопасности.

## 11. Подход к ресурсам MacBook/Mac mini

- Первоначально разделить `core` и `observability` по Compose profiles.
- Запускать llama.cpp с Metal на MacBook Pro M2 Pro 16 GB; замерять RAM, CPU, tok/s, context length, реальные tool-calling performance.
- По возможности перенести Elasticsearch/Kibana/Tempo/часть инфраструктуры на Mac mini M2 16 GB или отдельный стенд, оставив сетевые адреса конфигурируемыми.
- Не гарантировать одновременный запуск всего стека на одной 16 GB машине без профилирования.
- Сохранить техническую возможность переноса с localhost на отдельный сервер без переписывания бизнес-кода.

## 12. Документация запуска

Обязательно подготовить:

1. `README` с требованиями к платформе, Docker Desktop/Compose и необходимыми портами.
2. `.env.example` без чувствительных данных и пояснения каждой переменной.
3. Порядок получения/сборки образов из отдельных GitHub-репозиториев.
4. Команды запуска минимального `core` и расширенного `observability` профиля.
5. Запуск нативного `llama-server` и проверка API из Docker-контейнера.
6. Initial PostgreSQL migrations/bootstrap, health tests, проверку MCP link.
7. Подключение demo e-commerce, Alertmanager webhooks и первый реальный incident.
8. Остановку, сброс **только demo данных**, типовые неисправности и troubleshooting.

## 13. План работ

1. Минимальный Compose с PostgreSQL, RabbitMQ, DragonflyDB и одним Backend/AI/Frontend stub image.
2. Docker network и MCP connectivity, AI→host.docker.internal llama-server; здоровье контейнеров и resource monitoring.
3. GitHub Actions / CI templates, build/versioning и общие env conventions.
4. Elastic/Kibana + structured logging; Prometheus/Grafana; OTel Collector/Tempo.
5. Подключение реального e-commerce/testbed, instrumentations, alert rules, exporters и source links.
6. Integration/contract/e2e test workflows, восстановление после падения AI и тестирование cancel/retry.
7. Ресурсная оптимизация, документация «чистый старт» и подготовка сценария защиты.

## 14. Критерии приёмки

- [ ] Каждый сервис стартует из собственного repo image через общий Docker Compose; документация воспроизводима.
- [ ] `Backend ↔ AI` общается через RabbitMQ/MCP по внутренней сети без общих исходников в монорепозитории.
- [ ] AI-контейнер способен безопасно обратиться к нативному `llama-server` на macOS.
- [ ] При доступных source integrations появляются **реальные** логи в Kibana, метрики в Grafana и traces в Tempo.
- [ ] У demo e-commerce есть сквозные `trace_id`/`request_id` и примеры HTTP/RabbitMQ propagation.
- [ ] Alertmanager реально запускает Incident; AI получает доказательства и формирует RCA.
- [ ] Есть наблюдаемость самого Investigator: agent/tool latencies, queue, failures и spans.
- [ ] Избыточные ресурсы отключаются profiles; минимальный стек не требует всего ELK одновременно.
- [ ] Секреты не попадают в Git/GitHub Actions logs и образы, Docker Socket не открыт AI.
- [ ] Есть тестовый e2e run в CI или в документированном ручном pipeline с фиксированными image versions.
- [ ] Задокументированы ограничения железа, способы переноса инфраструктуры и безопасного сброса demo.

## 15. После MVP

- Подключение Qdrant (RAG + Incident Memory), если AI и Backend готовы к этому этапу.
- Расширение retention, monitoring dashboards, alert rules и инфраструктурных fault scenarios.
- При необходимости отдельный Kubernetes deployment, но **не обязательная цель** к декабрьской защите.
