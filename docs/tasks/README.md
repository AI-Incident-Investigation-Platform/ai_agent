# AI Incident Investigator — AI Backend: план задач для Codex

> **Назначение:** исполнимый реестр небольших задач для разработки AI Backend в репозитории [AI-Incident-Investigation-Platform/ai_agent](https://github.com/AI-Incident-Investigation-Platform/ai_agent). Текстовые задачи — **план**, а не подтверждение реализованного кода или утверждение API v1. Весь код пишется и проверяется в Codex; этот пакет не устанавливает BMad Method.

## 1. Что строим

Самостоятельный AI Backend на Python/FastAPI с **одним LangGraph ReAct-агентом**, локальной **Qwen2.5-Coder-7B-Instruct через llama.cpp**, **MCP Streamable HTTP Client** для **read-only** диагностики, **PostgreSQL checkpointing** и управлением длительным запуском. Результат — проверяемый Evidence-linked RCA: до 3 гипотез, timeline, ссылки на источники, рекомендации и честный `inconclusive` при недостатке данных.

```
Frontend ─ REST/WS ─ Main Backend (владелец Incident, Auth, Review)
                             ⇅ прямой internal API (REST либо gRPC — НЕ ВЫБРАН)
                         AI Backend (этот репозиторий)
                ┌────────────┼────────────┐
         LangGraph Agent   MCP Client   Durable Runtime/PG
                │               │             │
          llama-server     MCP Server*    checkpoints, registry
          Qwen2.5 7B      ↓ read-only
                    ES / Prometheus / Tempo / GitHub / Deployments
```

`*` MCP Server owner/location **пока не утверждены**. RabbitMQ **между Main Backend и AI Backend нет**. RabbitMQ может фигурировать как **диагностируемая** часть демо-ecommerce, не как транспорт AI.

## 2. Правила источников и актуального состояния

1. Реальный код и тесты в рабочей ветке: сначала **проверь**, что действительно реализовано и что уже меняется в соседней сессии.
2. `AGENTS.md` и `docs/00_START_HERE.md` — обязательный вход Codex; актуальные согласованные решения в `docs/04_DECISIONS_AND_CONFLICTS.md` и `docs/contracts/10_OPEN_DECISIONS.md`.
3. `docs/contracts/` — **v0.2-draft**, source of truth для **предложенных DTO** и точных кандидатов схем; поля не менять самостоятельно. REST OpenAPI и `.proto` — **варианты**, не утверждённый транспорт.
4. `docs/02_AI_SCOPE_AND_ARCHITECTURE.md`, `docs/03_AI_DELIVERY_PLAN.md` — AI-границы и приоритеты.
5. `docs/references/legacy_specs/` — история; требования RabbitMQ между Backend↔AI и фиксированного MCP-owner там **устарели**.
6. Этот каталог `docs/tasks/` определяет порядок исполнения, **не заменяет** контракты. Если текст Story конфликтует с более авторитетным источником — зафиксировать расхождение, остановить спорную часть и предложить ADR.

**Состояние на момент подготовки плана:** в `chore/ai-backend-bootstrap` обнаружен каркас FastAPI, базовый `LlamaCppProvider`, минимальный LangGraph и импортированные проектные документы. Локальный `llama-server` с Qwen2.5 уже отвечает через HTTP **по сообщению разработчика**. **AI-01 отправлена в Codex и выполняется; готовность / merge AI-01 не подтверждены.** Не перезапускать AI-01 параллельно и не переписывать её файлы до проверки результата.

**Важно про Python:** в текущем `pyproject.toml` было `requires-python >=3.14`, хотя первоначально рассматривали 3.12. Не изменять версию молча; перед подключением torch/transformers/ONNX, Postgres драйверов и прочих бинарных зависимостей проверить совместимость и зафиксировать командное решение.

## 3. Как понимать статусы и приоритеты

- **P0 (MVP)** — без этой функции нет законченного проверяемого расследования, надёжного исполнения или интеграции.
- **P1 (quality/hardening)** — надёжность, наблюдаемость, release-проверки.
- **P2 (optional)** — RAG и обучаемый роутер; не блокируют MVP.
- **Gate** — интеграционный барьер: до прохождения gate дальнейшие зависящие Stories нельзя считать готовыми.
- **Blocked by decision** — можно готовить интерфейсы/тесты, **нельзя** закреплять конкретное спорное решение в production.

## 4. Реестр Stories

| ID | Задача | Зависит от | Демонстрируемый результат | Приоритет |
|---|---|---|---|---|
| [AI-01](./AI-01_LLM_LANGGRAPH_INTEGRATION.md) | Реальный вызов Qwen из LangGraph | Каркас + локальный llama-server | Smoke: LangGraph → HTTP → Qwen → ответ | P0 · **уже запущена** |
| [AI-02](./AI-02_NATIVE_TOOL_CALLING_SPIKE.md) | Проверка настоящего tool calling | AI-01 | Воспроизводимый отчёт о поддержке функций в llama.cpp/Qwen | P0 |
| [AI-03](./AI-03_DOMAIN_AND_CONTRACTS.md) | Domain DTO, схемы, contract tests | AI-01 для чистой синхронизации файлов | Типы run/evidence/RCA + контрактные тесты | P0 |
| [AI-04](./AI-04_DETERMINISTIC_AGENT_GRAPH.md) | Контролируемый LangGraph state machine | AI-02, AI-03 | Graph с fake LLM и fake tools без реальных источников | P0 |
| [AI-05](./AI-05_MCP_CLIENT.md) | MCP Streamable HTTP client | AI-03 | Discovery и tools/call через тестовый MCP Server | P0 |
| [AI-06](./AI-06_TOOL_VALIDATION_AND_SECURITY.md) | Типизированные tools, ограничения доступа | AI-03, AI-05 | Безопасные tool adapters, ошибка/partial/truncated | P0 |
| [AI-07](./AI-07_EVIDENCE_AND_HYPOTHESES.md) | Evidence и до 3 гипотез | AI-04, AI-06 | Проверяемые доказательства без выдуманных source_refs | P0 |
| [AI-08](./AI-08_RCA_AND_FINALIZATION.md) | RCA, timeline, verdict | AI-07 | Структурированный completed/inconclusive report | P0 |
| [AI-09](./AI-09_BUDGETS_CANCEL_AND_FAILURES.md) | Лимиты, таймаут, отмена, сбои | AI-04, AI-06 | Bound execution: 20/40/1200, cancel, recovery outcome | P0 |
| [G01](./G01_LOCAL_INVESTIGATION_GATE.md) | Локальный E2E gate | AI-02…AI-09 | Демонстрационный run с fake MCP и optional real Qwen | Gate |
| [AI-10](./AI-10_POSTGRES_CHECKPOINTS.md) | Durable LangGraph checkpoints | AI-04, решение PG ownership | Checkpoint сохраняется и читается после рестарта | P0 · decision |
| [AI-11](./AI-11_DURABLE_RUN_EXECUTOR.md) | Registry, admission, recovery, cancel | AI-09, AI-10, policy overload | Запуск не теряется после рестарта, ≤1 active | P0 · decision |
| [AI-12](./AI-12_PROGRESS_AND_RESULT_DELIVERY.md) | Progress/callbacks и идемпотентность | AI-03, AI-11 | Event ID/sequence/retries/result без дублей | P0 |
| [AI-13](./AI-13_MAIN_BACKEND_INTEGRATION.md) | Внутренний transport adapter | AI-03, AI-11, AI-12, решение transport/auth | Один выбранный REST **или** gRPC contract | P0 · decision |
| [AI-14](./AI-14_OBSERVABILITY_AND_AUDIT.md) | Логи, tracing и технический audit | AI-04, расширяется после AI-11/12 | Correlation, latency, tool log без секретов | P1 |
| [G02](./G02_DURABLE_INTEGRATION_GATE.md) | Надёжность и межсервисная интеграция | AI-10…AI-14 | Crash/duplicate/cancel/callback integration suite | Gate |
| [AI-15](./AI-15_FAULT_SCENARIOS_AND_EVALS.md) | E-commerce faults и Evals | AI-08, AI-09, позже AI-13 | Повторяемые сценарии и отчёт о точности/ошибках | P0/P1 |
| [AI-16](./AI-16_OPTIONAL_RAG.md) | Qdrant, embeddings, reranking | G01, AI-15 baseline | Retrieval offline benchmark и `search_docs` (если принято) | **P2 optional** |
| [AI-17](./AI-17_OPTIONAL_INTENT_ROUTER.md) | Fast classifier/RAG gate | AI-16, данные для разметки | Измеримый accuracy/latency, safe fallback | **P2 optional** |
| [AI-18](./AI-18_RELEASE_HARDENING.md) | Финальная проверка | G01, G02, AI-15 | Воспроизводимый MVP demo, checks, readme | P1 |
| [G03](./G03_FINAL_ACCEPTANCE_GATE.md) | Приёмка MVP | AI-18 | Sign-off: no fabricated evidence, correct delivery, docs | Gate |

**Первый маршрут MVP:** **AI-01 → AI-02 + AI-03 → AI-04 + AI-05 → AI-06 → AI-07 → AI-08 + AI-09 → G01 → AI-10 → AI-11 → AI-12 → AI-13 → G02 → AI-15 → AI-18 → G03.** `AI-14` развивается рядом с соответствующими этапами. `AI-16/17` — отдельная ветка улучшений, не условие G03.

Подробная зависимость и допускаемая параллельность: [EXECUTION_SCHEME.md](./EXECUTION_SCHEME.md).

## 5. Порядок действий разработчика в Codex

**Одна Story — один логический worktree/ветка — одна свежая сессия Codex — тесты — ревью — PR.** Не отправлять все задачи одним мегапромптом. BMad как метод планирования/acceptance, **не устанавливать** CLI или `_bmad/`.

1. **Проверить Git:** текущая ветка, `git status`, запущенные Codex сессии, несохранённые изменения. Если AI-01 ещё выполняется — не трогать её файлы. Не начинать зависимую Story до результата и интеграции предшествующей.
2. **Прочитать:** `AGENTS.md`, `docs/00_START_HERE.md`, `docs/tasks/README.md`, `docs/tasks/QUALITY_GATE.md`, **один нужный** `AI-XX*.md`, и только релевантные контракты, перечисленные в ней.
3. **Analysis:** найти уже существующую реализацию, зависимости, affected files, контракты. Кратко сформулировать план из небольших шагов. Не переименовывать существующий `src/ai_agent` в новый шаблон без реальной причины.
4. **Implementation:** работать только в рамках Story; прежде тесты и domain / contract interface, потом инфраструктура, потом integration. Не трогать другие сервисы команды.
5. **Verification:** `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` и соответствующие real-smoke/integration команды только при наличии зависимостей. Не объявлять live проверку успешной, если была выполнена на fake adapter.
6. **Security review:** выполнить чек-лист `QUALITY_GATE.md`: source refs, untrusted tools, leakage, бюджеты, ошибки, повторы, контракты.
7. **PR/review:** одна Story → один PR с тестами, достигнутым DoD, точными командами и известными ограничениями. **Без push/merge по инициативе агента** — только при разрешении человека и по принятому GitFlow.
8. **Граница:** если встречено открытое решение — завершить нейтральную часть и открыть конкретный decision request из `DECISIONS_TO_APPROVE.md`, а не «угадывать» решение.

**На конец каждого шага Codex возвращает:** (a) планируемое vs фактическое; (b) изменённые файлы; (c) реальные результаты тестов; (d) демонстрационный сценарий; (e) зависимости/блокеры; (f) какой `AI-XX` следующий.

## 6. Как проверить готовность на gate

- **G01 / локальное расследование:** граф действительно завершает run, вызывает fake MCP, фиксирует реальные для теста source_refs, строит до трёх гипотез и RCA или честный inconclusive, соблюдает budget/cancel/error; отдельный живой smoke с Qwen не подменяет полностью детерминированные тесты.
- **G02 / долговременность:** PostgreSQL checkpoints + registry корректно восстанавливают execution, duplicate Start не создаёт новый run, callbacks идут с устойчивой идемпотентностью, transport утверждён, Main Backend принимает результат и не делает автоматический resolve.
- **G03 / сдача:** приложение и проектные демо-инциденты воспроизводимы, доки соответствуют коду, нет необъяснимых ложных Evidence, все критические проверки проходят, открытые решения зафиксированы, optional RAG не навязан MVP.

## 7. Правила проекта, которые нельзя нарушать

- LangGraph **один ReAct агент**; не заменять multi-agent framework без ADR.
- Qwen2.5-Coder-7B-Instruct через **llama.cpp**, без Ollama. Сначала проверять реальные tools capability, а не считать каждую версию llama.cpp/шаблон заведомо рабочими.
- MCP Streamable HTTP, не самодельный `POST /mcp/tool_name`; tools — только **read-only** с типизированными аргументами, project/environment scope и лимитами.
- **20 шагов / 40 tool calls / 1200 секунд**, один active run per executor (для MVP). Серверные лимиты обязательны, в prompts их недостаточно.
- Evidence с источником и provenance; **не генерировать** timestamps, source URLs, tool results, confidence без основания; инцидент может завершиться `inconclusive`.
- Cancel — кооперативная; Retry → **новый investigation_id**; терминальные статусы не переписывать.
- Main Backend владеет Incident, User/Auth/RBAC, Review; **AI не отправляет браузерные WebSocket** и не реализует email OTP.
- Длительный run не исполняется в FastAPI request и не полагается **только** на `BackgroundTasks`.
- No RabbitMQ между сервисами; не добавлять произвольные инструменты shell/SQL/Docker exec, доступы к секретам, обновления продакшена.
- `docs/contracts/` v0.2 — draft; никакого самостоятельного создания финального REST/gRPC wire-format.

## 8. Итог: что получим по фазам

| Фаза | Проверяемый конечный продукт |
|---|---|
| Foundation + AI-01…04 | Qwen вызывается из графа; контролируемый state/reasoning/action loop с детерминированными тестами |
| MCP + AI-05…09 + G01 | Локальный расследователь: safe tools → evidence → гипотезы → RCA / inconclusive под budget |
| Durable + AI-10…14 + G02 | Устойчивый к рестартам executor и единый выбранный API для Main Backend; прогресс и финальный результат доставляются безопасно |
| AI-15 + AI-18 + G03 | Демонстрационные e-commerce инциденты и воспроизводимая оценка качества; MVP готов к командной интеграции/защите |
| AI-16…17 (по решению) | Документный RAG, reranking, классификатор, только если измерено улучшение |

## 9. Шаблон следующего сообщения в Codex

```text
Продолжай проект AI Incident Investigator в этом репозитории. Сначала прочитай
AGENTS.md, docs/00_START_HERE.md, docs/tasks/README.md,
docs/tasks/QUALITY_GATE.md и файл задачи docs/tasks/AI-XX_....md.
Изучи текущий код и git status, проверь закрытие зависимостей этой Story.
Сначала дай краткий план, затем реализуй ТОЛЬКО AI-XX. Не менять контракты v0.2
самостоятельно; не выбирать за команду REST/gRPC, MCP-owner или auth.
Прогони тесты/линтер; отдельно сообщи, что реально тестировалось на живой
Qwen/PostgreSQL/MCP, а что на fake. Проверь Acceptance Criteria и Quality Gate.
Сформируй отчёт: изменения, команды, результаты, риски, следующая Story.
Не выполняй push/merge без разрешения.
```

Для AI-01, которая уже идёт в Codex, **не запускай второй параллельный промпт**; дождись её фактического результата, зафиксируй в PR и только потом переходи к AI-02/AI-03.
