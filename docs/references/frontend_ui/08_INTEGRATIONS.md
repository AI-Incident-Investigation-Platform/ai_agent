# 08. Integrations — Управление источниками данных

**Figma:** [B / Integrations — Connections & credentials](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-36)  
**Маршрут (предложение):** `/integrations`  
**Приоритет:** P0 — базовый список/создание/проверка важных подключений; P1 — расширенные формы и диагностика.  
**Роли:** Admin — управление, Developer/Viewer — просмотр статуса при разрешении Backend.

## 1. Назначение

Администратор подключает источники, которые AI Agent и диагностические tools используют для расследований. Страница управляет настройками на уровне **Project / Environment**, а не выполняет напрямую запросы внешних систем из браузера. Важны безопасность, понятные статусы подключений и проверка конфигурации.

## 2. Макет и содержание

Заголовок `Integrations`, пояснение `Configure read-only telemetry and code connections per project and environment`; справа кнопка `+ Add integration`. Основной контент — широкая панель `CONNECTED DATA SOURCES` с шестью строками. Каждая строка содержит квадратную иконку/двухбуквенный символ, имя и назначение, endpoint/repository hint, статус и ссылку `Configure →`.

Пример демонстрационных строк Figma:

| Интеграция | Назначение | Что показывает UI |
|---|---|---|
| Elasticsearch | Logs, stack traces, correlation IDs | URL/alias, состояние соединения |
| Prometheus | Metrics, alerts, PromQL diagnostics | URL/alias, состояние |
| Grafana Tempo | Traces и span metadata | URL/alias, состояние |
| GitHub | Repository code, commits and diffs | Organization/repositories, `read-only` |
| Docker diagnostics | Container state, restarts, OOM | Diagnostic adapter endpoint/status |
| Deployment API | Universal deployment event ingestion | Webhook/API state, не GitHub Actions интеграция |

`Connected` и `Limited` в Figma — **примерные UI-состояния**, окончательную семантику source health и permission scope даёт Backend. `Limited` может означать частичный доступ (например, Docker diagnostic read-only), но нельзя трактовать как ошибку без контрактов.

### 2.1. Добавление интеграции

Кнопка `+ Add integration` открывает wizard/side panel:

1. Выбрать тип (`Elasticsearch`, `Prometheus`, `Tempo`, `GitHub`, `Docker diagnostics`, `Deployment webhook` и т. д.).
2. Выбрать Project и, если применимо, Environment (из разрешённых).
3. Ввести endpoint/название/репозитории.
4. Ввести credentials **только в защищённую форму** с password field; не сохранять токен в localStorage или открытом клиентском кеше.
5. Нажать `Test connection`; отобразить `Testing`, `Connected`, `Authentication failed`, `Unreachable`, `Insufficient permissions`, `Timed out` или серверную ошибку.
6. Сохранить конфигурацию и вернуться к списку.

Если тест не пройден, правила разрешения сохранить «непроверенную» интеграцию определяются Backend (не решать молча на клиенте).

### 2.2. Редактирование

`Configure →` открывает подробности выбранной интеграции: alias, URL/host (без секретов), scope, access mode, `Last checked`, кнопки `Test`, `Edit`, `Disconnect` по правам. При изменении credentials **не показывать прежний секрет**, поле остаётся пустым с подсказкой `Keep existing token unless changed`, если Backend поддерживает такую семантику.

Удаление/disconnect — потенциально влияет на расследования; показывать подтверждение с объяснением. Никогда не отправлять запросы на удаление «на hover» и не проводить непредусмотренное auto-reconnect.

## 3. Что не входит в область этой страницы

- Сам MCP Client/Server и управление агентным ReAct loop.
- Прямое редактирование индексов Elasticsearch, Prometheus scrape targets, GitHub кода, Docker API.
- Анализ CI workflows / GitHub Actions — мы отдельно исключили из расследований.
- Настройка полноценного Multi-Tenant SaaS: вопрос откатили из требований, текущий MVP не требует отдельного управления компаниями.

## 4. Требования к Backend / контрактам

Backend обеспечивает **capabilities** (окончательные REST paths отдельно):

- `listIntegrations(projectId, environment)` + только безопасные public metadata.
- `getIntegration(id)` со статусом/last checked и без credentials.
- `create/update/deleteIntegration` (Admin-only, с audit).
- `testIntegrationConnection(id or draft)` — только через Backend, не через browser прямым запросом к чужому endpoint.
- `getAllowedIntegrationTypes` с обязательными/доступными полями, credential-kind, read-only capabilities (опционально).
- Запрет на SSRF и произвольный доступ к HTTP endpoints решается Backend; frontend валидирует формат как UX, но не полагается на это для безопасности.

### Credential handling

- Токены/пароли не отображать после сохранения, даже Admin.
- Ошибки не должны утекать raw tokens, private headers, connection strings с паролями.
- Не сохранять секреты в Redux DevTools, frontend logs, browser analytics.
- RBAC и доступ на уровне Project/Environment обязан проверять сервер.

## 5. UX и ошибки

- **Loading:** список skeleton.
- **Empty:** нет интеграций → Admin видит `Add integration`, Viewer — read-only info.
- **Connection unknown:** нейтральный label, не `Connected`.
- **Partial:** 4 источника работают, 2 недоступны → показывать статусы по каждому.
- **Temporary test failure:** error + retry, сохранённая интеграция не исчезает.
- **No permission:** `403`, без утечки endpoint/credentials.
- **Source decommissioned:** явный статус и время последнего успешного connection check.

## 6. Приёмка

- [ ] Источники отображаются по разрешённому проекту, типу и статусу.
- [ ] Admin может добавить/проверить/отредактировать подключение по контракту Backend.
- [ ] Viewer/Developer не могут менять секреты/подключения.
- [ ] Ни один секрет не возвращается/не появляется в DOM после сохранения.
- [ ] `Test connection` выполняет именно Backend, ошибки понятны.
- [ ] Сервисные ссылки и статусы не подменяются вымышленными «Connected».
