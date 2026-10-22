# AI-01. LLM Provider → реальная Qwen через LangGraph

**Приоритет:** P0  
**Статус при выпуске пакета:** **Промпт уже передан Codex, выполнение/merge ещё не проверены**  
**Зависимости:** Текущий bootstrap, живой `llama-server`  
**Исполнитель:** AI Backend owner (Codex под ревью человека).  
**Источники:** `AGENTS.md`, `docs/02_AI_SCOPE_AND_ARCHITECTURE.md`, текущий `src/ai_agent/agent/`, `llm/providers/llama_cpp.py`

## Зачем и что должно получиться

Получить честно работающий граф `START → llm_node → END`: тестовый incident symptom проходит через LangGraph и существующий `LlamaCppProvider`, возвращает реальный ответ локальной Qwen2.5-Coder-7B. Это **не** автономное расследование, а валидированный вертикальный срез LLM integration.

## Объём работы

1. Изучить текущий LlamaCppProvider/httpx и State/Graph: сохранять работающие модули.
2. Конфигурация `base_url`, model ID, timeout через Pydantic Settings; не загружать GGUF внутри FastAPI.
3. Корректная сериализация system/user/assistant messages, валидация `choices[0].message.content`, ошибки HTTP/connection/timeouts/bad JSON.
4. Инъекция fake provider/client для unit tests.
5. Реальный smoke script через **LangGraph**, отдельно от unit tests; README с командой и проверкой `/v1/models`.
6. Следить за отсутствием утечек промптов/секретов в логах.

## Не входит

MCP, tool calling, RAG, embeddings, Postgres, API запуска расследований, реальный RCA, multi-agent.

## Acceptance Criteria

1. Граф компилируется и имеет реальный вызов LLM.
2. Unit tests проходят без `llama-server`.
3. Live smoke получает ответ от Qwen и ясно помечен `LIVE`.
4. Timeout, network error, HTTP error, malformed response покрыты.
5. Изменения ограничены AI-01, нет самостоятельного wire API.

## Проверки и негативные сценарии

Тесты fake provider, response body missing/invalid, graceful connection refused, корректный state output. Выполнить `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`; отдельно smoke при работающем `llama-server`.

## Результат передачи / выходной контракт

После review → зафиксированный LLM integration baseline. Затем возможны AI-02 (tool-call experiment) и AI-03 (DTO/contracts), но только на интегрированной версии кода.

## Правила исполнения

- Перед изменениями: проверить текущее дерево и Git status; прочитать `AGENTS.md`, `README.md` этого каталога и `QUALITY_GATE.md`.
- Сначала реальная проверка предпосылок и краткий план, затем малые изменения с unit/contract tests.
- Не выполнять push/merge автоматически, не утверждать несуществующий API v1, не отчитываться о mock как о live.
- Закрыть Story только после выполнения DoD и отчёта с командами и результатами.

## Особые замечания

**Эту Story НЕ запускать повторно, пока текущий Codex workflow не завершится.** В `pyproject.toml` bootstrap пока указан Python >=3.14: решение совместимости фиксировать отдельно, не переписывать без причины.
