# AI Incident Investigator — AI Backend

Каркас самостоятельного AI Backend на Python 3.14. Основной Backend владеет
пользователями, проектами и инцидентами; этот сервис в дальнейшем будет выполнять
расследования с одним агентом на LangGraph. Контракты API и диагностических
инструментов пока имеют статус **v0.2-draft**, а не утверждённого production API.

## Документация проекта

Начните с [карты документации](docs/00_START_HERE.md), затем прочитайте
[границы AI Backend](docs/02_AI_SCOPE_AND_ARCHITECTURE.md) и
[принятые решения и конфликты](docs/04_DECISIONS_AND_CONFLICTS.md).
[План задач](docs/tasks/README.md) задаёт порядок дальнейшей разработки и
интеграционные барьеры G01–G03. В [пакете контрактов](docs/contracts/00_README.md)
находятся черновые JSON Schema, варианты OpenAPI и gRPC, каталог MCP-инструментов
и примеры. [Старые спецификации](docs/references/README.md) сохранены для
контекста, но требование RabbitMQ между Main Backend и AI Backend отменено.
Инструкции для работы с репозиторием — в [AGENTS.md](AGENTS.md).

## Локальный запуск

Установите [uv](https://docs.astral.sh/uv/) и Python 3.14, затем выполните:

```sh
uv sync
uv run uvicorn ai_agent.api.app:app --host 127.0.0.1 --port 8000
```

`GET http://127.0.0.1:8000/health` возвращает `{"status":"ok"}` и заголовок
`X-Request-ID`. Корректный ID из запроса сохраняется, иначе создаётся новый.
Для запуска FastAPI и проверки `/health` работающий `llama-server` не нужен.

Проверки качества:

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Для локальной настройки можно скопировать `.env.example` в `.env`.
`AI_AGENT_LLM_BASE_URL`, `AI_AGENT_LLM_MODEL` и `AI_AGENT_LLM_TIMEOUT_SECONDS`
задают адрес OpenAI-compatible API llama.cpp, ID модели и общий таймаут запроса.
Дополнительно доступны `AI_AGENT_LLM_CONNECT_TIMEOUT_SECONDS`,
`AI_AGENT_LLM_MAX_TOKENS` и `AI_AGENT_LLM_TEMPERATURE`. ID модели должен
совпадать с ответом вашего сервера на `/v1/models`; модель и `llama-server`
запускаются отдельно от этого репозитория. `AI_AGENT_LOG_LEVEL` управляет
уровнем структурированных JSON-логов.

## MCP Client (AI-05)

Для подключения к согласованному MCP endpoint задайте `AI_AGENT_MCP_URL`.
Опциональный `AI_AGENT_MCP_TOKEN` передаётся как Bearer token; значение хранится
в окружении/секретах. Таймауты и максимальный размер результата задают
`AI_AGENT_MCP_CONNECT_TIMEOUT_SECONDS`, `AI_AGENT_MCP_CALL_TIMEOUT_SECONDS` и
`AI_AGENT_MCP_MAX_RESULT_BYTES`.

`connect_mcp(settings)` открывает и закрывает native Streamable HTTP сессию
MCP SDK. `discover()` сверяет имена tools с read-only MVP-каталогом, а `call()`
допускает только обнаруженные разрешённые tools. Native `isError` обрабатывается
отдельно от application-level `status: error`. Автоматических повторов вызова
нет. Проверка scope и специфичных аргументов каждого инструмента — AI-06.

Локальная проверка без реальных диагностических источников:

```sh
uv run pytest tests/unit/test_mcp_client.py tests/integration/test_mcp_streamable_http.py -q
```

Интеграционный тест поднимает временный MCP Server с fake tools. Подробности —
в [отчёте AI-05](docs/tasks/AI-05_RESULT.md).

## Проверка локальной Qwen

Запустите `llama-server` отдельно. Затем выполните проверку реального ответа
модели через одноузловой граф LangGraph:

```sh
uv run python scripts/smoke_llm.py
AI_AGENT_RUN_LIVE_LLM=1 uv run pytest tests/integration/llm/test_llm_live.py -q
```

Скрипт сначала проверяет `/v1/models`, затем отправляет описание тестового
инцидента через граф и печатает ответ модели. Он **не** запрашивает реальные логи
или метрики и не выполняет диагностические инструменты. Live-тест запускается
только явно; обычный `uv run pytest` пропускает его. Этот граф — проверка
интеграции LLM, а не полноценное расследование.

Для отдельной проверки native tool calling на двух фиктивных read-only
инструментах запустите сервер с `--jinja`, затем:

```sh
uv run python scripts/smoke_tool_calling.py --repetitions 3
```

Smoke печатает форму ответа и число успешных структурированных вызовов;
код выхода `1` означает, что проверка не прошла. Текстовый JSON в
`message.content` никогда не исполняется как вызов инструмента. Результаты
для проверенной сборки Qwen/llama.cpp и ограничения приведены в
[отчёте AI-02](docs/tasks/AI-02_RESULT.md).

## Текущая структура

```text
src/ai_agent/
  api/app.py                  Сборка FastAPI и корреляция запросов
  api/routes/health.py        Технический маршрут /health
  core/config.py              Настройки из переменных окружения
  core/logging.py             Структурированные JSON-логи
  agent/state.py              Состояния графов и наблюдений
  agent/decisions.py          Типизированные решения и порты fake-адаптеров
  agent/graph.py              Управляемый цикл расследования и LLM probe
  domain/models.py            Типы расследования, Evidence, Hypothesis и RCA
  domain/lifecycle.py         Допустимые переходы статусов и правило Retry
  application/contracts.py    DTO для v0.2-draft без выбора REST/gRPC
  application/mappers.py      Преобразование Start DTO ↔ состояние графа
  application/services/       Вызов тестового графа вне HTTP-слоя
  llm/types.py                Типы сообщений, ответа и граница провайдера
  llm/providers/llama_cpp.py  Асинхронный HTTP-адаптер llama.cpp
  llm/tool_calling.py         Проверка native tool calls по схемам
  mcp/client.py               Streamable HTTP клиент и typed tool results
tests/unit/agent/            Переходы и ограничения агентного графа
tests/unit/application/      Преобразование DTO в состояние графа
tests/unit/domain/           Правила жизненного цикла расследования
tests/unit/llm/              LLM-адаптер и проверка tool calls
tests/unit/core/             Настройки и логирование
tests/contract/              Проверка DTO по схемам и доменным инвариантам
tests/integration/api/       Проверка HTTP /health
tests/integration/llm/       Отдельный live-тест LLM
scripts/smoke_llm.py          Явная проверка модели через LangGraph
scripts/smoke_tool_calling.py Проверка native tool calling на fake tools
```

Новые DTO описывают draft-контракт, но не создают HTTP-маршруты или доставку
событий. [Результат AI-03](docs/tasks/AI-03_RESULT.md) фиксирует расхождения
между JSON Schema и дополнительными доменными правилами.

Граф расследования принимает типизированный `ActionDecision` или
`FinishDecision` через внедряемый `DecisionProvider`. Перед вызовом
`ToolExecutor` он проверяет имя, схему аргументов и scope, затем сохраняет
короткое наблюдение и снова запрашивает решение. Например:
`ingest → decide(search_logs) → validate_action → execute → normalize(ok)
→ decide(finish) → ready_for_finalization`. Это **офлайн-цикл с fake-портами**;
он не переводит расследование в `completed` и не формирует RCA. `inconclusive`
используется при невалидных решениях, повторе или достижении лимита шагов.
`InvestigationState.context` и `budget` соответствуют моделям AI-03;
`observations` — внутреннее состояние, а `evidence` пока пустое до AI-07.
Текстовый JSON из Qwen не интерпретируется как действие. Одноузловой LLM probe
по-прежнему только генерирует текст. Подробности — в
[отчёте AI-04](docs/tasks/AI-04_RESULT.md).

MCP Client реализован как отдельная транспортная граница и пока не подключён
к графу расследования. Размещение продуктового MCP Server остаётся открытым
решением и не является маршрутом внутреннего FastAPI API.
PostgreSQL checkpoints и схема хранения пока не реализованы.

Открытые решения: REST или gRPC между Main Backend и AI Backend, владелец MCP
Server, политика при занятом исполнителе, восстановление результата, межсервисная
авторизация и владение хранилищем checkpoints. Текущий `/health` — техническая
проверка доступности, а не черновой `/internal/v1/health` из REST-кандидата.
