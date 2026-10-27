# Команды для контрактной отладки (кандидат REST)

Здесь показана последовательность, а не реальная авторизация: `<token>` и `<uuid>` заменить тестовыми секретами/идентификаторами. **Не использовать curl примеры для прямого доступа к prod источникам.**

```bash
# 1. Backend: список инцидентов
curl -sS 'http://localhost:8000/api/v1/incidents?status=open&limit=25' \
  -H 'Authorization: Bearer <user-token>'

# 2. Browser/User → Main Backend: start investigation
curl -sS -X POST 'http://localhost:8000/api/v1/incidents/<incident-id>/investigations' \
  -H 'Authorization: Bearer <user-token>' -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: 9dd7c0ba26414a63b1fe5db51d18b629' \
  -d '{}'

# 3. Main Backend → AI Backend: start with strict payload
curl -sS -X POST 'http://localhost:8080/internal/v1/investigations' \
  -H 'Authorization: Bearer <service-token>' -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: 9dd7c0ba26414a63b1fe5db51d18b629' \
  --data-binary '@examples/ai-start.request.json'

# 4. AI Backend → Main Backend: persisted tool event
curl -sS -X POST 'http://localhost:8000/internal/v1/ai/events' \
  -H 'Authorization: Bearer <service-token>' -H 'Content-Type: application/json' \
  --data-binary '@examples/ai-event.tool-completed.json'

# 5. Frontend: replay after sequence=12
curl -sS 'http://localhost:8000/api/v1/investigations/<run-id>/events?after_sequence=12' \
  -H 'Authorization: Bearer <user-token>'
```

REST↔gRPC пока не выбран. Эти команды — тестовые примеры **REST mapping candidate**, а не обязательство запускать именно HTTP между двумя backend-сервисами.

## Email OTP login sequence (v0.2)

```bash
# 1. Password check, response 202 includes challenge_id but NO JWT.
curl -i -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  --data-binary '@examples/auth-login.request.json'

# 2. Enter code from configured development inbox (Mailpit); replace code in fixture.
curl -i -X POST 'http://localhost:8000/api/v1/auth/otp/verify' \
  -H 'Content-Type: application/json' \
  --data-binary '@examples/auth-otp-verify.request.json'

# 3. Optional resend (only after resend_after seconds): old OTP becomes invalid.
curl -i -X POST 'http://localhost:8000/api/v1/auth/otp/resend' \
  -H 'Content-Type: application/json' \
  --data-binary '@examples/auth-otp-resend.request.json'
```

**Примеры не содержат настоящих паролей, токенов или активных OTP-кодов.**
