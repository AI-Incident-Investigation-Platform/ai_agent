# AI-14. Логи, метрики, tracing и технический audit

**Приоритет:** P1  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-04; завершается после AI-11/12  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/02_AI_SCOPE_AND_ARCHITECTURE.md`, `docs/contracts/08_SECURITY_AND_ERRORS.md`, `docs/03_AI_DELIVERY_PLAN.md`

## Зачем и что должно получиться

Сделать сами AI-расследования наблюдаемыми: можно диагностировать latency каждого узла, tool call, LLM request, ошибки checkpoint/delivery, бюджет run — без записи секретов и скрытых рассуждений модели.

## Объём работы

1. Correlation: trace/request ID, investigation_id, tool call ID, event sequence по всей цепочке.
2. Structured logs для start/finish/fail/cancel, action name, duration, capped output size и retry outcomes.
3. Latency и counters LLM/tool, failure rate, pending runs, checkpoint save failures и callback retries (через OpenTelemetry/Prometheus-style hooks либо выбранный lightweight механизм).
4. Raw log excerpts, credentials, LLM chain-of-thought и PII не писать в logs.
5. Отличать технический execution audit от **User Audit Log**: последний относится к Main Backend/RBAC и не входит в текущую AI Story.
6. Добавить минимальные health/readiness проверки, не путать существующий `/health` с подтверждением живого MCP/LLM.
7. Режим тестов не отправляет реальные telemetry во внешний collector без явной конфигурации.

## Не входит

Большой observability stack в этом репозитории, отдельный User Audit Log backend, полный Grafana dashboard без среды, trace raw prompts.

## Acceptance Criteria

1. По одному investigation ID можно восстановить последовательность технических действий.
2. Нет токенов/секретов в логах.
3. Метрики дают длительность, ошибки, ограничение шагов.
4. Health и readiness имеют корректную семантику.
5. Тесты воспроизводят лог без внешней infra.

## Проверки и негативные сценарии

Capture logs tests, secrets injection, fake clock, callbacks retry metrics, trace context propagation, malformed tool result, connection down.

## Результат передачи / выходной контракт

Наблюдаемый, безопасный execution lifecycle и краткая инструкция диагностики для Infra/Backend.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
