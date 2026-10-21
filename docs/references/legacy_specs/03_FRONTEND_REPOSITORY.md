# incident-investigator-frontend — техническое задание

**Ответственный:** Расул Садулаев — Frontend Engineer.  
**Входные зависимости:** Backend REST/OpenAPI и WebSocket events.  
**Связь с AI:** только через Backend; не обращаться из браузера напрямую к MCP, RabbitMQ, LangGraph, llama.cpp, PostgreSQL.  
**Общий контекст:** `00_PROJECT_OVERVIEW.md`.

## 1. Цель репозитория

Сделать профессиональный тёмный интерфейс **AI Incident Investigator** для управления подключёнными проектами, просмотра инцидентов, наблюдения за работой агента и изучения проверяемого RCA.

Основной пользовательский сценарий: пришёл alert → инцидент появился на Dashboard → пользователь открыл Incident Detail → увидел **Live Investigation** → рассмотрел гипотезы и Evidence → прочитал RCA → подтвердил/отклонил/скорректировал диагноз.

**Frontend должен демонстрировать реальные данные Backend**, а не анимировать выдуманные tool calls. Для разработки до готовности Backend разрешены строго отделённые mock fixtures, которые позднее заменяются API без переписывания страниц.

## 2. Границы и стек

- UI — отдельное приложение в собственном GitHub-репозитории, собираемое в Docker image.
- Технологический стек фронтенда (**React/Next.js, TypeScript, библиотека компонентов, state management**) команда ещё **не утверждала**; Расул предлагает рациональный вариант. Не закрепляем выдуманную версию Next.js.
- Backend — единственный источник доменных данных, авторизации, прав и событий.
- Протоколы: **REST** для запросов/команд и **WebSocket** для realtime updates.
- Дизайн: **тёмная тема, минималистичная эстетика observability/SRE**, высокая читаемость, отсутствие декоративных диаграмм.
- В интерфейсе **не использовать pie chart «Incidents by Severity»**: ранее от него отказались.
- Обязательны loading/empty/error/reconnecting/permission states, адаптация к разумным экранам ноутбука и монитора.

## 3. Структура экранов (MVP)

### 3.1. Dashboard

Содержимое:

- Общее количество активных инцидентов и расследований.
- Активные расследования и краткий текущий статус.
- Последние инциденты с сервисом, временем, severity и статусом.
- Затронутые сервисы / быстрый переход к проблемному проекту.
- Быстрые действия, в т. ч. ручной запуск investigation, если есть право.

Не перегружать дополнительной аналитикой ради заполнения экрана. Карточки должны помогать перейти к конкретной проблеме.

### 3.2. Incidents List

Таблица, например:

| ID | Время | Сервис | Инцидент | Severity | Статус |
|---|---|---|---|---|---|
| INC-1042 | 14:35 | payment-service | HTTP 500 errors | Critical | Investigating |
| INC-1041 | 13:20 | order-service | High latency | High | Awaiting Review |

Нужно реализовать:

- Поиск по ID, названию, сервису.
- Фильтры Project/Environment/Service, Severity (`Critical/High/Medium/Low`), Incident Status (`Open/Investigating/Awaiting Review/Resolved`), время.
- Сортировка по новизне/критичности, **серверная пагинация**.
- Переход по строке к Incident Detail.
- Новые/изменившиеся инциденты обновляются без reload через WebSocket или аккуратную инвалидацию REST-кэша.
- Устойчивое отображение пустого списка, потери сети и отсутствия прав.

Важно: **Incident Status и AI Run Status разные**. Не превращать `InvestigationCompleted` автоматически в `Resolved`.

### 3.3. Incident Detail

Общая информация: ID/title, Project/Environment, затронутые сервисы, severity, время возникновения, incident status, источник alert, run status и действия при разрешённых правах.

Вкладки/секции:

1. **Overview** — симптомы, описание, summary, текущий Root Cause (если есть), ключевые Evidence и causal chain.
2. **Live Investigation** — realtime история AI.
3. **Hypotheses** — до трёх гипотез и их изменения.
4. **Evidence** — все доказательства и ссылки.
5. **Timeline** — причинно-временной ряд событий.
6. **RCA Report** — финальный структурированный отчёт и human review.

Разрешено совместить/перегруппировать соседние блоки ради UX, но нельзя потерять ни одну из перечисленных функций.

## 4. Live Investigation — центральный экран

Утверждён отдельной вкладкой **внутри Incident Detail**.

### Что показывать

- Investigation ID и отдельный Run Status: queued/running/completed/inconclusive/failed/timed_out/cancelled (точные wire values согласуются позже).
- Реальные события Tool Calls: tool name, время, статус `pending/running/completed/failed`, краткая причина вызова, summary результата.
- Возможность раскрыть дополнительные **очищенные** подробности ответа инструмента, включая структурированный JSON, когда доступно.
- Hypothesis changes и Evidence collected по мере работы.
- Время от старта, число шагов/tool calls при наличии, состояние `waiting`/`reconnecting`.
- **Cancel** для активного run; **Retry** для повторного расследования. Новому run присваивается собственный ID, предыдущая история не исчезает.

### Чего показывать не надо

- «Скрытую цепочку рассуждений» LLM или raw system prompts.
- Непроверенные заявления «агент нашёл причину» до появления Evidence.
- Токены/пароли/cookies, случайно содержащиеся в логах или tool responses.
- Кнопки на автоматический restart/rollback/execute patch: таких прав у агента нет.

### Пример UX (иллюстрация, не реальный backend payload)

```text
INC-1042 — Live Investigation                         [Running]

14:35:02  ✓ search_logs         Найдены ошибки connection pool
14:35:08  ✓ query_prometheus    Пул соединений достиг лимита
14:35:15  ✓ get_recent_deployments   Был релиз за 20 минут до alert
14:35:21  ◉ git_diff           Изучение изменений release...

[Cancel investigation]
```

## 5. Hypotheses

Отображать **до трёх гипотез**:

- Название/описание.
- Confidence `High/Medium/Low`.
- Status `pending/supported/rejected`.
- Объяснение изменения статуса.
- Связанные Evidence (кликабельные references).
- Realtime updates без потери согласованности с REST-снимком.

Не вводить неутверждённые отдельные поля `evidence_for/evidence_against`; достаточны единый список Evidence и объяснение.

## 6. Evidence

Карточка или компактная таблица должна иметь:

- Идентификатор, source (Elasticsearch/Prometheus/Tempo/GitHub/Docker/deployment и др.).
- Сервис/время/summary и source excerpt, если получен.
- Обоснование, что именно подтверждает наблюдение.
- Связанные hypotheses или causal event.
- **Прямую ссылку на источник** (Kibana/Grafana/Tempo/GitHub), если она доступна.
- Раскрываемый просмотр данных с безопасным форматированием, обрезкой длинных логов и копированием разрешённого excerpt.

Не визуализировать source URL, если backend не подтвердил ссылку; не придумывать hyperlink из ID на клиенте. Работать с признаками недоступности/удаления источника по retention.

## 7. Timeline

- Хронологическая шкала инцидента: deployments, рост latency/errors, DB проблемы, restart, alert, investigation events.
- Timezone и исходные timestamp отображать корректно; предусмотреть одинаковые timestamps и события с диапазоном времени.
- Визуально различать подтверждённые факты и предполагаемые связи.
- По событию — переход к связанному Evidence/источнику.
- Не генерировать фальшивые точки/причинность только для красивого графика.

## 8. RCA Report и Human Review

В отчёте пользователь видит:

- Incident Summary, Severity, affected services.
- Symptoms и отличную от них Root Cause (если доказательств не хватает — `Unknown`/`Inconclusive`).
- Causal Chain, Timeline, Hypotheses + Confidence.
- Ссылки на Evidence с provenance.
- Remediation и Prevention рекомендации — **без кнопки автоматически применить**.
- Даты запуска и завершения, investigative metadata и gaps.

**Human-in-the-loop только после завершения:** пользователь с правами подтверждает, отклоняет либо корректирует Root Cause; автор, дата и текст поправки сохраняются. Viewer не может редактировать.

## 9. Logs, Metrics, Traces и Git Diff

**В MVP:** показывать найденные агентом факты и выдержки; ссылки на источник в Kibana/Grafana/Tempo/GitHub. Подробные графики/встраиваемые panels — вторым шагом после основного сквозного сценария.

**После MVP:** встроенные метрики HTTP errors/latency, CPU/RAM/DB; интерактивный trace/span graph с переходом по сервисам и ссылками на логи; просмотр Git Diff внутри UI. Данные только из Backend, без прямого доступа браузера к приватной инфраструктуре.

## 10. Projects / Environments / Services / Integrations

Отдельный раздел администрирования:

- Просмотр и создание проектов и окружений.
- Ручная регистрация и настройки сервисов, соответствие телеметрическим именам.
- Управление подключениями Elasticsearch, Prometheus, Tempo, GitHub, Docker diagnostic endpoint; отображение статуса `connected/error/unknown` по результатам проверки Backend.
- Создание/изменение интеграций — только с правами Admin; чувствительные ключи не отображать обратно после сохранения.
- Автоматическое обнаружение сервисов **не утверждено как обязательное в MVP**. Не проектировать frontend так, будто такой API уже есть.

## 11. Auth / RBAC

Утверждены `Admin`, `Developer`, `Viewer` и JWT:

| Действие | Admin | Developer | Viewer |
|---|---|---|---|
| Смотреть разрешённые инциденты/RCA | Да | Да | Да |
| Запускать / Cancel / Retry | Да | Да | Нет |
| Human review / корректировка Root Cause | Да | Да | Нет |
| Управлять проектами, пользователями, интеграциями | Да | Нет | Нет |

Frontend скрывает/отключает недоступные действия, но **сервер обязан проверять права независимо**. Обрабатывать `401`, `403`, expiring token, logout/relogin, запрет подписки WebSocket на чужой Incident. Предпочтительны безопасные способы хранения/обновления токенов с согласованной политикой Backend.

## 12. REST / WebSocket — что нужно от Backend

### REST capabilities (будет OpenAPI)

- Auth/session/current user + разрешения.
- List/filter/get Incidents, Projects, Environments, Services.
- Investigation start/status/history/cancel/retry.
- Hypotheses/Evidence/Timeline/RCA/review.
- Integration settings/test connection и Deployments для Admin.

### WebSocket capabilities (будет JSON Schema)

- Аутентифицированная подписка на Incident/Investigation.
- Event IDs/sequence, тип события, run IDs, timestamp, payload.
- `tool.started/tool.completed/tool.failed`, `hypothesis.updated`, `evidence.added`, `investigation.status.changed`, `rca.ready` и создание Incident (имена лишь иллюстративны).
- **Reconnect/replay**: при возврате клиента получить пропущенные события из REST/Event history либо согласованного replay механизма, без пропусков или случайных двойных записей в ленте.
- При ошибке соединения не менять локально статус расследования на `failed`: сетевой статус UI — отдельная сущность.

### Контрактная дисциплина

Фиксируем OpenAPI и WebSocket Event JSON Schema **до** совместной реализации. Для frontend нужны типизированный API client (автоматически генерируемый или эквивалент), моковые fixtures и contract tests. **Маршруты и реальные поля сейчас ещё не утверждены.**

## 13. Состояния UX и качество

- `loading`, `empty`, `not found`, `forbidden`, `server error`, `reconnecting`, `stale data`, `partial RCA`, `source link unavailable`.
- Длинные технические строки, timestamps, URLs, stack traces и JSON должны читаться и не ломать layout.
- Отделять Incident status от Investigation status, показывать старые runs при Retry.
- Ненавязчивая визуальная иерархия Critical/High/Medium/Low и статусов, не делать каждый элемент ярким.
- Доступность клавиатуры, контраст и focus; адаптация интерфейса к небольшим ноутбукам.
- Без лишней анимации, AI-мотивированных декоративных элементов и неподтверждённых «percent progress».

## 14. Тестирование

- Unit: форматирование severity/status, сортировка/фильтры, guards прав, Event reducer, dedup/replay.
- UI component tests: таблица, timeline, Evidence, hypotheses, RCA, error states.
- Integration с mocked REST + WebSocket: последовательность events, disconnect/reconnect, Cancel/Retry, role changes.
- E2E на общей Compose-стенде: созданный инцидент → live tools → RCA → human review.
- CI GitHub Actions: lint/typecheck/test/build Docker image.

## 15. План разработки

1. Каркас, UI-стиль и mock Incident List/Detail.
2. Auth/RBAC и REST client по контракту, список Incidents с filters/pagination.
3. Live Investigation c mock WebSocket event stream и Event reducer.
4. Реальный WebSocket/reconnect + actions Cancel/Retry.
5. Hypotheses/Evidence/Timeline/RCA + human review.
6. Projects/Services/Integrations и UX для неполных данных.
7. Встраиваемые charts/traces и Incident Chat — второй приоритет.

## 16. Критерии приёмки

- [ ] Таблица инцидентов поддерживает поиск, фильтрацию, пагинацию и кликабельные строки.
- [ ] Incident Detail содержит все согласованные вкладки и информативную страницу Overview.
- [ ] Действия LangGraph через Backend видны в реальном времени, без фабрикации tool calls.
- [ ] При разрыве WebSocket события восстанавливаются, текущий Incident не теряется.
- [ ] Справедливо отображаются `inconclusive/failed/timed_out/cancelled`, а не только happy path.
- [ ] Гипотезы, Evidence, Timeline, RCA отображают реальные источники и связи.
- [ ] Human Review, Cancel и Retry доступны только авторизованным ролям.
- [ ] Отчёт не содержит кнопок автоматического изменения production.
- [ ] Страница работоспособна с реальным Backend в общем Docker Compose и проходит CI/E2E.

## 17. После MVP

Контекстный Incident Chat по сохранённому расследованию (только LLM+контекст, **без новых tools**), встроенные Grafana-derived charts и интерактивный Tempo trace viewer. Реализовать после рабочего RCA-контура. **Restart with Context** также не относится к текущему MVP.
