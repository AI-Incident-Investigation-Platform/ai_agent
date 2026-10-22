# AI-16. P2: Qdrant + Embeddings + Reranker

**Приоритет:** P2 OPTIONAL  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** G01, baseline AI-15, отдельное решение о необходимости RAG  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/contracts/06_MCP_CONTRACTS.md` (P2 `search_docs`, `search_similar_incidents`), `docs/03_AI_DELIVERY_PLAN.md`, decision register

## Зачем и что должно получиться

Добавить **knowledge retrieval**, не подменяя живую диагностику: поиск по runbooks, прошлым RCA и архитектурным документам. Измерить, даёт ли RAG лучший результат, чем текущий LangGraph+MCP baseline.

## Объём работы

1. Определить corpus и privacy/retention: runbooks, docs, approved past RCA; исключить secrets и raw private logs без согласования.
2. Offline индексатор: parsing, chunking с source metadata, версионность документов, dedup, incremental reindex.
3. Сравнить **Qwen3-Embedding-0.6B** и **BGE-M3** на собственном benchmark: recall@k, latency, RAM, mixed RU/EN, exact identifiers. Модели — кандидаты, не утверждение качества.
4. Qdrant collection(s), фильтрация project/environment/access; scopes server-side.
5. Rerank только top-K при реальной пользе: **GTE multilingual reranker**, **BGE-reranker-v2-m3** или **Qwen3-Reranker-0.6B** — сравнить latency/quality и memory footprint.
6. Результаты возвращать структурированными с provenance и permission checks; по согласованию интегрировать tools `search_docs` и `search_similar_incidents` через MCP.
7. Не смешивать live telemetry/metrics/traces с docs vector memory: они остаются в первичных системах.
8. Учитывать resource contention с Qwen 7B на Mac; encoder models запускать отдельным runtime/on demand при необходимости.

## Не входит

RAG как обязательный путь для любого запроса; рекомендация модели без измерений; самовольное включение чужих RCA; пользовательский чат-бот вне scope.

## Acceptance Criteria

1. Воспроизводимый retrieval benchmark и baseline без reranker.
2. Output содержит original document IDs/urls/chunk spans, не fake citations.
3. Access/project filtering проверен.
4. Empty/no permission даёт пустой безопасный ответ.
5. Команда сравнила качество с/без RAG на eval cases и явно решила подключение.
6. MVP G03 остаётся независимым от P2.

## Проверки и негативные сценарии

Offline benchmark: 50+ размеченных query-doc пар по мере доступности корпуса; если корпуса/разметки нет — task blocked, не выдумывать score. Runbook old/new, RU/EN, exact service name, permission leak, long chunk, index drift.

## Результат передачи / выходной контракт

Отдельный P2 модуль, который можно выключить флагом и без него сохранить расследование; реальный выбор embedding/reranker сделан по замерам.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
