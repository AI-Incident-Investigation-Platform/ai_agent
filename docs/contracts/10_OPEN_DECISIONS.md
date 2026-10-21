# 10. Открытые решения перед фиксацией контрактов v1

**Важное правило:** этот файл отделяет то, что мы **знаем**, от того, что нужно **утвердить с Юрием**. Отсутствие окончательного решения не блокирует разработку DTO/моков и основной карты.

| ID | Вопрос | Предлагаемый дефолт / impact | Владелец |
|---|---|---|---|
| D-01 | **REST или gRPC между Main Backend и AI?** | REST проще для MVP, но **ещё не выбран**; если gRPC, нужны `.proto` и RPC mapping | Олег + Юрий |
| D-02 | Где физически расположен **MCP Server**? | Отдельный backend-owned MCP endpoint или AI-owned MCP layer; инструменты остаются read-only | Олег + Юрий |
| D-03 | Как запускать/планировать >1 расследования при **отсутствии RabbitMQ**? | P0: 1 active executor, 429 Retry-After при занятости; вариант persistent waiting требует решения | Олег + Юрий |
| D-04 | Кто инициирует расследование после алерта? | Backend autostart по configured policy или вручную; состав default policy утвердить | Юрий |
| D-05 | Как Backend получает **терминальный result**, если callback потерялся? | Повторный callback из AI durable outbox / GET result endpoint (добавить при утверждении) | Олег + Юрий |
| D-06 | Browser auth и refresh mechanism? | JWT + secure HttpOnly cookie/session; для WS cookie или short-lived ticket | Юрий + Расул |
| D-07 | Human-readable Incident ID? | wire `UUID`; UI display `INC-1042` потребуется отдельное поле `number/display_id` | Юрий + Расул |
| D-08 | Какие поля Integration config разрешены per provider? | Typed provider-specific schema: ES, Prometheus, Tempo, GitHub, Docker | Юрий + Даниил |
| D-09 | Сколько и как долго хранить Agent Events/Evidence? | PG metadata + bounded excerpts; сырая телеметрия остаётся в источниках | Юрий + Даниил |
| D-10 | Какие настройки Settings реально редактируемы в MVP? | AI бюджет readonly; без произвольных PATCH до утверждения | Юрий + Расул |
| D-11 | Как организовать PostgreSQL checkpoint persistence AI? | отдельная схема или БД, доступ только AI, никакой cross-service DB coupling | Олег + Юрий |
| D-12 | Будут ли Service Map, full Logs Explorer, Trace Waterfall backend-P0? | P1; при защите достаточно deep links и evidence excerpt | команда |
| D-13 | Где хранится общий `contracts/` source of truth? | git subtree/submodule или CI artifact, **без пятого runtime-сервиса** | Олег + Юрий |
| D-14 | `Review` и смена incident status: правила reopen / multiple reviews | Review привязан к конкретному run, не меняет исходный RCA; human resolve отдельно | Юрий |
| D-15 | Полный `outputSchema` для каждого MCP tool (помимо общих result и typed input)? | Обязательная отдельная итерация v0.2 до hard integration tests | Олег + Юрий |

После утверждения каждого пункта фиксировать решение в `docs/architecture/decisions/ADR-XXXX.md`, поднимать draft → approved, обновлять OpenAPI/JSON Schema/моки синхронно.

## Дополнение v0.2: новые связанные с email OTP решения

| ID | Вопрос | Рекомендация / влияние | Владелец |
|---|---|---|---|
| D-16 | Как Admin-created user получает первый пароль, приглашение, восстановление пароля? | Admin invite + одноразовая ссылка set-password или заранее оговорённый onboarding; **не смешивать с login OTP** | Юрий + Расул |
| D-17 | SMTP или email API, кто управляет доменом sender / SPF / DKIM / DMARC? | Mock Mailpit локально, реальный email provider и secrets в Infra | Юрий + Даниил |
| D-18 | OTP timeouts/limits, session refresh transport (дополнение D-06) | Baseline 6 digits/300 s/5 attempts/60 s resend/3 resends/15m max, но требуется ADR | Юрий + Олег |

**Утверждено пользователем:** OTP обязателен при каждом новом password-login, не только при первом. Нельзя оставлять старую 200-ответ выдачу JWT на `/auth/login`.
