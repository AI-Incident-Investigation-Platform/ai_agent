# AI-09. Execution budgets, cooperative cancel и error policy

**Приоритет:** P0  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-04 и AI-06; желательно интегрировать до G01  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/02_AI_SCOPE_AND_ARCHITECTURE.md`, `docs/contracts/05_INTERNAL_BACKEND_AI.md`, `08_SECURITY_AND_ERRORS.md`

## Зачем и что должно получиться

Ограничить агента серверными правилами: **20 шагов, 40 инструментальных вызовов, 1200 секунд** по умолчанию. Обеспечить управляемый выход `timed_out/canceled/failed/inconclusive` без потери полезного контекста.

## Объём работы

1. Конфигурируемые budgets с утверждёнными maximum clamps и явными расходами, учитывающими retry/failed calls по согласованному правилу.
2. Before each decision/tool call — проверка шагов, времени, cancellation flag, scope.
3. Цикл не делает бесконечных tool calls, даже при malformed LLM output или повторяющихся рекомендациях модели.
4. Cooperative cancellation + graceful checkpoints interface; терминальные переходы только один раз.
5. Deadline propagation к llama.cpp/MCP HTTP; retry bounded/backoff, не перекрывать общий budget.
6. Partial Evidence при отмене/таймауте разрешена, но не фальсифицировать completed.
7. Избегать неопределённой многопоточности: MVP 1 active run per executor закрепляется в AI-11.

## Не входит

Долговременный registry и worker leases (AI-11), реальные checkpoint migrations (AI-10), политическая трактовка busy-run без решения команды.

## Acceptance Criteria

1. 21-й шаг или 41-й вызов не запускаются.
2. Hard timeout корректно завершает run.
3. Cancel останавливает до следующего tool call.
4. Terminal-state race не приводит к двойному completed.
5. Partial evidence сохраняется в доступном state.
6. Результаты тестов воспроизводимы с fake clock/LLM.

## Проверки и негативные сценарии

Unit fake time/timer, tool retry counting, cancel-before-action, cancel during LLM, tool timeout, invalid output repair, simultaneous cancel/finish. Не ждать 1200 реальных секунд в тестах.

## Результат передачи / выходной контракт

Controlled execution boundary, необходимая для честного G01 и для AI-11 durable runner.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
