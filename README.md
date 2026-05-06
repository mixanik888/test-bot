# Portal MVP (test-bot)

Веб-портал с регистрацией, входом, профилем пользователя, организацией и базовым биллингом. **Этап 1 MVP**: FastAPI + SQLite, React (Vite) + TypeScript.

## Возможности

- **Backend:** JWT-авторизация, роли (`admin`, `manager`, `support_agent`), приглашение пользователей, заглушки OAuth (Google / Telegram), лимиты и план в биллинге.
- **Telegram (этап 2):** создание бота в организации, подключение токена BotFather, вебхук, приём текстовых сообщений и echo-ответ с учётом лимита сообщений по тарифу.
- **MAX (этап 3):** дополнительный канал для бота: подключение токена MAX, подписка на Webhook, приём событий и echo-ответ через MAX API.
- **Flow editor (этап 3):** упрощённый визуальный редактор процесса (`trigger` + `action`), сохранение схемы, валидация и версионирование.
- **Frontend:** экраны входа, профиля, организации, приглашений, **боты**; API по умолчанию на том же хосте, порт `8000`.

## Стек

| Часть      | Технологии                          |
| ---------- | ----------------------------------- |
| API        | Python 3, FastAPI, SQLAlchemy, SQLite |
| Клиент     | React 18, TypeScript, Vite 5        |

## Быстрый старт

Требования: **Python 3.10+**, **Node.js 18+** (для Vite 5 удобно [nvm](https://github.com/nvm-sh/nvm) и файл `frontend-react/.nvmrc`).

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# Frontend (другой терминал)
cd frontend-react
npm install
npm run dev
```

Оба сервера одной командой из корня репозитория:

```bash
./scripts/start-servers.sh
```

Подробности: [backend/README.md](backend/README.md), [frontend-react/README.md](frontend-react/README.md).

## Что добавлено в этапе 3 (MAX)

- Backend:
  - новый API-клиент `backend/app/max_api.py` (`/me`, `/subscriptions`, `/messages`);
  - новая таблица интеграции `bot_max_integrations` (миграция `backend/migrations/003_max.sql`);
  - новые endpoint'ы подключения MAX:
    - `POST /api/v1/bots/{id}/max`
    - `DELETE /api/v1/bots/{id}/max`
  - новый webhook: `POST /api/v1/webhooks/max/{webhook_secret}`;
  - расширен `BotResponse` полями `max_bot_username` и `has_max`.
- Frontend:
  - в разделе ботов добавлены поля и кнопки для подключения/отключения MAX токена.

## Структура репозитория

```
test-bot/
├── backend/           # FastAPI, модели, роутеры
├── frontend-react/    # SPA на Vite
├── scripts/           # start-servers.sh и вспомогательные скрипты
└── README.md
```

## Лицензия

Укажите лицензию при необходимости (репозиторий без `LICENSE` по умолчанию).
