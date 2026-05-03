# Backend (MVP: этапы 1–2)

## Запуск

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Telegram (этап 2)

Перед подключением бота задайте публичный URL API (для `setWebhook`):

```bash
export PUBLIC_BASE_URL="https://xxxx.ngrok.io"
```

## Основные endpoint'ы

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/oauth/google` (заглушка)
- `POST /api/v1/auth/oauth/telegram` (заглушка)
- `GET /api/v1/me`
- `GET /api/v1/org`
- `POST /api/v1/org/users/invite`
- `PATCH /api/v1/org/users/{user_id}/role`
- `GET /api/v1/billing/plan`
- `GET /api/v1/billing/limits`

### Боты и Telegram

- `GET /api/v1/bots` — список ботов организации
- `POST /api/v1/bots` — создать бота (admin/manager)
- `GET /api/v1/bots/{id}`
- `DELETE /api/v1/bots/{id}`
- `POST /api/v1/bots/{id}/telegram` — тело `{ "token": "<BotFather>" }`, выставляет webhook
- `DELETE /api/v1/bots/{id}/telegram` — отключить Telegram
- `GET /api/v1/bots/{id}/messages` — последние сообщения (лог)
- `POST /api/v1/webhooks/telegram/{webhook_secret}` — вызывается Telegram (не для браузера)

## Ограничения текущей версии

- SQLite как локальная БД.
- OAuth не реализован, возвращает `501`.
- Создание таблиц пока через SQLAlchemy `create_all`.

## Тестовые данные для входа

Заполнение/обновление тестовых данных:

```bash
cd backend
source .venv/bin/activate
python scripts/seed_test_data.py
```

Тестовые учётные записи:

- `admin@example.com` / `Pass123!` (роль `admin`)
- `manager@example.com` / `Manager123!` (роль `manager`)
- `support@example.com` / `Support123!` (роль `support_agent`)
