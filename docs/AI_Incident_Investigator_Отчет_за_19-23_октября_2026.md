# AI Incident Investigator — отчёт о работе за 19–23 октября 2026 года

**Период:** 19–23 октября 2026 г.  
**Проект:** AI Incident Investigator — платформа автоматизированного расследования инцидентов в микросервисных системах  
**Организация GitHub:** https://github.com/AI-Incident-Investigation-Platform  
**Фокус отчёта:** кратко Frontend, подробно AI Backend, инфраструктура и обоснование технологического стека.

> **Правило интерпретации статусов.** В отчёте различаются: **реализовано и зафиксировано в GitHub**, **проверено локально по отчёту разработчика/Codex**, **подготовлено в документации**, **выбрано как архитектурный принцип** и **не утверждено / запланировано**. Наличие Story или архитектурной схемы не означает, что функция реализована. Проверка проводилась по содержимому публичных репозиториев организации и материалам нашего обсуждения на 23 октября 2026 года.

---

## 1. Краткие итоги пяти дней

За последние дни мы вывели проект из стадии обсуждения архитектуры к воспроизводимому началу разработки. Для **Frontend** подготовлены отдельный набор задач, последовательность выполнения и правила визуального качества; в репозитории есть стартовый React-каркас. Для **AI Backend** зафиксированы границы ответственности, документация и контракты, создана структура проекта, реализован первый реальный сквозной вызов `LangGraph → llama.cpp → Qwen2.5-Coder-7B`, подготовлен большой план продолжения разработки в Codex. Параллельно уточнили технологическую инфраструктуру, исходя из фактического содержимого отдельного репозитория `infra`.

| Направление | Что реально имеется | Что пока не готово |
|---|---|---|
| Frontend | React + TypeScript + Vite, маршрутизация/тестовый каркас, документация с 8 UI-задачами | Девять полноценных продуктовых экранов и интеграция с Main Backend |
| AI Backend | FastAPI-каркас, конфигурация, логирование, провайдер llama.cpp, минимальный LangGraph и live smoke | Реальный ReAct-цикл, MCP Client, Evidence/RCA, долговременные runs, интеграция Main Backend |
| Контракты | Handoff, API/MCP JSON-схемы и кандидаты OpenAPI/gRPC `v0.2-draft` | Финализация транспорта и ряда межсервисных решений |
| Инфраструктура | В репозитории `infra` описан k3d/Kubernetes-стенд, БД и observability-стек | Подтверждение полной совместной работоспособности всех сервисов на конкретной машине |
| Процесс | Реестр AI-01…AI-18, G01/G02/G03; отдельный Frontend task pack | Последовательная реализация и прохождение всех gates |

## 2. Frontend — кратко

**Репозиторий:** https://github.com/AI-Incident-Investigation-Platform/frontend

1. Взяли за основу **Figma B / Product screens**: https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-2. В макетах — девять основных экранов: Overview, Incidents, Live Investigations, Service Map, Logs & Metrics, Traces, Integrations, Settings и Incident Detail.
2. Подготовили пакет из **8 задач FE-01…FE-08**: дизайн-система и каркас; Overview; реестр инцидентов; экран расследования и RCA; активность AI; три observability-экрана; интеграции и настройки; Login + email OTP.
3. Для каждой задачи описали состав экрана, взаимодействия, mock-данные, состояния `loading / empty / error`, критерии приёмки и ссылки на Figma. В `README.md` и `EXECUTION_SCHEME.md` определили порядок выполнения и зависимости.
4. Добавили **Anti-AI-slop Design Directive**: строгая SRE/DevOps-консоль вместо типового «AI SaaS»; никаких случайных градиентов, сияний, гигантских карточек, декоративных графиков и вымышленных данных. Критерий — полезная информационная плотность и воспроизведение Figma.
5. По текущему содержимому GitHub уже есть **React + TypeScript + Vite**, `React Router`, стартовая страница и файлы тестов/конфигурации. Пакет задач находится в `frontend/docs/tasks/`. Это **фундамент**, а не завершённая вёрстка всех экранов.
6. Frontend будет общаться **только с Main Backend** через REST и WebSocket; прямой доступ браузера к AI Backend не предполагается.

**Ближайший результат фронтендера:** последовательность **FE-01 → FE-02 → FE-03 → FE-04** должна дать рабочий дизайн-каркас, дашборд, реестр инцидентов и детальную страницу расследования с едиными mock-данными. Реальная интеграция с Backend — после согласования контрактов и готовности API.

---

## 3. AI Backend — что мы спроектировали

**Репозиторий:** https://github.com/AI-Incident-Investigation-Platform/ai_agent  
**Рабочая ветка на дату проверки:** `chore/ai-backend-bootstrap` (не следует автоматически считать изменения слитыми в `main`).

### 3.1. Разделили роли компонентов

```text
Frontend (React)
    │ REST / WebSocket
    ▼
Main Backend (FastAPI; владельцы пользователей, проектов, инцидентов, ревью)
    │ прямой internal API: REST или gRPC — ВЫБОР НЕ ЗАФИКСИРОВАН
    ▼
AI Backend (наш Python/FastAPI-сервис)
    ├── Application: запуск, статус, отмена, лимиты, доставка результатов
    ├── LangGraph: один управляемый ReAct-агент
    │     └── LLM Provider → llama-server → Qwen2.5-Coder-7B-Instruct
    ├── MCP Client → MCP Server (владелец/размещение пока TBD)
    │     └── read-only диагностика: логи, метрики, трейсы, Git, deploy, health
    ├── PostgreSQL: будущие checkpoints и durable execution registry
    └── Observability: структурированные логи, события, метрики/трейсинг
```

**Почему отдельный AI Backend:** основной Backend не должен управлять промптами, состоянием графа и низкоуровневыми диагностическими tool calls. Он владеет пользователями, инцидентами, сохранением результатов и WebSocket-отправкой фронту. AI-сервис отвечает за ограниченное, наблюдаемое и проверяемое расследование.

**Почему не стали использовать RabbitMQ между Main Backend и AI Backend:** принято прямое межсервисное взаимодействие; для продолжительных расследований надёжность обеспечивается устойчивой регистрацией запуска, checkpoints и восстановлением исполнения, а не наличием брокера «по умолчанию». При этом конкретная схема durable executor и доставка callback-событий ещё **не реализованы и требуют согласования**. RabbitMQ может присутствовать в *демонстрационной e-commerce системе* как объект диагностики; это другое назначение.

### 3.2. Выбрали подход к агенту

- **LangGraph и один ReAct-агент**, без преждевременного перехода к CrewAI/AutoGen/multi-agent.
- Реальные данные об инциденте приходят через **MCP-инструменты только для чтения**. Агент сам выбирает необходимое действие, а runtime проверяет его допустимость.
- Целевое завершение: до **трёх гипотез**, подтверждения **Evidence**, timeline и **RCA Report**; при недостатке подтверждений — `inconclusive`, а не выдуманная причина.
- Ограничения по плану: **до 20 шагов, до 40 вызовов инструментов и до 1200 секунд**; на MVP — **одно активное расследование на executor**. Эти ограничения должны реализовываться кодом, не только промптом.
- Отмена кооперативная, повторный запуск создаёт **новый investigation_id**. Никакого автоматического исправления production, перезапуска контейнеров, выполнения shell-команд и других небезопасных действий.
- Ответ агента не заменяет решение человека: закрытие инцидента и одобрение RCA остаются за Main Backend и пользователем.

**Почему LangGraph:** явное состояние и переходы между узлами, управляемость лимитов, возможность checkpointing, тестирование разных путей исполнения и восстановление после сбоя. Для расследования с несколькими инструментами и длительной работой это важнее «свободного» циклического вызова LLM.

### 3.3. Зафиксировали архитектурные документы и контракты

В `ai_agent` находится пакет проектного контекста:

- `AGENTS.md` — постоянные инструкции и границы действий Codex;
- `docs/00_START_HERE.md` — карта документации;
- `docs/01_PROJECT_BRIEF.md` — задачи продукта и роли;
- `docs/02_AI_SCOPE_AND_ARCHITECTURE.md` — архитектура и взаимодействие сервисов;
- `docs/03_AI_DELIVERY_PLAN.md` — реалистичная последовательность разработки;
- `docs/04_DECISIONS_AND_CONFLICTS.md` — принятые/отменённые/открытые решения;
- `docs/contracts/` — схемы, примеры, MCP catalog, варианты OpenAPI/gRPC;
- `docs/references/` — исторические и сопутствующие материалы.

**Статус контрактов — `v0.2-draft`.** Это база для проектирования и тестирования DTO, но не утверждённый production v1. В старых материалах сохранились устаревшие идеи (RabbitMQ между Backend и AI, обязательное владение MCP-сервером основным Backend); актуальные решения имеют приоритет.

### 3.4. Создали базовый проект на Python/FastAPI

В ветке `chore/ai-backend-bootstrap` уже есть:

- `src/ai_agent/api/app.py` и health route;
- `src/ai_agent/core/config.py` с настройками через **Pydantic Settings**;
- `src/ai_agent/core/logging.py` со структурированными JSON-логами и request correlation;
- `src/ai_agent/llm/` и асинхронный HTTP `LlamaCppProvider`;
- `src/ai_agent/agent/` — состояния и графы LangGraph;
- `src/ai_agent/application/` — вызов workflow вне HTTP-роутов;
- `tests/unit/`, `tests/integration/`, `scripts/smoke_llm.py`;
- `pyproject.toml`, `uv.lock`, `.env.example`, README.

Текущий `pyproject.toml` требует **Python >=3.14**; ранее обсуждалась версия 3.12. Важно не менять Python автоматически: перед установкой ML-библиотек с бинарными зависимостями проверить совместимость.

**Почему FastAPI:** единый с командой Python-стек, асинхронный HTTP для внутренних сервисных вызовов, типизированные схемы и независимый от транспорта прикладной слой. FastAPI здесь выступает **обёрткой AI-сервиса**, а не движком самого агента.

### 3.5. Выбрали и запустили локальную LLM

**Выбранный кандидат:** `Qwen2.5-Coder-7B-Instruct`, GGUF с квантованием **Q4_K_M**, запуск через **llama.cpp / llama-server** и ускорение на Apple Metal.

**Почему:** достаточно компактная для локальной проверки на Mac модель с хорошей ориентацией на код и технические тексты; OpenAI-compatible HTTP API упрощает подключение Python-сервиса. Не требуется внешний платный inference API. Мы сознательно **не используем Ollama**: прямой llama.cpp даёт более прозрачную конфигурацию inference и API.

Локально проверили последовательность:

1. `llama-server` поднят на `127.0.0.1:8080`;
2. `/v1/models` отвечает;
3. `/v1/chat/completions` принимает тестовое сообщение и возвращает ответ;
4. в `.env` задаются `AI_AGENT_LLM_BASE_URL`, `AI_AGENT_LLM_MODEL` и таймаут;
5. затем проверили **вызов модели из настоящего LangGraph workflow**.

Важно: успешный HTTP-ответ LLM сам по себе **не означает работающий агент**, tool calling или корректное RCA.

### 3.6. Выполнили Story AI-01: LangGraph ↔ llama.cpp ↔ Qwen

Согласно коду и опубликованному в репозитории отчёту `docs/WORK_REPORT_2026-10-22_2026-10-23.md`, AI-01 реализована в коммите `9f02f894246d5d6d2a8d1a8a6feade932543e9c5` с сообщением `feat(llm): integrate llama.cpp with LangGraph`.

**Что добавлено:**

- асинхронный `LlamaCppProvider` с обработкой сетевых и HTTP-ошибок, timeout, malformed/truncated response и проверкой структуры ответа;
- поддержку сообщений `system/user/assistant`, настройки `base_url`, model ID, timeout, temperature и ограничений выдачи;
- возможность подменить HTTP-клиент и провайдер для unit-тестирования;
- **минимальный граф `START → call_model → END`**, который вызывает настоящую Qwen;
- application-сервис для вызова графа вне FastAPI;
- `scripts/smoke_llm.py` для живого ручного теста;
- отдельный opt-in интеграционный тест с реальным llama-server;
- тесты негативных сценариев, README и env-пример.

**По отчёту об испытаниях от 22 октября:**

| Проверка | Зафиксированный результат |
|---|---|
| `uv sync` | Успешно (68 packages resolved, 65 checked) |
| `uv run pytest` | **23 passed, 1 skipped** (живой тест по умолчанию пропускается) |
| `uv run ruff check .` | Успешно |
| `uv run ruff format --check .` | Успешно |
| `uv run python scripts/smoke_llm.py` | Успешно: реальная Qwen отвечала через LangGraph |
| `AI_AGENT_RUN_LIVE_LLM=1 uv run pytest tests/integration/test_llm_live.py -q` | **1 passed** |
| Недоступный llama-server / порт `127.0.0.1:9` | Контролируемая ошибка подключения |

Эти значения **взяты из сохранённого отчёта Codex**, а не получены повторным запуском тестов при составлении этого документа. Коммит AI-01 виден в репозитории; **merge в main не подтверждён**.

**Критически важный результат:** одношаговый LangGraph + LLM действительно работает. При этом попытка native tool calling пока **не подтвердила устойчивый структурированный `tool_calls`**: в тесте сервер выдавал вызов инструмента как текстовый JSON. Это проблема совместимости формата/шаблона/настроек, которую нужно исследовать в AI-02. Не следует выдавать такое поведение за настоящий function calling.

### 3.7. Подготовили весь план разработки AI Backend для Codex

Создан каталог `docs/tasks/` с **18 Stories AI-01…AI-18**, контрольными точками **G01, G02, G03** и отдельными документами `README.md`, `EXECUTION_SCHEME.md`, `QUALITY_GATE.md`, `DECISIONS_TO_APPROVE.md`, `CODEX_RUNBOOK.md`.

Основная цепочка:

```text
AI-01  LLM + LangGraph                                [реализован первый срез]
  ↓
AI-02  Native tool calling spike
AI-03  Domain models / schemas / contract tests
  ↓
AI-04  Контролируемый агентный граф
AI-05  MCP Streamable HTTP client
AI-06  Tool validation / read-only security
AI-07  Evidence + hypotheses
AI-08  RCA / timeline / finalization
AI-09  Budgets / cancellation / failures
  ↓
G01    Локальное E2E-расследование — ОБЯЗАТЕЛЬНЫЙ БАРЬЕР
  ↓
AI-10  PostgreSQL checkpoints
AI-11  Durable run executor / восстановление
AI-12  Progress/events/results delivery
AI-13  Main Backend integration (после transport decision)
AI-14  Наблюдаемость и аудит
  ↓
G02    Проверка durability / интеграции
  ↓
AI-15  Fault scenarios и Evals
AI-18  Release hardening
  ↓
G03    Финальная приёмка MVP

P2 (не блокируют MVP): AI-16 RAG, AI-17 intent router
```

**Два важных уточнения по плану:**

1. **G01 обязателен перед AI-10**, даже если короткая таблица зависимостей в README не перечисляет его. При исполнении приоритет имеет согласованная схема барьеров.
2. `QUALITY_GATE.md` описывает также проверки готового MVP; на ранних Stories его требования применяются **в пределах конкретной задачи**. Отсутствие будущих MCP, checkpoints или RCA не является дефектом AI-01.

**Процесс Codex:** одна небольшая Story → изучение текущего кода и контрактов → короткий план → реализация → unit/integration tests → review → интеграция через GitFlow. Установка BMad Method не требуется: используем методологию декомпозиции и контроля результата, а не отдельный фреймворк.

---

## 4. Инфраструктура: что выбрали, почему и что реально есть

**Репозиторий:** https://github.com/AI-Incident-Investigation-Platform/infra

Нужно различать **ранние обсуждения** и **фактическую инфраструктуру команды**. Ранее мы говорили о Docker Compose, Elasticsearch/Kibana, Prometheus/Grafana и Tempo. При проверке существующего `infra` обнаружилась более конкретная реализация: **k3d (локальный Kubernetes) + Traefik + PostgreSQL + DragonflyDB + SeaweedFS + Loki + Prometheus + Tempo + Grafana + Alloy**.

| Технология | Роль в системе | Почему полезна / выбор |
|---|---|---|
| **k3d / K3s** | Локальный Kubernetes-кластер | Приближает конфигурацию к развертыванию сервисов в Kubernetes; изоляция сервисов, конфигурации, оркестрация. В `cluster.yaml` описан кластер `aiip` с одним server-node и локальными портами 80/443. |
| **Traefik** | Единая HTTP(S) точка входа / ingress | Маршрутизация запросов к сервисам без открытия произвольного порта для каждого из них. |
| **PostgreSQL** | Реляционная БД | Устойчивое хранение бизнес-данных в Main Backend и, по будущему решению об ownership, LangGraph checkpoints/run registry AI Backend. |
| **DragonflyDB** | Совместимое с Redis API in-memory хранилище/кэш | Низкая задержка для кэширования и вспомогательных задач; **не означает**, что согласован Redis-queue между Main Backend и AI. |
| **SeaweedFS** | S3-совместимое объектное хранилище | Файлы/артефакты и крупные объекты отдельно от реляционной БД. Назначение конкретных бакетов для AI ещё требует определения. |
| **Prometheus** | Метрики | Численные показатели и PromQL-диагностика, в том числе будущий read-only MCP tool. |
| **Loki** | Централизованные логи | Хранение и поиск логов как часть Grafana-стека. **Важно:** в раннем MCP catalog встречается Elasticsearch, а текущая infra использует Loki. Требуется решение по провайдеру/адаптеру, не подмена контракта втихую. |
| **Tempo** | Распределённые трейсы | Исследование цепочек запросов и узких мест по trace/span. |
| **Grafana** | UI для observability | Единая точка просмотра метрик, логов и трассировок. |
| **Alloy** | Сбор/маршрутизация телеметрии | Приём и экспорт сигналов наблюдаемости, включая OTLP. |
| **llama.cpp (на macOS host)** | Локальный inference Qwen | На старте удобнее запускать GGUF вне Kubernetes, с доступом к Apple Metal. Для сервиса в контейнере адрес `127.0.0.1` будет указывать на сам контейнер, а не на Mac: сетевой доступ нужно отдельно настроить. |

**Сравнение с первоначальным планом:** это не означает, что «Elasticsearch заменили Loki по согласованному ADR». Пока мы **наблюдаем расхождение** между старой проектной документацией/макетами и фактической конфигурацией репозитория. Перед AI-05/AI-06 команде необходимо подтвердить используемый источник логов и семантику инструмента `search_logs` (возможный вариант: адаптер, скрывающий от агента конкретный backend поиска).

**Как развертывается инфраструктура в исходниках команды:** `infra/Makefile` имеет цели `make env`, `make up`, `make status`, `make logs`, `make forward`, `make service name=...`, а манифесты находятся в `infra/k8s/`. В составе определены PostgreSQL, DragonflyDB, SeaweedFS и observability-сервисы. Наличие файлов и команд **не доказывает**, что весь кластер уже запущен у нас локально и интегрирован с агентом.

**Почему не следует прямо сейчас переносить llama-server в K8s:** наша уже работающая локальная Qwen использует macOS/Metal. Сначала стоит стабилизировать agent/tool-calling и измерить задержку; инфраструктуру LLM можно вынести позднее по реальной потребности.

---

## 5. Дополнительные модели — обсуждали, но не устанавливали как часть MVP

Мы рассмотрели архитектуру будущего RAG и маршрутизатора запросов, однако **не сделали их обязательными для первого расследования**.

### 5.1. Классификатор/Router

Задача — направлять запросы к фактической диагностике через MCP, к поиску базы знаний RAG или к обоим механизмам. Пример предполагаемых классов: `diagnostics`, `knowledge`, `hybrid`, `unsupported`, `clarification`.

Рассмотрены **fastText** как лёгкий CPU baseline, **multilingual DistilBERT** как кандидат для fine-tuning и **XLM-RoBERTa-base** как более тяжёлый многоязычный вариант. Fine-tuned классификатор нельзя считать готовым без размеченных примеров и теста на наших запросах. Для MVP достаточно простого Router; он не должен блокировать агенту доступ к необходимым источникам.

### 5.2. Embeddings и reranking

- **Qwen3-Embedding-0.6B** — кандидат для первых retrieval-экспериментов;
- **BGE-M3** — альтернативная embedding-модель, интересная для многоязычного и гибридного поиска;
- **GTE multilingual reranker**, **BGE-reranker-v2-m3** и **Qwen3-Reranker-0.6B** — кандидаты на сравнительные тесты reranking;
- **Qdrant** — предлагаемый векторный индекс, **не обязательный инфраструктурный компонент текущего MVP**.

**Принцип:** текущие ошибки, показатели Prometheus и факты из trace нельзя искать в RAG как замену live-инструментам. RAG нужен для runbook, прошлых RCA и внутренних знаний. Модели сравнивать по **качеству поиска на наших данных, времени ответа и потреблению памяти**, а не только по общим бенчмаркам.

---

## 6. Что конкретно остаётся неготовым

На 23 октября **не следует считать реализованными** следующие компоненты:

1. Надёжный native function/tool calling из Qwen через llama.cpp (AI-02 ещё требует spike и проверки формата ответов).
2. Полный stateful ReAct-цикл и typed domain DTO контракты расследования.
3. MCP Streamable HTTP Client и реальные read-only tools для логов, метрик, трейсов, репозитория и deployments.
4. Сбор и строгая проверка Evidence, гипотез и RCA.
5. Лимиты исполнения, отмена и надёжная обработка невалидных LLM/tool responses.
6. PostgreSQL checkpoint saver, устойчивый registry, lease/recovery длительных задач.
7. Подтверждённый REST **либо** gRPC Main Backend ↔ AI и межсервисная аутентификация.
8. Надёжная доставка прогресса и результата в Main Backend, сохранение/реплей событий.
9. Переход всего MVP через G01/G02/G03 с fault scenarios и повторяемыми evals.
10. Дополнительные RAG, классификатор и reranker (фаза P2).

**Открытые архитектурные решения:** транспорт REST/gRPC; владелец и место исполнения MCP Server; Postgres ownership/миграции checkpoints; overload/admission policy; inter-service auth; семантика durable callbacks/result recovery; выбор Elasticsearch против Loki (или поддержка обоих через адаптер).

---

## 7. Рекомендованный следующий порядок работ

### Немедленно — AI-02 + AI-03

1. **AI-02: native tool calling spike.** Проверить, умеют ли текущая сборка llama.cpp и чат-шаблон Qwen выдавать корректный структурированный `tool_calls` по OpenAI-compatible API, а не JSON-текст. Провести позитивные и негативные тесты, зафиксировать результат.
2. **AI-03: domain + contracts.** На основе `docs/contracts/` собрать внутренние модели расследования и контрактные тесты для Evidence, Hypotheses, RCA, статусов и ошибок. Не утверждать спорный transport.
3. После этого — **AI-04, AI-05, AI-06**, то есть граф, MCP Client и security/tool validation.

### Следующий результат — G01

На **G01** показать полное локальное тестовое расследование с **детерминированными fake-инструментами**: агент получает контекст, вызывает tools, собирает настоящие *для этого теста* source IDs, формирует Evidence/гипотезы/RCA или `inconclusive`, не выходит за лимиты. Живую Qwen тестировать отдельно. **G01 обязателен до AI-10.**

### После G01 — durability и команда

Подтвердить owner checkpoint DB и межсервисные решения, реализовать PostgreSQL checkpoints, durable executor, idempotent events/callbacks и один утверждённый transport; затем G02, fault scenarios/evals, release hardening и G03.

### Параллельно без риска для AI кода

- Согласовать с командой **Loki vs Elasticsearch**, владельца MCP Server, транспорт, авторизацию и доступ к Postgres.
- Подготовить **3–6 воспроизводимых e-commerce инцидентов**: pool exhaustion, bad deployment, latency cascade, OOM/restarts, queue consumer lag, outage зависимого сервиса.
- Для каждого сценария сохранить ожидаемую root cause, логи, метрики, трейсы, deployment context и корректные source references; отдельно сценарий с недостаточными доказательствами.
- Не загружать и не держать постоянно дополнительную тяжёлую ML-модель только «на будущее» до появления измеримой задачи RAG.

---

## 8. Основные материалы и ссылки

- **AI Backend:** https://github.com/AI-Incident-Investigation-Platform/ai_agent
- **Рабочая ветка:** https://github.com/AI-Incident-Investigation-Platform/ai_agent/tree/chore/ai-backend-bootstrap
- **AI task plan:** https://github.com/AI-Incident-Investigation-Platform/ai_agent/tree/chore/ai-backend-bootstrap/docs/tasks
- **Отчёт Codex за 22–23 октября:** https://github.com/AI-Incident-Investigation-Platform/ai_agent/blob/chore/ai-backend-bootstrap/docs/WORK_REPORT_2026-10-22_2026-10-23.md
- **AI-01 commit:** https://github.com/AI-Incident-Investigation-Platform/ai_agent/commit/9f02f894246d5d6d2a8d1a8a6feade932543e9c5
- **Frontend:** https://github.com/AI-Incident-Investigation-Platform/frontend
- **Frontend task plan:** https://github.com/AI-Incident-Investigation-Platform/frontend/tree/main/docs/tasks
- **Figma B:** https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-2
- **Infrastructure:** https://github.com/AI-Incident-Investigation-Platform/infra
- **Authentication service:** https://github.com/AI-Incident-Investigation-Platform/auth

## 9. Одним абзацем: общий результат

За пять дней подготовили организационную и архитектурную основу AI Incident Investigator: выделили отдельные репозитории и сервисные зоны ответственности, сформировали задачи фронтенда и AI, зафиксировали будущий API/MCP-контур и ограничения агента, выбрали локальную Qwen2.5-Coder-7B на llama.cpp и проверили её в настоящем одноузловом LangGraph. В GitHub уже присутствуют стартовые React и FastAPI-проекты, документация, тесты и пример живой LLM-интеграции. Для инфраструктуры обнаружен и описан существующий k3d/Kubernetes-стек с PostgreSQL, Traefik, DragonflyDB, SeaweedFS и Grafana Observability. Следующая основная инженерная цель — **надёжный tool calling → MCP Client → доказательное локальное расследование G01**, а после него — durable execution, межсервисная интеграция и финальные E2E/eval-проверки.
