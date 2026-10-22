# AI-15. Демо-инциденты, regression evals и baseline качества

**Приоритет:** P0/P1  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-08 и AI-09; полноценный сервисный E2E после G02  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/03_AI_DELIVERY_PLAN.md`, `docs/01_PROJECT_BRIEF.md`, `docs/contracts/03_DOMAIN_MODELS.md`

## Зачем и что должно получиться

Сформировать измеримый тестовый набор расследований по известным неисправностям e-commerce. Оценивать не красоту ответа, а **правильность инструментов, evidence grounding, честное inconclusive, устойчивость и время**.

## Объём работы

1. Согласовать с Infra 6 сценариев: PostgreSQL pool exhaustion, bad deployment, latency cascade, OOM/restarts, RabbitMQ consumer lag, DragonflyDB outage. Здесь RabbitMQ **является диагностируемой системой**, не транспортом AI Backend.
2. Для каждого кейса: конфигурация среды, точная ground truth root cause, симптомы, time window, источники/IDs, expected Evidence, допустимый итог.
3. Два набора: deterministic fixture eval (без серверов) и optional live smoke с настоящими sources/model.
4. Измерять schema validity, evidence precision/unsupported claims, correct incident root cause, tool selection, invalid tool calls, time-to-diagnosis, limit violations, inconclusive calibration.
5. Сохранить результаты и environment provenance: commit, seed, model GGUF, llama.cpp build, hardware, repeated runs sample count.
6. Не выдавать 1 успешный прогон за доказанную accuracy. Добавить regression suite для prompt/tool changes.
7. В eval failures выводить примеры, какие claims/links не подтвердились.

## Не входит

Production fixes, выдуманные «реальные» логи, тесты против чужих сред без разрешения, обязательный RAG до baseline.

## Acceptance Criteria

1. Есть воспроизводимые fixture datasets с известной ground truth.
2. Запуск eval CLI выдаёт машинно-читаемые outcomes.
3. Unsupported Evidence пойман evaluator.
4. Отчёт отделяет offline/mock от live.
5. Нет устойчиво незавершённых run или превышения budget.
6. Минимум один inconclusive test case.

## Проверки и негативные сценарии

Повторные прогон fake/real Qwen по fixed cases, malformed partial data, contradictory source, tool failure, timeout, wrong root cause. Evals не требуют полного инфраструктурного стенда по умолчанию.

## Результат передачи / выходной контракт

Baseline отчёт для защиты проекта; основа решения, имеет ли смысл AI-16 RAG и AI-17 классификатор.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
