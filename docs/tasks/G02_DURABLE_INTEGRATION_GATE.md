# G02. Durable execution + Main Backend integration gate

**Зависимости:** AI-10, AI-11, AI-12, AI-13, AI-14, G01.  
**Блокеры решений:** REST vs gRPC, service auth, PG ownership, busy strategy, final readback policy.

## Цель

Доказать, что investigation надёжно регистрируется, переживает restart, продолжает безопасно или заканчивается понятным failure, а progress/result по **одному выбранному API** доставляется Main Backend с идемпотентностью.

## Сценарии

1. Start → durable persisted ack → run started → progress sequence → final callback.
2. Duplicate Start с тем же investigation_id/idempotency key → не создан новый run.
3. Kill worker между двумя шагами → checkpoint recovery/controlled failure.
4. Cancel одновременно с complete → одна терминальная запись; partial state available.
5. Callback 503 + timeout + duplicate ACK → один и тот же event_id при retries.
6. Callback loss → согласованная readback/reconciliation path, нет потерянного результата.
7. No auth / invalid identity → 401/403 или эквивалентное поведение выбранного протокола.
8. Two executor competition → не более одного active run при выбранной admission policy.

## Criteria

- [ ] Существуют утверждённые ADR и обновлённые соответствующие wire contracts.
- [ ] Не используется RabbitMQ между AI↔Main Backend.
- [ ] Никаких длинных in-request runs и in-memory-only durability.
- [ ] Дубликаты событий/результатов не создают новую историю.
- [ ] Восстановление после рестарта продемонстрировано с реальной PG, не просто fake.
- [ ] Main Backend не требует direct browser WS от AI.
- [ ] Логи не содержат токенов/secret fragments.
- [ ] Unit/contract/integration checks прошли с явными командами.

**Выход:** report G02 PASS/FAIL, версии согласованных контрактов, фактическая end-to-end трасса тестового инцидента.
