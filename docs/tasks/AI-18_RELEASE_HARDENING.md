# AI-18. Release readiness и end-to-end стабилизация

**Приоритет:** P1  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** G01, G02, AI-15, AI-14 интегрированы  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/03_AI_DELIVERY_PLAN.md`, `docs/contracts/14_CONTRACT_VALIDATION.md`, `AGENTS.md`, `docs/GITFLOW.md`

## Зачем и что должно получиться

Свести реализованные Stories к воспроизводимому AI Backend MVP: локальный запуск, durable investigation, инструментальная диагностика, validated result delivery и repeatable fault demos без ручной магии.

## Объём работы

1. Документировать установку (uv, Python target, llama.cpp Metal/server), env, запуск FastAPI, worker, PostgreSQL, MCP endpoint и тесты.
2. Pin совместимые версии нужных библиотек, обновить lockfile; не требовать на старте live MCP/LLM для базового `/health`.
3. Обновить operator runbook: start/cancel/retry, connection issues, checkpoint recovery, callback reconciliation, readiness.
4. Сквозные проверки из AI-15, contract/schema tests, security review и failure drills.
5. Проверить конфигурацию secrets, logging retention, log redaction, access, immutable source IDs.
6. Проверить устаревшие docs/README, но не переписывать AGENTS.md без согласования.
7. Чётко разделить реализованное, отсутствующее, mock и P2. Подготовить краткий demo script и известные ограничения.
8. Проверить, что AI output не переводит Incident в resolved и нет side effects.

## Не входит

Присвоение v1-done контрактам v0.2 без review, внедрение optional P2 как requirement, автономные production fixes, переделка чужих репозиториев.

## Acceptance Criteria

1. Новому разработчику понятно как запустить и протестировать систему.
2. Все P0 tests и contract checks проходят на зафиксированной среде.
3. Демо воспроизводится, есть documented known limitations.
4. Нет критичных нарушений read-only/provenance.
5. Каждый live вывод подтверждён реальным запуском.
6. G03 может принять конкретный commit как release candidate.

## Проверки и негативные сценарии

Manual+automated regression: clean setup, no llama model on start, no MCP, no PG, cancel during run, callback failure, prompt injection, eval suite, secret scan. Сохранять логи команды только без приватных данных.

## Результат передачи / выходной контракт

Release-candidate commit и доказательная приёмка G03, без необоснованного заявления о production-grade reliability на одном ноутбуке.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
