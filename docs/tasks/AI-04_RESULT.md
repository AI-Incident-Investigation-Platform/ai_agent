# AI-04 — результат контролируемого графа

## Реализовано

`build_graph(decision_provider, tool_executor, tool_schemas)` строит один
LangGraph loop: ingest → decide → validate_action → execute → normalize → decide.
Решение задаётся внутренним типизированным `ActionDecision` или
`FinishDecision`; произвольный текст модели не разбирается как вызов инструмента.
Неверное решение получает одну дополнительную попытку, затем статус
`inconclusive`. Неизвестный инструмент, неверные аргументы, чужой scope,
повтор того же действия и превышение бюджета блокируются до executor.

`InvestigationState` хранит контекст AI-03, budget, счётчики, историю действий,
краткие наблюдения и безопасные event summaries. `ready_for_finalization` —
внутреннее состояние перед будущей AI-08, а не wire-статус `completed` и не RCA.
Поле `evidence` пока пустое: преобразование observations в проверенные Evidence
относится к AI-07. Результат инструмента сохраняется без сырых `items` и
`summary`; события не включают аргументы или содержимое ответа.

Пример fake-пути: `ingest → action(search_logs) → validation → fake execute
→ observation(ok) → finish → ready_for_finalization`.

## Проверка

- `uv run pytest -q` — 90 passed, 1 skipped (live LLM тест не запускался).
- `uv run ruff check .` — passed.
- `uv run ruff format --check .` — passed.
- `git diff --check` — passed.

Unit-тесты охватывают 0 и 2 последовательных действия, одинаковый replay,
неизвестное имя, неверные аргументы и scope, повтор, неверное решение, лимиты,
empty/partial/error и исключение fake executor. Все эти проверки — **FAKE**,
без llama.cpp, MCP и PostgreSQL.

## Граница работы

AI-02 показала, что выбранная конфигурация Qwen/llama.cpp не выдаёт устойчивые
native `tool_calls`. Подключение реального decision provider зависит от
согласованного безопасного action protocol; текущий граф его не подменяет.
Точные allowlists и санация ответов инструментов — AI-06, Evidence/RCA —
AI-07/08, таймаут/отмена — AI-09, долговечные checkpoints — AI-10.
