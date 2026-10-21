# 10. Incident Detail — Экран расследования и RCA

**Figma:** [B / Incident detail — Case / investigation / RCA](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-40)  
**Маршрут (предложение):** `/incidents/:incidentId`  
**Приоритет:** P0 — ключевой экран продукта.  
**Роли:** чтение Admin/Developer/Viewer; Cancel/Retry/Human Review — Admin/Developer.

> **Граница макета:** непосредственно в Figma изображён Incident Detail с активной вкладкой **Live Investigation**, summary, краткими гипотезами и Evidence. Подробное содержание остальных вкладок ниже взято из ранее согласованных требований продукта. Для них нужен полноценный frontend-design/implementation pass, а не предположение, что в Figma уже лежат отдельные готовые фреймы.

## 1. Назначение

Incident Detail — центральная страница. Пользователь приходит сюда из Overview, Incidents или Live Investigations и последовательно получает ответы:

1. Что случилось и какой сервис затронут?
2. На какой стадии инцидент и какие AI-расследования запускались?
3. Какие инструменты агент вызывал, что нашёл и какие альтернативы проверил?
4. Где находятся доказательства и можно ли проверить исходный источник?
5. Какая наиболее вероятная первопричина, насколько она подтверждена?
6. Что надо исправить и что подтвердил или поправил человек?

Эта страница должна помогать **проверять диагноз**, а не создавать впечатление, что LLM всегда права.

## 2. Общая композиция Figma

Стандартный sidebar варианта B, активен пункт `Incidents`. Заголовок `INC-1042 / payment-service`, подпись про Root Cause investigation. Справа — компактные действия/статусы:

- `Investigating` — **Incident status**.
- `Critical` — severity.
- `Retry` — запустить новое расследование.
- `Cancel` — отменить активный run.

Под заголовком `INCIDENT SUMMARY` на всю ширину: например, `Checkout HTTP 500 errors after payment deployment`, project (`E-commerce`), environment (`Production`), service, время обнаружения. Заголовок описывает симптом и контекст, не должен заранее утверждать корневую причину, если она ещё не подтверждена.

Далее горизонтальные вкладки: `Overview`, `Live investigation`, `Hypotheses`, `Evidence`, `Timeline`, `RCA report`. В текущем фрейме активна **Live investigation**; внизу большая левая панель live Tool Calls, справа `HYPOTHESES & EVIDENCE`.

В реальной реализации вкладки изменяют URL/query/hash или nested route так, чтобы на конкретную вкладку можно было дать ссылку. Вкладки не должны терять состояние инцидента или историю WebSocket при переключении.

### Общие поля шапки инцидента

| Поле | Значение / правило |
|---|---|
| ID/title | Настоящий incident ID + краткое описание |
| Project / Environment | Контекст области доступа |
| Affected services | Один или несколько сервисов, primary выделен |
| Severity | Critical / High / Medium / Low |
| Incident status | Open / Investigating / Awaiting Review / Resolved |
| Investigation status | Отдельная информация по выбранному run; `completed` ≠ `resolved` |
| Created / detected / updated timestamps | Обязательно по часовому поясу |
| Alert source | Alertmanager/Grafana/manual/другой источник, если сервер предоставляет |
| Run selector | При наличии нескольких попыток — выбрать нужный `investigationId` |

## 3. Вкладка Overview — сводка инцидента

### Контент

- **Summary**: короткое нейтральное описание симптомов, длительности, влияния на систему.
- **Affected services**: primary + cascaded services, если есть подтверждённые наблюдения.
- **Root Cause**: вероятная первопричина, confidence и статус проверки человеком; при недостаточных данных `Not determined / Inconclusive`, без искусственной уверенности.
- **Symptoms vs Root Cause**: явно различать «HTTP 500 выросли» (симптом) и «пул соединений не освобождается после deployment» (возможная причина).
- **Causal chain**: например `deployment → pool saturation → DB timeout → checkout 500`, с пометкой, какие переходы подтверждены Evidence, а какие пока гипотезы.
- **Key Evidence**: 3–5 самых важных наблюдений со ссылкой на вкладку Evidence.
- **Investigation outcome**: состояние последнего run + время выполнения + доступность полного RCA.

### Действия

Переходы `View live investigation`, `View all evidence`, `Read RCA report`. Если RCA ещё не готов — disabled/`Pending`, а не подставленный текст. Viewer только читает.

## 4. Вкладка Live Investigation — ход работы агента

Это **обязательная часть P0**, отображаемая в текущем Figma-фрейме.

### 4.1. Шапка вкладки

Состояние выбранного run (`Queued`, `Running`, `Completed`, `Inconclusive`, `Failed`, `Timed out`, `Cancelled`), `investigationId`, начальное время, elapsed, число шагов, tool calls. В проекте согласованы ограничения **до 20 шагов, до 40 tool calls, до 20 минут**. Не показывать fictitious progress percentage: `step 12/20` означает использованный бюджет шагов, не «готовность 60%».

### 4.2. Feed событий и Tool Calls

Пример из Figma:

```text
14:36  search_logs                124 DB connection timeouts
14:37  query_prometheus           Pool utilization reached 100%
14:38  get_trace                  DB acquisition spans slowed
14:39  get_recent_deployments     Payment release v2.4.1
14:40  git_diff                   Reviewing connection cleanup logic
```

Это **демо-текст макета**, а не предподготовленный маршрут агента. Реальная последовательность ReAct может быть любой; интерфейс строится исключительно по фактическим events Backend.

Каждая запись содержит время, название инструмента, summary «зачем/что проверяется» без скрытых рассуждений, статус pending/running/completed/failed, длительность, краткий observation, раскрываемые sanitized details, связанные Evidence и исходные URL, если присутствуют.

Отдельно в той же ленте могут отображаться события `Hypothesis updated`, `Evidence collected`, `Investigation completed` как события другого типа, а не имитация tool call. Long raw JSON показывать в collapsible viewer с ограничением количества символов.

### 4.3. Правая панель

`HYPOTHESES & EVIDENCE` — краткий обзор до трёх гипотез + прямые ссылки на ключевые источники. Не дублирует полноту соответствующих вкладок. Пример макета:

- `PostgreSQL connection leak` — Supported.
- `CPU saturation` — Rejected.
- `Deployment regression` — Pending.
- `Elasticsearch: pool timeout ↗`.
- `Prometheus: connections 100% ↗`.
- `GitHub: deployment diff ↗`.

### 4.4. Cancel / Retry

- `Cancel`: доступно только при server-allowed active status. Открыть confirmation dialog: `Остановить расследование? Сохранённые результаты и история останутся.` Пока команда обрабатывается — disabled/spinner. Отмена может быть не мгновенной.
- `Retry`: доступно по серверным правилам. Создать **новый investigation run ID**, старые события остаются доступны. После успешного старта открыть новый run; если очередь загружена — статус `Queued`.
- `Restart with Context` **не входит в MVP**.
- Вмешиваться с user chat в активный ReAct loop нельзя (раньше договорились только о чате по завершённому расследованию, этап 2).

### 4.5. WebSocket/reconnect

По первоначальной загрузке получить исторические events; затем подписаться на поток выбранного run. События должны иметь ID/sequence. При reconnect догрузить пропущенное и дедуплицировать; при переключении вкладки история не теряется. Нельзя считать `WebSocket disconnected` равным `Agent failed`.

## 5. Вкладка Hypotheses — гипотезы

### Структура карточки гипотезы

- Заголовок и краткое описание предполагаемой причины.
- Порядковый номер/ID, но порядок не равен вероятности.
- Confidence: **High / Medium / Low**; не вычислять псевдоточные проценты.
- Status: **Pending / Supported / Rejected**.
- `reasoning_summary`/explanation — краткое, пригодное для пользователя объяснение, какие факты повлияли на оценку; **не chain-of-thought**.
- Связанные Evidence refs — перейти в Evidence с фильтром по гипотезе.
- `updatedAt`, при необходимости история изменения статуса.

Максимум три гипотезы. Важно различать: `Supported` — гипотеза поддерживается данными, но это не абсолютное доказательство; окончательное подтверждение Root Cause — человеческий review после расследования. Не вводить дополнительные обязательные списки `evidence_for/evidence_against` — пользователь ранее их исключил.

### Интерактивность

Из Live Investigation статусы обновляются в реальном времени; пользователь может раскрыть объяснение и связанные Evidence. Viewer только читает. Самостоятельное редактирование гипотез человеком пока не согласовано — ручной review применяется к Root Cause/RCA.

### Состояния

До первых гипотез — `Agent is investigating`. Если агент вернул 0 гипотез — `No supported hypotheses`. Противоречащие выводы не маскировать. Если run упал, оставить ранее полученные гипотезы с пометкой `Incomplete run`.

## 6. Вкладка Evidence — доказательства

### Таблица/карточки

| Поле | Что отображаем |
|---|---|
| Evidence ID/type | Уникальный ID + категория (`log`, `metric`, `trace`, `code_change`, `container_event`, `deployment_event`, `doc_excerpt`) |
| Source | Elasticsearch / Prometheus / Tempo / GitHub / Docker / Deployment API |
| Service / timestamp | Контекст и время наблюдения |
| Summary / excerpt | Что именно увидел инструмент; короткий фрагмент |
| Significance | Какой вывод поддерживается этим доказательством, без выдуманной причинности |
| Hypothesis link | Одна или несколько связанных гипотез |
| Source URL | `View in Kibana`, `View in Grafana`, `View Trace`, `View Diff` — только URL от Backend |

### Просмотр Evidence Detail

Раскрыть panel/drawer: sanitized raw fragment, structured data (для metrics — series name/timestamp/value/unit, для logs — message/trace ID, для code — file path/commit/diff), `source_reference`, условия выборки, `collectedAt`, путь к первоисточнику. Кнопка copy excerpt — если позволяет RBAC.

**Нельзя**: хранить безлимитные сырые логи в браузере; показывать секреты; строить невалидный Kibana URL из строки лога; выдавать похожий старый инцидент (Incident Memory) за прямое Evidence нового происшествия.

### Фильтры

По источнику, service, гипотезе, виду Evidence, времени. Пустые/удалённые по retention источники должны иметь label `Original source unavailable` при сохранении ранее собранного и подтверждённого excerpt.

## 7. Вкладка Timeline — временная последовательность

Отображаем наблюдаемые события в строгом порядке timestamps с проверяемыми ссылками:

```text
14:10  Deployment payment-service v2.4.1
14:15  Prometheus: DB connection count began to increase
14:22  Tempo: p95 latency increased
14:30  Elasticsearch: HTTP 500 spike
14:35  Alertmanager: incident created
14:36  AI investigation started
```

Весь текст — пример, не обязательный заранее прописанный causal сценарий.

### Типы событий

Deployment, metric anomaly, application error/log, trace observation, Docker container state, alert, incident status changed, investigation tool event, human review. В интерфейсе можно включать/отключать технические и агентные события.

### Правила

- Timestamp в UTC внутри данных; вывод с понятной timezone (пользовательская зона или UTC с явной подписью).
- Равные timestamps упорядочиваются устойчиво (sequence/event ID), неизвестное точное время помечается.
- Визуально отличать **наблюдаемый факт** от **гипотетической причинной связи** (например, сплошная/пунктирная стрелка + текст «inferred»).
- По клику открывается Evidence, Trace, Log, Deployment или tool call по reference.
- Если Evidence нет, Timeline не должен просто рисовать красивую фальшивую историю.

## 8. Вкладка RCA Report — итог расследования

Этот раздел может быть пустым до завершения agent run. После появления `rca.ready` загружается **структурированный**, проверяемый отчёт.

### Разделы отчёта

1. **Incident Summary**: ID, title, timestamps, severity, affected services, duration.
2. **Symptoms / Impact**: какой пользовательский/технический сбой наблюдался.
3. **Root Cause**: конкретная наиболее вероятная первопричина; `Unknown/Inconclusive`, если недостаточно информации.
4. **Confidence**: High/Medium/Low или equivalent qualitative label.
5. **Causal Chain**: как события связаны; источники подтверждения отдельных звеньев.
6. **Hypotheses**: supported/pending/rejected с объяснением и Evidence refs.
7. **Evidence**: таблица/ссылки на первичные источники.
8. **Timeline**: краткая событийная последовательность.
9. **Remediation**: конкретные предложения по устранению проблемы (код/конфигурация/процесс), **без исполнения действий**.
10. **Prevention**: как уменьшить вероятность повторения.
11. **Investigation metadata**: run ID, время, tools used, технические ограничения, source gaps.
12. **Human Review**: состояние проверки человеком.

Если агент не подтвердил причинность, писать «вероятная причина» / «недостаточно данных», а не оформлять её как 100%-факт. Длинный отчёт должен иметь внутреннюю навигацию/якоря, копирование/экспорт при согласовании. Не нужно генерировать PDF в MVP автоматически, если такого требования не было.

### Human-in-the-loop — проверка **после** расследования

У Admin/Developer после завершения:

- `Confirm Root Cause` — подтверждение текущего вывода.
- `Reject Root Cause` — отклонение с комментарием.
- `Correct Root Cause` — ввод корректной причины/пояснения, подтверждение изменения.

Backend хранит автора, время, решение и комментарий; прошлый оригинальный RCA нельзя бесследно заменить поправкой. Viewer читает результат и историю подтверждения, но не редактирует. Не просить подтверждения перед каждым read-only Tool Call и не блокировать агента вопросами во время выполнения.

### Run failure/inconclusive

Если run timed out или inconclusive, показывать `Partial investigation` с доступными Evidence, причинами нехватки данных и опцией Retry. Не прятать уже собранные факты.

## 9. Данные и требуемые Backend capabilities

Нужны следующие возможности; **это не окончательные API endpoints**:

- `getIncident(incidentId)` → core metadata, statuses, project/environment, affected services.
- `listInvestigations(incidentId)` → все runs с run IDs, статусами, timestamps; `getInvestigation(runId)`.
- `listInvestigationEvents(runId, cursor/afterSequence)` → historical feed и reconnect/replay.
- `listHypotheses(runId)` → 0–3 entries с Evidence refs.
- `listEvidence(runId, filters)` / `getEvidence(evidenceId)` → structured snippets/source links.
- `getIncidentTimeline(incidentId,runId?)` → типизированные события с provenance.
- `getRcaReport(incidentId,runId)` → structured RCA document с статусом readiness.
- `submitRootCauseReview(incidentId,decision,correction?,comment?)`.
- `cancelInvestigation(runId)` / `retryInvestigation(runId)`.
- Auth scopes and permissions, source deep links, system errors.

Предпочтительны typed frontend domain models, за которыми скрыт OpenAPI-generated client. WebSocket events только обновляют конкретные entity instances; итоговое содержимое report/large Evidence лучше загружать REST.

## 10. UI state machine и запрещённые упрощения

| Incident status | Run status | Что видеть |
|---|---|---|
| Open | Нет run | Инцидент есть, расследование можно запустить по правам |
| Investigating | Queued/Running | История, прогресс шагов, Cancel |
| Awaiting Review | Completed | Готовый RCA и действие Human Review |
| Open / Investigating | Inconclusive/Failed/Timed out | Частичный результат, Retry по правам, ошибка отдельно от incident status |
| Resolved | Completed или старый run | История и подтверждение; данные не исчезают |

Матрица описывает **смысл UI**, а не утверждённые транзакции Backend: фактические допустимые transitions нужно согласовать с Юрием. Не ставить Resolved от одного лишь `investigation.completed`.

## 11. Состояния и безопасность

- Loading summary / loading конкретной вкладки независимо.
- Not found / project forbidden — никаких чужих данных.
- No current investigation — приглашение запустить (Admin/Developer).
- Live reconnect — явный badge `Reconnecting`, сохранённая история; при reconnect дедуплицировать events.
- Source expired — Evidence excerpt остаётся, original deep link может быть недоступен.
- RCA pending / ready / partial / validation failed — отдельные UI состояния.
- Cancel pending, Retry pending, Review pending, Review rejected by Backend, concurrent review conflict.
- Санитизация tool output, блокировка XSS в логах, никаких raw token/LLM prompt, никаких GitHub/API credentials.

## 12. Критерии приёмки

- [ ] Точная навигация по `incidentId`, статусу и выбранному `investigationId`.
- [ ] Все **шесть вкладок** присутствуют и имеют содержимое/корректные пустые состояния.
- [ ] Live Investigation показывает реальный feed, а не scripted tool sequence.
- [ ] Hypotheses — не более трёх, confidence/статус/ссылки на Evidence.
- [ ] Evidence связаны с первоисточниками и доступен sanitized detail.
- [ ] Timeline не смешивает факт с предположенной причинностью.
- [ ] RCA содержит symptoms/root cause/remediation/prevention/metadata.
- [ ] Human review доступен Admin/Developer, сохраняется на сервере.
- [ ] Cancel/Retry создают корректные состояния и сохраняют историю предыдущего run.
- [ ] `Investigation completed` **не** означает `Incident resolved`.
- [ ] Graceful handling для reconnect, timeouts, inconclusive, partial data, missing source и forbidden.
