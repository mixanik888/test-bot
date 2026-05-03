# Деплой на bot-1c.ru (ISPmanager / `/var/www/www-root/data/www/bot-1c.ru`)

Если **нельзя** класть файлы в `/etc/nginx/vhosts-resources/bot-1c.ru/`, правьте основной конфиг сайта вручную — см. **`nginx-edit-inline.md`** (куда вставить блоки `location ^~ /api/` и опционально `location = /`).

Каталог, который отдаёт nginx/Apache как **корень сайта**, должен содержать только **собранный фронт** (`npm run build` → содержимое `dist/`). Исходники и Python-бэкенд в открытый `www` класть не нужно — только статические файлы и при желании служебные скрипты вне DocumentRoot.

## Рекомендуемая схема

| Путь | Назначение |
|------|------------|
| `/var/www/www-root/data/www/bot-1c.ru` | **Только** файлы из `frontend-react/dist/` (index.html, assets/) |
| Например `/var/www/www-root/data/www/bot-1c-api` или `/home/deploy/test-bot/backend` | Бэкенд FastAPI + `.venv` (не доступен напрямую из браузера) |

Reverse-proxy в nginx: запросы `/api/` → `http://127.0.0.1:8000`.

## 1. Один раз на сервере

```bash
# Куда класть API (пример — рядом с www)
sudo mkdir -p /var/www/www-root/data/www/bot-1c-api
sudo chown "$USER":"$USER" /var/www/www-root/data/www/bot-1c-api
```

Скопируйте проект (или только `backend/`) в `bot-1c-api`, создайте venv и зависимости:

```bash
cd /var/www/www-root/data/www/bot-1c-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Создайте файл окружения для продакшена (путь поправьте под себя):

```bash
sudo tee /etc/default/portal-api >/dev/null <<'EOF'
PUBLIC_BASE_URL=https://bot-1c.ru
EOF
```

`systemd`-юнит см. `portal-api.service` в этой папке; в нём укажите `WorkingDirectory` и `User` под вашу установку.

## 2. Собрать фронт и выложить в DocumentRoot

Из каталога репозитория на сервере (или после `git pull`):

```bash
cd /path/to/test-bot/frontend-react
npm ci
npm run build
```

Копирование в панельный путь (останется только статика):

```bash
sudo rsync -a --delete dist/ /var/www/www-root/data/www/bot-1c.ru/
sudo chown -R www-data:www-data /var/www/www-root/data/www/bot-1c.ru
```

Флаг `--delete` удаляет старые hashed-assets из прошлой сборки.

## 3. Nginx (ISPmanager: vhost с прокси на :8080)

В типичном vhost панели уже есть:

- `include /etc/nginx/vhosts-resources/bot-1c.ru/*.conf;` — **сюда** добавляются свои фрагменты;
- запросы уходят в `@fallback` → `http://127.0.0.1:8080`;
- для путей с расширениями (`.js`, `.css`, …) сначала `try_files $uri` с диска — **собранный Vite** из `dist/` в `root` отдастся, если файлы на месте.

**Обязательно API:** скопируйте содержимое `nginx-vhosts-resources-api.conf` в новый файл на сервере, например:

```bash
sudo cp /path/to/repo/deploy/bot-1c.ru/nginx-vhosts-resources-api.conf \
  /etc/nginx/vhosts-resources/bot-1c.ru/api-proxy.conf
```

Префикс `location ^~ /api/` перехватывает трафик **раньше** общего `location /` и шлёт его на **uvicorn** `127.0.0.1:8000` (запустите бэкенд и проверьте `curl -s http://127.0.0.1:8000/health`).

**Главная страница `/`:** сейчас она тоже уходит на `:8080`. Если фронт — только разложенный `dist/`, подключите опционально `nginx-vhosts-resources-root-index.conf` под тем же каталогом `vhosts-resources/bot-1c.ru/` (например `spa-root.conf`), чтобы `location = /` отдавал `index.html` с диска. Наше SPA не меняет путь в URL, поэтому глубоких маршрутов в nginx не требуется.

```bash
sudo nginx -t && sudo systemctl reload nginx
```

Альтернатива: оставить `/` на порту 8080 и настроить там тот же статический корень — тогда фрагмент `root-index` не нужен.

### Автономный пример vhost (без панели)

Файл `nginx-bot-1c.ru.conf` в этой папке — для сравнения, панель его обычно **не заменяет** основным куском, чтобы не потерять правки при регенерации.

SSL (Let's Encrypt), если ещё не сделали в панели:

```bash
sudo certbot --nginx -d bot-1c.ru -d www.bot-1c.ru
```

Telegram webhook требует **HTTPS** — после сертификата задайте:

```bash
PUBLIC_BASE_URL=https://bot-1c.ru
```

## 4. Обновление после изменений в коде

- Фронт: `npm run build` → `rsync` в `bot-1c.ru`.
- Бэкенд: `git pull` в каталоге API → `pip install -r requirements.txt` при изменении зависимостей → `sudo systemctl restart portal-api`.

## Альтернатива без второго каталога

Можно держать репозиторий целиком в `/home/deploy/test-bot`, а в `/var/www/.../bot-1c.ru` только **результат** `rsync` из `frontend-react/dist`. Бэкенд запускать из `/home/deploy/test-bot/backend` — так часто проще обновлять через `git pull`.
