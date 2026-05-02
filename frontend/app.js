const API_BASE = "http://127.0.0.1:8000";
const viewEl = document.getElementById("view");
const titleEl = document.getElementById("title");
const logoutBtn = document.getElementById("logoutBtn");

function getToken() {
  return localStorage.getItem("portal_token");
}

function setToken(token) {
  localStorage.setItem("portal_token", token);
}

function clearToken() {
  localStorage.removeItem("portal_token");
}

async function api(path, method = "GET", body = null) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });

  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  if (!res.ok) {
    throw new Error(data.detail || "API error");
  }
  return data;
}

function renderLogin() {
  titleEl.textContent = "Вход";
  viewEl.innerHTML = `
    <div class="card">
      <h3>Логин</h3>
      <label>Email</label>
      <input id="loginEmail" type="email" value="admin@example.com">
      <label>Пароль</label>
      <input id="loginPassword" type="password" value="Pass123!">
      <button id="loginSubmit" class="primary">Войти</button>
      <p class="muted">Если пользователя нет, нажмите "Быстрая регистрация".</p>
      <button id="registerSubmit" class="primary">Быстрая регистрация</button>
      <pre id="loginResult"></pre>
    </div>
  `;

  document.getElementById("loginSubmit").onclick = async () => {
    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;
    const out = document.getElementById("loginResult");
    try {
      const data = await api("/api/v1/auth/login", "POST", { email, password });
      setToken(data.access_token);
      out.textContent = "Успех: токен сохранен";
    } catch (e) {
      out.textContent = `Ошибка: ${e.message}`;
    }
  };

  document.getElementById("registerSubmit").onclick = async () => {
    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;
    const out = document.getElementById("loginResult");
    try {
      const data = await api("/api/v1/auth/register", "POST", {
        email,
        password,
        full_name: "Admin User",
        organization_name: "My Portal Org",
      });
      setToken(data.access_token);
      out.textContent = "Регистрация успешна: токен сохранен";
    } catch (e) {
      out.textContent = `Ошибка: ${e.message}`;
    }
  };
}

async function renderProfile() {
  titleEl.textContent = "Профиль";
  viewEl.innerHTML = `<div class="card"><pre>Загрузка...</pre></div>`;
  try {
    const me = await api("/api/v1/me");
    viewEl.innerHTML = `
      <div class="card">
        <h3>Профиль</h3>
        <pre>${JSON.stringify(me, null, 2)}</pre>
      </div>
    `;
  } catch (e) {
    viewEl.innerHTML = `<div class="card"><pre>Ошибка: ${e.message}</pre></div>`;
  }
}

async function renderOrg() {
  titleEl.textContent = "Организация и лимиты";
  viewEl.innerHTML = `<div class="card"><pre>Загрузка...</pre></div>`;
  try {
    const org = await api("/api/v1/org");
    const limits = await api("/api/v1/billing/limits");
    viewEl.innerHTML = `
      <div class="card">
        <h3>Организация</h3>
        <pre>${JSON.stringify(org, null, 2)}</pre>
        <h3>Лимиты</h3>
        <pre>${JSON.stringify(limits, null, 2)}</pre>
      </div>
    `;
  } catch (e) {
    viewEl.innerHTML = `<div class="card"><pre>Ошибка: ${e.message}</pre></div>`;
  }
}

function renderUsers() {
  titleEl.textContent = "Пользователи";
  viewEl.innerHTML = `
    <div class="card">
      <h3>Пригласить пользователя</h3>
      <label>Email</label>
      <input id="inviteEmail" type="email" value="manager2@example.com">
      <label>Имя</label>
      <input id="inviteName" type="text" value="Manager User 2">
      <label>Роль</label>
      <select id="inviteRole">
        <option value="manager">manager</option>
        <option value="support_agent">support_agent</option>
        <option value="admin">admin</option>
      </select>
      <label>Временный пароль</label>
      <input id="invitePassword" type="text" value="Temp123!">
      <button id="inviteSubmit" class="primary">Пригласить</button>
      <pre id="inviteResult"></pre>
    </div>
  `;

  document.getElementById("inviteSubmit").onclick = async () => {
    const email = document.getElementById("inviteEmail").value;
    const full_name = document.getElementById("inviteName").value;
    const role = document.getElementById("inviteRole").value;
    const temp_password = document.getElementById("invitePassword").value;
    const out = document.getElementById("inviteResult");
    try {
      const data = await api("/api/v1/org/users/invite", "POST", {
        email,
        full_name,
        role,
        temp_password,
      });
      out.textContent = JSON.stringify(data, null, 2);
    } catch (e) {
      out.textContent = `Ошибка: ${e.message}`;
    }
  };
}

function show(view) {
  if (view === "login") {
    renderLogin();
  } else if (view === "profile") {
    renderProfile();
  } else if (view === "org") {
    renderOrg();
  } else if (view === "users") {
    renderUsers();
  }
}

document.querySelectorAll("[data-view]").forEach((btn) => {
  btn.addEventListener("click", () => show(btn.dataset.view));
});

logoutBtn.addEventListener("click", () => {
  clearToken();
  show("login");
});

show("login");
