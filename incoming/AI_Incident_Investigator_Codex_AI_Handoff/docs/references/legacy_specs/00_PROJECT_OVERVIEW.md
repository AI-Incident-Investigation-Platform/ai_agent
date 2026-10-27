# AI Incident Investigator — единая спецификация проекта

**Статус:** зафиксированные требования по итогам обсуждения (09.10.2026).  
**Назначение:** общий контекст для команды, основа для архитектуры, планирования и подготовки API-контрактов.  
**Приоритет:** работающее ядро к защите в середине декабря 2026 года; затем дополнительные возможности.

> Документ описывает, **что** строим и **какие решения уже приняты**. Конкретные REST/MCP/WebSocket/RabbitMQ-схемы, таблицы БД и внутреннее разбиение Backend предстоит согласовать отдельно. Примеры ниже не являются утверждёнными контрактами.

## 1. Кратко: что это за продукт и что он умеет

**AI Incident Investigator** — система автономного расследования технических инцидентов в микросервисных приложениях. Она получает сигнал об ошибке, запускает одного AI-агента, предоставляет ему диагностические инструменты, собирает доказательства и формирует **Root Cause Analysis (RCA)**: наиболее вероятную первопричину, цепочку последствий и рекомендации по исправлению.

Что увидит пользователь:

1. Подключает проект и источники телеметрии/кода (Elasticsearch, Prometheus, Tempo, GitHub, Docker и др.).
2. При ошибке приходит alert или пользователь вручную инициирует расследование.
3. На дашборде появляется инцидент; AI-расследование запускается асинхронно.
4. В **Live Investigation** в реальном времени видны вызовы инструментов, их статусы, результаты и изменения гипотез.
5. Агент исследует логи, метрики, распределённые трассировки, состояние контейнеров, развёртывания и нужные фрагменты кода.
6. В отчёте доступны симптомы, затронутые сервисы, до трёх гипотез, **Evidence со ссылками на первоисточники**, Timeline, Root Cause, уверенность и практические рекомендации.
7. Человек подтверждает, отклоняет или корректирует вывод; история сохраняется. Можно отменить или повторить запуск расследования.

**Пример:** после нового релиза `payment-service` начал отвечать HTTP 500. Агент обнаруживает timeout подключения к PostgreSQL в логах, насыщение пула соединений в Prometheus, медленные DB spans в Tempo и подозрительное изменение в GitHub. Он связывает факты, но не объявляет виновным commit без достаточных доказательств. Финальный RCA объясняет, **почему** ошибка возникла, а не просто повторяет текст алерта.

## 2. Цель и границы

- Универсальный, **production-like** продукт, который можно интегрировать с существующими приложениями; тестовый e-commerce — только стенд для проверки.
- Универсальность инструментов и модели инцидента важнее заранее зашитых сценариев.
- Покрываем ошибки HTTP 500, latency, падения сервисов, OOM/restarts, проблемы PostgreSQL, DragonflyDB, RabbitMQ, внешних API, ошибки deployment/config и каскадные межсервисные сбои.
- Агент отличает **симптом**, **промежуточное следствие** и **первопричину**, допускает несколько сервисов в причинной цепочке.
- Необходимо честно показывать неопределённость: при нехватке данных статус запуска `inconclusive`, а не выдуманный диагноз.
- Система **не** исправляет production автоматически: никаких произвольных shell-команд, patch/PR, restart, rollback, изменений конфигурации от агента. Только контролируемые read-only инструменты и рекомендации человеку.
- Первое развёртывание — локальный Docker Compose. Окончательная продуктовая модель Self-hosted/SaaS **не утверждена**. Полноценный Multi-Tenancy и обязательное автообнаружение сервисов **не входят в согласованный MVP**: эти темы отдельно обсуждались и затем были отозваны.

## 3. Концептуальная архитектура

```text
                      FRONTEND (репозиторий Расула)
                Dashboard / Incidents / RCA / Live
                             │ REST + WebSocket
                             ▼
                    BACKEND (репозиторий Юрия)
       Projects · Environments · Services · Incidents · RBAC
       Integrations · Evidence · RCA · WebSocket · MCP Server
                  │                │             ▲
                  │                ▼             │ MCP Streamable HTTP
                  │             RabbitMQ         │
                  │                │             │
                  ▼                ▼             │
               PostgreSQL    AI WORKER ── MCP Client
                             (репозиторий Олега)
                             LangGraph / ReAct
                             Agent State / RCA
                                  │ HTTP
                                  ▼
                      llama.cpp on macOS (Metal)
                      Qwen2.5-Coder-7B-Instruct

       MCP Server / integration adapters → Elasticsearch, Prometheus,
       Tempo, GitHub, Docker diagnostic adapter, health endpoints,
       deployment history

       INFRA (репозиторий Даниила): Docker Compose, RabbitMQ,
       PostgreSQL, DragonflyDB, Elastic/Kibana, Prometheus/Grafana,
       OpenTelemetry Collector/Tempo, CI/CD, observability
```

**Важное уточнение:** схема показывает логические области. Внутренние границы backend-микросервисов, число процессов, владельцев БД и устройство слоёв определяет **Юрий**. Не создавать произвольные дополнительные сервисы только ради схемы.

### 3.1. Четыре отдельных GitHub-репозитория

| Репозиторий (рабочее название) | Владелец | Зона ответственности |
|---|---|---|
| `incident-investigator-backend` | Юрий Бурцев | Backend, HTTP/WebSocket API, MCP Server и интеграции, инциденты, безопасность |
| `incident-investigator-ai` | Олег Митин | Single-Agent LangGraph/ReAct, MCP Client, гипотезы, Evidence, RCA, evaluation |
| `incident-investigator-frontend` | Расул Садулаев | UI, Dashboard, Incident Detail, Live Investigation, RCA |
| `incident-investigator-infra` | Даниил Митин | Compose, инфраструктурные сервисы, telemetry, GitHub Actions, интеграционный стенд |

Названия рабочие. У каждого репозитория есть отдельная спецификация в этом наборе файлов. Даниил также берёт небольшие Backend-задачи по согласованию с Юрием. Демонстрационный e-commerce поручен **отдельному разработчику**, не считается пятым внутренним микросервисом Investigator.

## 4. Типовой жизненный цикл инцидента

1. **Trigger:** Alertmanager/Prometheus, Grafana Alerting, Sentry или иные интеграции через входные webhook/API. Ручной запуск поддерживается; запуск инцидента по свободному тексту — низкий приоритет.
2. **Нормализация и сохранение:** Backend определяет Project/Environment/Service, временной диапазон и источник, создаёт или связывает инцидент, сохраняет начальный контекст в PostgreSQL.
3. **Очередь:** Backend публикует задание `investigation.requested` в RabbitMQ. Содержимое компактное: идентификаторы и версию сообщения; секреты и большой массив логов не передаются.
4. **AI Worker:** получает задачу, загружает контекст и проверяет ограничения. На Mac MVP — один активно исполняемый run, остальные ждут очереди.
5. **ReAct:** LLM выбирает read-only MCP-инструменты, агент собирает результаты, обновляет Evidence/гипотезы, сохраняет checkpoint LangGraph в PostgreSQL.
6. **Realtime:** события статусов и результатов сохраняются и публикуются через Backend → WebSocket → Frontend. Разрыв WebSocket не прекращает расследование; пропущенное восстанавливается из истории.
7. **Итог:** валидируется структурированный RCA Report; Backend сохраняет результат, отображает UI, разрешает human review.
8. **Review:** человек подтверждает/отклоняет/корректирует Root Cause, может повторить run. Завершение агента ≠ автоматическое устранение инцидента.

Пример логической последовательности (не утверждённые имена payload):

```text
IncidentCreated → InvestigationQueued → InvestigationStarted
  → ToolStarted → ToolCompleted → HypothesisUpdated
  → InvestigationCompleted | InvestigationInconclusive
    | InvestigationFailed | InvestigationTimedOut | InvestigationCancelled
  → RCAReviewed (человеком)
```

**Состояние инцидента**: `Open`, `Investigating`, `Awaiting Review`, `Resolved`.  
**Состояние запуска AI**: завершён успешно / недостаточно доказательств / ошибка / таймаут / отменён. Реальные enum и переходы будут формально согласованы в контрактах. **Retry создаёт новый `investigation_id`** и не удаляет предыдущую историю; Cancel выполняется контролируемо и кооперативно. `Restart with Context` отложен.

## 5. Модель продукта и данных

- Базовая иерархия: **Project → Environment → Service → Deployment**. Один пользователь может работать с разрешёнными проектами; один инцидент может затрагивать несколько сервисов.
- Проект имеет настройки внешних источников (логов, метрик, трассировок, кода), сопоставление идентификаторов сервисов, историю запусков.
- PostgreSQL: проекты/сервисы, интеграции (без хранения секретов в открытом виде), пользователи и права, incidents, investigations, tool events, hypotheses, evidence, RCA, deployments, review/audit, LangGraph checkpoints (логически разделённая зона).
- **DragonflyDB**: кэш и временные данные, не единственный источник истины.
- **RabbitMQ**: доставка заданий/событий, не хранилище Agent State; подтверждение обработки, идемпотентность, обработка повторов и ошибок.
- **Elasticsearch, Prometheus, Tempo**: исходная телеметрия остаётся там; PostgreSQL хранит выборки/ссылки/метаданные, нужные для аудита и объяснения. Предусмотреть ситуацию, когда исходник позднее удалён retention-политикой.
- **Qdrant (этап 2)**: отдельное векторное хранилище документации и похожих инцидентов, со строгой фильтрацией по проекту. Индексируем `README.md` и `docs/` (`.md`, `.txt`, `.pdf`; `.docx` позже). Код через GitHub tools, а не embeddings.
- Точная схема БД, её физическое разделение и миграции — ответственность Backend/Infra, не фиксируем в этом документе.

## 6. AI-часть: зафиксированный подход

- **Один агент**, не Multi-Agent; **LangGraph + ReAct**, без отдельного planning-agent и без принудительного плана перед каждым run.
- **Локальная LLM:** `Qwen2.5-Coder-7B-Instruct` (кандидат), GGUF, ориентир квантования `Q4_K_M`; inference — **llama.cpp / llama-server**, **без Ollama**.
- На Apple Silicon `llama.cpp` запускаем **нативно на macOS с Metal**; контейнер AI обращается к нему через `host.docker.internal`. Другие deployment-окружения требуют другого конфигурирования URL и accelerator.
- Проверка модели обязательна: tool calling, JSON/structured output, корректность выводов на технических данных. Выбранная модель — исходная гипотеза, не доказанная пригодность.
- **Лимиты**: до `20` шагов, `40` MCP/Tool вызовов, общее ограничение расследования `20 минут` (настройки конфигурируемы). Итог на лимите может быть `inconclusive` с сохранёнными Evidence.
- **Agent State**: история нужных сообщений, гипотезы, Evidence, tool events, источники, бюджеты и статус. Checkpointing — PostgreSQL. Не хранить целиком огромные логи в контексте LLM: структурное состояние, выборки, summaries и лимиты на tool output.
- До **3 гипотез**: статусы `pending/supported/rejected`, уверенность качественная `High/Medium/Low`, объяснение и связанные доказательства; отдельные поля `evidence_for/evidence_against` не требуются.
- RCA: описание инцидента, симптомы, affected services, root cause (или «не установлена»), confidence, гипотезы, Evidence, Timeline, причинная цепочка, рекомендации/предотвращение, активность агента, кликабельные источники.
- Анализ внешних логов, README и кода **не должен превращаться в выполнение инструкций из этих источников**. Данные источников — недоверенные.

## 7. Подключаемые источники и инструменты

| Источник | Для чего | Общие требования |
|---|---|---|
| Elasticsearch + Kibana | JSON-логи, errors, stacktraces, корреляции | Поиск по сервису, времени, `request_id`/`trace_id`; защищённый Query DSL |
| Prometheus + Grafana | CPU/RAM/HTTP, БД, DragonflyDB, RabbitMQ, infra | Параметризованные tools и контролируемый PromQL; guardrails |
| OpenTelemetry + Tempo | Distributed traces и spans | `get_trace`, slow span, cross-service chain, `trace_id` |
| GitHub | Read-only code search, files, history, diff, blame | Только подключённые репозитории; deployment/commit корреляция |
| Docker | Статус, restarts, OOMKilled, health, events | Без выдачи агенту привилегированного Docker Socket |
| Deployments API | История версий и rollout | Универсальные входные события, без анализа GitHub Actions pipelines |
| External API | Health/доступность зависимостей | Только allowlist, безопасные GET/HEAD, таймауты, SSRF-защита |
| PostgreSQL приложения | Только косвенная диагностика | Через метрики/exporters и логи; **без прямого SQL-доступа** |

**MCP**: Backend предоставляет MCP Server через **Streamable HTTP**, AI — MCP Client. Backend реализует диагностические adapters и контроль доступа. Агент самостоятельно выбирает инструменты, но не получает доступ к произвольной сети, shell или credentials. API/MCP-схемы не утверждены, будут оформлены в отдельной спецификации.

## 8. Frontend: что видит пользователь

- Тёмный минималистичный профессиональный интерфейс; на Dashboard нет декоративной круговой диаграммы «Incidents by Severity».
- **Dashboard**: активные инциденты, работающие расследования, recent incidents, затронутые сервисы, быстрые действия.
- **Incidents**: таблица с поиском, фильтрами Project/Service/Severity/Status/Time, сортировкой, пагинацией, обновлениями в real time.
- **Incident Detail**: общая информация, `Live Investigation`, `Hypotheses`, `Evidence`, `Timeline`, `RCA Report`.
- **Live Investigation**: status `pending/running/completed/failed`, краткое объяснение вызова tool (не скрытая chain-of-thought), раскрываемые безопасные результаты, изменения гипотез, шаги/время, Cancel и Retry.
- **Evidence**: карточки/таблица с выдержками и прямыми ссылками в Kibana/Grafana/Tempo/GitHub.
- **Logs/Metrics/Traces/Git Diff**: в MVP — релевантные результаты и переходы в источники. Встроенные графики и интерактивные трассировки — следующий этап после основного вертикального сценария.
- **Incident Chat** (этап 2): вопросы к сохранённому RCA/контексту без новых инструментальных вызовов.
- **RBAC**: `Admin`, `Developer`, `Viewer`; базовый JWT. Доступ к проектам обязателен, а не только скрытие кнопок в UI.

## 9. MVP, второй этап и запреты

### Обязательно в MVP к середине декабря 2026

- Сквозной вертикальный сценарий alert/manual → incident → RabbitMQ → LangGraph → MCP tools → RCA/Evidence → PostgreSQL → WebSocket → Frontend.
- Микросервисный Backend на FastAPI, REST/WebSocket/MCP, RBAC, базовое управление Project/Environment/Service/Integrations.
- Single-Agent ReAct + локальная LLM; устойчивость к ошибкам источников, budgets, checkpointing, Cancel/Retry, вывод `inconclusive`.
- Первые интеграции Elasticsearch/Prometheus, затем Tempo/GitHub/Docker и deployment history для целевых сценариев.
- Наблюдаемость самого Investigator, история investigation events, источники доказательств и review результата.
- Docker Compose, CI/CD GitHub Actions, интеграционные и контрактные тесты; работающий воспроизводимый demo-сценарий.
- Минимально достаточные, но реальные права доступа, secrets/redaction и ограничения diagnostic tools.

### После основного контура / второй приоритет

- Qdrant RAG по документации и Incident Memory (семантический поиск прошлых случаев; прошлые случаи — подсказки, не доказательства).
- Контекстный чат по завершённому расследованию.
- Встроенные интерактивные метрики и span-графы, UX-полировка.
- Restart with Context, дополнительные интеграции, Kubernetes (только при наличии ресурсов).

### Не реализуем агентом

- Multi-Agent; shell/SQL внутри чужих приложений; автоматические fixes/rollback/restart; анализ CI/CD workflows и unit-тестов как обязательные diagnostic tools; разработку SaaS и сложного Multi-Tenancy в MVP.

## 10. Тестирование и демонстрационный e-commerce

Отдельный разработчик создаёт e-commerce из **6 сервисов**: `api-gateway`, `user-service`, `order-service`, `payment-service`, `inventory-service`, `review-service`. Данные: PostgreSQL, **DragonflyDB**, **RabbitMQ**. Инструмент fault injection с API и минимальным admin UI работает **только в тестовой среде**, имеет автоматический stop/rollback по таймауту и производит **настоящую телеметрию**, а не подставные ответы агента.

Утверждённые 6 первых неисправностей:

1. PostgreSQL connection pool exhaustion.
2. Bad deployment (код или конфигурация).
3. High latency downstream / cascade.
4. OOM и перезапуск контейнера.
5. RabbitMQ consumer failure / backlog.
6. DragonflyDB failure / деградация кэша.

Расширение до **10–15 ground-truth сценариев**. Оцениваем `root cause accuracy`, корректность tool selection, число лишних вызовов, время диагностики, использование LLM/токенов, качество и проверяемость Evidence. Регрессионные тесты промптов/агента, mocks адаптеров, e2e и проверки прав доступа.

### Успешная защита

Искусственно ломаем `payment-service` → реальная телеметрия → alert → incident → RabbitMQ → autonomous LangGraph/MCP investigation → видимые шаги во Frontend → RCA со ссылками на реальные данные → независимая проверка известного root cause. **Никаких заранее зашитых ответов.**

## 11. API-контракты — отдельная следующая работа (важно)

Разработка идёт в **разных GitHub-репозиториях**, поэтому до независимой реализации интеграций фиксируем **Contract-First**:

| Граница | Будущая спецификация |
|---|---|
| Frontend ↔ Backend | REST OpenAPI: маршруты, запросы/ответы, ошибки, auth |
| Backend → Frontend | WebSocket: сообщения, порядковые номера, восстановление после разрыва |
| Backend → AI | RabbitMQ commands: запуск, cancel/retry, correlation/identity, версия |
| AI → Backend | Progress/events, hypotheses/evidence/RCA, статусы и idempotency |
| AI ↔ MCP Server | MCP tool names/JSON Schema, result blocks, ошибки, ограничения, auth |
| Репозитории ↔ Infra | Env-переменные, Docker service names, health/readiness, конфигурация |

Нужно создать **единый источник истины схем**, версионирование, mocks и contract tests. Конкретные endpoint names, event payloads, поля Tool Results, ошибка-формат и методы передачи live events **пока не утверждены**. Примеры в документации — иллюстративные, не окончательные.

## 12. Принципы реализации и риски

- **Ресурсы:** MacBook Pro M2 Pro, 16 GB unified RAM и Mac mini M2, 16 GB. LLM + Elasticsearch/Kibana + вся observability + тестовый стенд могут не поместиться одновременно. Compose profiles, частичный запуск, разнесение сервисов по машинам.
- **llama.cpp:** Metal ускорение только в нативном macOS-процессе; Linux Docker на Mac для GPU-инференса не подходит как эквивалент.
- **MCP Server:** доступ по внутренней сети и аутентификация, не открыт в интернет по умолчанию.
- **Idempotency:** RabbitMQ допускает повторную доставку; операция запуска/записи событий должна быть безопасна при дублях.
- **Cancellation:** корректное прекращение работы, сохранение статуса/checkpoint, недопущение потери следов.
- **Точность AI:** красивые объяснения без проверяемых доказательств не считаются успешной диагностикой.
- **Таймлайны и увереность:** не путать корреляцию во времени с причинной связью и `High` с гарантией.

## 13. Следующие работы после этих пяти файлов

1. Утвердить **сквозной сценарий** и границы компонент.
2. Выпустить отдельную точную **Contract-First API/MCP/Event specification** (совместно Олег + Юрий + Расул + Даниил).
3. Подготовить mock Backend/MCP и mock Agent events, чтобы репозитории разрабатывались параллельно.
4. Подготовить roadmap, backlog по ответственным и критерии приёмки задач.
5. Начать с одной действительно работающей связки и постепенно добавлять диагностические инструменты.

**Главный принцип:** продукт должен не «делать вид, что нашёл причину», а строить проверяемую картину инцидента из реальных наблюдений и честно обозначать неопределённость.
