# 09. Settings — Настройки Workspace и безопасности

**Figma:** [B / Settings — Workspace configuration](https://www.figma.com/design/JFUcynM2y9vIq6vJ7efTOc?node-id=6-38)  
**Маршрут (предложение):** `/settings`  
**Приоритет:** P0 — базовые параметры/права, если есть Backend settings API; P1 — полный экран редактирования и управления пользователями.  
**Роли:** Admin редактирует, Developer/Viewer — только разрешённый read-only просмотр; при отсутствии разрешений раздел скрывается/выводит `Access denied`.

## 1. Цель

Настройки управляют поведением приложения, безопасностью и отображением текущего проекта/окружения. Это **не** консоль безлимитного управления AI-моделью или инфраструктурой; инженерные лимиты задаются сервером и всегда валидируются им независимо от того, что нарисовано в UI.

## 2. Компоновка

Заголовок `Settings`, описание `Workspace preferences, project access, roles and incident behavior`. Две колонки:

- Большая левая панель `GENERAL SETTINGS` (~766×639).
- Справа верхняя панель `ACCESS CONTROL / RBAC` (~393×384).
- Справа нижняя панель `AI RUNTIME / Local` (~393×242).

### 2.1. General Settings

В Figma показаны следующие поля:

| Поле | Пример Figma | UI-требование |
|---|---|---|
| Workspace name | `SRE Platform` | Текстовое имя текущего пространства/проекта по согласованной модели |
| Default project | `E-commerce` | Select из доступных проектов |
| Default environment | `Production` | Select с доступными окружениями |
| Incident retention | `90 days` | Отображать policy, редактирование только если Backend разрешает |
| Investigation timeout | `20 minutes` | Для MVP согласован 20-минутный предел; нельзя превышать серверный лимит |
| Max tool calls | `40` | Глобальный агентный guardrail; UI не должен поднимать сверх конфигурации |
| Agent execution steps | `20` | Глобальный guardrail, server-authoritative |

`Save settings` размещена справа внизу панели. Для редактируемых полей — клиентская валидация, disabled при save, success/error feedback, dirty state, предупреждение перед выходом с несохранёнными данными.

**Критически важно:** показанные значения в макете — иллюстрации ранее согласованных параметров. Возможность администратора изменять `20 steps / 40 calls / 20 minutes` **не была утверждена**; до отдельного решения отображать такие лимиты read-only. Также политику `Incident retention = 90 days` команда отдельно не утверждала — выводить лишь после получения реального значения от Backend.

### 2.2. Access Control / RBAC

Карточка с тремя ролями:

- `Admin` — управление users/projects/integrations.
- `Developer` — запуск investigation, review root cause.
- `Viewer` — чтение доступных инцидентов и отчётов.

В P0 достаточно документировать роли в интерфейсе и отразить актуальную роль пользователя. Если API управления участниками появится, добавить отдельный users table, invitation/revoke/edit-role flow — **не выдумывать поля и процедуры регистрации/приглашений без Backend-контракта**.

### 2.3. AI Runtime

Figma показывает:

- Runtime: `llama.cpp`.
- Model: `Qwen2.5-Coder-7B-Instruct`.
- Execution: `Read-only tools`.

Это обзор текущего состояния AI, а не пункт конфигурации llama.cpp из браузера. В будущем можно показать model health, endpoint reachable, last heartbeat, context window, concurrency — **только при наличии надежных показателей**. Запуск/остановка модели и raw server commands не входят в MVP.

## 3. Поведение и права

- Страница относится к текущему Workspace/Project/Environment согласно серверной модели.
- Server returns effective settings + field-level editability/capabilities, если есть.
- Admin может изменять только разрешённые поля. Developer/Viewer видят допустимые значения в режиме просмотра; настройки секретов на этой странице не показывать.
- Валидация `Save`: интерфейсно и серверно, с обработкой conflict (settings changed elsewhere).
- Источником истины по настройкам является Backend, не localStorage или frontend `.env`.

## 4. API capabilities (предварительные)

- `getEffectiveSettings(context)` → name, project/environment preferences, limits, retention, feature flags/capabilities.
- `updateSettings(context, partial)` → admin-only, validation feedback.
- `getCurrentUserPermissions` и, позднее, управление пользователями/ролями.
- `getAiRuntimeStatus` — опционально и только если отдаёт Backend.

Все имена приведены как **потребности фронтенда**, реальные endpoints/DTO готовятся отдельно в Contract-First.

## 5. States

Loading, read-only, admin editing, dirty, saving, saved, validation error, forbidden, server error, conflict, AI runtime unreachable. При `409/conflict` не перезаписывать серверные значения автоматически. Если нет API для управления конкретным полем — UI отображает текст и состояние `Managed by server`, а не неработающий input.

## 6. Приёмка

- [ ] Стили и расположение полей совпадают с макетом B.
- [ ] Отображаются реальные effective settings или явно `Not configured`.
- [ ] Настройки guardrails не дают поднять лимиты без серверной поддержки.
- [ ] Все изменения, если доступны, проходят RBAC и server-side validation.
- [ ] Состояния сохранения/ошибки не приводят к потере введённых изменений без подтверждения.
- [ ] AI Runtime показан честно, без фиктивной «зелёной» работоспособности.
