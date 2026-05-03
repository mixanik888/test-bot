import { useMemo, useState } from "react";
import "./App.css";

type View = "login" | "profile" | "org" | "users" | "bots";
type Role = "admin" | "manager" | "support_agent";

type ApiError = { detail?: string | unknown };
// В dev Vite (5173) API на :8000; в продакшене nginx проксирует /api на тот же хост.
const API_BASE = import.meta.env.DEV
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : window.location.origin;

type BotItem = {
  id: number;
  name: string;
  status: string;
  telegram_bot_username: string | null;
  webhook_url: string;
  has_telegram: boolean;
};

function App() {
  const [view, setView] = useState<View>("login");
  const [token, setToken] = useState<string>(localStorage.getItem("portal_token") || "");
  const [output, setOutput] = useState<string>("");
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("Pass123!");
  const [inviteEmail, setInviteEmail] = useState("manager3@example.com");
  const [inviteName, setInviteName] = useState("Manager User 3");
  const [inviteRole, setInviteRole] = useState<Role>("manager");
  const [invitePassword, setInvitePassword] = useState("Temp123!");
  const [bots, setBots] = useState<BotItem[]>([]);
  const [newBotName, setNewBotName] = useState("Мой бот");
  const [tgTokenByBot, setTgTokenByBot] = useState<Record<number, string>>({});

  const isAuth = useMemo(() => Boolean(token), [token]);

  async function api<T>(path: string, method = "GET", body?: unknown): Promise<T> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    const text = await res.text();
    const parsed = text ? (JSON.parse(text) as T | ApiError) : ({} as T);
    if (!res.ok) {
      const detail = (parsed as ApiError).detail;
      const msg =
        typeof detail === "string"
          ? detail
          : detail !== undefined
            ? JSON.stringify(detail)
            : "API error";
      throw new Error(msg);
    }
    if (!text) return {} as T;
    return parsed as T;
  }

  async function login() {
    try {
      const data = await api<{ access_token: string }>("/api/v1/auth/login", "POST", { email, password });
      localStorage.setItem("portal_token", data.access_token);
      setToken(data.access_token);
      setOutput("Успех: вход выполнен.");
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  async function register() {
    try {
      const data = await api<{ access_token: string }>("/api/v1/auth/register", "POST", {
        email,
        password,
        full_name: "Admin User",
        organization_name: "My Portal Org",
      });
      localStorage.setItem("portal_token", data.access_token);
      setToken(data.access_token);
      setOutput("Успех: регистрация выполнена.");
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  async function loadProfile() {
    try {
      const data = await api("/api/v1/me");
      setOutput(JSON.stringify(data, null, 2));
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  async function loadOrg() {
    try {
      const org = await api("/api/v1/org");
      const limits = await api("/api/v1/billing/limits");
      setOutput(JSON.stringify({ org, limits }, null, 2));
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  async function loadBots() {
    try {
      const list = await api<BotItem[]>("/api/v1/bots", "GET");
      setBots(list);
      setOutput(JSON.stringify(list, null, 2));
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  async function createBot() {
    try {
      await api("/api/v1/bots", "POST", { name: newBotName });
      await loadBots();
      setOutput("Бот создан.");
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  async function connectTelegram(botId: number) {
    const tok = tgTokenByBot[botId]?.trim();
    if (!tok) {
      setOutput("Укажите токен от @BotFather.");
      return;
    }
    try {
      await api(`/api/v1/bots/${botId}/telegram`, "POST", { token: tok });
      await loadBots();
      setOutput("Telegram подключён, webhook назначен.");
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  async function disconnectTelegram(botId: number) {
    try {
      await api(`/api/v1/bots/${botId}/telegram`, "DELETE");
      await loadBots();
      setOutput("Telegram отключён.");
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  async function deleteBot(botId: number) {
    try {
      await api(`/api/v1/bots/${botId}`, "DELETE");
      await loadBots();
      setOutput("Бот удалён.");
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  async function loadBotMessages(botId: number) {
    try {
      const msgs = await api<unknown[]>(`/api/v1/bots/${botId}/messages`, "GET");
      setOutput(JSON.stringify(msgs, null, 2));
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  async function inviteUser() {
    try {
      const data = await api("/api/v1/org/users/invite", "POST", {
        email: inviteEmail,
        full_name: inviteName,
        role: inviteRole,
        temp_password: invitePassword,
      });
      setOutput(JSON.stringify(data, null, 2));
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  function logout() {
    localStorage.removeItem("portal_token");
    setToken("");
    setView("login");
    setOutput("Выход выполнен.");
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <h2>Portal</h2>
        <button onClick={() => setView("login")}>Вход</button>
        <button onClick={() => setView("profile")} disabled={!isAuth}>Профиль</button>
        <button onClick={() => setView("org")} disabled={!isAuth}>Организация</button>
        <button onClick={() => setView("users")} disabled={!isAuth}>Пользователи</button>
        <button onClick={() => setView("bots")} disabled={!isAuth}>Боты</button>
        <button onClick={logout}>Выход</button>
      </aside>
      <main className="content">
        <h1>Личный кабинет</h1>
        <div className="card">
          {view === "login" && (
            <>
              <label>Email</label>
              <input value={email} onChange={(e) => setEmail(e.target.value)} />
              <label>Пароль</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
              <div className="row">
                <button className="primary" onClick={login}>Войти</button>
                <button className="primary" onClick={register}>Быстрая регистрация</button>
              </div>
            </>
          )}

          {view === "profile" && <button className="primary" onClick={loadProfile}>Загрузить профиль</button>}
          {view === "org" && <button className="primary" onClick={loadOrg}>Загрузить организацию и лимиты</button>}

          {view === "users" && (
            <>
              <label>Email</label>
              <input value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} />
              <label>Имя</label>
              <input value={inviteName} onChange={(e) => setInviteName(e.target.value)} />
              <label>Роль</label>
              <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value as Role)}>
                <option value="manager">manager</option>
                <option value="support_agent">support_agent</option>
                <option value="admin">admin</option>
              </select>
              <label>Временный пароль</label>
              <input value={invitePassword} onChange={(e) => setInvitePassword(e.target.value)} />
              <button className="primary" onClick={inviteUser}>Пригласить</button>
            </>
          )}

          {view === "bots" && (
            <>
              <p className="hint">
                Создание и подключение токена — для ролей admin/manager. Для webhook нужен публичный{" "}
                <code>PUBLIC_BASE_URL</code> на бэкенде (локально — ngrok).
              </p>
              <div className="row">
                <label>Имя бота</label>
                <input value={newBotName} onChange={(e) => setNewBotName(e.target.value)} />
                <button className="primary" type="button" onClick={createBot}>Создать бота</button>
                <button type="button" onClick={loadBots}>Обновить список</button>
              </div>
              <ul className="bot-list">
                {bots.map((b) => (
                  <li key={b.id}>
                    <strong>{b.name}</strong> — {b.status}
                    {b.telegram_bot_username ? ` @${b.telegram_bot_username}` : ""}
                    <div className="muted small">Webhook: {b.webhook_url}</div>
                    <div className="row">
                      <input
                        placeholder="Токен BotFather"
                        type="password"
                        autoComplete="off"
                        value={tgTokenByBot[b.id] ?? ""}
                        onChange={(e) =>
                          setTgTokenByBot((prev) => ({ ...prev, [b.id]: e.target.value }))
                        }
                      />
                      <button type="button" className="primary" onClick={() => connectTelegram(b.id)}>
                        Подключить Telegram
                      </button>
                      <button type="button" onClick={() => disconnectTelegram(b.id)}>
                        Отключить
                      </button>
                      <button type="button" onClick={() => loadBotMessages(b.id)}>
                        Сообщения
                      </button>
                      <button type="button" onClick={() => deleteBot(b.id)}>
                        Удалить бота
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}

          <pre>{output || "Результат операций будет показан здесь."}</pre>
        </div>
      </main>
    </div>
  );
}

export default App;
