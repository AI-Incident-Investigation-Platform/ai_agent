# AI-06. Safe tool wrappers, scope и нормализация результатов

**Приоритет:** P0  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-03, AI-05; интеграция с AI-04 после готовности  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/contracts/06_MCP_CONTRACTS.md`, `mcp/tool-catalog.json`, `schemas/mcp-results.schema.json`, `08_SECURITY_AND_ERRORS.md`

## Зачем и что должно получиться

Обеспечить **защищённую границу** между решением LLM и диагностическими источниками: валидировать инструмент, аргументы, проектный scope, лимиты и вывод. Возвращать агенту структурированные наблюдения с реальными source refs.

## Объём работы

1. Typed wrappers для MVP catalog; начать с вертикали `get_incident_context`, `search_logs`, `query_prometheus`, `get_trace`, потом расширять по утверждённому каталогу.
2. Input JSON schema / Pydantic validation до вызова; `project_id/environment_id`, time window, max hits/samples, allowed repo/target.
3. Normalize `ok|empty|partial|error` + `truncated`, native MCP errors, `isError`; не терять error code или provenance.
4. Restrict dangerous capabilities: нет arbitrary SQL, shell, docker exec/restart, git write, arbitrary HTTP URLs; authorization enforced execution-side/MCP server-side.
5. Redact secrets/PII and sanitize tool text before feeding model/events. Текст log/README/issue **не** является system instruction.
6. Лимит размера payload и безопасных ссылок. Встроить fake sandbox tool results для live graph integration.
7. Scope server-side — обязательная проверка будущего MCP Server owner; клиентская валидация — дополнительный слой, не замена.

## Не входит

Написание Elasticsearch/Prometheus production-адаптеров на стороне источников до решения ownership; внешний MCP Server deployment; write-actions.

## Acceptance Criteria

1. Unknown/unsafe tool не вызывает transport.
2. Out-of-scope input отклоняется до tool call.
3. Partial/error/truncated честно передаются в state.
4. Source references не создаются из воздуха.
5. Вредоносные tool contents не становятся инструкциями.
6. Минимальная диагностическая вертикаль работает на fake MCP.

## Проверки и негативные сценарии

Negative: prompt injection в логе, секрет в stacktrace, outbound URL SSRF, project ID mismatch, huge log payload, unknown tool, invalid PromQL scope, native `isError`, disconnection.

## Результат передачи / выходной контракт

Secure tool execution interface для Agent Graph и задокументированные требования к реализации MCP Server (для согласуемого владельца).

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
