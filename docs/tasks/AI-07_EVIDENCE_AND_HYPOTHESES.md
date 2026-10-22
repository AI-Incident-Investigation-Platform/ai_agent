# AI-07. Evidence provenance и проверка гипотез

**Приоритет:** P0  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-04, AI-06  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `docs/contracts/03_DOMAIN_MODELS.md`, `schemas/domain.schema.json`, `schemas/mcp-results.schema.json`, `docs/02_AI_SCOPE_AND_ARCHITECTURE.md`

## Зачем и что должно получиться

Структурированно превращать реальные результаты MCP в Evidence, связывать до трёх гипотез с конкретными доказательствами и явно различать наблюдения, предположения и подтверждённую первопричину.

## Объём работы

1. Evidence хранит источник, service/project/environment scope, time window, locator/url/ID, excerpt, redaction/truncation flags, source_refs.
2. Стабильный ID для evidence; дедуп однотипных observation с сохранением source provenance.
3. Hypothesis status/confidence/evidence_for/evidence_against согласно draft domain schemas; hard max 3.
4. Проверять, что ссылка на Evidence действительно присутствует в run, разрешена для данного scope и подтверждает вывод только в заявленных пределах.
5. Степень уверенности — модельное предположение, не статистическая гарантия; если недостаточно фактов — `inconclusive` или pending.
6. Внутреннее обновление graph state должно быть атомарно с точки зрения одного шага; пропуск/неполный tool result не скрывать.
7. Покрыть unsupported claim (source hallucination, swapped service, wrong time window).

## Не входит

Отправка отчёта Main Backend, Human approve/reject, search by embeddings, создание synthetic source URLs.

## Acceptance Criteria

1. Evidence всегда воспроизводится из реально полученного fake/live observation.
2. Невалидные ссылки отбрасываются/маркируются, не становятся RCA proof.
3. Гипотез ≤3; evidence-for и evidence-against различаются.
4. `partial`/`truncated` снижает доступность выводов, не выдаётся за полный массив логов.
5. Состояние согласовано с JSON Schemas v0.2-draft.

## Проверки и негативные сценарии

Unit: empty data→inconclusive, conflicting evidence, duplicate source ref, fake URL, wrong service/environment, tool error, truncated data, 4 hypotheses, 0 facts.

## Результат передачи / выходной контракт

Проверяемая структура Evidence/Hypotheses, которую AI-08 использует для составления RCA без генерации фактов.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
