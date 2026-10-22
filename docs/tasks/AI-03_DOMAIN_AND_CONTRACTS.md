# AI-03. Pydantic domain DTO, state transitions и contract tests

**Приоритет:** P0  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-01 merged; независима от AI-02  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/contracts/03_DOMAIN_MODELS.md`, `05_INTERNAL_BACKEND_AI.md`, `schemas/{domain,ai-start-request,ai-events,ai-result-callback,rca-report}.schema.json`, `docs/contracts/examples/`

## Зачем и что должно получиться

Один typed домен для `investigation_id`, lifecycle, `Hypothesis`, `Evidence`, `RCAReport`, `InvestigationEvent`, `AIResultCallback`, лимитов и ошибок. Изолировать бизнес-модели от REST/gRPC и LLM parsing.

## Объём работы

1. Провести инвентаризацию существующих DTO и реального shape v0.2-draft.
2. Добавить Pydantic v2 models (и внутренние domain типы, где нужно) с валидацией UUID, timestamps, enums, scope, count≤3, optional report для terminal states по схеме.
3. Отделить external DTO и внутреннее LangGraph state mapper; не зашивать HTTP объект в graph.
4. Явно реализовать допустимые state transitions, запрет terminal→terminal, idempotent repeated state checks.
5. Contract tests против `docs/contracts/examples/*` и `$defs`, а также негативные несовместимые payloads.
6. Не менять canonical JSON Schema, если тест выявил расхождение: показать несостыковку и предложить согласование.

## Не входит

Любой реальный transport endpoint; миграции базы; реальная доставка callbacks; решение REST/gRPC.

## Acceptance Criteria

1. Валидные examples парсятся по v0.2-draft.
2. Заведомо неверные payloads отклоняются.
3. Domain не импортирует FastAPI и MCP transport.
4. Terminal semantics, Retry new ID и ограничения hypotheses зафиксированы тестами.
5. Несоответствия исходным контрактам перечислены, не замаскированы.

## Проверки и негативные сценарии

Schema/examples round trip; invalid UUID/time, 4 hypotheses, absent source locator where required, invalid terminal report, illegal transition; test mapping to/from internal state.

## Результат передачи / выходной контракт

Единый типизированный фундамент для AI-04, AI-05, AI-06 и AI-12/13; список open contract mismatches на ревью.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
