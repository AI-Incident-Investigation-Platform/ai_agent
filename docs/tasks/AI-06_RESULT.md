# AI-06 — первая безопасная вертикаль инструментов

**Статус:** реализована минимальная диагностическая вертикаль в рабочей ветке
`feature/ai-06-safe-tools`; полное покрытие MVP-каталога и server-side
авторизация остаются открытыми.

## Реализовано

- `SafeToolExecutor` принимает контекст расследования и MCP transport port.
  Неизвестные инструменты отклоняются до транспорта.
- Pydantic input schemas для `get_incident_context`, `search_logs`,
  `query_prometheus`, `get_trace`. Проверяются UUID scope, список сервисов,
  UTC-окно времени, лимиты выборки и отсутствие лишних аргументов.
- Prometheus допускает только простой metric selector с точными метками
  `project_id` и `environment_id`. Сложные PromQL выражения отклоняются до
  появления server-side parser/validator.
- MCP результат сохраняет status/partial/truncated/error и полученные
  `source_refs`; новых ссылок не создаёт. Сырые элементы ограничены, текст
  очищается от распространённых секретов и email, ссылки с HTTP, credentials
  или query string исключаются. Graph observation не включает `items`.
- Native MCP error превращается в контролируемый `source_unavailable`.

## Проверки

- Unit: unknown tool, чужой project/investigation/service, неверный лимит и
  интервал, неограниченный PromQL, опасный URL, секреты и большой результат.
- Fake integration: один LangGraph action `get_incident_context` вызывает
  fake MCP, возвращает partial/truncated и реальный source ref; сырой текст
  с prompt injection не попадает в graph state.
- `uv run pytest -q` — 121 passed, 1 skipped (live LLM не запускался).
- `uv run ruff check .` — passed.

## Ограничения

Это клиентская дополнительная проверка. MCP Server должен независимо
авторизовать scope по identity и `investigation_id`, ограничивать PromQL/ES,
проверять URL и репозитории, сканировать secrets и ограничивать объём ответа.
Владелец и размещение MCP Server не утверждены. Остальные 10 MVP tools пока
не входят в `SafeToolExecutor` и не могут быть вызваны через него. Никаких
живых Elasticsearch/Prometheus/Tempo вызовов не выполнялось.
