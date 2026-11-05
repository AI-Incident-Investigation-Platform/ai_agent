# AI-05 — MCP Client для Streamable HTTP

## Реализовано

Ветка `feature/ai-05-mcp-client` создана отдельно от незакоммиченной AI-04 на
базе `origin/dev`. `src/ai_agent/mcp/client.py` открывает native Streamable HTTP
сессию через официальный Python SDK, проверяет `tools` capability, выполняет
постраничный `tools/list` и фильтрует описания по 14 read-only MVP именам из
`docs/contracts/mcp/tool-catalog.json`. `call()` обращается только к
обнаруженному разрешённому имени. Неизвестные и P2 инструменты исключены.

`tools/call` возвращает типизированный application result по общей форме
v0.2-draft. Клиент предпочитает MCP `structuredContent`; один JSON text content
поддерживается как совместимый вариант. Native `isError`, неполный/невалидный
MCP-ответ, неверный application result и превышение размера различаются.
Таймауты подключения/вызова и лимит размера задаются через `Settings`.
Отмена `asyncio` проходит наружу. Сессия и HTTP-клиент закрываются через
async context managers. Автоматических повторов нет.

Совместимость проверена с `mcp==2.3.0` и `httpx2==2.15.1` из `uv.lock`.
Диапазоны зависимостей в `pyproject.toml`: `mcp>=2.3,<3`, `httpx2>=2.15,<3`.
Используется SDK API `Client(streamable_http_client(...))`; собственный JSON-RPC
или продуктовый MCP Server не добавлялись.

## Проверки

- Unit с fake session: allowlist, capabilities, пагинация, успешный,
  empty/partial/error result, native `isError`, битый/крупный ответ,
  timeout, transport error и propagation отмены.
- Integration: локальный тестовый MCP Server с двумя fake tools работает через
  настоящий Streamable HTTP и SDK; `search_logs` вызывается, `write_file`
  блокируется до обращения к серверу; после закрытия сессии вызов отклоняется.
- `uv run pytest -q` — 108 passed, 1 skipped после обновления на AI-04
  (live LLM не запускался).
- `uv run ruff check .` — passed.
- `uv run ruff format --check .` — passed.
- `git diff --check` — passed.

Интеграционный тест — **LOCAL FAKE**, он не проверяет живые Elasticsearch,
Prometheus, GitHub, Qwen или инфраструктурный MCP Server.

## Ограничения и следующие шаги

Местоположение и владелец продуктового MCP Server остаются открытым решением.
Bearer token — опциональная конфигурация клиента, не утверждение межсервисной
схемы авторизации. AI-06 должен проверить аргументы и scope каждого инструмента,
typed `items`, sanitation/redaction, allowlists репозиториев и URL. Клиент не
исполняет произвольные имена, но не может доказать read-only семантику сервера
по одному имени. AI-04 содержит отдельный fake агентный цикл; подключение
реального MCP к нему будет отдельной интеграцией после AI-06.
