# Как начать работу в Codex

## 1. Подготовка репозитория

Вариант CLI (локально):

```bash
# Нужен действующий git checkout твоего AI-репозитория.
cd /path/to/incident-investigator-ai
# Скопируй сюда AGENTS.md и docs/ из handoff-пакета.
# Если файлы уже есть, сначала сравни содержимое и объедини инструкции.
git status --short
```

Открой эту директорию как проект в Codex CLI или Codex app. Документы лучше коммитить в git: тогда любой новый сеанс имеет контекст проекта. Из другого репозитория Codex автоматически не читает документы, если они не доступны в открытой рабочей папке.

## 2. Первый запрос (копировать в Codex)

> Мы продолжаем разработку AI Incident Investigator в репозитории `incident-investigator-ai`. Сначала прочитай `AGENTS.md`, `docs/00_START_HERE.md`, `docs/01_PROJECT_BRIEF.md`, `docs/02_AI_SCOPE_AND_ARCHITECTURE.md`, `docs/04_DECISIONS_AND_CONFLICTS.md`, `docs/contracts/05_INTERNAL_BACKEND_AI.md`, `docs/contracts/06_MCP_CONTRACTS.md`, `docs/contracts/10_OPEN_DECISIONS.md`. Затем изучи фактическую структуру репозитория, зависимости, тесты и git status. Составь аудит: что уже реализовано, что отсутствует, что противоречит текущему draft contract v0.2 и какие решения пока открыты. Дай конкретный план AI-разработки в небольших этапах, с тестами и зависимостями от Backend Юрия. **Пока ничего не меняй в коде.** Не внедряй RabbitMQ между Main Backend и AI. Не выбирай REST/gRPC и owner MCP Server вместо нас.

## 3. Запрос на первую реализацию

> Реализуй первый маленький и тестируемый AI Backend срез из согласованного плана: Pydantic v2 domain DTO для `Start`, `InvestigationEvent`, `AIResultCallback` и `RCAReport`, сверяя поля по `docs/contracts/schemas/` и примерам в `docs/contracts/examples/`. Реализация должна быть независима от REST/gRPC, без предположений о MCP Server owner. Напиши валидационные и unit tests. До изменений кратко перечисли план и затронутые файлы; после покажи результаты реально запущенных тестов и расхождения с draft v0.2.

## 4. По каким файлам задавать специализированные вопросы

- MCP Client: `docs/contracts/06_MCP_CONTRACTS.md` + `docs/contracts/mcp/tool-catalog.json`.
- Agent loop: `docs/02_AI_SCOPE_AND_ARCHITECTURE.md` + `docs/03_AI_DELIVERY_PLAN.md`.
- Progress events / result delivery: `docs/contracts/05_INTERNAL_BACKEND_AI.md` + JSON schemas / examples.
- Что увидит Frontend: `docs/references/frontend_ui/04_LIVE_INVESTIGATIONS.md`, `10_INCIDENT_DETAIL.md` + `docs/contracts/04_FRONTEND_API_AND_WS.md`.
- Дополнительные бизнес-требования: `docs/references/legacy_specs/00_PROJECT_OVERVIEW.md`, но **игнорируй его устаревшую схему RabbitMQ**.

## 5. Поддерживать актуальность

По мере изменения реализации обновляй `AGENTS.md` **только при изменении постоянных правил**, docs/ADR — при архитектурных решениях, OpenAPI/JSON Schema и examples — при одобренном изменении DTO. Указывай, какой документ — specification, какой — implementation status. Ни одна строка здесь не гарантирует, что код уже существует.
