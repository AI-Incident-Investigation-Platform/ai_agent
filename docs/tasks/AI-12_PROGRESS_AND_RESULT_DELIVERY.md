# AI-12. Event/outbox, delivery retries и terminal result

**Приоритет:** P0  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-03, AI-11  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/contracts/05_INTERNAL_BACKEND_AI.md`, `schemas/ai-events.schema.json`, `ai-result-callback.schema.json`, `examples/ai-event.tool-completed.json`, `ai-result.callback.json`

## Зачем и что должно получиться

Сделать последовательные, повторно доставляемые progress events и итоговый `AIResultCallback`, пригодные для Main Backend. Сеть может падать; данные и последний результат не должны теряться.

## Объём работы

1. Доменное событие имеет `event_id`, `investigation_id`, монотонный `sequence` в рамках run, timestamp, bounded/redacted payload.
2. Durable outbox/delivery state либо другой **согласованный надёжный механизм**; commit run state и запись outgoing event без окна потери.
3. Callback retries exponential backoff / bounded attempts; **те же event_id/sequence** при повторах; distinguish retryable 5xx/network и non-retryable 4xx/schema.
4. Terminal result соответствует v0.2-draft, может включать partial Evidence и failed state.
5. Дедуп и in-order semantics: источник sequence монотонный, consumer обязан принимать duplicate/out-of-order по контракту.
6. Lost final callback reconciliation/readback — отдельно согласовать, не объявлять GET fallback уже утверждённым.
7. Не посылать пользователю WebSocket из AI. Backend persisting/forwarding отвечает Юрий.

## Не входит

Реальный браузерный WS, принятие Main Backend schema без review, полное постоянное хранение Incident на AI стороне.

## Acceptance Criteria

1. Два одинаковых callback имеют один event_id и sequence.
2. При 503 сообщение остаётся для повторной доставки.
3. При 422 схема не гоняется бесконечно.
4. Sequence не скачет/не повторяется ошибочно.
5. Final delivered лишь после устойчивой фиксации соответствующего terminal output.
6. Payload redacted и bounded.

## Проверки и негативные сценарии

Fake HTTP receiver, 503-then-202, timeout-then-ack, duplicate delivery, out-of-order injection, crash between finalization/send, invalid callback, secret in payload.

## Результат передачи / выходной контракт

Transport-neutral event publisher + durable delivery mechanism. AI-13 подключает согласованный протокол.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
