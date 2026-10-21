# 06. MCP Tool Contracts — агентный интерфейс

**Транспорт:** MCP Streamable HTTP; **потребитель:** AI LangGraph/MCP Client; **размещение MCP Server:** на согласовании (не считать владельцем автоматически ни Юрия, ни Олега).

Машинный каталог: [`mcp/tool-catalog.json`](mcp/tool-catalog.json) — **все имена и `inputSchema`**. API `/internal/v1/investigations` не является MCP Tool.

## 1. MVP каталог (14 инструментов)

| Инструмент | Источник | Что возвращает |
|---|---|---|
| `search_logs` | Elasticsearch | структурированные error/log excerpts, Kibana URLs, IDs |
| `query_prometheus` | Prometheus | series, labels, time range, Grafana link |
| `get_trace` | Tempo | trace/span summary, service relationships, Tempo link |
| `get_service_health` | Metrics / configured health | service health, error rate, p95 |
| `get_container_status` | Docker safe adapter | status, restarts, oom, resource limits |
| `get_container_events` | Docker safe adapter | restart/oom/stop events |
| `get_recent_deployments` | Backend deployment registry | version, sha, time, status, source URL |
| `github_search_code` | GitHub | matches with repo, path, line, commit URL |
| `github_get_file` | GitHub | bounded file content with repo/ref provenance |
| `github_get_commit` | GitHub | commit details and changed files |
| `github_compare_commits` | GitHub | diff metadata, bounded patch hunks |
| `github_get_blame` | GitHub | line-level history where supported |
| `http_health_check` | allowlisted endpoint | safe GET/HEAD response/timing |
| `get_incident_context` | Main Backend | normalized Incident, services, surrounding deployments |

**P2:** `search_docs` (Qdrant docs RAG), `search_similar_incidents` (Incident Memory; links to PostgreSQL entities).

## 2. Общий MCP tool result (проект)

```json
{
  "status": "ok",
  "summary": "124 DB pool timeout errors found",
  "source_refs": [
    {"source_type":"elasticsearch","source_id":"log-b3c9","url":"https://kibana.example/app/discover#/..."}
  ],
  "items": [{"timestamp":"2026-10-19T14:35:00Z","message":"Connection acquire timeout"}],
  "truncated": false,
  "error": null
}
```

`status: ok|empty|partial|error`. `source_refs` — provenance, `items` — bounded sanitized records, `truncated` — true если применён лимит; `error`: `{code,message}` или `null`. **Это application-level result inside MCP tool content**, а не замена нативному MCP `isError` и JSON-RPC error envelope.

Для каждого инструмента фактический `items` должен пройти отдельную typed output schema (пока TBD на v0.2). MCP error handling должен различать `permission_denied`, `source_unavailable`, `timeout`, `rate_limited`, `invalid_query`, `out_of_scope`, `truncated`, `internal_error`.

## 3. Принцип ограничения источников

- **Scope обязателен:** `project_id`/`environment_id`, где подходит. MCP Server **не доверяет**, что agent сам выбрал разрешённый scope: авторизует его по `investigation_id` и identity токена.
- **Не выполнять произвольный SQL**, shell команды, произвольные Docker exec, restart, git write, PR, CI logs/test runners, config change, rollback.
- **Elasticsearch:** агенту разрешено задавать query в верифицированной форме. Произвольный DSL только через bounded adapter с enforceable allowlist/limits, а не сырая пересылка без проверки.
- **PromQL:** query parse/validate, project scoping, timeout, max samples/series, запрещён обход namespace/project labels.
- **HTTP health:** только предварительно зарегистрированный `service.health_url`, allowlist DNS/IP and scheme; блокировать private/meta IP SSRF обход (localhost/network metadata), redirects и DNS rebinding по правилам среды.
- **GitHub:** только allowlisted репозитории проекта; read-only API credential, ограничение файлов и размера diff; secret scanning и redaction.
- **Docker:** отдельный узкий диагностический read-only adapter; **не выдавать agent container напрямую Docker socket**.
- **URLs:** формировать подтверждённые source deep-links; не принимать произвольные JavaScript/data URLs и секреты в query string.
- **Audit:** tool name, bounded input, duration, status, trace_id, error code, identifiers; без приватных ключей и PII.

## 4. MCP transport и управление

`POST/GET/DELETE /mcp` — **типовые** методы Streamable HTTP согласно используемому SDK/версии MCP. Не подменять их собственным FastAPI `POST /mcp/tool_name`. Клиент делает capabilities discovery и `tools/list`, вызывает `tools/call`; input schemas берёт из native tool descriptors.

Параметры сервера: MCP base URL конфигурацией, auth per service, connection timeout, call deadline, bounded result, retry только идемпотентных read-only операций. MCP Server не обязан быть одним процессом с Main Backend.

## 5. Пример диагностики

1. `get_incident_context` → сервис и окно времени.
2. `query_prometheus` → рост ошибок и насыщение PostgreSQL pool.
3. `search_logs` → pool timeout и correlation IDs.
4. `get_trace` → зависание acquiring connection в критическом пути.
5. `get_recent_deployments` + `github_compare_commits` → возможная причинная связь.
6. Agent создаёт до трёх гипотез, привязывает реальные `Evidence.source_refs`, записывает timeline с честным `causality`.

Нет hardcoded порядков: ReAct выбирает инструменты самостоятельно в рамках budget.

## 6. Typed output schemas

Кроме input schemas каждый из **16 инструментов** в `mcp/tool-catalog.json` теперь содержит **свой `outputSchema`** (специализированный `items`, единый status/summary/source_refs/truncated/error). Их также можно валидировать через `schemas/mcp-results.schema.json`, где находятся `$defs.search_logs_Output` и аналоги. Семантика полей — кандидат до API review с разработчиками источников.
