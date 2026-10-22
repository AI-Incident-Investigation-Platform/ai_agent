# G03. AI Backend MVP — финальная приёмка

**Зависимости:** G01, G02, AI-15, AI-18. **AI-16/AI-17 НЕ обязательны**.

## Критерии

1. Локальный AI Backend с FastAPI/worker запускается с документированными env settings; база/LLM/MCP конфигурируются независимо.
2. AI работает как **один** LangGraph ReAct-агент, не вызывает незаявленные инструменты и соблюдает runtime budgets.
3. При доступной диагностике выполняет tool calls, собирает evidence, выдаёт до 3 гипотез и RCA с источниками.
4. При неполных, ошибочных и противоречивых данных выдаёт честный `inconclusive`/error, а не уверенно сочиняет причины.
5. Read-only security: нет shell/SQL/Docker exec/writes/rollback, есть scope allowlists, redaction и prompt-injection handling.
6. PostgreSQL checkpoints + run registry восстанавливают/закрывают незавершённые investigation after crash.
7. Межсервисный API определён командой (REST или gRPC), callback/idempotency/test contracts согласованы с Main Backend.
8. Main Backend остаётся владельцем Incident/Auth/Review/WS. AI не закрывает инцидент самостоятельно.
9. Регрессионные сценарии AI-15 имеют точную ground truth, повторяемые результаты и зафиксированные false positives / limitations.
10. `pytest`, Ruff, integration suite и docs/runbooks проходят по фактическим командам; состояние code review и ADR явно известно.

## Что предоставить на защите

- Список commit/PR и версии моделей/инфры.
- Краткая архитектурная схема и последовательность AI run.
- Один успешный fault-demo и один `inconclusive` demo с реальными/помеченными fake Evidence.
- Crash/recovery и callback retry демонстрация.
- Таблица P0 выполнено / blocked / not started; P2 отмечено отдельно.
- Отчёт quality gate и известных ограничений.

**Результат:** `G03 PASS` означает **готовность MVP AI Backend к проектной демонстрации и интеграции**, а не автоматическое заявление о production deployment без эксплуатационных тестов.
