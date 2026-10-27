# 08. Auth, RBAC, безопасность, ошибки

**Обязательно для v0.2:** email/password + email OTP при каждом password login. Успех `/auth/login` возвращает только `202 LoginChallenge`; только `/auth/otp/verify` выдаёт пользовательскую сессию/JWT. Один code, 5 минут, 5 попыток, resend 60 секунд/3 раза — **предлагаемые конфигурируемые лимиты**, см. `12_AUTH_EMAIL_OTP.md`. OTP хранить только как секретно вычисляемый HMAC digest, не логировать. Пароли хранить с Argon2id (предпочтительно) или иной актуальной password KDF, не plaintext.

## 1. Матрица RBAC (с проверкой project scope на сервере)

| Действие | Admin | Developer | Viewer |
|---|---|---|---|
| Читать разрешённые Incidents, Evidence, RCA, telemetry views | ✓ | ✓ | ✓ |
| Запускать, Cancel, Retry investigations | ✓ | ✓ | — |
| Подтверждать / отклонять / исправлять RCA | ✓ | ✓ | — |
| Resolve/Reopen incident | ✓ | ✓ | — |
| Создавать/править Project, Environment, Service | ✓ | — | — |
| Создавать/изменять/удалять integrations | ✓ | — | — |
| Управлять users / permissions | ✓ | — | — |
| Читать AI budget / runtime config | ✓ | ✓ | ✓ |

Viewer не должен получить доступ к чужому project через подмену UUID, даже если знает `incident_id`.

## 2. Три разные security модели

- **Browser → Main Backend:** JWT access/refresh или server-side session (способ хранения refresh ещё надо утвердить); HTTPS, HttpOnly/SameSite cookies предпочтительнее localStorage для токена, CSRF защита если cookies.
- **Main Backend ↔ AI Backend:** отдельный **service identity**, не пользовательский access token; scope как минимум `ai:start`, `ai:cancel`, `ai:events:write`, `ai:results:write`, `ai:context:read`. В Docker network API не становится «безопасным автоматически».
- **External ingestion:** токен/signature webhook per source, rotation и replay protection. MCP использует собственный service identity / scopes, и права проекта проверяет сервер инструментов.

## 3. Нормализованные HTTP ответы

Success: `200` read/update, `201` create, `202` async accepted, `204` no content. Error: `application/problem+json`, структурный объект:

```json
{
 "type":"https://api.example/problems/forbidden",
 "title":"Forbidden",
 "status":403,
 "code":"project_access_denied",
 "detail":"The current identity cannot access this project",
 "request_id":"req-7c7c82e2",
 "errors":[]
}
```

| HTTP | Когда | Code пример |
|---|---|---|
| 400 | invalid cursor/bad input | `invalid_query` |
| 401 | credentials missing/invalid, invalid OTP | `unauthorized`, `invalid_credentials`, `otp_invalid` |
| 410 | OTP code expired or consumed | `otp_expired` |
| 403 | forbidden project/role/scope | `project_access_denied` |
| 404 | resource unavailable/not accessible | `not_found` |
| 409 | invalid state transition, idempotency conflict | `invalid_transition`, `idempotency_conflict` |
| 412 | optimistic concurrency/If-Match mismatch (optional) | `version_mismatch` |
| 422 | schema validation | `validation_error` |
| 429 | capacity/rate limit or OTP attempts/resend throttled | `capacity_exhausted`, `otp_rate_limited` |
| 502 | upstream MCP/telemetry failure | `source_unavailable` |
| 503 | AI/model unavailable | `ai_unavailable` |
| 504 | request to upstream timed out | `upstream_timeout` |

Error `detail` не содержит internal stacktrace, prompts, токены и raw credentials. `request_id` коррелируется с OpenTelemetry trace id.

## 4. Бounded operations

- Filter/project scoping прежде всего. Длина строк/query, лимит `limit`, max time range, max bytes, max series/span count, timeout — **на стороне сервера**, а не только frontend.
- Telemetry Explorer может возвращать `partial`/`truncated`; не показывать неотфильтрованное тело исключения Elasticsearch в браузере.
- `source_url`: allowlisted HTTPS/GitHub, без data/javascript scheme/embedded secrets.
- Authz проверяется отдельно при HTTP REST, WebSocket subscriptions, внутреннем context endpoint, MCP tool call.
- Review аудит; `corrected_root_cause` хранить как человеко-изменённое дополнение, а не переписывать агентный RCA.

## 5. Versioning и observability

`/api/v1`, `/internal/v1`, `schema_version:"1.0"` в межсервисных событиях. `X-Request-ID` и `traceparent` (W3C) прокидывать по Main Backend → AI → MCP / callbacks. Logs redacted, Prometheus counters/latencies, trace spans по вызовам AI/LLM/MCP. Никакого обязательного LangSmith.
