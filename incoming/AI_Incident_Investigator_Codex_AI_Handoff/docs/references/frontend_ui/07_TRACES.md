# 07. Traces — Distributed Tracing

**Figma:** [B / Traces — Distributed tracing](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-34)  
**Маршрут (предложение):** `/traces`  
**Приоритет:** P0 — ссылка на реальные Tempo traces и краткая причина задержки в Evidence; P1 — встроенный waterfall и навигация по spans.

## 1. Задача

Показать фактический путь запроса через микросервисы: где возникла задержка, какие spans вернули error, как связаны сервисы, какой trace_id соответствует проблеме. Трассировки приходят из OpenTelemetry/Tempo через Backend. Поддержка trace/request correlation с логами — ключевая потребность системы.

## 2. Макет

Заголовок `Traces`, текст `Distributed traces and spans collected through OpenTelemetry / Tempo`. Верхняя полоса фильтров `Service: All`, `Status: Error`, `Duration: > 500ms`, `Last 1 hour`, кнопка `Search traces`.

Ниже две большие панели по всей ширине контента:

- `RECENT TRACES` — табличный список.
- `TRACE WATERFALL` — список span-операций с горизонтальными длительностями на общей временной оси.

В макете trace IDs укорочены (`af1233d7...`), root services (`api-gateway` и др.), durations (`1.48s`, `1.21s`, `892ms`), spans count и `Error`.

### 2.1. Таблица Traces

Колонки:

| Поле | Отображение |
|---|---|
| Trace ID | Укороченный hex ID + копирование полного ID в detail |
| Root service | Начальный/entry service, если подтверждён |
| Duration | Число + единица, единый формат |
| Span count | Целое количество |
| Status | Error/OK/Unknown (из трассировки, не severity incident) |
| Start time | Timestamp + timezone |

Поддержать серверный поиск/фильтры, лимиты, next page. Нажатие на строку выбирает trace и обновляет waterfall без перехода на другую страницу, если так удобнее. Также deep-link в Grafana Tempo при наличии.

### 2.2. Trace Waterfall

В Figma пятирядный пример:

```text
api-gateway / POST checkout
  order-service / process
    payment-service / charge
      postgres / acquire connection
    inventory-service / reserve
```

Каждый span рисуется на **общей временной оси** с реальным start offset и duration, иначе сравнение некорректно. Отступ показывает parent/child. Цвет выделяет ошибочные/медленные участки, но не должен означать достоверную первопричину.

В карточке span при выборе:

- Operation name, Service name.
- Span ID/Trace ID, Parent Span ID.
- Start timestamp, duration, status/error.
- Attributes/events, сетевые и DB metadata после серверной санитизации.
- Ссылка `Find related logs` по trace ID; при доступности — `Open in Tempo`.

**Нюанс для разработчика:** parent span обычно включает время child spans. Нельзя автоматически пометить span с наибольшей inclusive duration как виновника. Визуализация показывает наблюдение, вывод RCA делает агент по всем Evidence.

## 3. UX-сценарии

1. Из Evidence/Incident Detail открыть trace ID с предустановленным проектом/временем.
2. В списке выбрать error trace → увидеть реальную waterfall-схему.
3. Выбрать медленный DB span → detail и ссылка на связанные логи.
4. Кликнуть `Open in Tempo` → новая вкладка с проверенным URL.
5. По отсутствующему trace показать `Trace not found / expired`, а не пустую чёрную панель.

## 4. Backend capabilities

- `searchTraces({projectId,environment,serviceId,timeRange,status,minDuration,pagination})`, если Tempo-поиск доступен.
- `getTrace(traceId,context)` → metadata + spans (IDs, parent IDs, service, operation, times, status, sanitized attributes/events).
- `getTraceDeepLink`, опционально correlation to logs.
- Time units в API должны быть однозначны (`ms`, `ns` или ISO), фронтенд не угадывает.
- Ошибки `not found`, `expired`, `source unavailable`, `access denied` различаются.

Не выполнять запросы напрямую из браузера в Tempo. Не конструировать из сырых span attributes потенциально опасные URL.

## 5. Состояния / performance

- Traces loading и waterfall skeleton.
- Search gave no matching traces.
- Trace отсутствует из-за истекшего retention.
- Частичный trace: некоторые spans/parent IDs отсутствуют, показывать `Partial trace`.
- Очень глубокая цепочка: сворачивание поддеревьев, ограничение числа строк с опцией `Load more`.
- Нестандартные duration / clock skew: не рисовать отрицательные полосы, явно обозначить аномалии.
- Mobile: таблица компактная/локальный scroll, waterfall отдельно со скроллом и zoom.

## 6. Приёмка

- [ ] Таблица показывает реальные trace summaries и фильтруется по сервису/времени.
- [ ] Waterfall визуально соответствует началу/длительности каждого span.
- [ ] Можно открыть span detail и перейти к связанным логам/Tempo.
- [ ] Истёкший trace и недоступный Tempo корректно различаются.
- [ ] Нет недоказанной маркировки span как Root Cause.
- [ ] Переход из Incident Detail сохраняет контекст проекта, сервиса и времени.
