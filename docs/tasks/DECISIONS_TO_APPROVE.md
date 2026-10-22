# Открытые решения — владельцы и точки остановки

Этот файл **не объявляет решения принятыми**. Их канонические описания: `../04_DECISIONS_AND_CONFLICTS.md`, `../contracts/10_OPEN_DECISIONS.md`, `../contracts/13_BACKEND_READINESS_AUDIT.md`. После утверждения оформить отдельный ADR и обновить документы/контракты с согласованием.

| Вопрос | Почему влияет на разработку | Нужно до | Действие |
|---|---|---|---|
| **REST vs gRPC** для Main Backend ↔ AI | Определяет transport adapter, client generation, deadlines и auth metadata | Закрытия **AI-13/G02** | Олег + Юрий выбирают **один** вариант |
| **MCP Server owner/location** | Кто реализует инструменты, scopes, auth, safe adapters | Live tools deployment после **AI-05/06** | Совместный ADR AI/Backend/Infra |
| **Service-to-service auth** | Нельзя принимать Start/Cancel и отправлять callbacks без доверенной identity | **AI-13/G02** | Backend + AI, с Infra |
| **PostgreSQL ownership/migrations** | Где живут checkpoint tables, run registry, кто мигрирует и бэкапит | **AI-10/11** | AI + Main Backend + Infra |
| **Busy run policy** | `429 Retry-After` vs durable waiting при одном executor | **AI-11** | AI + Main Backend |
| **Final result readback/recovery** | Повтор доставки результата при потерянном callback | **AI-12/13** | Backend + AI |
| **Auto-start policy по alert** | Кто инициирует AI run, ручное/автоматическое правило | Продуктовая интеграция **AI-13** | Main Backend/product |
| **Пределы хранения events/evidence** | Payload boundaries, privacy/retention | **AI-12/14**, прод deployment | Backend + Infra |
| **Python runtime target** | На текущем bootstrap указан Python >=3.14; бинарные AI зависимости требуют проверки | При первом добавлении incompatible packages, особенно **AI-16/17** | AI repo owner, с Infra |
| **RAG MVP/P2 и embedding benchmark** | Не тащить Qdrant/модели до доказанного retrieval value | **AI-16** | AI owner |

**До решения:** можно разработать typed interfaces, deterministic fakes, mock contract tests. Нельзя выдавать выбранный по умолчанию сервер/транспорт/auth как утверждённое командное решение.

### Мини-формат ADR

```
ADR-XXX — <тема>
Status: proposed / accepted / rejected
Date: YYYY-MM-DD
Deciders: роли и участники, реально участвовавшие в решении
Context: почему нужен выбор, ограничения
Options: альтернативы + последствия
Decision: одно явное решение (только после согласования)
Consequences: схемы, тесты, миграции, rollout
Affected tasks/contracts: AI-XX, docs/contracts/... 
```
