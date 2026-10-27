# AI Incident Investigator — UI / UX Technical Specification

**Базовый дизайн:** вариант B — Observability / SRE Style.  
**Адрес Figma:** https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc  
**Страница с актуальными макетами:** `02 — B / Product screens` (не путать с исходными концептами A/B/C).  
**Назначение документации:** передать frontend-разработчику самостоятельный комплект подробных требований по каждому экрану.  
**Язык интерфейса макетов:** английский; описание и технические требования — русский.  
**Статус:** спецификация интерфейса на основании созданных макетов и ранее согласованных требований продукта. Не является утверждённым OpenAPI/JSON Schema.

## Кратко о продукте

AI Incident Investigator — интерфейс системы автономного анализа технических инцидентов. Подключённые источники телеметрии и кода предоставляют факты; Backend создаёт и хранит инциденты, запускает AI-расследования и отправляет события; frontend отображает происходящее, Evidence и итоговый RCA Report. Сам AI-агент использует read-only инструменты и **не устраняет проблемы автоматически**.

## Состав комплекта

| Файл | Экран / область | Макет Figma | Предлагаемый путь |
|---|---|---|---|
| `01_DESIGN_SYSTEM_AND_APP_SHELL.md` | Общий стиль, навигация, компоненты, состояния, правила | [Страница макетов](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-2) | Общий layout |
| `02_OVERVIEW.md` | Overview / Service observability | [Открыть](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-24) | `/overview` |
| `03_INCIDENTS.md` | Incidents / Incident registry | [Открыть](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-26) | `/incidents` |
| `04_LIVE_INVESTIGATIONS.md` | Live investigations / Agent runs | [Открыть](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-28) | `/investigations` |
| `05_SERVICE_MAP.md` | Service dependency map | [Открыть](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-30) | `/service-map` |
| `06_LOGS_AND_METRICS.md` | Logs & metrics / Telemetry explorer | [Открыть](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-32) | `/telemetry` |
| `07_TRACES.md` | Traces / Distributed tracing | [Открыть](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-34) | `/traces` |
| `08_INTEGRATIONS.md` | Integrations / Sources & credentials | [Открыть](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-36) | `/integrations` |
| `09_SETTINGS.md` | Settings / Workspace configuration | [Открыть](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-38) | `/settings` |
| `10_INCIDENT_DETAIL.md` | Incident Detail / вкладки, RCA, Evidence | [Открыть](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-40) | `/incidents/:incidentId` |
| `11_IMPLEMENTATION_AND_ACCEPTANCE.md` | Общая последовательность разработки, проверка и handoff | — | Сквозные требования |

*Пути маршрутизации в таблице — **предложение** для реализации frontend; с командой ещё не утверждены.*

## Приоритеты

**P0 (сквозной MVP):** единая оболочка, Overview, Incidents, Incident Detail (основные вкладки), Live Investigation, Evidence, Hypotheses, Timeline, RCA Review, чтение и управление расследованиями через Backend, состояния ошибок, RBAC. **Интеграции:** базовый экран для подключения и проверки источников. **Settings:** минимальные настройки, если соответствующие Backend API готовы.

**P1 (после сквозного сценария):** расширенный Logs & Metrics, подробные Traces/waterfall, интерактивный Service map, встроенные графики, расширенный административный UI. Макеты этих разделов **существуют уже сейчас**, но наличие макета не означает, что Backend или инструментальные API готовые.

**P2:** контекстный чат после завершения расследования, RAG/Incident Memory-интерфейсы, дополнительные виды аналитики и продвинутые взаимодействия.

## Ключевые границы ответственности

- **Frontend → Backend:** REST + WebSocket. Браузер не обращается напрямую к MCP, LangGraph, RabbitMQ, PostgreSQL, Docker, llama.cpp, Elasticsearch или Prometheus.
- **Состояние инцидента** (`Open`, `Investigating`, `Awaiting Review`, `Resolved`) и **состояние отдельного AI-run** (`queued/running/completed/inconclusive/failed/timed_out/cancelled` — примерные коды) — две разные сущности.
- Роль **Viewer** читает данные, но не запускает/отменяет расследования; **Developer** анализирует и подтверждает RCA; **Admin** управляет интеграциями, проектами и пользователями. Backend независимо проверяет права.
- Данные из источников только **реальные**; в макетах показаны демонстрационные значения (`ACME`, `INC-1042`, `payment-service`, даты и числа). Нельзя использовать их как фиктивный live-output в продукте.
- Окончательные API-контракты ещё предстоит согласовать с Юрием: OpenAPI для REST, JSON Schema для WebSocket/очередей и MCP tool schemas. Формы данных в этих файлах — требования к UI/предварительные потребности, не утверждённые wire formats.

## Как использовать разработчику

1. Открыть `01_DESIGN_SYSTEM_AND_APP_SHELL.md` и соответствующий фрейм в Figma.
2. Реализовать разделы как независимые маршруты, переиспользуя единый sidebar/header/таблицы/бейджи.
3. До появления Backend подставлять явно помеченные mock fixtures и мок-события WebSocket; потом переключить адаптеры на настоящие API.
4. Согласовать со владельцем Backend недостающие поля и операции до интеграции.
5. Проверить требования «Состояния» и «Критерии приёмки» из файла конкретного экрана.

**Не менять** утверждённую концепцию на светлую тему, не добавлять декоративные pie charts «Incidents by Severity», не отображать chain-of-thought LLM, не делать кнопки автоматического rollback/restart/patch.
