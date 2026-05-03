#!/usr/bin/env bash
# Сборка фронта и выкладка в DocumentRoot ISPmanager.
# Запуск из корня репозитория: ./deploy/bot-1c.ru/sync-frontend-to-www.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEST="${DEST:-/var/www/www-root/data/www/bot-1c.ru}"

cd "$ROOT/frontend-react"
npm run build

if [[ ! -d "$DEST" ]]; then
  echo "Каталог назначения не найден: $DEST" >&2
  echo "Создайте его или задайте DEST=/path/to/site" >&2
  exit 1
fi

sudo rsync -a --delete dist/ "$DEST/"
sudo chown -R www-data:www-data "$DEST"
echo "Готово: статика в $DEST"
