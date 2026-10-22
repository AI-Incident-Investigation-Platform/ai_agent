# AI-02. Проверка Qwen2.5 native tool calling

**Приоритет:** P0  
**Статус при выпуске пакета:** Не начата  
**Зависимости:** AI-01 reviewed/merged  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** текущий LLM Provider/graph; `docs/02_AI_SCOPE_AND_ARCHITECTURE.md`; официальная документация текущей установленной версии llama.cpp (для параметров template)

## Зачем и что должно получиться

Доказать экспериментом, может ли конкретный **Qwen2.5-Coder-7B-Instruct GGUF Q4_K_M** через установленный `llama-server` возвращать структурированные `tool_calls` по OpenAI-compatible API. **Не считать поддержку доказанной только из `/v1/models` или успеха обычного чата.**

## Объём работы

1. Зафиксировать llama.cpp build/version, model id, chat template, relevant flags, частоту ошибок, аппаратное окружение.
2. Подключить mock read-only инструменты `search_logs` и `query_prometheus` (в памяти, без MCP/реальной диагностики) с явными JSON schemas.
3. Проверить: выбор инструмента, корректные аргументы и ID, последовательное выполнение двух инструментов, выбор не вызывать инструмент, неправильное имя/аргументы, некорректный JSON, отказ модели/timeout.
4. Встроить минимальный адаптер для structured tool calls или оформить технический отчёт о недостатках API. Нельзя писать собственный парсер произвольного «текста, похожего на функцию» как безусловную production-гарантию.
5. Если native tool calling нестабилен — зафиксировать *предлагаемый* fallback с его границами и попросить решение до production цикла.
6. Вынести live checks в отдельный smoke, deterministic tests — отдельно.

## Не входит

Полноценный LangGraph ReAct, MCP Client, прод tool execution, автоматическое переключение моделей, model fine-tune.

## Acceptance Criteria

1. В отчёте содержатся raw shape примера успешного `tool_calls` и отказа/ошибки (без секретов).
2. Known model/template/build воспроизводимы.
3. Вызовы валидируются против schemas; unknown tool/arg не исполняется.
4. Детерминированные тесты не требуют Qwen.
5. Чёткий verdict: native supported/partially supported/not reliable; **не подменён предположением**.

## Проверки и негативные сценарии

Fake successful tool call, no-tool response, invalid JSON/schema, wrong tool, 2-step action, timeout. Live smoke повторяется несколько раз; записать число попыток и неудач, а не заявление «100% работает» по одному случаю.

## Результат передачи / выходной контракт

Решение о безопасном способе LLM tool calling для AI-04 и документированный контракт provider-level action representation.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.
