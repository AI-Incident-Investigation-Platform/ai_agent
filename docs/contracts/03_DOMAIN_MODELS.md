# 03. Доменные модели, статусы и ограничения

Машинный источник схем: [`schemas/domain.schema.json`](schemas/domain.schema.json) (`$defs`), также OpenAPI `components.schemas`. Ниже закрепляем бизнес-смысл полей.

## 1. Конвенции

- IDs в wire-contract: **UUID string**, независимы от внутренних PK БД. Публичный Figma ID `INC-1042` — человекочитаемый *display number*; текущая v0.1 использует UUID как API ID, короткий номер UI вычисляет/хранит отдельно при необходимости (см. вопросы).
- API поля: `snake_case`; значения enum: `lower_snake_case`.
- Время: **RFC3339 UTC** (`2026-10-19T14:35:00Z`). Ни один компонент не предполагает локальное время в данных.
- Списки: `{ "items": [ ... ], "next_cursor": null }`; переход к следующей странице по opaque cursor; `limit` сервером ограничен.
- Изменения: `PATCH` для ограниченного набора полей; запрет произвольной замены объекта; audit пользовательских действий.
- Endpoint names v0.1 предлагаемые. Перед merge на утверждённый контракт — code review обеих команд.

## 2. Иерархия

`Project → Environment → Service → Deployment`.

| Модель | Поля | Принцип |
|---|---|---|
| `Project` | `id`, `name`, `slug`, `description`, `created_at` | область прав доступа / интеграций |
| `Environment` | `id`, `project_id`, `name`, `slug`, `is_production` | Production/Staging/Dev независимы |
| `Service` | `id`, `project_id`, `environment_id`, `name`, `external_names`, `repository_url` | имена и связи настраиваются, обязательного discovery нет |
| `Deployment` | `id`, `project_id`, `environment_id`, `service_id`, `version`, `commit_sha`, `deployed_at`, `status`, `source_url` | внешний deployment event, не чтение CI pipeline |

## 3. Incident ≠ Investigation

`Incident`: `title`, `description`, `severity`, `project_id`, `environment_id`, **`service_ids[]`**, `source`, `detected_at`, `status`, `latest_investigation_id`.

`severity`: **`critical`, `high`, `medium`, `low`**.

`status` инцидента: **`open` → `investigating` → `awaiting_review` → `resolved`**. Разрешён `resolved → open` при переоткрытии. `resolved` требует человеческого решения и не устанавливается автоматически завершением агентной работы. `awaiting_review` может появиться после `completed` или `inconclusive`.

`Investigation`: `id`, `incident_id`, `status`, `attempt`, `parent_investigation_id`, `budget`, `current_step`, `tool_calls_count`, `created_at`, `started_at`, `finished_at`, `failure_code`.

`status` расследования: **`pending` → `running` →** одна из `completed | inconclusive | failed | timed_out | canceled`. Pending может перейти в `canceled`, если запуск ещё не начался. Терминальные состояния не меняются повторными callback; retry создаёт **новый UUID** и `attempt+1`.

> Не интерпретировать `failed` как «не найден Root Cause». `failed` означает инфраструктурную/исполнительную ошибку, `inconclusive` — агент выполнил работу, но данных недостаточно.

## 4. Analysis models

**Hypothesis:** до трёх на run, `id`, `title`, `explanation`, `status: pending|supported|rejected`, `confidence: high|medium|low`, `evidence_ids[]`, `updated_at`. **Не вводим отдельные `evidence_for`/`evidence_against`**, ранее отказались от этого.

**Evidence:** `id`, `investigation_id`, `source` (`source_type`, `source_id`, `url`, `observed_at`, `metadata`), `title`, `summary`, `excerpt` (sanitized), `service_ids[]`, `hypothesis_ids[]`, `collected_at`. Сырые TB логов не храним в своей БД. Сохраняем краткий excerpt + provenance; UI deep-link ведёт в Elasticsearch/Kibana/Grafana/Tempo/GitHub.

**TimelineEntry:** `occurred_at`, `title`, `event_type`, `service_ids[]`, `source`, `causality: observed|correlated|supported_cause|unknown`. Одна лишь хронология — не доказательство причинности.

**RCAReport:** `id`, `incident_id`, `investigation_id`, `outcome: completed|inconclusive`, `summary`, `symptoms[]`, `root_cause` (nullable), `root_cause_service_ids[]`, `causal_chain[]`, `hypothesis_ids[]`, `evidence_ids[]`, `timeline_entry_ids[]`, `confidence`, `remediation[]`, `prevention[]`, `limitations[]`, `generated_at`. **Итог без доказательств не должен маскироваться под высокую уверенность.**

**Review:** обязательно `investigation_id`, `decision: confirmed|rejected|corrected`, `corrected_root_cause`, `comment`, `reviewer_id`, `created_at`. Исправление AI-вывода сохраняет оригинальный отчёт без мутации; корректировка живёт в Review.

## 5. Integrity и индексы (логически обязательны, SQL — Юрия)

- `Incident(project_id, environment_id, detected_at DESC)` и поиск по status/severity.
- `Investigation(incident_id, attempt UNIQUE)`; `Investigation.id` — глобально уникален.
- `InvestigationEvent(event_id UNIQUE)` и `UNIQUE(investigation_id, sequence)`.
- `RCAReport(investigation_id UNIQUE)`; `Hypothesis(investigation_id, id)`; Evidence source provenance.
- `Review.investigation_id` принадлежит тому же incident; Server проверяет; Editor/Viewers без прав не могут записать review.
- `Deployment(source, source_event_id)` дедуп; `Alert(source, source_event_id)` дедуп; внешние ID не доверять как авторизацию.
- Time/source/service indexes позволяют вернуть корректный инцидент без загрузки всей телеметрии.

## 6. P2 (второй этап)

`Qdrant` для проектных документов и Incident Memory, постфактум чат без новых tools, улучшенные визуальные Trace/Service Map. Эти сущности нельзя навязывать реализации core MVP.
