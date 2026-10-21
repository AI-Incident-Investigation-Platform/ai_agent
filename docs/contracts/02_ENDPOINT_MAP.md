# Полная карта эндпоинтов — актуальный черновик v0.1

> Основано на документах проекта и девяти экранах Figma B. **Транспорт Main Backend ↔ AI не утверждён**. OpenAPI AI показывает REST-кандидат, а не принятое решение.

## Main Backend /api/v1 + incoming internal callbacks

| Метод | URL | Назначение | Этап |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Check email/password, create and email OTP challenge. **202; NO JWT** | P0 |
| `POST` | `/api/v1/auth/otp/verify` | Validate one-time email code, **only then issue JWT session** | P0 |
| `POST` | `/api/v1/auth/otp/resend` | Rate-limited resend, invalidating previous code | P0 |
| `POST` | `/api/v1/auth/refresh` | Refresh access token | P0 |
| `POST` | `/api/v1/auth/logout` | Revoke current session | P0 |
| `GET` | `/api/v1/users/me` | Authenticated user and project scopes | P0 |
| `GET` | `/api/v1/users` | List users (Admin) | P1 |
| `POST` | `/api/v1/users` | Invite/create user (Admin) | P1 |
| `GET` | `/api/v1/projects` | List accessible projects | P0 |
| `POST` | `/api/v1/projects` | Create project (Admin) | P0 |
| `GET` | `/api/v1/projects/{project_id}` | Get project | P0 |
| `PATCH` | `/api/v1/projects/{project_id}` | Update project (Admin) | P0 |
| `GET` | `/api/v1/projects/{project_id}/environments` | List environments in project | P0 |
| `POST` | `/api/v1/projects/{project_id}/environments` | Create environment (Admin) | P0 |
| `PATCH` | `/api/v1/environments/{environment_id}` | Update environment (Admin) | P0 |
| `GET` | `/api/v1/projects/{project_id}/services` | List configured services | P0 |
| `POST` | `/api/v1/projects/{project_id}/services` | Register configured service (Admin) | P0 |
| `GET` | `/api/v1/services/{service_id}` | Get service configuration | P0 |
| `PATCH` | `/api/v1/services/{service_id}` | Update service mapping (Admin) | P0 |
| `GET` | `/api/v1/services/{service_id}/health` | Current bounded health summary | P1 |
| `GET` | `/api/v1/projects/{project_id}/topology` | Read-only service dependencies | P1 |
| `GET` | `/api/v1/deployments` | Search deployments | P0 |
| `GET` | `/api/v1/services/{service_id}/deployments` | Deployment history for service | P0 |
| `GET` | `/api/v1/deployments/{deployment_id}` | Deployment detail | P0 |
| `GET` | `/api/v1/incidents` | Search, filter, sort incidents | P0 |
| `POST` | `/api/v1/incidents` | Manually create incident (Developer/Admin) | P0 |
| `GET` | `/api/v1/incidents/{incident_id}` | Incident detail including linked investigation | P0 |
| `PATCH` | `/api/v1/incidents/{incident_id}/status` | Resolve/reopen incident (Developer/Admin) | P0 |
| `GET` | `/api/v1/incidents/{incident_id}/timeline` | Evidence-backed ordered incident timeline | P0 |
| `GET` | `/api/v1/incidents/{incident_id}/reviews` | Human review history | P0 |
| `POST` | `/api/v1/incidents/{incident_id}/reviews` | Create human root-cause review (Developer/Admin) | P0 |
| `GET` | `/api/v1/incidents/{incident_id}/investigations` | List all runs for incident | P0 |
| `POST` | `/api/v1/incidents/{incident_id}/investigations` | Start a new AI investigation (asynchronous) | P0 |
| `GET` | `/api/v1/investigations` | List investigation runs | P0 |
| `GET` | `/api/v1/investigations/{investigation_id}` | Get investigation state | P0 |
| `POST` | `/api/v1/investigations/{investigation_id}/cancel` | Request cooperative cancel | P0 |
| `POST` | `/api/v1/investigations/{investigation_id}/retry` | New run with new investigation ID | P0 |
| `GET` | `/api/v1/investigations/{investigation_id}/events` | Paginated ordered event replay for WebSocket recovery | P0 |
| `GET` | `/api/v1/investigations/{investigation_id}/hypotheses` | Up to three hypotheses | P0 |
| `GET` | `/api/v1/investigations/{investigation_id}/evidence` | Evidence cards/links | P0 |
| `GET` | `/api/v1/evidence/{evidence_id}` | Evidence detail with sanitised excerpt | P0 |
| `GET` | `/api/v1/investigations/{investigation_id}/report` | Structured RCA report, 404 until available | P0 |
| `GET` | `/api/v1/overview` | Dashboard summary for permitted scope | P0 |
| `POST` | `/api/v1/telemetry/logs/search` | Bounded filtered Elasticsearch log search (P1) | P1 |
| `POST` | `/api/v1/telemetry/metrics/query` | Bounded Prometheus metric query (P1) | P1 |
| `GET` | `/api/v1/telemetry/traces` | Search traces in Tempo (P1) | P1 |
| `GET` | `/api/v1/telemetry/traces/{trace_id}` | Read span waterfall (P1) | P1 |
| `GET` | `/api/v1/integrations` | List connected integrations (Admin) | P0 |
| `POST` | `/api/v1/integrations` | Register connection (Admin) | P0 |
| `GET` | `/api/v1/integrations/{integration_id}` | Safe integration configuration, no secrets | P0 |
| `PATCH` | `/api/v1/integrations/{integration_id}` | Update connection (Admin) | P0 |
| `DELETE` | `/api/v1/integrations/{integration_id}` | Remove connection (Admin) | P0 |
| `POST` | `/api/v1/integrations/{integration_id}/test` | Test connection without exposing secrets (Admin) | P0 |
| `GET` | `/api/v1/settings` | Read runtime settings; limits are read-only for MVP | P1 |
| `POST` | `/api/v1/ingest/alerts` | Generic external alert ingestion | P0 |
| `POST` | `/api/v1/ingest/deployments` | Ingest deployment events | P0 |
| `POST` | `/api/v1/ingest/alertmanager` | Prometheus Alertmanager native webhook | P0 |
| `POST` | `/internal/v1/ai/events` | AI → Main Backend single event callback | P0 |
| `POST` | `/internal/v1/ai/results` | AI → Main Backend final structured result | P0 |
| `GET` | `/api/v1/users/{user_id}` | Get user (Admin) | P1 |
| `PATCH` | `/api/v1/users/{user_id}` | Update user role/projects/status (Admin) | P1 |
| `GET` | `/internal/v1/ai/incidents/{incident_id}/context` | AI backend reads scoped sanitized incident context | P0 |

## AI Backend, service-to-service REST-кандидат

| Метод | URL | Назначение |
|---|---|---|
| `POST` | `/internal/v1/investigations` | Start durable asynchronous AI execution |
| `GET` | `/internal/v1/investigations/{investigation_id}` | Read AI execution status for reconciliation |
| `POST` | `/internal/v1/investigations/{investigation_id}/cancel` | Request agent cancellation |
| `GET` | `/internal/v1/health` | AI backend model and concurrency readiness |

| `GET` | `/internal/v1/investigations/{investigation_id}/result` | Retrieve terminal AI result for reconciliation |

## Вне обычного REST

| Канал | Контракт |
|---|---|
| WebSocket | `WS /ws/v1/events`; подписки, sequence, backfill, авторизация — `04_FRONTEND_API_AND_WS.md` |
| MCP | MCP Streamable HTTP / `tools/list`, `tools/call`; catalog `mcp/tool-catalog.json` |

### MCP-инструменты

| Имя | Этап | Источник |
|---|---|---|
| `search_logs` | MVP | Elasticsearch/Kibana |
| `query_prometheus` | MVP | Prometheus/Grafana |
| `get_trace` | MVP | Tempo |
| `get_service_health` | MVP | Prometheus/health |
| `get_container_status` | MVP | Docker safe adapter |
| `get_container_events` | MVP | Docker safe adapter |
| `get_recent_deployments` | MVP | Main Backend deployment registry |
| `github_search_code` | MVP | GitHub |
| `github_get_file` | MVP | GitHub |
| `github_get_commit` | MVP | GitHub |
| `github_compare_commits` | MVP | GitHub |
| `github_get_blame` | MVP | GitHub |
| `http_health_check` | MVP | Allowlisted HTTP GET/HEAD |
| `get_incident_context` | MVP | Main Backend |
| `search_docs` | P2 | Qdrant |
| `search_similar_incidents` | P2 | Qdrant + PostgreSQL |
