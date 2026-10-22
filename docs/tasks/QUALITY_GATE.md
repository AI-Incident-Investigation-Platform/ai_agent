# Quality & Safety Gate — обязательные проверки каждой Story

## A. Совместимость с проектом

- [ ] Начало работы: прочитаны `AGENTS.md`, task README, нужная Story, действующий `docs/contracts/`.
- [ ] Проверено фактическое дерево Git и не затёрты незакоммиченные изменения другой сессии.
- [ ] Функция не претендует на утверждённый wire contract, если он по-прежнему v0.2-draft.
- [ ] Код остаётся внутри **AI Backend**; не реализует Frontend, Auth/OTP/RBAC, Main Backend-owned Incident/Review.
- [ ] Нет RabbitMQ transport, нет ненужного multi-agent, нет новой инфраструктуры без согласования.

## B. Модель и агент

- [ ] LLM call реально через configured llama.cpp; offline fake — только явным тестовым адаптером.
- [ ] Нет prompt-only гарантий: бюджеты, аргументы инструментов, scope, размер результатов проверяются в Python.
- [ ] Native function calling протестирован с **актуальным llama.cpp build, моделью и chat template**; нет предположений по умолчанию.
- [ ] Нет бесконечных циклов; ограничены попытки repair невалидного structured output и сетевые ретраи.
- [ ] Таймауты, cancellation, model unavailable имеют определённое terminal outcome.

## C. Evidence / safety

- [ ] Каждая гипотеза имеет реальные зафиксированные `source_refs` либо честно маркируется неподтверждённой, что не превращается в подтверждённую RCA.
- [ ] Связь evidence → утверждение валидируется, чужие/несуществующие source IDs отклоняются.
- [ ] Логи, retrieved docs, tool descriptions и Git содержимое считаются **недоверенным вводом**; инструкции в них не повышают привилегии.
- [ ] Tools read-only. Запрещены произвольные shell/SQL, `docker exec`, restart/rollback, write GitHub, произвольные HTTP target.
- [ ] Scope `project_id`, `environment_id`, allowlisted tools/repos/targets проверяются **на стороне исполнения**, не только в prompt.
- [ ] Secret/PII redaction, размер и время ответа ограничены; links и identifiers нормализованы.

## D. Контракт, durability и интеграции

- [ ] JSON Schema / Pydantic тесты на примерах v0.2-draft; изменения wire DTO отдельно согласованы.
- [ ] Повторный `Start` c тем же `investigation_id` не создаёт новый run; Retry = **новый** ID.
- [ ] Event ID и sequence стабильны на повторных доставках; terminal result не дублируется.
- [ ] Нет 20-минутного HTTP request и отсутствует единственный in-memory `BackgroundTasks` вместо durable execution.
- [ ] При рестарте незавершённый run восстанавливается или фиксирует управляемый terminal failure, а не остаётся бесконечно running.
- [ ] AI не отдаёт browser WS и не переводит Incident в `resolved` — это решение Main Backend и человека.

## E. Тесты и доказательства готовности

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Если зависимостей нет или команда не запускается — укажи причину; не пиши «всё прошло». Реальные MCP/Postgres/llama.cpp тесты выделяются отдельно и маркируются как **LIVE**, иначе `FAKE` / `MOCK`. Данные замеров: модель, квантование, hardware, контекст, sample size, p50/p95 и реальные ошибки (если сравниваешь производительность).

### Минимальные тестовые категории

- Happy path и empty result.
- Timeout, network error, invalid JSON, wrong tool name/args, out-of-scope request.
- Truncated/partial, prompt injection в tool result, секреты в log excerpt.
- Duplicate/replay/out-of-order, cancellation race, crash/restart (для runtime).
- Evidence provenance, inconclusive, false positive RCA.

## F. Проверяемый отчёт для PR

1. Story ID и цель.
2. Изменённые файлы и причина изменения.
3. Сопоставление acceptance criteria с тестами.
4. Команды и реальные pass/fail/skip.
5. Демонстрационный ввод и краткий фактический выход без секретов.
6. Что не входит и что осталось заблокировано решением команды.
7. Следующая Story / Gate.

**Если хотя бы один safety-critical criterion провален, Story нельзя объявлять закрытой.**
