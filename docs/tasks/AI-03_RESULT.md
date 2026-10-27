# AI-03 — typed domain и contract tests

**Статус:** реализация в рабочей ветке `feature/ai-03-domain-contracts`;
требует review. Использован контракт `docs/contracts/` **v0.2-draft**.
Транспорт Main Backend ↔ AI Backend не выбирался.

## Реализовано

- Pydantic v2 модели для Start, budget/window, Investigation, Hypothesis,
  Evidence/SourceLink, Timeline, RCA, event payloads, final callback и Problem.
- Чистые правила переходов `pending → running → terminal`, отмены ожидающего
  run и идемпотентной проверки того же статуса. Retry требует нового ID,
  следующего attempt и ссылки на предыдущий run.
- Явное преобразование Start DTO ↔ входное состояние LangGraph без FastAPI
  объектов и без нового HTTP-маршрута.
- Контрактные тесты читают реальные JSON Schema и примеры из `docs/contracts/`.
  Проверка `date-time` использует dev-only `rfc3339-validator`.

## Расхождения draft-схем и доменных правил

| Область | Что допускает JSON Schema v0.2 | Что делает текущая модель / что требуется решить |
|---|---|---|
| Evidence locator | У `SourceLink` обязателен только `source_type`; `source_id` и `url` могут отсутствовать. | DTO пока сохраняет форму схемы. Перед AI-07 нужно согласовать минимальный provenance locator для подтверждённого Evidence. |
| Гипотезы | В `AIResultCallback.hypotheses` нет `maxItems`. | DTO отклоняет четвёртую гипотезу согласно проектному лимиту ≤3; ограничение следует добавить в контракт после review. |
| Время и окно | `date-time` допускает смещение от UTC; схема не сравнивает `window.from/to`. | DTO требует UTC и `from ≤ to` согласно текстовым правилам. |
| Итоговый отчёт | Schema требует непустой `report` при `completed/inconclusive`, но не связывает `report.outcome` и его IDs со статусом/IDs callback. | DTO проверяет совпадение статуса и scope. Схему можно усилить после согласования. |

Ни один канонический JSON Schema/OpenAPI/proto-файл не менялся. Эти различия
закреплены тестами, а не замаскированы в примерах. Проверка ссылок
`hypothesis.evidence_ids` на фактически полученные Evidence остаётся задачей
AI-07, а не фиктивной гарантией AI-03.

## Границы результата

Нет реализации REST/gRPC, MCP, PostgreSQL, доставки событий или реального
расследования. Тесты используют контрактные примеры и локальные fake-данные,
не живую Qwen или Main Backend. Следующие независимые шаги после review —
AI-05 (MCP Client) и подготовка AI-04; AI-04 также ожидает решение по
отрицательному native tool-calling verdict AI-02.

## Проверка

- `uv sync` — зависимости установлены.
- `uv run pytest -q` — 76 passed, 1 skipped; skipped относится к отдельной
  live-проверке LLM, не к AI-03.
- `uv run ruff check .`, `uv run ruff format --check .`, `git diff --check` —
  прошли после финальной правки теста.
