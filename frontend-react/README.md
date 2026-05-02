# Frontend React + TypeScript

## Запуск

Нужен **Node.js 18+** (рекомендуется 20 — см. `.nvmrc`). Системный Node 12 из Ubuntu не подходит для Vite 5.

```bash
# при использовании nvm (из корня репозитория)
cd frontend-react && nvm install && nvm use
npm install
npm run dev
```

Или оба сервера сразу: из корня репозитория `./scripts/start-servers.sh` (подхватывает `~/.nvm` при наличии).

По умолчанию Vite: `http://127.0.0.1:5173` (порт: `npm run dev -- --port 5174`). В `vite.config.ts` включён `host: true`, чтобы портал открывался **по IP/из сети**, не только с localhost.

Запросы к API идут на тот же hostname, порт **8000** (см. `App.tsx`). Если доступ извне не проходит, проверьте файрвол (`ufw`/security group) для портов **5173** и **8000**.

## Что реализовано

- Экран входа/быстрой регистрации.
- Экран профиля (`/api/v1/me`).
- Экран организации и лимитов (`/api/v1/org`, `/api/v1/billing/limits`).
- Экран приглашения пользователя (`/api/v1/org/users/invite`).

Backend API: тот же хост, что у страницы, порт **8000** (локально это `http://127.0.0.1:8000`).

## Тестовый вход

Основной тестовый пользователь:

- Email: `admin@example.com`
- Password: `Pass123!`

Если данных нет в БД, заполнить их можно скриптом:

```bash
cd backend
source .venv/bin/activate
python scripts/seed_test_data.py
```
