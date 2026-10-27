# AI Incident Investigator — Codex handoff for AI development

Этот каталог подготовлен для переноса всего **проверенного документального контекста** проекта в репозиторий `incident-investigator-ai` и продолжения разработки через Codex CLI либо приложение Codex.

## Начать за 2 минуты
1. Скопируй **содержимое** этого каталога в корень `incident-investigator-ai` (`AGENTS.md`, `README.md`, `docs/`). Перед копированием проверь существующий `AGENTS.md`/`README.md`: не затирай действующие файлы без просмотра и объединения.
2. Открой репозиторий как рабочую папку Codex. Codex прочитает проектные инструкции `AGENTS.md` и сможет обращаться к документации в `docs/`.
3. Дай Codex стартовый запрос из [`docs/05_CODEX_ONBOARDING.md`](docs/05_CODEX_ONBOARDING.md). Первый запрос — только аудит текущего кода и план работ.
4. После принятия командой архитектурных решений обнови [`docs/04_DECISIONS_AND_CONFLICTS.md`](docs/04_DECISIONS_AND_CONFLICTS.md) и соответствующие формальные контракты.

## Описание продукта
**AI Incident Investigator** исследует инциденты в микросервисных приложениях: из алерта создаётся Incident, Main Backend запускает AI-расследование, LangGraph-агент изучает диагностические источники через MCP и формирует **RCA** с проверяемыми Evidence, гипотезами, хронологией и рекомендациями. Человек подтверждает либо корректирует вывод. Агент не исправляет production автоматически.

## Куда смотреть
| Путь | Что содержит |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Постоянные правила работы Codex и актуальные архитектурные ограничения |
| [`docs/00_START_HERE.md`](docs/00_START_HERE.md) | Индекс и приоритет документов |
| [`docs/01_PROJECT_BRIEF.md`](docs/01_PROJECT_BRIEF.md) | Продукт и все четыре подсистемы |
| [`docs/02_AI_SCOPE_AND_ARCHITECTURE.md`](docs/02_AI_SCOPE_AND_ARCHITECTURE.md) | Что обязан реализовать AI Backend |
| [`docs/03_AI_DELIVERY_PLAN.md`](docs/03_AI_DELIVERY_PLAN.md) | Этапы, тесты, критерии готовности |
| [`docs/04_DECISIONS_AND_CONFLICTS.md`](docs/04_DECISIONS_AND_CONFLICTS.md) | Согласовано, спорно, устарело |
| [`docs/05_CODEX_ONBOARDING.md`](docs/05_CODEX_ONBOARDING.md) | Запросы для начала работы в Codex |
| [`docs/contracts/`](docs/contracts/) | Полный API contract pack v0.2 с OTP: OpenAPI, JSON Schema, MCP, gRPC-кандидат, примеры |
| [`docs/references/legacy_specs/`](docs/references/legacy_specs/) | Оригинальные спецификации 4 репозиториев и обзор проекта; **исторические**, часть утверждений устарела |
| [`docs/references/frontend_ui/`](docs/references/frontend_ui/) | Полный комплект ТЗ экранов варианта B для общего понимания UI |

Исходные макеты Figma: https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-2

### Не перепутать
- **RabbitMQ исключён только из Main Backend ↔ AI.** Внутри тестового e-commerce оно может использоваться как объект диагностики.
- **REST vs gRPC ещё не решено.** Не разворачивай оба транспорта из предположения.
- Каталог `docs/contracts/` — текущая **черновая** версия v0.2, не финальная v1.
- Этот архив содержит **контекст и контракты, а не исходный код работающего AI-сервиса**. При установке в готовый репозиторий необходимо сделать аудит существующего кода.
