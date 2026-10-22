# AI-17. P2: Intent classifier / RAG gating

**Приоритет:** P2 OPTIONAL  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-16 и размеченные маршрутизируемые запросы  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** AI-16 benchmarks, product user intents, `docs/02_AI_SCOPE_AND_ARCHITECTURE.md`

## Зачем и что должно получиться

Классификатор нужен **только если** он надёжно улучшит выбор между `diagnostics`, `knowledge`, `hybrid`, `unsupported`, `clarification` и не будет скрывать от агента необходимые фактические источники. Важнее false-negative safety, чем модель «ради модели».

## Объём работы

1. Сначала baseline правила+domain routing и deterministic tests.
2. Разметить корпус request/route примеров, разделить train/validation/test по смыслу, чтобы не протекали дубликаты.
3. Сравнить CPU fastText, multilingual DistilBERT, fine-tuned XLM-RoBERTa (последний только при достаточной скорости и качестве).
4. Задать threshold/confidence calibration, low confidence→hybrid/clarification, fail-open для разрешённых diagnostics (без обоснованного отказа).
5. Чистый Router API с timeouts, inference CPU, versioned model artifact, feature flags и fallback без модели.
6. Измерять precision/recall/F1, per-class confusion, inference p50/p95 и RAM на целевой машине.
7. Prompt injection / adversarial text / multilingual mix; не давать недоверенному документу определять маршрут как системную команду.

## Не входит

Запрет MCP при слабом классификаторе, обучение XLM-R «по умолчанию», обязательное обучение classifier до первого рабочего агента.

## Acceptance Criteria

1. Route classes объяснимы, тестируемы и совпадают с поведением приложения.
2. Low confidence не создаёт необоснованный жёсткий `NOT RAG`.
3. Есть baseline сравнение и held-out evaluation.
4. CPU inference p95 и memory измерены в реальной среде.
5. Feature flag полностью отключает classifier без падения агента.
6. P2 не блокирует G03 MVP.

## Проверки и негативные сценарии

Misroutes: real-time vs runbook, hybrid mixed requests, irrelevant request, insufficient context, RU/EN, service IDs. Без размеченных данных отложить Story — нельзя объявить fine-tune выполненным.

## Результат передачи / выходной контракт

Сменный intent router с реальными цифрами; adoption только после сравнения с простыми правилами и текущим агентом.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
