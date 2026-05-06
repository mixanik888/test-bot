#!/usr/bin/env bash
# Запуск backend (FastAPI/uvicorn) и frontend (Vite) в одном терминале.
# Остановка: Ctrl+C — завершаются оба процесса.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"

# Подхватить nvm в том же процессе (скрипт не всегда наследует PATH из .bashrc).
load_nvm_if_needed() {
  if [[ -n "${NODE_BIN:-}" ]]; then
    return 0
  fi
  if [[ ! -s "$HOME/.nvm/nvm.sh" ]]; then
    return 0
  fi
  # shellcheck source=/dev/null
  . "$HOME/.nvm/nvm.sh"
  local oldpwd="$PWD"
  if [[ -f "$ROOT/frontend-react/.nvmrc" ]]; then
    cd "$ROOT/frontend-react" || return 0
    nvm use 2>/dev/null || true
    cd "$oldpwd" || true
  fi
}

usage() {
  cat <<'EOF'
Использование: start-servers.sh [опции]

  --backend-only   Только API (uvicorn)
  --frontend-only  Только Vite
  --with-nginx     Перед запуском поднять/проверить nginx (systemd)
  -h, --help       Справка

Переменные окружения:
  BACKEND_PORT   Порт API (по умолчанию: 8000)
  BACKEND_HOST   Хост uvicorn (по умолчанию: 0.0.0.0)
  NODE_BIN       Полный путь к node 18+ (если в PATH старая версия)
  NGINX_SERVICE  Имя systemd-сервиса nginx (по умолчанию: nginx)
EOF
}

# Vite 5 требует Node.js 18+ (иначе SyntaxError на top-level await в vite.js).
require_node_min() {
  local min_major="$1"
  local node_bin="${NODE_BIN:-node}"
  local node_path

  if ! node_path="$(command -v "$node_bin" 2>/dev/null)"; then
    echo "Не найден Node.js: $node_bin" >&2
    exit 1
  fi

  local major
  major="$("$node_path" -p 'parseInt(process.versions.node, 10)' 2>/dev/null)" || {
    echo "Не удалось определить версию Node.js: $node_path" >&2
    exit 1
  }

  if [[ "$major" -lt "$min_major" ]]; then
    echo "Для фронтенда нужен Node.js ${min_major}+ (Vite 5). Сейчас: $($node_path -v), путь: $node_path" >&2
    echo "Установите Node 20 (nvm: см. https://github.com/nvm-sh/nvm — затем в каталоге frontend-react: nvm install && nvm use), либо NODE_BIN=/путь/к/node20" >&2
    exit 1
  fi

  export PATH="$(dirname "$node_path"):$PATH"
}

BACKEND_ONLY=false
FRONTEND_ONLY=false
WITH_NGINX=false
NGINX_SERVICE="${NGINX_SERVICE:-nginx}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-only)
      BACKEND_ONLY=true
      shift
      ;;
    --frontend-only)
      FRONTEND_ONLY=true
      shift
      ;;
    --with-nginx)
      WITH_NGINX=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Неизвестный аргумент: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "$BACKEND_ONLY" == true && "$FRONTEND_ONLY" == true ]]; then
  echo "Нельзя одновременно указывать --backend-only и --frontend-only" >&2
  exit 1
fi

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

if [[ "$BACKEND_ONLY" != true ]]; then
  load_nvm_if_needed
  require_node_min 18
fi

start_backend() {
  if [[ ! -d "$ROOT/backend/.venv" ]]; then
    echo "Ожидается виртуальное окружение: backend/.venv" >&2
    echo "Создайте его: cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
    exit 1
  fi
  # shellcheck source=/dev/null
  source "$ROOT/backend/.venv/bin/activate"
  cd "$ROOT/backend"
  exec uvicorn app.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT"
}

start_frontend() {
  if [[ ! -d "$ROOT/frontend-react/node_modules" ]]; then
    echo "Не найден frontend-react/node_modules. Выполните: cd frontend-react && npm install" >&2
    exit 1
  fi
  cd "$ROOT/frontend-react"
  exec npm run dev
}

ensure_nginx_running() {
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "Опция --with-nginx требует systemd/systemctl." >&2
    exit 1
  fi

  if systemctl is-active --quiet "$NGINX_SERVICE"; then
    echo "nginx уже запущен ($NGINX_SERVICE)."
    return 0
  fi

  echo "Запускаю nginx ($NGINX_SERVICE)..."
  if [[ "$EUID" -eq 0 ]]; then
    systemctl start "$NGINX_SERVICE"
  elif command -v sudo >/dev/null 2>&1; then
    if sudo -n systemctl start "$NGINX_SERVICE" 2>/dev/null; then
      true
    else
      echo "Нужны права для запуска nginx. Выполните: sudo systemctl start $NGINX_SERVICE" >&2
      exit 1
    fi
  else
    echo "sudo не найден. Запустите nginx вручную: systemctl start $NGINX_SERVICE" >&2
    exit 1
  fi

  if ! systemctl is-active --quiet "$NGINX_SERVICE"; then
    echo "Не удалось запустить nginx ($NGINX_SERVICE)." >&2
    exit 1
  fi
}

if [[ "$FRONTEND_ONLY" == true ]]; then
  start_frontend
fi

if [[ "$BACKEND_ONLY" == true ]]; then
  start_backend
fi

if [[ "$WITH_NGINX" == true ]]; then
  ensure_nginx_running
fi

(
  start_backend
) &
BACKEND_PID=$!

(
  start_frontend
) &
FRONTEND_PID=$!

echo "Запущены серверы:"
echo "  Backend:  http://${BACKEND_HOST/0.0.0.0/localhost}:$BACKEND_PORT  (PID $BACKEND_PID)"
echo "  Frontend: Vite dev server (см. вывод ниже, обычно http://localhost:5173) (PID $FRONTEND_PID)"
echo "Остановка: Ctrl+C"
echo "---"

wait "$BACKEND_PID" "$FRONTEND_PID"
