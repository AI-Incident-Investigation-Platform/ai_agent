# AI-08. RCA report, timeline и terminal validation

**Приоритет:** P0  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-07  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/contracts/schemas/rca-report.schema.json`, `ai-result-callback.schema.json`, `examples/rca-report.json`, `docs/contracts/05_INTERNAL_BACKEND_AI.md`

## Зачем и что должно получиться

Формировать финальный результат расследования: symptoms, probable root cause, до трёх evidence-linked гипотез, timeline и next actions. **На слабых данных итог должен честно говорить `inconclusive`**, не изображая уверенную диагностику.

## Объём работы

1. Typed RCA assembler/validator, привязка ключевых утверждений к evidence ID/source_refs; проверка связей.
2. Bounded structured LLM generation + Pydantic validation; невалидный output имеет лимит попыток repair.
3. Описание root-cause claim отдельно от symptoms/correlations; поддержка null/uncertain root cause.
4. Timeline: реальные timestamps из observations/events, сортировка и provenance; не выдумывать точное время.
5. Рекомендации только как предложения человеку, никакого автоматического изменения production.
6. Terminal statuses completed/inconclusive/failed/timed_out/canceled по согласованным схемам; partial evidence допустим по контракту.
7. Отображаемое human-action summary без LLM hidden reasoning; Main Backend делает human review и управляет resolved.

## Не входит

Human approve/reject, Main Backend таблицы и UI, автолечение или выдуманные уверенности, принудительная точная RCA для любого инцидента.

## Acceptance Criteria

1. RCA проходит draft schema и ссылается только на фактические evidence.
2. Когда данных мало — valid `inconclusive`.
3. Ошибка parsing не вызывает бесконечный repair.
4. Timeline содержит подтверждённые times/source links.
5. Terminal report отражает partial failure правильно.
6. Рекомендации не исполняются агентом.

## Проверки и негативные сценарии

Тесты: known root-cause fake case, insufficient evidence, contradictory cases, invalid hallucinated source, incorrect RCA JSON, absent optional fields, failed/canceled report=null.

## Результат передачи / выходной контракт

RCA assembler и finalization node, пригодные для G01 и будущей AIResultCallback delivery.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
