# AI-04. Один управляемый LangGraph ReAct loop

**Приоритет:** P0  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-02 capability verdict, AI-03 typed DTO  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/02_AI_SCOPE_AND_ARCHITECTURE.md`, `03_AI_DELIVERY_PLAN.md`, `docs/contracts/06_MCP_CONTRACTS.md`

## Зачем и что должно получиться

Собрать логический LangGraph `context → decision → (validate/action/result)* → finalization`, который можно полностью проверить **без настоящей модели и без живой инфраструктуры**. При этом один агент сам решает, какие инструменты уместны; жёсткого обхода всех MCP tools нет.

## Объём работы

1. Явные graph state поля: run id, scope, context, message/action history, tool-call counters, budget, normalized observations, evidence, terminal status.
2. Узлы: ingest/restore, decision, validate intended action, tool execution port, normalization, next decision, final outcome. Делать только реально нужные узлы, без boilerplate.
3. Внедряемый fake decision provider и fake tool executor; deterministic transitions и branching.
4. Некорректные LLM structured responses: bounded repair или финальный controlled failure/inconclusive.
5. Нет исполнения инструмента до schema/scope check.
6. Прозрачный event summary «что агент сделал», но **без chain-of-thought**.
7. Не связывать граф напрямую с FastAPI, docker и БД.

## Не входит

Промышленный MCP Server, динамические permissions, PG checkpoints, HTTP callbacks, RAG, Multi-agent planner.

## Acceptance Criteria

1. Graph может выбрать 0/1/несколько действий, затем завершиться.
2. Неправильное имя/аргументы никогда не вызывают реальный executor.
3. Empty/partial/error observations обработаны.
4. State воспроизводим при одинаковых fake inputs.
5. Нет бесконечного цикла и скрытых side effects.
6. Документирована связь state ↔ доменные модели AI-03.

## Проверки и негативные сценарии

Unit: no tool needed, valid sequential tools, tool error, invalid response, repeated action, unavailable tool, inconclusive; все тесты без llama.cpp и MCP network.

## Результат передачи / выходной контракт

Чистый агентный движок, готовый к AI-06 и AI-09, с текстовым примером пути состояний в README/Story отчёте.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.

## Особые замечания

Если AI-02 показала нестабильность native function calling, нельзя скрыто обходить результаты эксперимента: сначала одобрить безопасную схему action DTO / adapter.
