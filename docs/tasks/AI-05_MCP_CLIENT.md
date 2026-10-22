# AI-05. MCP Client для Streamable HTTP

**Приоритет:** P0  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-03 DTO; может идти параллельно AI-04 в отдельной ветке  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/contracts/06_MCP_CONTRACTS.md`, `mcp/tool-catalog.json`, `schemas/mcp-results.schema.json`

## Зачем и что должно получиться

Рабочая инфраструктурная интеграция с **настоящим MCP протоколом**, а не HTTP-ручки инструментов. Создать MCP Client с native `tools/list`, `tools/call`, проверкой capabilities и безопасным lifecycle.

## Объём работы

1. Выделить transport client и typed interface, который будет использовать LangGraph.
2. MCP Streamable HTTP по официальному SDK установленной версии; сервер конфигурируется URL/credentials/timeout, не hardcode.
3. Discovery available tools и сопоставление с allowlisted catalog; unknown tools не попадают в разрешённый набор.
4. `tools/call`: arguments→ SDK → native content/isError → application result normalization; не путать MCP ошибки с `status=error` в содержимом ответа.
5. Bounded connect/call timeouts, graceful close, cancellation propagation и ограниченный retry **только для безопасных идемпотентных запросов**.
6. Поднять изолированный тестовый MCP Server с 1–2 fake tools, не требуя реальных Elasticsearch/GitHub и не утверждая MCP-owner.

## Не входит

Полные реализации 14 реальных источников; собственный JSON-RPC протокол; обязательное владение MCP Server этим repo; произвольные MCP tools модели.

## Acceptance Criteria

1. SDK client подключается к тестовому Streamable HTTP MCP endpoint.
2. Discovery возвращает ожидаемые tools и capabilities.
3. `tools/call` отдаёт нормализованный typed result.
4. Offline unit tests не требуют сети.
5. Session closed/timeout/network errors корректно обрабатываются.
6. Нет неожиданных обращений к неразрешённым tools.

## Проверки и негативные сценарии

Unit с fake MCP transport + integration с локальным тестовым сервером; empty/error/isError/bad protocol response, lost connection/timeout/cancel.

## Результат передачи / выходной контракт

Независимый MCP transport adapter, совместимый с AI-06. Зафиксировать совместимую версию MCP SDK.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
