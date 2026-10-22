# Как отдать следующую Story Codex

## Сначала закончи уже запущенную AI-01

AI-01 передана Codex и может ещё исполняться. **Не запускай вторую сессию, изменяющую те же файлы.** Когда получишь отчёт, проверь real smoke, unit test, `ruff`, `git diff`, интегрируй изменения в baseline согласно `docs/GITFLOW.md`. Затем смотри AI-02 и AI-03.

## Универсальный промпт

```text
Работаем в репозитории AI Incident Investigator / ai_agent. Выполни ТОЛЬКО
Story AI-XX из docs/tasks/AI-XX_....md. Прочитай AGENTS.md,
docs/00_START_HERE.md, docs/tasks/README.md, docs/tasks/QUALITY_GATE.md,
саму Story и перечисленные в ней контракты. Проверь текущую ветку, git status
и реальные реализованные модули; не предполагай, что будущие Stories сделаны.

Покажи краткий план, зависимости, затрагиваемые файлы, риски и открытые
решения. Реализуй минимальный объём Story; не меняй DTO v0.2-draft по своему
усмотрению. Тестируй на deterministic fakes, реальный llama.cpp/MCP/Postgres
используй только в явно отмеченных smoke/integration сценариях.

Запусти pytest, Ruff check/format и специфичные tests Story. Для каждого
acceptance criterion покажи свидетельство, какие результаты LIVE, какие MOCK.
Проверь secrets, read-only tools, budget/cancel, provenance по Quality Gate.
Дай отчёт: файлы, тесты, ограничения, нерешённые ADR, следующий AI-XX.
Не делай push/merge без моего подтверждения.
```

## Краткий промпт именно на AI-02

```text
AI-01 закончена и проверена. Выполни docs/tasks/AI-02_NATIVE_TOOL_CALLING_SPIKE.md.
Прочитай AGENTS.md, README каталога задач, Quality Gate, реальный LLM Provider,
LangGraph smoke. Проведи измеряемую проверку native tool calling Qwen2.5-Coder-7B
через текущий llama.cpp: вызов правильного инструмента, аргументы, none, invalid,
повтор, отказ сети. Tool должен быть чистым fake read-only, без MCP и прод-данных.
Задокументируй точный model ID/chat template/build, фактические запросы и ответы.
Не строй полноценного агента и не меняй draft contracts. Unit tests отдельно,
live тест запускать только при доступности llama-server. Отчёт + ограничения;
не делай push без разрешения.
```

## Статус после каждой Story

Предлагай разработчику вести короткую таблицу в PR или issue tracker (не плодить автогенерируемую фиктивную историю выполнения):

`AI-XX | not started/in progress/review/merged/blocked | branch/PR | test evidence | next`.

Никакой массовой команды «выполни AI-01…18»: работа — по одной проверяемой вертикали.
