# AI-13. Интеграция с Main Backend по утверждённому транспорту

**Приоритет:** P0 · BLOCKED BY DECISION  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-03, AI-11, AI-12; **approved transport + internal auth**  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/contracts/05_INTERNAL_BACKEND_AI.md`, `10_OPEN_DECISIONS.md`, `openapi/ai-backend-rest-candidate.openapi.yaml`, `proto/ai-backend-candidate.proto`, `08_SECURITY_AND_ERRORS.md`

## Зачем и что должно получиться

После **совместного решения с Юрием** реализовать один production transport adapter для операций `Start`, `GetStatus`, `Cancel`, event/result delivery, optional readback. Любое спорное поле проекта сначала согласовывается.

## Объём работы

1. Получить ADR REST vs gRPC, service identity/auth, callback endpoint ownership, timeouts/status codes.
2. Реализовать **один** выбранный протокол и typed adapter вокруг AI-11/12; не дублировать бизнес-логику в transport.
3. Входной validation/dedup/authorization check; `Start` отвечает после durable ack, не держит HTTP до готового RCA.
4. `GetStatus`, `Cancel`, error envelope, request IDs, retries и idempotency handling.
5. Исходящие progress/results соответствуют v0.2-draft либо утверждённой новой ревизии; вызов не раскрывает секреты.
6. Contract tests совместно с Main Backend (matching DTO/proto/OpenAPI), end-to-end mock receiver.
7. Backend remains owner incident/review/OTP/user JWT. Не создавать browser WS в AI.
8. Если decision не принято — закончить только transport-neutral groundwork и обозначить Story как blocked.

## Не входит

Автоматически выбирать REST, одновременная полная реализация REST и gRPC, login/email OTP на AI, прямой frontend API.

## Acceptance Criteria

1. Выбранный adapter покрывает Start/Status/Cancel и доставку результата.
2. Auth ошибку отклоняет без side effects.
3. Duplicate Start получает тот же зарегистрированный run.
4. Работа выполняется асинхронно и восстанавливается.
5. Contract round trip согласован с Main Backend.
6. Нет несанкционированных полей/адресов и утечки данных.

## Проверки и негативные сценарии

Mock peer integration: wrong auth, duplicate ID, timeout, callback lost, cancel/complete race, invalid schema, protocol-specific deadline. Совместные smoke с backend owner после появления среды.

## Результат передачи / выходной контракт

Утверждённый internal API AI Backend и взаимодействие с Main Backend, без перехода на произвольный новый архитектурный транспорт.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
