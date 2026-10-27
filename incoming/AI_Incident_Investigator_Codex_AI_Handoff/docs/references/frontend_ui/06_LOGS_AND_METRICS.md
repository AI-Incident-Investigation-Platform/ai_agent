# 06. Logs & Metrics — Просмотр телеметрии

**Figma:** [B / Logs & metrics — Telemetry explorer](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-32)  
**Маршрут (предложение):** `/telemetry`  
**Приоритет:** P0 — просмотр Evidence excerpts + ссылки в источник из инцидента; P1 — полноценный исследовательский экран с запросами и встроенными метриками.

## 1. Назначение

Позволить инженеру проверить исходные сигналы: ошибки приложения, timestamp, request/trace correlation, значения метрик и ссылку на оригинальную систему (Kibana/Prometheus/Grafana). **Frontend не заменяет Elasticsearch и Grafana**; для MVP достаточно найденных агентом фактов и переходов к оригиналам. Figma описывает более продвинутую P1-панель.

## 2. Расположение в макете

Название `Logs & metrics`, описание `Query and inspect indexed logs alongside application and system metrics`. Верхняя панель `Telemetry query bar` (поле запроса, источник Elasticsearch, tag `Logs`, кнопка `Run query`). Ниже две колонки: слева `LOG RESULTS` примерно 2/3 ширины, справа `METRICS / PROMETHEUS` примерно 1/3.

### 2.1. Запрос логов

В Figma иллюстративный запрос:

```text
service.name: payment-service AND log.level: ERROR
```

Это **пример строки поиска**, а не гарантия поддержки произвольного Elasticsearch Query DSL. Конкретный режим поиска выбирается с Backend: безопасный structured filter и/или ограниченный query language, per-project scope, max range, лимиты пагинации и timeout. В UI всегда показывать выбранные Project, Environment, Service, time range и source. Нельзя выполнять запросы Elasticsearch непосредственно из браузера и передавать credentials клиенту.

Поведение `Run query`: локальная проверка полей → backend request → loading spinner → log results / descriptive error. Дебаунс без запуска тяжёлых запросов на каждый символ. Отмена активного UI-запроса не означает Cancel Agent Run.

### 2.2. Список Logs Results

В демо показаны записи от `payment-service`, `order-service`, `api-gateway`, `inventory-service` с уровнями `ERROR`, `WARN`, `INFO`. Каждая строка должна показывать:

- Время события с миллисекундами и timezone.
- Уровень `ERROR/WARN/INFO/DEBUG` как текст+badge.
- Service, источник логов, при необходимости environment.
- Краткое сообщение с обрезкой длинной строки.
- По клику: раскрываемый detail с полным очищенным excerpt, полями `trace_id`, `request_id`, `correlation_id`, оригинальным source link, копированием разрешённых фрагментов.

Пагинация/cursor — со стороны Backend, без попытки загрузить все исторические логи. Поиск по trace/request ID — важный shortcut. Если полей нет, не подставлять выдуманные идентификаторы.

### 2.3. Metric inspector

Четыре компактные метрики из макета:

- HTTP error rate (`12.8%`).
- p95 latency (`1.48s`).
- DB pool usage (`100%`).
- CPU usage (`62%`).

Рядом со значением горизонтальный bar/индикатор. **Данные, единицы измерения, знаменатель процентов и timestamp должны быть определены Backend**. p95 latency не является «заполнением полоски», если верхняя граница неизвестна: можно показывать реальное число и график за время вместо произвольного прогресс-бара.

Для P1 добавить реальные line charts с соответствующим запросом PromQL, диапазоном и легендой series. Переход `Open in Grafana` на валидный URL из Backend. Если метрика недоступна, показывать `Unavailable`, не изображать 0%.

## 3. Сценарии

1. Из Incident Evidence нажать на `Connection pool timeout` → открыть Logs & Metrics с предустановленными `project`, `service`, `time range`, возможно `traceId`/query.
2. Выбрать ошибочный лог → раскрыть trace/request ID и перейти в Traces.
3. Переключить таймфрейм → синхронно перезагрузить log results и metrics для нового интервала (без неверных сравнимостей).
4. Открыть оригинальный Kibana/Grafana deep-link для ручной проверки факта.
5. Viewer смотрит только доступные данные; Developer/Admin также выполняют разрешённые поисковые запросы. Даже read-only query считается операцией, требующей лимитов.

## 4. Входящие данные / Backend capabilities

- `searchLogs({projectId,environment,serviceId,range,query,level,traceId,requestId,pagination})` — типизированный безопасный поиск; окончательную схему согласовать.
- `getLogRecord`/selected excerpt для раскрываемой карточки.
- `getMetricSeries` или `getMetricSummary` по allowlisted/validated PromQL, включая units, labels, samples, timeRange.
- `getSourceDeepLink` либо `sourceUrl` в результате запроса (только backend-verified).
- `getConnectionStatus` источника Elasticsearch/Prometheus для понятных ошибок.

Нельзя считать произвольный `query` инструментом неограниченного Elasticsearch DSL; контролировать размер и частоту ответов.

## 5. Состояния / безопасность

- `No data in selected range` отличается от `Source disconnected`.
- Ошибка query syntax выводится пользователю как validation error, не как «нет логов».
- Частично доступная телеметрия: Logs работают даже если Prometheus временно недоступен, и наоборот.
- Secrets, Authorization headers, cookies, tokens, PII в логе маскируются на Backend; frontend не хранит unredacted payloads в localStorage или аналитике.
- Очень длинный JSON/stack trace рендерится в разворачиваемом viewer с безопасным text rendering (не `dangerouslySetInnerHTML`).
- Ограничить слишком длинные диапазоны/количество записей, поддержать cancellation UI-request через AbortController.

## 6. Критерии приёмки

- [ ] По выбору service/range отображаются корректные log excerpts и metric summaries.
- [ ] Можно перейти из Evidence в заранее отфильтрованный результат.
- [ ] Открываются только валидные исходные ссылки, ни один URL не изобретается клиентом.
- [ ] Backend недоступен → чёткий error + retry; пустые данные → отдельный empty state.
- [ ] Длинные сообщения не разрушают таблицу.
- [ ] P1 интерактивный query builder не блокирует P0 исходные Evidence ссылки.
