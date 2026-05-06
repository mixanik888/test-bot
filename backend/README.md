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

## MAX (этап 3)

Для подключения MAX также нужен публичный HTTPS URL API:

```bash
export PUBLIC_BASE_URL="https://xxxx.ngrok.io"
```

Подключение MAX выполняется токеном из платформы MAX (раздел "Интеграция -> Получить токен").
Сервер выполняет `GET /me`, затем создаёт webhook-подписку `POST /subscriptions` на URL
`/api/v1/webhooks/max/{webhook_secret}`.

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
- `POST /api/v1/bots/{id}/max` — тело `{ "token": "<MAX access token>" }`, подписывает webhook через MAX API
- `DELETE /api/v1/bots/{id}/max` — отключить MAX
- `GET /api/v1/bots/{id}/messages` — последние сообщения (лог)
- `POST /api/v1/webhooks/telegram/{webhook_secret}` — вызывается Telegram (не для браузера)
- `POST /api/v1/webhooks/max/{webhook_secret}` — вызывается MAX (не для браузера)
- `GET /api/v1/bots/{id}/flow` — получить черновик схемы процесса
- `PUT /api/v1/bots/{id}/flow` — сохранить черновик схемы (только `trigger` и `action`)
- `POST /api/v1/bots/{id}/flow/publish` — создать новую версию процесса
- `GET /api/v1/bots/{id}/flow/versions` — список версий процесса

### Миграции

- `003_max.sql` — таблица `bot_max_integrations` для хранения токена и данных подключённого MAX-бота.
- `004_flows.sql` — таблицы `flow_definitions` и `flow_versions` для конструктора процессов.

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
