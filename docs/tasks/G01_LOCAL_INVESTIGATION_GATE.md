# G01. Local investigation gate — first complete investigation

**Зависимости:** merged AI-01…09 (минимально необходимая функциональная вертикаль).  
**Принимает:** AI разработчик, независимое code review.  
**Не требует:** реальный PostgreSQL, Main Backend, живой Elasticsearch, RAG.

## Цель

Один полный **детерминированный** run через LangGraph: context→tool calls→evidence→hypotheses→RCA или inconclusive. Живую Qwen использовать отдельным smoke для подтверждения действительного model integration; не подменять им unit и contract tests.

## Сценарии

1. `payment-service`: PG connection pool 100%, 5xx, недавний deployment, согласованные fake logs/metrics/traces. Проверить, что RCA ссылается на точные fake source IDs.
2. Inconclusive: доступно только поверхностное сообщение без достоверных источников — нет уверенного root-cause claim.
3. Tool error/partial/truncated: нет выдуманных фактов, граф корректно завершается.
4. Запрошен неизвестный/неразрешённый инструмент → отбой до MCP transport.
5. Превышение шага/tool/deadline и cancel → bounded termination.

## Criteria

- [ ] Все paths имеют определённое terminal outcome и не зацикливаются.
- [ ] RCA и Evidence проходят валидаторы v0.2-draft.
- [ ] Нет source refs, которых не было в tool results.
- [ ] `inconclusive` возникает при недостатке данных.
- [ ] Не более 20 шагов/40 tool calls/1200 сек по runtime code.
- [ ] Не раскрывается chain-of-thought, creds и необработанные injection instructions.
- [ ] `pytest`, `ruff check`, `ruff format --check` проходят.
- [ ] Утверждения о live LLM отдельно подтверждены.

**Выход:** датированный отчёт «G01 PASS/FAIL», commit/PR, actual tests и открытые блокеры. Только после PASS переходить к durable phase как к интегрированному локальному расследователю.
