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

## Проверка локальной Qwen

Запустите `llama-server` отдельно. Затем выполните проверку реального ответа
модели через одноузловой граф LangGraph:

```sh
uv run python scripts/smoke_llm.py
AI_AGENT_RUN_LIVE_LLM=1 uv run pytest tests/integration/test_llm_live.py -q
```

Скрипт сначала проверяет `/v1/models`, затем отправляет описание тестового
инцидента через граф и печатает ответ модели. Он **не** запрашивает реальные логи
или метрики и не выполняет диагностические инструменты. Live-тест запускается
только явно; обычный `uv run pytest` пропускает его. Этот граф — проверка
интеграции LLM, а не полноценное расследование.

## Текущая структура

```text
src/ai_agent/
  api/app.py                  Сборка FastAPI и корреляция запросов
  api/routes/health.py        Технический маршрут /health
  core/config.py              Настройки из переменных окружения
  core/logging.py             Структурированные JSON-логи
  agent/state.py              Состояния графов
  agent/graph.py              Каркас расследования и одноузловой LLM-граф
  application/services/       Вызов тестового графа вне HTTP-слоя
  llm/types.py                Типы сообщений, ответа и граница провайдера
  llm/providers/llama_cpp.py  Асинхронный HTTP-адаптер llama.cpp
tests/unit/                  Тесты настроек, графа и адаптера с fake/mock
tests/integration/           Проверка /health и отдельный live-тест LLM
scripts/smoke_llm.py          Явная проверка модели через LangGraph
```

В графе расследования пока нет диагностических узлов и вызовов инструментов.
Одноузловой LLM-граф выполняет только генерацию текста. После согласования
контрактов узлы расследования будут размещены в `agent/nodes`, а оркестрация —
в `application`. MCP Streamable HTTP Client и возможный MCP Server относятся к
отдельным протокольным границам и не являются маршрутами внутреннего FastAPI API.
PostgreSQL checkpoints и схема хранения пока не реализованы.

Открытые решения: REST или gRPC между Main Backend и AI Backend, владелец MCP
Server, политика при занятом исполнителе, восстановление результата, межсервисная
авторизация и владение хранилищем checkpoints. Текущий `/health` — техническая
проверка доступности, а не черновой `/internal/v1/health` из REST-кандидата.
