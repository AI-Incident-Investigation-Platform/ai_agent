# 04. Live Investigations — Реестр запусков AI-агента

**Figma:** [B / Live investigations — Agent runs](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-28)  
**Маршрут (предложение):** `/investigations`  
**Приоритет:** P0  
**Важно:** этот экран — **общий список investigation runs**; вкладка `Live Investigation` внутри Incident Detail описана отдельно в `10_INCIDENT_DETAIL.md`.

## 1. Задача экрана

Показывать, какие расследования выполняются, какие закончились, какие требуют проверки и по какой причине произошла ошибка. Это операционный мониторинг **AI Worker / LangGraph**, не сервисных метрик исследуемого приложения.

## 2. Компоновка макета

Заголовок `Live investigations`, подпись `Active and historical agent executions with tool-by-tool progress`. Первый ряд: три KPI:

- `RUNNING` — в демо `01`, подстрока `INC-1042 · Step 12/20`.
- `AWAITING REVIEW` — демо `02`, но смысл уточняется: это количество инцидентов, ожидающих человеческой проверки RCA (не AI run status).
- `COMPLETED / 24H` — демо `18` завершённых расследований за сутки.

Ниже две панели: слева `RECENT AGENT RUNS` (компактный список), справа `INC-1042 / LIVE TOOL CALLS` (лента выбранного run). Правая область шире, данные плотные, заголовок ленты явно показывает `STEP 12 / 20`.

## 3. Левая панель — Investigation Runs

Каждый элемент:

- Incident ID и, если есть, run ID или попытка `#2`.
- Основной service и project/environment.
- Run status: Queued / Running / Completed / Inconclusive / Failed / Timed out / Cancelled.
- StartedAt, продолжительность, количество шагов или tool calls, если информация доступна.
- При выборе подсвечивается строка и загружается правая лента; в URL желательно передавать `investigationId`.

**Важно:** Retry создаёт новый run; список должен позволять отличить историю предыдущих попыток. Не перезаписывать старые траектории одной записью и не путать completed run с resolved incident.

## 4. Правая панель — Tool Activity Feed

Макет содержит образцы: `search_logs`, `query_prometheus`, `get_trace`, `get_recent_deployments`, `git_diff`. У каждого события:

| Поле | Требование |
|---|---|
| Время | Timestamp события (включая дату при необходимости), timezone |
| Tool name | Читаемое имя инструмента/операции |
| Status | Pending/Running/Completed/Failed с текстом и индикатором |
| Action summary | Что агент пытается проверить (без скрытой chain-of-thought) |
| Result summary | Краткое наблюдение; не путать с root cause |
| Duration | Время вызова инструмента, если есть |
| Details | Раскрываемая санитизированная информация, валидный JSON/фрагмент при наличии |
| Evidence links | Ссылки на Evidence, если результат вошёл в доказательную базу |

Лента — события конкретного `investigationId`, отсортированные по sequence/timestamp. Новые события добавляются снизу без постоянной потери scroll position. Если пользователь ушёл вверх читать историю, не «дёргать» прокрутку: показать `N new events · Jump to latest`.

Состояния Tool Calls отображаются отдельно от статуса самого расследования; Tool Call `failed` не означает, что всё расследование провалилось.

## 5. Realtime / WebSocket

Алгоритм клиентской реализации:

1. REST: загрузить текущий snapshot выбранного run и исторические events.
2. WebSocket: подписаться на **конкретный run** или соответствующий incident по утверждённому контракту.
3. Отобразить живые `tool.started`, `tool.completed`, `tool.failed`, `hypothesis.updated`, `evidence.added`, `investigation.completed` (названия **иллюстративны**).
4. При reconnect запросить пропущенные события или reload snapshot; удалить дубликаты по event ID/sequence.
5. При `completed/failed/timed_out/cancelled` закрыть live-state, но сохранить исторические события.

WebSocket содержит минимум уникальный event ID, incidentId, investigationId, type, timestamp и sequence. Полную shape уточнить с Backend в Contract-First процессе.

## 6. Действия

- Выбрать расследование слева.
- Перейти по run/incident в Incident Detail.
- Раскрыть details tool call и связанные Evidence.
- `Cancel` активного run — Admin/Developer, с подтверждением и состоянием ожидания; отмена может быть не мгновенной.
- `Retry` завершённого/ошибочного run — Admin/Developer, новый investigation ID и сохранение старой истории. Когда именно разрешать Retry (пока running? после cancel?) определяется серверным state machine.
- `Restart with Context` **не входит в MVP**.

## 7. Данные от Backend

- `listInvestigations(filters, page)`.
- `getInvestigation(id)` со статусом и метаданными run.
- `listInvestigationEvents(id, afterSequence?)`.
- `cancelInvestigation(id)` и `retryInvestigation(id)`.
- Realtime subscription + replay/reload strategy.

Окончательные эндпоинты, event names и JSON payloads пока не утверждены; не вводить их жёстко внутри UI-компонентов.

## 8. Состояния и ограничения

- `Queued`: показывать очередь и отсутствие активных tool calls без фиктивного прогресса.
- `Running`: время, последние events, индикатор активности.
- `Inconclusive`: расследование завершено без доказанной первопричины — это допустимый результат.
- `Failed`: ошибка системы/инструмента с безопасным сообщением.
- `Timed out`: достигнут лимит ~20 минут; отдельное состояние, сохранённый progress.
- `Cancelled`: чётко отличать от Failed.
- `Disconnected`: connection status UI не меняет run status.
- Допускаются пропуски телеметрии, tool errors и redacted данные; показывать объяснение, но не секреты.

Никогда не отображать скрытые рассуждения LLM, system prompts или непроверенное утверждение «агент точно нашёл root cause».

## 9. Приёмка

- [ ] В списке ясно различимы incident и отдельные investigation runs.
- [ ] Реaltime события приходят, отображаются по порядку и не дублируются после reconnect.
- [ ] Tool feed показывает имя, статус, summary и раскрываемые очищенные details.
- [ ] Cancel/Retry работают с реальным Backend, включая права и ошибки.
- [ ] Завершение run не переводит автоматически incident в Resolved.
- [ ] Успешно отработаны сценарии long-running (до 20 минут), disconnected и cancelled.
