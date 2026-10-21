# 12. Email OTP при КАЖДОМ password-login — контракт v0.2

**Статус:** функционально согласовано пользователем; численные лимиты и реализация доставки — предлагаемый безопасный baseline до совместного code review Юрия и Расула. Не путать с TOTP-приложением: здесь **email OTP**.

## 1. Порядок входа (обязателен)

```text
Browser                       Main Backend                 Mail provider
   | POST /api/v1/auth/login         |                            |
   | {email,password} -------------->| verify password            |
   |                                 | create challenge           |
   |                                 | email OTP ---------------->|
   |<----------------------- 202 {challenge_id, masked_email,
   |                             expires_in, resend_after}      |
   |                                 |                            |
   | user receives 6 digits          |                            |
   | POST /api/v1/auth/otp/verify     |                            |
   | {challenge_id,code} ----------->| atomic verify & consume    |
   |<------------------------- 200 AuthTokens / session        |
```

* **Сразу после `/auth/login` Main Backend НЕ отдаёт access/refresh tokens.** Он только проверяет пароль, создаёт одноразовый `challenge_id`, ставит письмо на отправку.
* Только после успешного `/auth/otp/verify` выдаются JWT/sessions; новые действия с API до verify возвращают 401.
* При **каждом новом входе по email+паролю** повторяется OTP, даже если пользователь уже ранее входил. `refresh` внутри существующей валидной сессии **не** требует повторной почтовой проверки. Logout/revocation уничтожают refresh-сессию.
* Frontend для входа/OTP пока отсутствует в девяти макетах Figma B. Нужно добавить отдельные экраны `Login` и `Verify email`, а также состояния resend/expired/rate-limited.

## 2. Точные операции

### `POST /api/v1/auth/login` → `202 LoginChallenge`

`Content-Type: application/json`, без bearer.

Request (`LoginRequest`):

```json
{"email":"developer@example.com","password":"********"}
```

`202 Accepted`:

```json
{"challenge_id":"ch_A8x7K4p9M2c5D6eF8gH1jL0qR3tU7vW2","delivery_status":"queued","masked_email":"d***@example.com","expires_in":300,"resend_after":60}
```

`delivery_status: queued` означает **принято на отправку**, не гарантию фактической доставки. Ошибка email/password: единый 401 `invalid_credentials` (не раскрывать существует ли email). Ошибка сервиса отправки: 503 `otp_delivery_unavailable`; избыточные запросы: 429 `otp_rate_limited`.

### `POST /api/v1/auth/otp/verify` → `200 AuthTokens`

```json
{"challenge_id":"ch_A8x7K4p9M2c5D6eF8gH1jL0qR3tU7vW2","code":"004271"}
```

Код — **строка из ровно шести ASCII-цифр**; ведущие нули значимы. Ответ 200 использует существующий объект `AuthTokens` (`access_token`, `refresh_token`, `token_type`, `expires_in`). Способ доставки refresh-токена браузеру (JSON vs secure HttpOnly cookie) остаётся ADR D-06; реализация с cookie должна соответствующим образом изменить OpenAPI, CSRF и клиентский код.

Ошибки: 401 `otp_invalid` (неправильный код/челлендж), 410 `otp_expired` (просроченный/использованный), 429 `otp_rate_limited` с `Retry-After` (исчерпаны попытки), 422 `validation_error` (невалидная форма). При успешном подтверждении челлендж атомарно становится `consumed`, повторное использование невозможно.

### `POST /api/v1/auth/otp/resend` → `202 OtpResendResponse`

```json
{"challenge_id":"ch_A8x7K4p9M2c5D6eF8gH1jL0qR3tU7vW2"}
```

Ответ:

```json
{"challenge_id":"ch_A8x7K4p9M2c5D6eF8gH1jL0qR3tU7vW2","delivery_status":"queued","expires_in":300,"resend_after":60}
```

Resend перевыпускает код для существующего password-verified challenge, **предыдущий код аннулируется**. Нельзя отправлять новый OTP, не прошедший первоначальную проверку пароля. Ошибки 410, 429, 422.

## 3. Предлагаемые ограничения (baseline до утверждения)

| Защита | Значение | Где реализовать |
|---|---|---|
| Код | 6 цифр, криптографический CSPRNG | Backend |
| TTL одного кода | 5 минут | Backend, часы сервера |
| Число ошибочных проверок | максимум 5 на challenge | Атомарно в DB |
| Пауза между resend | минимум 60 секунд | Backend, `Retry-After` |
| Повторные отправки | максимум 3 на challenge | Backend |
| Максимальная длительность challenge | 15 минут независимо от resend | Backend |
| Параллельные челленджи | новый password-login делает прежний активный challenge пользователя невалидным | DB |
| Лимит входов | IP + account/email, конфигурируемые квоты и временная блокировка | Backend/cache |
| OTP после успеха | одноразовость, транзакционный consume | DB |
| Rate-limit response | `429` + `Retry-After` | Backend |

## 4. Данные Backend / хранение

Предлагаемая таблица `auth_otp_challenges`:

- `id` — криптографически случайный непрогнозируемый идентификатор `ch_...`; внешний `challenge_id` не JWT и не session-id.
- `user_id`, `purpose=login`, `created_at`, `expires_at`, `absolute_expires_at`, `resend_not_before`.
- `otp_digest` — HMAC-SHA-256 с серверным секретом (pepper), nonce/challenge binding; **НЕ SHA256(code) без секрета**: 6 цифр легко перебрать офлайн.
- `attempts`, `resend_count`, `consumed_at`, `revoked_at`.
- Audit login attempts and timestamps **без** сохранения OTP, plaintext password или токенов.

Хранить состояние в PostgreSQL или согласованном серверном transactional store; DragonflyDB допустим для дополнительных rate-limit buckets, но не для единственного состояния, если нужна устойчивость после рестарта. HMAC pepper — секрет конфигурации, не в git/logs, план ротации обязателен.

При `verify` сервер **одной транзакцией** проверяет, что challenge активен, что TTL не истёк, что лимит попыток не исчерпан, увеличивает счётчик неверных попыток / атомарно помечает успех, затем создаёт сессию. При конкурентных verify/resend предусмотреть блокировку строки/compare-and-swap. При resend новый digest инвалидирует старый до выдачи ответа.

SMTP / provider sender: конфигурация через секреты Infra; SPF/DKIM/DMARC и доставляемость почты настраиваются владельцем домена. Транспорт писем **не требует RabbitMQ между Backend и AI**; возможен внутренний outbox+worker для надёжной доставки, но это архитектурный выбор Юрия. Не логировать код и не выдавать его в production API. Для локальной разработки допустим Mailpit/mailhog или mock email sender **без отправки реальных писем**.

## 5. Правила Frontend

1. `Login` форма email, password → POST login; состояние `submitting` / error. Не сохранять пароль после ответа.
2. После 202 переход на `Verify email`: маскированный email, 6-разрядное поле, индикатор срока действия, кнопка повторной отправки с таймером `resend_after`.
3. Verify success → уже авторизованное приложение и загрузка `GET /users/me`.
4. Неверный код: аккуратная ошибка, **не сбрасывать challenge_id**; истёк: CTA `Sign in again`; 429: cooldown, `Retry-After`.
5. Кнопка resend остаётся disabled до окончания интервала; после resend заменить отсчёт и очистить код.
6. Обновление страницы на шаге verify: восстановить только `challenge_id` в краткоживущем state / session storage (потребуется security review), либо повторить login. Не сохранять пароль и OTP.
7. Viewer, Developer, Admin входят одинаково; RBAC начинает работать только после успешной OTP-проверки.

## 6. Контрактные/интеграционные проверки

- Неправильный пароль: **401**, не 202, токенов и активной OTP-сессии нет; детали не раскрывают наличие email.
- Верный пароль: **202**, в ответе нет токенов; письмо ставится на доставку, challenge привязан к user.
- Неправильный OTP: **401**, попытка засчитана; после 5 — 429 до нового login/cooldown согласно policy.
- Правильный OTP: **200** + токены; второй такой же запрос отклоняется.
- TTL: после 5 минут код больше не работает, даже если письмо доставилось позже.
- Resend: старый код не работает, новый работает, resend throttling 429.
- Race: два одновременных verify одного challenge не создают две сессии.
- Невозможно вызвать другие пользовательские API, включая WebSocket, с `challenge_id` вместо JWT.
- Ни код, ни пароль, ни raw token не появляются в логах, трассировках, errors или analytics.
- Refresh-токен **не создаётся** до OTP, токены после OTP подчиняются policy revocation/rotation.

## 7. Что потребует отдельного решения

- **D-06:** JSON или HttpOnly cookie для refresh, SameSite/CSRF, WS auth.
- **D-16:** пользовательский onboarding — как Admin создаёт пароль / приглашает пользователя и подтверждает email. В v0.2 пока нет отдельного registration/invite/password-reset API.
- **D-17:** SMTP/Mail API provider и его конфигурация, `From` domain, доставляемость, серверный outbox/worker.
- **D-18:** конкретные численные лимиты OTP, политика lockout и TTL сессий (предложены в таблице, ещё не подтверждены).
