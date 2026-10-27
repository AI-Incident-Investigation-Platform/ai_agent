# Валидация контрактов v0.2

- OpenAPI 3.1 YAML: **parsed**.
- Main Backend operations: **62** (ранее 60; +2 OTP).
- JSON Schema files: **11**; все проверены по Draft 2020-12.
- OTP fixtures: **4 схемно проверены** (`LoginChallenge`, `OtpVerifyRequest`, `OtpResendRequest`, `OtpResendResponse`).
- `POST /auth/login` больше не возвращает 200 `AuthTokens`; используется 202 `LoginChallenge`.
- `POST /auth/otp/verify` → 200 `AuthTokens`; `POST /auth/otp/resend` → 202 `OtpResendResponse`.
- Формальные `$ref` OpenAPI для операций существуют.

**Что не проверено:** соответствие реализации Backend, успешная доставка e-mail, интеграционные тесты Figma Frontend и AI, компиляция `proto` и все контрактные сценарии реальных сервисов. Это всё задачи разработчиков до фиксации `v1`.
