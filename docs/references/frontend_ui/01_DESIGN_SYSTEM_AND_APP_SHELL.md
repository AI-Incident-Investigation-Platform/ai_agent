# 01. Общий дизайн, App Shell и компоненты

**Figma:** [Все макеты варианта B](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-2).  
**Связанные экраны:** все 9 макетов. **Обязательность:** P0.

## 1. Визуальный характер

Направление — профессиональный инструмент наблюдаемости/SRE, близкий по информационной плотности к Grafana/Datadog, но со своей спокойной стилистикой. Приоритет: диагностика, читаемость, реальные данные, доступность. Не использовать glow, большие градиенты, декоративные 3D-иллюстрации, бессодержательные KPI, карточки ради заполнения пространства и «нейрослоп».

В существующих макетах базовый desktop frame **1440 × 940 px**. Это ориентир, не жёсткий размер окна. **Sidebar шириной ~207 px**, верхняя полоса высотой ~73 px; основной контент начинается примерно на `x=244 px` и имеет боковой отступ ~37 px. Отступы между крупными панелями обычно 14–20 px, внутри панелей — около 16–20 px. Радиус панелей ~8 px, полей ~5 px. Уточнять по Figma, не кодировать макет абсолютными координатами.

### Цвета из Figma / дизайн-токены

| Токен | HEX | Использование |
|---|---|---|
| `app/bg` | `#0D151E` | Основной фон приложения |
| `sidebar/bg` | `#111C28` | Левая навигация |
| `panel/bg` | `#131E2A` | Панели, карточки, списки |
| `panel/raised` | `#192736` | Формы и интерактивные области |
| `border` | `#2B3A49` | Разделители/границы |
| `text/primary` | `#F2F5F8` | Основной текст |
| `text/secondary` | `#9CAFC0` | Подписи/второстепенные сведения |
| `text/muted` | `#758B9E` | Лейблы, вспомогательная информация |
| `accent/amber` | `#E9A968` | Акцент навигации, активный элемент |
| `signal/success` | `#79CDA9` | Успешные подключения/состояния |
| `signal/error` | `#ED9394` | Ошибки/Critical |
| `signal/warning` | `#E7B67D` | High/Degraded/Pending |
| `signal/info` | `#93B5E8` | Активные расследования/ссылки |

В Figma на странице `02 — B / Product screens` создана коллекция цветовых переменных `SRE / Dark UI`. Желательно использовать их как отправную точку для CSS variables/theme object. Цвет — **дополнительный** признак статуса, обязательно использовать текст/значок.

### Типографика и плотность

- **Inter**: Regular / Medium / Semi Bold; в макете встречается Bold в логотипе.
- Заголовок страницы ~27 px, имя панели ~12–14 px с Semi Bold, значения KPI ~27 px.
- Табличные строки ~11–12 px, лейблы заглавными буквами ~10 px. Для реального приложения при необходимости увеличить мелкий текст до 12 px при сохранении плотности и контраста; не жертвовать доступностью ради точного пиксельного совпадения.
- Технические идентификаторы и код допускается отображать моноширинным шрифтом, значения должны переноситься/усекаться управляемо.
- Выравнивание таблиц, единиц измерения и чисел должно быть последовательным. Время — с указанием timezone в контексте.

## 2. App Shell

### Левая навигация (sticky на desktop)

Бренд вверху: иконка `//`, имя `IncidentOps`, подпись `OBSERVABILITY` — **рабочие названия из Figma**, на финальной стадии можно заменить на AI Incident Investigator без изменения структуры.

Раздел `EXPLORE` в точном порядке:

1. Overview
2. Incidents
3. Live investigations
4. Service map
5. Logs & metrics
6. Traces

Под разделителем:

7. Integrations
8. Settings

Пункт активного маршрута подсвечивается тёмно-синим прямоугольником и янтарной меткой слева от названия; остальные — приглушённые. Навигация keyboard-accessible и сопровождается `aria-current="page"`. Не дублировать каждый экран отдельным приложением: общий shell един для всех маршрутов.

### Верхняя панель

Слева контекст текущего workspace/project, справа текущий environment (`Production` в макете), дата/время/фильтр окружения, при необходимости user menu. Названия `ACME / PLATFORM` — фиктивные, подставлять реальные выбранные данные.

Если пользователь изменяет Project/Environment, **все экранные запросы должны получать согласованный контекст**; контент другого проекта не должен «подмешиваться» из кэша. Текущий Project/Environment — и в URL/query params, и в приложении с одним источником истины по согласованному UX.

### Контентная область

Заголовок страницы, короткое описание, затем содержимое. На desktop сетка панелей с 2–4 колонками по месту; при уменьшении ширины — перестраивается в 1–2 колонки. Не допускать горизонтального скролла **всей страницы** из-за таблиц; при необходимости горизонтально прокручивается только таблица/контейнер с данными.

## 3. Библиотека общих UI-компонентов

| Компонент | Назначение | Важные props/состояния |
|---|---|---|
| `AppShell` | Sidebar + header + content | activeRoute, workspace, environment |
| `SidebarNavItem` | Пункт навигации | label, active, disabled, href |
| `EnvironmentSelector` | Переключение окружения | value, options, loading, forbidden |
| `PageHeader` | Заголовок/подзаголовок + действия | title, description, actions |
| `MetricCard` | Число/единица/тренд | label, value, delta, severity, updatedAt |
| `StatusBadge` | Severity, IncidentStatus, RunStatus | variant, label, icon |
| `DataTable` | Отображение коллекций | columns, sorting, loading, pagination, empty |
| `FilterField`, `SearchField` | Поиск и фильтры | onChange, debounce, clear, disabled |
| `Panel`, `KeyValueRow` | Компактные контейнеры | title, subtitle, collapsible |
| `TimeRangePicker` | Диапазон для телеметрии | from/to, relative presets, timezone |
| `SourceLink` | Ссылка в Kibana/Grafana/Tempo/GitHub | validatedUrl, source, availability |
| `CodeExcerptViewer` | Raw excerpt, JSON, Git diff | redact, maxLength, copy, wrap |
| `EventFeed` | События расследования | sequence, timestamp, toolStatus, details |
| `EmptyState`, `ErrorState`, `LoadingSkeleton` | Системные состояния | message, retry, permission |
| `ConfirmationDialog` | Подтверждение отмены | pending/error/final |

В Figma есть начальные компоненты `Sidebar item / active` и `Sidebar item / default`; остальную библиотеку можно создать в frontend по мере реализации. Если компонент переиспользуется на многих страницах, его нужно выделить в единое UI-ядро.

## 4. Единая семантика статусов

### Severity (инцидент)

`Critical`, `High`, `Medium`, `Low`. Отображать и цвет, и текст. Severity не равен состоянию расследования.

### Incident status (жизненный цикл инцидента)

`Open`, `Investigating`, `Awaiting Review`, `Resolved` — согласованные пользовательские названия.

### Investigation run status

**Отдельный статус** конкретного запуска. Примерные отображаемые значения: `Queued`, `Running`, `Completed`, `Inconclusive`, `Failed`, `Timed out`, `Cancelled`. Wire codes и полный transition graph ещё согласуются в API-контрактах. `Completed` ≠ `Resolved`.

### Tool call status

`Pending`, `Running`, `Completed`, `Failed`; при необходимости `Cancelled`. Статус tool call привязан к конкретному investigation run, а не ко всему incident.

### Hypothesis

`Pending`, `Supported`, `Rejected` плюс confidence `High`, `Medium`, `Low`. Поддерживаются **до трёх гипотез**. Confidence качественный, **не рисовать искусственный процент вероятности**.

## 5. API и WebSocket — глобальное поведение

- Источник всех данных и команд — **Backend REST API**; поток живых событий — **WebSocket**.
- Приложение должно иметь API adapter и типы/схемы данных независимо от компонентов. Пока Backend готовится, mock-provider должен использовать те же клиентские интерфейсы.
- На WebSocket reconnect: загрузить актуальный snapshot и пропущенные события по `event_id/sequence`, убрать дубликаты, соблюдать порядок внутри run. Не считать потерю соединения с браузером ошибкой самого агента.
- Редактируемые или критичные состояния (`Cancel`, `Retry`, `Human Review`, integrations) отправляются командами в Backend с обработкой pending, success, rejection и error.
- Нельзя полагаться на клиентское скрытие кнопок для безопасности. Проверка project/environment permissions — ответственность Backend.
- Секреты и raw chain-of-thought не выводить. Raw logs, tool JSON и git diff — только санитизированные backend excerpts с ограничением размера.

## 6. RBAC

| Действие | Admin | Developer | Viewer |
|---|---|---|---|
| Просмотр разрешённых инцидентов, диагностических данных, RCA | Да | Да | Да |
| Start / Cancel / Retry investigation | Да | Да | Нет |
| Подтвердить / отклонить / исправить Root Cause | Да | Да | Нет |
| Управлять Project, Environment, Integration, User | Да | Нет | Нет |

Для Viewer управляющие кнопки неактивны или скрыты; для `403` отображать понятный отказ без утечки данных. Для `401` — переход к авторизации/обновлению сессии по выбранной командой схеме.

## 7. Обязательные состояния каждой страницы

`initial loading`, `empty`, `no results after filtering`, `partial data`, `permission denied`, `request error + retry`, `disconnected/reconnecting WS`, `stale data`, `resource not found`, `slow backend`. Внесённые фильтры и табы не должны неожиданно обнуляться при кратковременной потере сети. Пустые данные — не то же самое, что ноль на графике.

## 8. Responsive, accessibility, performance

- Desktop ≥ 1280: фиксированный sidebar, контент 2–4 колонки; ноутбук 1024–1279: sidebar может сжиматься/сворачиваться; tablet/mobile: drawer/hamburger с доступным фокусом, карточки в одну колонку.
- Все действия доступны с клавиатуры, видимый focus; у таблиц корректные заголовки, у кнопок aria-label, у live region ненавязчивое озвучивание критичных статусов.
- WCAG AA по контрасту текста как целевой стандарт; не использовать цвет как единственный признак severity.
- Длинные trace IDs, query, stack traces и log entries — truncation с полным просмотром, виртуализация для действительно больших списков.
- Графики доступны альтернативой в виде таблиц с данными; учитывать `prefers-reduced-motion`.

## 9. Не включать без отдельного согласования

- Круговую диаграмму `Incidents by Severity` (пользователь её исключил).
- Кнопки `Auto-fix`, `Restart container`, `Rollback`, `Execute patch`; агент read-only.
- Отображение скрытой цепочки рассуждений модели; можно показывать только короткое описание диагностического шага.
- Генерацию выдуманных логов, Evidence или live activity в рабочем окружении.
- Прямую сетевую коммуникацию браузера с llama.cpp, MCP Server или инфраструктурой исследуемого приложения.

## 10. Критерий готовности общего каркаса

- Навигация открывает все 8 разделов, а из инцидентов — Incident Detail; кнопки «Назад» и прямой URL работают.
- Тема визуально соответствует Figma; нет горизонтальной прокрутки страницы на 1280 px.
- Соответствующий пункт sidebar подсвечен, environment работает единообразно.
- Для каждого раздела есть минимум loading/empty/error/success и понятные RBAC-состояния.
- У проекта единые компоненты, типизация и работающий mock mode — frontend можно разрабатывать до готовности Backend.
