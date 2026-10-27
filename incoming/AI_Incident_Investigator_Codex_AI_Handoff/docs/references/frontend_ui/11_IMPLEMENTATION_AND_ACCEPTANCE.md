# 11. План передачи frontend-разработчику и общая приёмка

## 1. Что получает разработчик

- Редактируемые Figma-макеты: [AI Incident Investigator — вариант B](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-2).
- 9 самостоятельных документов по экранам (`02`–`10`).
- Общая дизайн-система и shell (`01`), оглавление (`00`).
- Контекст остальных систем: Backend REST/WebSocket и AI Agent через Backend. Основной продукт не требует прямого браузерного MCP.

Демо-значения из Figma (например, `ACME`, `INC-1042`, `12.8%`, `Connected`) нужны исключительно для визуализации и mock-режима. В готовом приложении они заменяются данными Backend.

## 2. Ожидаемый результат работы

Реализовать frontend в отдельном репозитории, максимально близкий к макетам, с корректным navigation/layout и переиспользованием компонентов. Экран состоит из **реальных DOM-компонентов**, а не статичного большого изображения макета. Frontend работает на моках до готовности API и затем подключается к Backend через стабильный слой API client.

Стек React/Next.js/другой frontend-фреймворк и пакет UI-компонентов не утверждены; разработчик предлагает выбор и фиксирует его отдельно. Исходить из поддерживаемости, TypeScript-типизации и качественного тестирования. Не навязывать лишние state libraries/микрофреймворки.

## 3. Рекомендуемая последовательность реализации

### Фаза A. Foundation (обязательная)

- Структура frontend-проекта, TypeScript, линтинг, code style, CI GitHub Actions.
- `SRE / Dark UI` tokens (цвета/отступы/типографика), App Shell (sidebar + top bar + content).
- Общая библиотека UI: Button, Badge, Panel, Table, Filter, Tabs, Skeleton, Empty/Error state, SourceLink.
- Routes, 404/403/login guard, подготовка RBAC-модели в клиента.
- Mock provider и fixtures для всех экранов.

### Фаза B. Сквозной MVP (обязательная)

1. **Overview** и **Incidents** с фильтрами, пагинацией, ссылками.
2. **Incident Detail** с заголовком, summary, вкладками.
3. **Live Investigation** (общая страница + вкладка) с моком WebSocket events, затем реальной интеграцией.
4. **Hypotheses, Evidence, Timeline, RCA Report** на основе backend data.
5. **Cancel, Retry, Human Review** с permission guards и жизненным циклом запроса.
6. **Integrations** — базовый список/форма/проверка подключения при готовом Backend.

### Фаза C. Полнота макета / расширения

- **Service Map** с подтверждёнными связями и fallback.
- **Logs & Metrics** с безопасным query explorer + metric charts при поддержке.
- **Traces** с реальным waterfall/span viewer.
- **Settings** с админскими формами при готовом API.
- Расширение accessibility/responsive/performance на длинных данных и больших инсталляциях.

Важно: макеты всех 9 экранов должны иметь **хотя бы визуально работающий навигационный каркас**, даже если диагностические backend-функции отдельных P1-страниц будут реализованы позже.

## 4. Согласование с Backend до настоящей интеграции

**Contract-First** — отдельная командная задача (спецификации ещё не утверждены):

| Контракт | Для каких UI возможностей нужен |
|---|---|
| REST OpenAPI | Инциденты, проекты, сервисы, runs, Evidence, RCA, integrations/settings |
| WebSocket JSON Schema | События по incident/run, live tool calls, статус, reconnect |
| Permissions/role model | Доступ к разделам и командам, guard на уровне проектов |
| Source deep-link contract | Безопасные ссылки в Kibana, Grafana, Tempo, GitHub |
| Error taxonomy | 401, 403, 404, 409, 429, validation, source unavailable |

Полезно хранить схемы централизованно, из них генерировать TS-типы, а mock fixtures в тестах валидировать теми же схемами. **Названия маршрутов в этих документах предлагаемые**, реальные URL решаются с Юрием.

## 5. Сквозные проверочные сценарии

1. Alertmanager → создан новый Incident → Overview/Incidents показывает новую запись → пользователь открывает Incident Detail.
2. Backend публикует investigation started → общая страница Live Investigations и вкладка в Incident Detail отображают run.
3. AI вызывает read-only инструменты → в UI приходят настоящие tool call events и краткие результаты, доступен Evidence link.
4. WebSocket пропадает на 15 секунд → интерфейс показывает reconnect, после восстановления исторический feed полон и не дублируется.
5. AI завершает investigation с RCA → инцидент попадает в Awaiting Review, но **не становится Resolved автоматически**.
6. Developer подтверждает/исправляет Root Cause → сервер сохраняет решение и review metadata.
7. Viewer видит те же разрешённые отчёты, но не видит управляющие действия или получает disabled с причиной.
8. Пользователь Cancel текущий run, затем Retry → создаётся новый ID, история старого запуска остаётся доступной.
9. Один источник (Tempo) выключен, остальные доступны → Incident Detail показывает частично собранные Evidence без фальшивого «всё работает».
10. Лог содержит огромный stack trace/строку/потенциальную HTML-инъекцию → UI отображает как безопасный текст и не ломает layout.

## 6. Unit / integration / E2E

**Unit:** mapping статус→badge, timezones, percent/unit formatting, table filters, route guard, event dedup/reducer, permissions. **Component:** Tabs, EvidenceDetail, RCA Review, Request/Error states, ToolFeed, DataTable. **Integration:** typed API client с mock REST/WS (pending/late/duplicate/missing messages), Cancel/Retry, permission changes. **E2E:** совместный docker-compose стенд с настоящими Backend/AI, минимум один воспроизводимый fault сценарий до RCA.

## 7. QA для дизайна

- Сравнить реальный скриншот приложения с Figma для каждого из 9 экранов при 1440×940, тёмная тема.
- Проверить sidebar/header, panel spacing, типографику, responsive на 1280/1024/768/390.
- Показать 0/1/1000 записей, критичные и длинные строки, пустой источник, длительный running >10 минут.
- Никаких лишних круговых диаграмм, красочных декоративных блоков, фальшивой AI-активности.
- Видимый keyboard focus, aria labels, чтение таблиц, сохранение состояния фильтров после Back/Forward.
- Интеграции и ссылки не получают секреты из клиента, все privileged операции через Backend.

## 8. Что требуется передать команде по завершении

- Ссылку на frontend-репозиторий и работающую инструкцию локального запуска.
- Демо на mock API + режим подключения к настоящему Backend; переключение конфигурацией.
- Скриншоты 9 страниц для визуального сравнения и список сознательных отличий от Figma.
- Документацию о требуемых Backend API и полях; список блокирующих контрактных вопросов.
- Тесты и CI GitHub Actions (lint/typecheck/test/build).
- Dockerfile + соответствующий Compose service contract для инфраструктурного репозитория.

## 9. Открытые решения (не считать согласованными)

- Конкретный frontend-стек и UI-библиотека.
- Итоговые REST endpoints, JSON Schema WebSocket событий, структура response/error DTO.
- Реальная серверная модель user session/refresh JWT и frontend токен-хранилища.
- Точный набор управляемых полей Settings, retention policy и организация Workspace.
- Возможности серверных API Service Map, произвольного Logs/PromQL Explorer, Tempo search.
- Полные визуальные подэкраны вкладок Incident Detail: Figma пока показывает одну активную вкладку; остальные расписаны в `10_INCIDENT_DETAIL.md` на уровне реализации.

С этими пунктами **нужно не угадывать**, а согласовать контракт с владельцем Backend/Team Lead. На моках можно продолжать UI-разработку параллельно.
