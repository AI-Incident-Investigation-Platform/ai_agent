# AI-11. Durable registry, admission control и recovery

**Приоритет:** P0 · BLOCKED BY DECISION  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-09, AI-10; требуется решение busy-run policy  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/02_AI_SCOPE_AND_ARCHITECTURE.md`, `docs/contracts/05_INTERNAL_BACKEND_AI.md`, `docs/contracts/10_OPEN_DECISIONS.md`

## Зачем и что должно получиться

Устойчиво принимать и исполнять **длительные до 20 минут** расследования вне HTTP request. Старты/отмены/результаты не должны теряться при рестарте сервиса. В MVP — **≤1 active run per executor**.

## Объём работы

1. Durable run registry c run ID, attempt, state, timestamps, lease/heartbeat, dedup, deadline; согласованная storage ownership.
2. Start принимает запрос только после durable registration; `202` допустим **только после записи**, если выбран REST.
3. Отдельный worker/executor: не полагаться на FastAPI BackgroundTasks как единственную гарантию.
4. Без RabbitMQ: worker может читать durable registry; exact polling/lease policy проектируется внутри выбранного решения.
5. Idempotent repeated Start with same ID/request key, new investigation_id for Retry.
6. Admission strategy при занятости (`429 Retry-After` **только кандидат**, либо durable waiting по решению команды).
7. Crash/restart recovery: resume безопасно или controlled terminal failure без бесконечного `running`.
8. Cancel requested → cooperative stop/terminal CAS; conflict cancel vs completion.
9. Продумать cap по memory, deadlines и остановку процесса; не изменять Main Backend domain.

## Не входит

Новый брокер, Celery/RabbitMQ, auto-resolve инцидента, механизм browser WS, неутверждённый overload policy.

## Acceptance Criteria

1. После restart ни один run не исчезает бесследно.
2. Duplicate Start не создаёт второй executor run.
3. Завершение/отмена атомарны и терминальны.
4. Конкурентная емкость ≤1; busy policy согласована.
5. Полезный partial state доступен после failure.
6. Test с двумя одновременно работающими executors не приводит к дублирующей работе.

## Проверки и негативные сценарии

Интеграционные: process killed mid-tool, lease expiry/reclaim, duplicate launch, cancel vs complete, PG outage, double executor, idempotency repeated call, terminal replay.

## Результат передачи / выходной контракт

Рабочий durable execution engine, независимый от транспорта AI-13. Существующие LangGraph checkpoints используются правильно, но не заменяют registry.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
