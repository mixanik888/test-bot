import { useMemo, useState } from "react";
import "./App.css";

type View = "login" | "profile" | "org" | "users";
type Role = "admin" | "manager" | "support_agent";

type ApiError = { detail?: string };
const API_BASE = `${window.location.protocol}//${window.location.hostname}:8000`;

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
    const data = text ? (JSON.parse(text) as T | ApiError) : ({} as T);
    if (!res.ok) throw new Error((data as ApiError).detail || "API error");
    return data as T;
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

          <pre>{output || "Результат операций будет показан здесь."}</pre>
        </div>
      </main>
    </div>
  );
}

export default App;
