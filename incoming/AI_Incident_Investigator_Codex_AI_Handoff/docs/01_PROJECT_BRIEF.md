# AI Incident Investigator — общая картина продукта

## Продукт и ценность
AI Incident Investigator — платформа для автономного **Root Cause Analysis технических инцидентов** в микросервисной системе. Вместо ручного переключения между логами, метриками, трассировками, GitHub и контейнерами пользователь видит единый Incident и последовательность шагов AI-агента. Итог — обоснованная вероятная **первопричина**, её связь с симптомами, Evidence, timeline и рекомендации. Это **диагностика и объяснение**, а не система автоматического исправления production.

## Сквозной пользовательский сценарий
1. Команда регистрирует Project, Environment, Services и подключает ограниченные диагностические источники.
2. В Main Backend поступает Alertmanager webhook / другой alert, либо пользователь инициирует расследование вручную.
3. Main Backend фиксирует Incident и решает, запускать ли AI (политика автозапуска ещё на согласовании).
4. Main Backend напрямую обращается к AI Backend (REST/gRPC — решение ожидается). Запрос **асинхронно принимается**; на 20 минут HTTP соединение не остаётся открытым.
5. LangGraph ReAct agent получает контекст, выбирает следующие **read-only MCP tools** и анализирует фактические результаты.
6. AI отправляет structured tool/progress/hypothesis/evidence events и итоговый RCA в Main Backend; тот сохраняет и транслирует через WebSocket.
7. Frontend показывает progress, до трёх конкурирующих гипотез, Evidence и причинную цепочку.
8. Человек подтверждает, отклоняет либо корректирует вывод. Завершение исследования **не равно** исправлению Incident. Retry создаёт новый investigation ID; Cancel прерывает работу управляемо.

## Пример
После релиза `payment-service` увеличились HTTP 500. Сравниваются logs Elasticsearch (`connection timeout`), metrics Prometheus (pool saturation), traces Tempo (DB acquire spans), deployment history и GitHub diff. Агент различает временную корреляцию релиза и **доказанную причинную связь**: если хватает данных — выдаёт RCA со ссылками; иначе — `inconclusive`, включая список недостающих доказательств.

## Части продукта и ответственность
| Репозиторий / владелец | Задачи |
|---|---|
| `incident-investigator-frontend` / Расул | Dark SRE UI, Overview, Incidents, Live Investigations, Service Map, Logs & Metrics, Traces, Integrations, Settings, Incident Detail; REST + WS через Main Backend |
| `incident-investigator-backend` / Юрий | Project/Environment/Service, Incident/Investigation lifecycle and durable records, integrations, RBAC & email OTP login, API & WebSocket, AI orchestration, event ingest; внутренняя микросервисная детализация — решение владельца |
| `incident-investigator-ai` / Олег | AI Backend service boundary, LangGraph single-agent ReAct, MCP Client, budgets/checkpoints, hypotheses/evidence/RCA, AI results and tests/evaluation |
| `incident-investigator-infra` / Даниил | Docker Compose/telemetry stack, databases & deployment, CI, dev environment, operational integrations |
| Отдельный demo contributor | Fault-injection e-commerce стенд для воспроизводимых инцидентов; не путать с продуктовым Backend |

## MVP
- Инциденты и асинхронные расследования без очереди Main ↔ AI; одна активная работа на executor в стартовой конфигурации.
- LangGraph ReAct, read-only MCP, evidence-grounded structured RCA/`inconclusive`, human review, replay событий после reconnect, Cancel/Retry.
- Источники: Elasticsearch, Prometheus, Tempo, GitHub, health/deployments, Docker diagnostic adapter (по реализованным адаптерам).
- Эталонные fault-injection сценарии: исчерпание PG pool, bad deployment, latency cascade, OOM/restart, RabbitMQ consumer lag/failure **в demo e-commerce**, DragonflyDB недоступен.
- Демо локально на Docker Compose; llama.cpp/llama-server на macOS нативно с Metal (исходный согласованный план).

## Не входит в обязательный MVP
- Multi-agent orchestration, автоматические production fixes, shell/SQL arbitrary execution, generic SaaS/multitenancy, autoremediation.
- RAG для документации и Incident Memory на Qdrant — **этап 2**.
- Полная интерактивная визуализация Service Map / Logs Explorer / Trace Waterfall может разрабатываться после ядра (приоритет по команде).

## Ссылка на макеты
Figma / `02 — B / Product screens`: https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-2

## Дополнительные источники
`contracts/README.md` — подробное описание общего проекта, `contracts/01_ARCHITECTURE.md` — обновлённая архитектура, `references/legacy_specs/00_PROJECT_OVERVIEW.md` — исходный полный контекст **с устаревшим transport section**.
