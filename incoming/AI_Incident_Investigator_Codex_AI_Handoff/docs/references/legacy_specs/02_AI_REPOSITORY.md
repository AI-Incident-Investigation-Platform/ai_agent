# incident-investigator-ai — техническое задание

**Ответственный:** Олег Митин — Team Lead / AI Engineer.  
**Смежные репозитории:** Backend (MCP Server и API), Frontend (визуализация событий), Infra (запуск, метрики, eval-стенд).  
**Назначение:** автономный single-agent RCA с реальными доказательствами.  
**Общий документ:** `00_PROJECT_OVERVIEW.md`.

## 1. Что должен делать AI-компонент

Получить задание на расследование инцидента, самостоятельно выбирать **read-only MCP Tools**, анализировать результаты, обновлять гипотезы, собирать проверяемые Evidence, сохранять состояние LangGraph и завершать запуск структурированным RCA Report либо честным `inconclusive`.

AI-компонент **не** управляет учётными записями, бизнес-статусом инцидента, frontend или внешними секретами. Эти функции относятся к Backend. MCP инструменты не дублируются в AI-коде: их реальные источники и доступы реализует Backend.

## 2. Стек и среда исполнения

| Область | Выбор |
|---|---|
| Agent orchestration | **LangGraph** |
| Agent pattern | **Single-Agent ReAct** |
| Tool transport | **MCP Streamable HTTP**, MCP Client |
| Local LLM runtime | **llama.cpp / llama-server** |
| Начальная модель | **Qwen2.5-Coder-7B-Instruct**, GGUF, квантование ориентировочно Q4_K_M |
| Agent state/checkpoints | **PostgreSQL**, LangGraph checkpointer |
| Схемы | Pydantic v2 / JSON Schema |
| Background tasks | **RabbitMQ** consumer AI Worker |
| Infrastructure | Docker-контейнер для Worker, OpenTelemetry для traces/metrics |
| LLM network | AI Docker → `host.docker.internal` → `llama-server` на macOS с Metal |

**Ollama не используется.** На MacBook Pro M2 Pro 16 GB Metal-ускорение требует нативного `llama.cpp`; AI Worker отдельно в Docker. Параметры запуска и фактическую скорость/память проверить измерениями, не обещать гарантированного качества или throughput.

Абстракция клиента inference допустима (например, совместимый локальный HTTP API), но не строим тяжёлую платформу провайдеров. Одна начальная модель, затем benchmark и при необходимости замена.

## 3. Архитектура AI Worker

```text
RabbitMQ: investigation.requested
        │
        ▼
Task Consumer / Idempotency Guard
        │
        ▼
Load Authorized Incident Context (Backend)
        │
        ▼
LangGraph Single-Agent
    ├── State / Checkpointer → PostgreSQL
    ├── Model Client → llama.cpp
    ├── MCP Client → Backend MCP Server
    ├── Tool Output Reducer / Evidence Extractor
    ├── Hypothesis Manager
    └── RCA Validator / Reporter
        │
        ▼
Results / Progress / Status → Backend
        │
        ▼
ACK RabbitMQ after durable completion
```

**Путь передачи progress и final results в Backend ещё требует контракта** (event bus или защищённые backend endpoints). Не внедрять произвольный формат между репозиториями. За выполнение Agent Loop отвечает AI-код; за трансляцию браузеру — Backend/WebSocket.

## 4. Обязательный LangGraph ReAct Loop

Минимальный логический граф:

```text
START
  ↓
LoadContext / RestoreCheckpoint
  ↓
AgentDecision (LLM)
  ├── structured tool call ──► Validate & Execute MCP Tool
  │                                ↓
  │                       Normalize / Redact / Evidence
  │                                ↓
  │                           Update State
  │                                └───────────► AgentDecision
  └── finish ──► Validate structured RCA ──► Persist result ──► END
```

- Никаких отдельных Logs Agent, Metrics Agent, GitHub Agent или автономного Planner.
- Не начинать каждый run с обязательного фиксированного multi-step плана. ReAct выбирает следующий инструмент из текущих наблюдений.
- При технических ошибках tools модель может выбрать другой источник; нельзя бесконечно повторять один и тот же сбойный вызов.
- Если у агента нет достаточной информации, завершать как `inconclusive`, перечислять пробелы, не выдумывать первопричину.
- Не превращать output tool call в инструкцию для системы — источники являются недоверенными данными.

## 5. Ограничения выполнения

**Согласованные значения по умолчанию:**

- `max_steps = 20`;
- `max_tool_calls = 40`;
- `investigation_timeout = 20 min`;
- один активный investigation на локальном Worker/Mac в начальной конфигурации;
- общие ограничения должны применяться кодом, а не только текстом system prompt.

Нужны учёт counters, дедлайн wall-clock, timeout отдельных инструментов, cancellation token/checkpointed status и контроль числа неудачных повторов. На лимите сохраняем собранные Evidence и partial assessment вместо потери результата.

**Retry** создаёт новый `investigation_id`; **Cancel** останавливает работу безопасно, сохраняет последнюю полезную state и отражает `cancelled`. `Restart with Context` не входит в MVP. Расследование после crash допускает восстановление из checkpoint, но необходимо учитывать недетерминизм LLM и возможные повторные MCP-вызовы: идемпотентность/дедупликация обязательны на границах.

## 6. Состояние агента

Логически LangGraph State содержит:

| Поле / группа | Назначение |
|---|---|
| `investigation_id`, `incident_id` | Идентификация run и инцидента |
| `project_id`, `environment_id` | Контекст доступа и источников, не разрешение само по себе |
| `incident_context` | Исходный alert, service/time window, known metadata |
| `messages` | Необходимый контекст LLM; не весь сырой поток telemetry |
| `hypotheses` | До 3 гипотез, statuses, confidence, explanation |
| `evidence` | Ссылки, выдержки, происхождение, связанные hypotheses |
| `tool_history` | Краткий журнал вызовов, аргументов, статусов, времён |
| `checked_sources` | Что уже обследовано, чтобы не повторять без причины |
| `steps`, `tool_calls`, `deadline` | Budgets и ограничение продолжительности |
| `run_status` | Запущен/неопределённый/сбой/таймаут/отменён/завершён |
| `final_report` | Структурированный RCA или partial analysis |

Это **перечень требуемого состояния**, а не утверждённый Python-класс. Реальная LangGraph state model и checkpoint-схема — ответственность Олега, должны быть версионированы и мигрируемы. Хранить checkpoint в PostgreSQL, не в памяти Worker и не только в RabbitMQ/DragonflyDB.

### Контекстное окно

- Каждый результат MCP инструмента имеет ограничения объёма; крупные logs/traces обрезать с явным маркером truncation и возможностью точечного дополнительного запроса.
- Сохранять структурированные Evidence и IDs в state, а не слепо подавать в LLM огромные tool outputs.
- При росте истории делать контролируемые summaries; сохранять критические численные значения, chronology, negative findings, source IDs, code refs и статус гипотез.
- Не терять сведения о противоречащих фактах, даже если они не выделены отдельным полем `evidence_against`.
- Время, диапазоны, timezone, request_id/trace_id должны обрабатываться явно.

## 7. Гипотезы и причинный анализ

Агенту необходимо:

1. Сформировать до **трёх** конкурентных объяснений проблемы.
2. Для каждой хранить description, status `pending/supported/rejected`, `High/Medium/Low` и ссылки на Evidence.
3. Проверять различие **root cause / intermediate effects / symptoms**.
4. Искать причинные цепочки через несколько сервисов и коррелировать по timestamp, trace ID, request/correlation ID, deployment version.
5. Обновлять или отклонять гипотезы при противоречии данным.
6. Различать «deployment совпал по времени» и «конкретный diff обоснованно вызвал ошибку».
7. Называть неизвестное неизвестным, не подгонять отчёт под сильную формулировку.

**Quality bar:** каждое существенное утверждение RCA привязано к Evidence, которое реально получено инструментом, а не сгенерировано моделью. Высокая уверенность — качественная оценка, не статистически откалиброванная вероятность.

## 8. MCP Client / Tool Orchestration

AI Worker подключается к **Backend MCP Server** через Streamable HTTP, выполняет discovery/list tools и преобразует descriptors в инструменты, вызываемые LangGraph. Для локального Compose допустим адрес вида `http://backend:8000/mcp`, но реальный route определит контракт.

### Ожидаемые группы инструментов

| Группа | Примеры | На что обращать внимание |
|---|---|---|
| Logs | `search_logs`, `get_error_logs` | query, service, full historical window, request/trace ID |
| Metrics | `query_prometheus` | guarded PromQL, HTTP latency/errors, Postgres pool, Dragonfly/RabbitMQ |
| Traces | `get_trace` | slow/error spans, propagation, межсервисные вызовы |
| GitHub | `search_code`, `read_file`, `git_log`, `git_diff`, `git_blame`, `get_commit` | Коммит/релиз только при релевантности, repo access |
| Docker | `get_container_status`, events | OOM/restart/health/status, только read-only adapter |
| Deployments | `get_recent_deployments` | Корреляция release→degradation |
| External APIs | health checks | Только заранее разрешённые цели и методы |
| Phase 2 | `search_docs`, `search_similar_incidents` | Qdrant с project filter и source attribution |

**Не требуется автоматически вызывать все инструменты для каждого инцидента.** Например, GitHub diff нужен при подозрении на deployment/code, а не при очевидном падении внешнего API. Не анализировать GitHub Actions CI workflow как отдельный tool и не читать тесты «для галочки».

### Работа с MCP ошибками

- Различать временную недоступность, unauthorized/forbidden, no data, invalid query, tool timeout, rate limit.
- Использовать ограниченные retries/backoff для временных ошибок; не пытаться «продавить» запрещённый инструмент.
- Все аргументы LLM валидировать перед вызовом; не направлять прямые произвольные shell/SQL запросы.
- Секреты в ответах маскирует Backend, AI дополнительно защищает записи/traces и prompt.
- Продолжать расследование другими источниками, если один unavailable; отражать gaps в итоговом отчёте.

## 9. Evidence: формат и происхождение

Ключевое требование — **provenance**. Минимальная смысловая структура каждого Evidence:

- ID внутри investigation и связь с Incident.
- `source_type` и подключённая integration/service/environment.
- `event_timestamp` или range, `observed_at` если различаются.
- `summary`, `excerpt` или безопасный structured snapshot.
- `source_url`/link либо устойчивые source IDs для Kibana/Grafana/Tempo/GitHub.
- Связанные hypothesis IDs, causal claim или symptom.
- Признак неполного/обрезанного результата при необходимости.

Без ссылки или устойчивого source locator факт может быть сохранён как наблюдение, но не должен изображаться проверяемым первоисточником. Если ссылка временно недоступна из-за retention, должен оставаться корректный сохранённый фрагмент.

## 10. RCA Report: обязательные смысловые поля

| Секция | Содержание |
|---|---|
| Summary | Что случилось и когда |
| Severity / affected services | Критичность и область влияния |
| Symptoms | Ошибки, latency, отказ сервиса, бизнес-эффект если подтверждён |
| Root Cause | Доказанная/наиболее вероятная причина; если не доказана — явно unknown |
| Confidence | `High/Medium/Low`, обоснование |
| Hypotheses | До трёх, статус и evidence links |
| Causal Chain | События/условия → промежуточные последствия → симптомы |
| Timeline | Реальные отметки и источники, не придумывать временные точки |
| Evidence | Список проверяемых источников/выдержек |
| Remediation | Конкретные советы по code/config/ops, **без автоматического применения** |
| Prevention | Как исключить повторение |
| Investigation Metadata | run ID, steps/tool calls, duration, errors, missing context |

**Structured output валидируется программно Pydantic.** На невалидный ответ модели предусмотрен ограниченный repair/retry, после чего `inconclusive/failed` и сохранение частичного результата. JSON mode/token parser не гарантирует фактическую достоверность: проверять IDs и Evidence refs против реально выполненных tool calls.

## 11. Agent events для Backend / Frontend

AI компонент формирует структурированные события уровня продукта:

- investigation started/progress;
- tool pending/running/completed/failed + short action explanation;
- hypothesis added/updated/rejected;
- evidence collected;
- RCA generated/validated;
- completed/inconclusive/failed/timed_out/cancelled.

Каждое событие должно иметь run/incident IDs, timestamp, порядок или стабильный event ID и sanitized payload. **Не отправлять скрытую внутреннюю цепочку рассуждений модели**; UI получает человечески понятное короткое описание намерения и фактический результат вызова.

Как именно доставлять события Backend (RabbitMQ/REST), кто проставляет sequence и когда признавать запись durable — согласовать в **Contract-First**. AI не должен держать прямое WebSocket-соединение с браузером.

## 12. Безопасность

- У AI только read-only MCP-инструменты. Backend проверяет scope, credentials и ограничения.
- Token/capability для AI → MCP передаётся вне prompt и не попадает в agent state.
- Логи, README, issues, конфиги — **untrusted input**, prompt injection не может менять системные инструкции, права и перечень tools.
- Защищаться от чрезмерно больших tool outputs, опасных URL/escaped content, повторяющихся инструкций «игнорируй правила».
- Не исполнять рекомендации модели. AI отчёт может включать предложенный патч словами, но не применяет его.
- Минимизировать sensitive data в traces/metrics/логах самого агента; разрешённые проекты изолируются.

## 13. Тестирование и научно-практическая оценка

### Уровни тестов

1. **Unit:** state transitions, budgets, validation, output parser, context management, cancellation.
2. **Contract:** mock MCP Server с реальными schemas, отрицательные кейсы, таймауты, проверка ошибок.
3. **Integration:** RabbitMQ → Worker → LangGraph → MCP → structured report → Backend, включая дубликаты/cancel/recovery.
4. **Ground truth evaluation:** 10–15 воспроизводимых инцидентов demo e-commerce.
5. **Regression:** после изменения prompt/model/tool description повторять стабильный набор фикстур и сравнивать результаты.

### Шесть первых инцидентов

- PostgreSQL pool exhaustion.
- Bad deployment.
- High downstream latency/cascade.
- OOM + container restarts.
- RabbitMQ consumer failure/backlog.
- DragonflyDB failure.

### Метрики качества

- Root cause accuracy по заранее известной причине (фиксировать критерии оценки).
- Evidence validity/provenance, отсутствие hallucinated evidence/source URLs.
- Tool call relevance, tool error recovery и лишние вызовы.
- Time to diagnosis, latency по tools/LLM, steps, counts, token usage.
- Частота `inconclusive` и её обоснованность.

В MVP моделирование всех классов с идеальной точностью не обещаем. Нужна **настоящая измеряемая проверка**, не красивый неподтверждённый RCA.

## 14. Observability самого агента

- OpenTelemetry spans: `investigation_run`, LLM call, LangGraph node, MCP tool call, report validation, checkpoint.
- Prometheus: active/queued/completed/failed runs, duration, tool errors/latency, timeouts, token input/output при наличии точных счетчиков.
- Traces в Tempo и дашборды Grafana; история продукта и agent events — в PostgreSQL.
- Не вводить LangSmith как обязательную зависимость.
- Trace/correlation IDs сквозные между RabbitMQ, Backend, MCP и AI.

## 15. Разделение MVP и второго этапа

**MVP:** end-to-end ReAct, MCP Client, PostgreSQL checkpoints, budgets, 2 стартовых инструмента Logs/Metrics с реальными источниками; затем Tempo/GitHub/Docker; hypotheses/evidence/RCA; cancellation/retry; telemetry/eval; стабильность.

**Этап 2:** Qdrant RAG по документации, Incident Memory по прошлым RCA с проектной изоляцией, контекстный чат после расследования **без новых Tool Calls**, расширение набора tools и качество обработки контекста. Прошлый похожий инцидент — ориентир, но не доказательство актуальной первопричины.

## 16. Очередность реализации

1. Dockerized AI Worker, подключение RabbitMQ, health, env конфигурация, link к llama-server на host macOS.
2. Проверка Qwen2.5-Coder-7B-Instruct: tool calling/JSON/latency/память в измеримых мини-тестах.
3. LangGraph state/checkpointer, bounded ReAct loop, limits и no-data completion.
4. MCP Client + **mock** `search_logs`/`query_prometheus` → реальные инструменты Backend.
5. Hypothesis/Evidence manager, report schema, result submission/events, cancel/retry.
6. Трассировки, тестовые поломки, fallback/error paths, regression harness.
7. По готовности — RAG/Incident Memory и дополнительные возможности.

## 17. Критерии приёмки

- [ ] AI Worker получает задание, запускает ReAct и фиксирует уникальный run ID.
- [ ] MCP Client вызывает Backend Server по Streamable HTTP из другого контейнера.
- [ ] Реальные logs/metrics обрабатываются, результаты ограничены и хранятся как проверяемые Evidence.
- [ ] Агент не вызывает запрещённых инструментов, соблюдает максимум шагов/calls/времени.
- [ ] После crash есть корректная стратегия restore/checkpoint без опасных дублей.
- [ ] LLM создаёт валидный structured RCA; при отсутствии данных даёт `inconclusive`, не выдумывает факт.
- [ ] На Frontend через Backend видны tool events/progress, evidence и гипотезы.
- [ ] Cancel и Retry работают, предыдущий run не теряется.
- [ ] Шесть утверждённых faults проходят измеряемую end-to-end оценку, есть тесты регрессии.
- [ ] Работает наблюдаемость самого AI без обязательного LangSmith.

## 18. Что надо согласовать с Backend отдельно

**Contract-First:** модель задания RabbitMQ и cancel, identity/context API, MCP tool schemas и common error envelope, доставка событий/результатов в Backend, RCA/Hypotheses/Evidence schemas, статусные enum, retry/idempotency/recovery, auth AI Worker, env/endpoint URLs. Не выдумывать «окончательные» поля без согласования с Юрием. До реального Backend AI должен уметь работать с mock MCP и mock Incident Context.
