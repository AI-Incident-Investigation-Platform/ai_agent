# AI-02 — результат проверки native tool calling

**Статус на 26 октября 2026:** capability spike выполнен с отрицательным
вердиктом. Это **не** подтверждение работающего native tool calling и не
разрешение исполнять production-инструменты. Способ получения и валидации
действий агента для AI-04 требует отдельного решения команды.

**Вердикт для проверенной конфигурации: `not reliable`.** В повторяемом live
сценарии Qwen описывала вызов инструмента в `message.content`, но не возвращала
`message.tool_calls`. Такой текст не исполняется. Двухшаговый live-сценарий
не мог начаться; двухшаговый обмен с fake provider проверен unit-тестом.

## Проверенная конфигурация

| Параметр | Значение |
|---|---|
| Хост | MacBook Pro, Apple M2 Pro (10 CPU cores), 16 GB RAM |
| `llama-server` | 0.7.0, build `11669`, commit `620d2225c` |
| Модель | `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M`; snapshot `13fb94bfda8c8cf22497dc57b78f391a9acb426a`, два GGUF shard |
| Квантование | Q4_K_M, 7.6B parameters по `/v1/models` |
| Шаблон | встроенный `chat_template` из GGUF; SHA-256 `4e9918361c284a93880606d182d64da6a9fe97cdc1f5c5a78c1c8840444246fc`; `/props` сообщает `supports_tool_calls=true`, `supports_tools=true` |
| Запуск основного smoke | `--jinja --flash-attn on --ctx-size 8192 --host 127.0.0.1 --port 8080 --no-webui` |
| Запрос | OpenAI-compatible `/v1/chat/completions`, `temperature=0`, два fake read-only tools со строгими схемами |

Сервер запускался с локальным GGUF; модель не скачивалась и реальные источники
диагностики не вызывались. `--jinja` и tool-aware шаблон есть, поэтому одного
флага или наличия `supports_tool_calls` недостаточно для вывода о работоспособности.
Документация [llama.cpp Function Calling](https://github.com/ggml-org/llama.cpp/blob/master/docs/function-calling.md)
описывает `--jinja`, шаблоны и нативные форматы; проверка выше относится именно
к установленному build и этой модели.

## Live результаты

Команда: `uv run python scripts/smoke_tool_calling.py --repetitions 3`.
Проверено три независимых вызова первого инструмента и три запроса без
инструмента. Вывод: `first_native=0/3`, `two_step_native=0/3`
(`not_attempted` после отсутствия первого native call), `direct_no_tool=3/3`.
Smoke корректно завершился кодом `1`. Форма одного фактического ответа:

```json
{
  "finish_reason": "stop",
  "message": {
    "role": "assistant",
    "content": "```json\n{\"name\": \"search_logs\", \"arguments\": {\"service_id\": \"payment-service\", \"limit\": 3}}\n```"
  }
}
```

Повторная live-проверка **26 октября 2026** той же командой и на том же
`llama-server` build дала `first_native=0/3`, `two_step_native=0/3`,
`direct_no_tool=3/3`; каждый первый ответ был `text_only` с `finish_reason=stop`.
Код выхода снова был `1` — ожидаемое свидетельство отсутствия native calls,
а не успешное прохождение tool-calling smoke.

Отдельно проверены `tool_choice=auto` и `tool_choice=required` на тех же
фиктивных данных. `required` три раза вернул `message.content` с XML/JSON
вместо `tool_calls`; ответы имели `finish_reason=length`. Простая фиктивная
функция `get_weather` также вернулась текстом при `auto` и `required` (по
одному вызову). Запуск с `--chat-template chatml` и `required` один раз дал
обычный текстовый отказ: этот встроенный шаблон не передал модельной сессии
описание инструментов и не решил проблему. Эти дополнительные пробы не
входят в показатель `0/3` основного smoke.

Успешная структурированная форма ниже получена **только в mock HTTP unit-тесте**,
не от живой Qwen:

```json
{
  "finish_reason": "tool_calls",
  "message": {
    "role": "assistant",
    "content": null,
    "tool_calls": [{
      "id": "call_1",
      "type": "function",
      "function": {
        "name": "search_logs",
        "arguments": "{\"service_id\":\"payment-service\",\"limit\":3}"
      }
    }]
  }
}
```

## Что реализовано и проверено

- `LlamaCppProvider` сохраняет native calls как данные, сериализует историю
  assistant/tool-сообщений для следующего шага и принимает строковые или
  объектные arguments от `llama-server`. Он не исполняет инструменты.
- `validate_tool_calls` принимает только `tool_calls` из структуры ответа,
  проверяет имя, уникальный непустой ID и Pydantic-схему с запретом лишних
  аргументов. Текстовый JSON не превращается в действие.
- Live smoke содержит два фиктивных in-memory инструмента, может выполнить
  последовательность `search_logs → query_prometheus → final answer` при
  наличии native calls и отдельно проверяет выбор прямого ответа.
- Детерминированные тесты охватывают корректный вызов, два шага, отказ от
  инструмента, неверное имя/аргументы/ID, текстовый псевдовызов,
  некорректный JSON и timeout. Последние два также проверены тестами
  LLM-провайдера. MCP и production диагностика не использовались.

## Предложение для решения команды

Native tool calling этой комбинации нельзя считать готовой границей для AI-04.
Варианты: протестировать другую модель/сборку с тем же контрактом либо
согласовать **отдельный typed action DTO**, возвращаемый через ограниченную
JSON-грамматику, с повторной Pydantic-валидацией, allowlist и лимитами в Python.
Это не парсинг произвольного JSON из обычного текстового ответа. В короткой
дополнительной пробе `response_format={"type":"json_object","schema":...}`
и вложенный вариант `json_schema` удержали запрещённое значение `action` вне
ответа; вариант `{"type":"json_schema","schema":...}` на этом build схему
**не применил**. Эта проба не доказывает семантическую надёжность fallback.
Решение о production action protocol и его собственные evals нужны до
исполнения действий AI-04.

Проверки после изменений: `uv run pytest -q` — 39 passed, 1 skipped;
`uv run ruff check .` — passed; `uv run ruff format --check .` — passed;
`git diff --check` — passed.

## Сопоставление с Acceptance Criteria AI-02

| Критерий | Свидетельство и ограничение |
|---|---|
| Форма успешного вызова и отказа | Выше приведены **mock**-форма структурированного `tool_calls` и **live**-форма текстового ответа. Реального успешного `tool_calls` в этой конфигурации нет. |
| Воспроизводимость | Зафиксированы модель, квантование, build, template hash, флаги запуска, команда smoke и число попыток. |
| Безопасная валидация | `validate_tool_calls` принимает только структурированное поле, проверяет allowlist, ID и строгие Pydantic-схемы; неизвестный инструмент и неверные аргументы не исполняются в fake-пробе. |
| Offline-тесты | Детерминированные unit-тесты не требуют llama-server. |
| Чёткий verdict | `not reliable` только для указанной конфигурации; fallback остаётся предложением, не production-решением. |

AI-02 как **исследование возможности** может быть передана на review с
отрицательным результатом. Закрывать её как подтверждение native tool calling
нельзя. Следующий этап AI-04 не должен исполнять инструменты на основе
произвольного текста модели без согласованного и отдельно проверенного
action protocol.
