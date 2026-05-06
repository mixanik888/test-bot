import { useMemo, useRef, useState, type MouseEvent } from "react";
import "./App.css";

type View = "login" | "profile" | "org" | "users" | "bots" | "flow";
type Role = "admin" | "manager" | "support_agent";

type ApiError = { detail?: string | unknown };
// В dev Vite (5173) API на :8000; в продакшене nginx проксирует /api на тот же хост.
const API_BASE = import.meta.env.DEV
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : window.location.origin;
const FLOW_GRID_STEP = 20;

type BotItem = {
  id: number;
  name: string;
  status: string;
  telegram_bot_username: string | null;
  max_bot_username: string | null;
  webhook_url: string;
  has_telegram: boolean;
  has_max: boolean;
};

type FlowBlockType = "trigger" | "action";

type FlowTriggerPath = {
  id: string;
  name: string;
  regex: string;
};

type FlowBlock = {
  id: string;
  type: FlowBlockType;
  label: string;
  x: number;
  y: number;
  trigger_paths?: FlowTriggerPath[] | null;
  condition_regex?: string | null;
  fallback_action_value?: string | null;
  action_type?: "return_string" | null;
  action_value?: string | null;
};

type FlowEdge = {
  from_block_id: string;
  to_block_id: string;
  when?: string;
};

type FlowSchemaResponse = {
  bot_id: number;
  blocks: FlowBlock[];
  edges: FlowEdge[];
  is_valid: boolean;
  errors: string[];
};

type FlowVersion = {
  id: number;
  version: number;
  blocks: FlowBlock[];
  edges: FlowEdge[];
  created_at: string | null;
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
  const [maxTokenByBot, setMaxTokenByBot] = useState<Record<number, string>>({});
  const [selectedFlowBotId, setSelectedFlowBotId] = useState<number | null>(null);
  const [flowBlocks, setFlowBlocks] = useState<FlowBlock[]>([]);
  const [flowEdges, setFlowEdges] = useState<FlowEdge[]>([]);
  const [flowVersions, setFlowVersions] = useState<FlowVersion[]>([]);
  const [selectedFlowBlockId, setSelectedFlowBlockId] = useState<string | null>(null);
  const [connectFromBlockId, setConnectFromBlockId] = useState<string | null>(null);
  const [draggingBlockId, setDraggingBlockId] = useState<string | null>(null);
  const [triggerTestTextByPathId, setTriggerTestTextByPathId] = useState<Record<string, string>>({});
  const [triggerConnectPathByBlockId, setTriggerConnectPathByBlockId] = useState<Record<string, string>>({});
  const flowCanvasRef = useRef<HTMLDivElement | null>(null);
  const dragPointerOffsetRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

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

  async function openFlowEditor() {
    try {
      const list = await api<BotItem[]>("/api/v1/bots", "GET");
      setBots(list);
      const initialBotId = list[0]?.id ?? null;
      setSelectedFlowBotId(initialBotId);
      if (!initialBotId) {
        setFlowBlocks([]);
        setFlowVersions([]);
        setOutput("Сначала создайте бота.");
        return;
      }
      await loadFlowByBot(initialBotId);
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  async function loadFlowByBot(botId: number) {
    try {
      const flow = await api<FlowSchemaResponse>(`/api/v1/bots/${botId}/flow`, "GET");
      const versions = await api<FlowVersion[]>(`/api/v1/bots/${botId}/flow/versions`, "GET");
      setFlowBlocks(flow.blocks);
      setFlowEdges(flow.edges);
      setSelectedFlowBlockId(flow.blocks[0]?.id ?? null);
      setFlowVersions(versions);
      setOutput(
        flow.is_valid
          ? "Схема валидна."
          : `Ошибки валидации: ${flow.errors.join("; ")}`,
      );
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  function createBlock(type: FlowBlockType): FlowBlock {
    return {
      id: `${type}_${Date.now()}_${Math.random().toString(16).slice(2, 6)}`,
      type,
      label: type === "trigger" ? "Триггер: входящее сообщение" : "Действие: ответ",
      x: type === "trigger" ? 80 : 320,
      y: 80 + flowBlocks.length * 120,
      trigger_paths:
        type === "trigger"
          ? [{ id: `path_${Date.now()}`, name: "Путь 1", regex: ".*" }]
          : null,
      condition_regex: null,
      fallback_action_value: type === "trigger" ? "Не понял запрос, уточните, пожалуйста." : null,
      action_type: type === "action" ? "return_string" : null,
      action_value: type === "action" ? "Ответ по умолчанию" : null,
    };
  }

  function addFlowBlock(type: FlowBlockType) {
    if (type === "trigger" && flowBlocks.some((block) => block.type === "trigger")) {
      setOutput("В схеме может быть только один блок trigger.");
      return;
    }
    setFlowBlocks((prev) => [...prev, createBlock(type)]);
  }

  function updateFlowBlockLabel(id: string, label: string) {
    setFlowBlocks((prev) => prev.map((block) => (block.id === id ? { ...block, label } : block)));
  }

  function addTriggerPath(blockId: string) {
    setFlowBlocks((prev) =>
      prev.map((block) => {
        if (block.id !== blockId || block.type !== "trigger") return block;
        const nextPath: FlowTriggerPath = {
          id: `path_${Date.now()}_${Math.random().toString(16).slice(2, 6)}`,
          name: `Путь ${(block.trigger_paths?.length ?? 0) + 1}`,
          regex: ".*",
        };
        return { ...block, trigger_paths: [...(block.trigger_paths ?? []), nextPath] };
      }),
    );
  }

  function removeTriggerPath(blockId: string, pathId: string) {
    setFlowBlocks((prev) =>
      prev.map((block) => {
        if (block.id !== blockId || block.type !== "trigger") return block;
        return { ...block, trigger_paths: (block.trigger_paths ?? []).filter((path) => path.id !== pathId) };
      }),
    );
    setFlowEdges((prev) => prev.filter((edge) => !(edge.from_block_id === blockId && edge.when === pathId)));
  }

  function updateTriggerPath(blockId: string, pathId: string, patch: Partial<FlowTriggerPath>) {
    setFlowBlocks((prev) =>
      prev.map((block) => {
        if (block.id !== blockId || block.type !== "trigger") return block;
        return {
          ...block,
          trigger_paths: (block.trigger_paths ?? []).map((path) =>
            path.id === pathId ? { ...path, ...patch } : path,
          ),
        };
      }),
    );
  }

  function updateFlowBlockFallbackValue(id: string, fallbackActionValue: string) {
    setFlowBlocks((prev) =>
      prev.map((block) =>
        block.id === id
          ? {
              ...block,
              fallback_action_value:
                block.type === "trigger" ? fallbackActionValue : block.fallback_action_value,
            }
          : block,
      ),
    );
  }

  function updateTriggerTestText(pathId: string, testText: string) {
    setTriggerTestTextByPathId((prev) => ({ ...prev, [pathId]: testText }));
  }

  function getTriggerPathRegexMatch(path: FlowTriggerPath): boolean | null {
    const rawPattern = (path.regex ?? "").trim();
    let pattern = rawPattern;
    let flags = "";
    const inlineFlagsMatch = rawPattern.match(/^\(\?([a-zA-Z]+)\)/);
    if (inlineFlagsMatch) {
      const supportedFlags = inlineFlagsMatch[1]
        .toLowerCase()
        .split("")
        .filter((flag) => ["i", "m", "s", "u"].includes(flag))
        .filter((flag, idx, arr) => arr.indexOf(flag) === idx)
        .join("");
      pattern = rawPattern.slice(inlineFlagsMatch[0].length);
      flags = supportedFlags;
    }
    const slashRegexMatch = rawPattern.match(/^\/(.+)\/([a-z]*)$/i);
    if (slashRegexMatch) {
      pattern = slashRegexMatch[1];
      flags = slashRegexMatch[2];
    }
    if (!pattern) return null;
    try {
      const matcher = new RegExp(pattern, flags);
      return matcher.test(triggerTestTextByPathId[path.id] ?? "");
    } catch {
      return null;
    }
  }

  function updateFlowActionType(id: string, actionType: "return_string") {
    setFlowBlocks((prev) =>
      prev.map((block) => (block.id === id ? { ...block, action_type: actionType } : block)),
    );
  }

  function updateFlowActionValue(id: string, actionValue: string) {
    setFlowBlocks((prev) =>
      prev.map((block) => (block.id === id ? { ...block, action_value: actionValue } : block)),
    );
  }

  function removeFlowBlock(id: string) {
    setFlowBlocks((prev) => prev.filter((block) => block.id !== id));
    setFlowEdges((prev) => prev.filter((edge) => edge.from_block_id !== id && edge.to_block_id !== id));
  }

  function moveFlowBlock(id: string, axis: "x" | "y", delta: number) {
    setFlowBlocks((prev) =>
      prev.map((block) =>
        block.id === id ? { ...block, [axis]: Math.max(0, block[axis] + delta) } : block,
      ),
    );
  }

  function addEdgeByIds(fromBlockId: string, toBlockId: string) {
    if (fromBlockId === toBlockId) {
      setOutput("Нельзя связать блок сам с собой.");
      return;
    }
    const exists = flowEdges.some(
      (edge) => edge.from_block_id === fromBlockId && edge.to_block_id === toBlockId,
    );
    if (exists) {
      setOutput("Такая связь уже существует.");
      return;
    }
    const sourceBlock = flowBlocks.find((block) => block.id === fromBlockId);
    let branch = "always";
    if (sourceBlock?.type === "trigger") {
      const selectedPathId = triggerConnectPathByBlockId[fromBlockId];
      branch = selectedPathId || "fallback";
    }
    setFlowEdges((prev) => [...prev, { from_block_id: fromBlockId, to_block_id: toBlockId, when: branch }]);
  }

  function startNodeConnect(blockId: string) {
    if (!connectFromBlockId) {
      setConnectFromBlockId(blockId);
      setOutput("Выберите второй блок для создания связи.");
      return;
    }
    addEdgeByIds(connectFromBlockId, blockId);
    setConnectFromBlockId(null);
  }

  function startPathConnect(triggerBlockId: string, pathId: string) {
    setTriggerConnectPathByBlockId((prev) => ({ ...prev, [triggerBlockId]: pathId }));
    setConnectFromBlockId(triggerBlockId);
    setOutput(`Выбран путь '${pathId}'. Теперь кликните по блоку action для связи.`);
  }

  function getCanvasPoint(clientX: number, clientY: number): { x: number; y: number } | null {
    const canvas = flowCanvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    return {
      x: Math.max(0, Math.round(clientX - rect.left + canvas.scrollLeft)),
      y: Math.max(0, Math.round(clientY - rect.top + canvas.scrollTop)),
    };
  }

  function snapToGrid(value: number): number {
    return Math.max(0, Math.round(value / FLOW_GRID_STEP) * FLOW_GRID_STEP);
  }

  function handleCanvasDoubleClick(event: MouseEvent<HTMLDivElement>) {
    const point = getCanvasPoint(event.clientX, event.clientY);
    if (!point) return;
    const type: FlowBlockType = event.shiftKey ? "trigger" : "action";
    if (type === "trigger" && flowBlocks.some((block) => block.type === "trigger")) {
      setOutput("Trigger уже существует. Двойной клик добавляет action (Shift+двойной клик — trigger).");
      return;
    }
    const block = createBlock(type);
    setFlowBlocks((prev) => [...prev, { ...block, x: snapToGrid(point.x), y: snapToGrid(point.y) }]);
  }

  function handleNodeMouseDown(event: MouseEvent<HTMLDivElement>, block: FlowBlock) {
    event.preventDefault();
    event.stopPropagation();
    const point = getCanvasPoint(event.clientX, event.clientY);
    if (!point) return;
    dragPointerOffsetRef.current = { x: point.x - block.x, y: point.y - block.y };
    setDraggingBlockId(block.id);
  }

  function handleCanvasMouseMove(event: MouseEvent<HTMLDivElement>) {
    if (!draggingBlockId) return;
    const point = getCanvasPoint(event.clientX, event.clientY);
    if (!point) return;
    const nextX = point.x - dragPointerOffsetRef.current.x;
    const nextY = point.y - dragPointerOffsetRef.current.y;
    setFlowBlocks((prev) =>
      prev.map((block) =>
        block.id === draggingBlockId
          ? { ...block, x: snapToGrid(nextX), y: snapToGrid(nextY) }
          : block,
      ),
    );
  }

  function stopDragging() {
    if (!draggingBlockId) return;
    setDraggingBlockId(null);
  }

  function removeEdgeByIds(fromBlockId: string, toBlockId: string) {
    setFlowEdges((prev) =>
      prev.filter((edge) => !(edge.from_block_id === fromBlockId && edge.to_block_id === toBlockId)),
    );
  }

  function getFlowBlockById(blockId: string): FlowBlock | undefined {
    return flowBlocks.find((block) => block.id === blockId);
  }

  function getEdgeLabel(edge: FlowEdge): string {
    const sourceBlock = getFlowBlockById(edge.from_block_id);
    if (!sourceBlock || sourceBlock.type !== "trigger") return edge.when ?? "always";
    if ((edge.when ?? "") === "fallback") return "fallback";
    const path = (sourceBlock.trigger_paths ?? []).find((item) => item.id === edge.when);
    return path ? `path:${path.name}` : edge.when ?? "always";
  }

  const selectedFlowBlock = selectedFlowBlockId ? getFlowBlockById(selectedFlowBlockId) : undefined;

  async function saveFlow() {
    if (!selectedFlowBotId) {
      setOutput("Выберите бота для схемы.");
      return;
    }
    try {
      const result = await api<FlowSchemaResponse>(`/api/v1/bots/${selectedFlowBotId}/flow`, "PUT", {
        blocks: flowBlocks,
        edges: flowEdges,
      });
      setFlowEdges(result.edges);
      setOutput(
        result.is_valid
          ? "Схема сохранена и валидна."
          : `Схема сохранена, но есть ошибки: ${result.errors.join("; ")}`,
      );
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  async function publishFlow() {
    if (!selectedFlowBotId) {
      setOutput("Выберите бота для публикации.");
      return;
    }
    try {
      const version = await api<FlowVersion>(`/api/v1/bots/${selectedFlowBotId}/flow/publish`, "POST");
      const versions = await api<FlowVersion[]>(`/api/v1/bots/${selectedFlowBotId}/flow/versions`, "GET");
      setFlowVersions(versions);
      setOutput(`Версия процесса v${version.version} опубликована.`);
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

  async function connectMax(botId: number) {
    const tok = maxTokenByBot[botId]?.trim();
    if (!tok) {
      setOutput("Укажите токен MAX.");
      return;
    }
    try {
      await api(`/api/v1/bots/${botId}/max`, "POST", { token: tok });
      await loadBots();
      setOutput("MAX подключён, webhook назначен.");
    } catch (e) {
      setOutput(`Ошибка: ${(e as Error).message}`);
    }
  }

  async function disconnectMax(botId: number) {
    try {
      await api(`/api/v1/bots/${botId}/max`, "DELETE");
      await loadBots();
      setOutput("MAX отключён.");
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
        <button
          onClick={() => {
            setView("flow");
            void openFlowEditor();
          }}
          disabled={!isAuth}
        >
          Процессы
        </button>
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
                    {b.max_bot_username ? ` MAX:${b.max_bot_username}` : ""}
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
                        Отключить Telegram
                      </button>
                    </div>
                    <div className="row">
                      <input
                        placeholder="Токен MAX"
                        type="password"
                        autoComplete="off"
                        value={maxTokenByBot[b.id] ?? ""}
                        onChange={(e) =>
                          setMaxTokenByBot((prev) => ({ ...prev, [b.id]: e.target.value }))
                        }
                      />
                      <button type="button" className="primary" onClick={() => connectMax(b.id)}>
                        Подключить MAX
                      </button>
                      <button type="button" onClick={() => disconnectMax(b.id)}>
                        Отключить MAX
                      </button>
                    </div>
                    <div className="row">
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

          {view === "flow" && (
            <>
              <p className="hint">
                MVP редактора процесса: доступно только 2 блока — <code>trigger</code> и <code>action</code>.
              </p>
              <div className="row">
                <label>Бот</label>
                <select
                  value={selectedFlowBotId ?? ""}
                  onChange={(e) => {
                    const nextId = Number(e.target.value);
                    setSelectedFlowBotId(nextId);
                    void loadFlowByBot(nextId);
                  }}
                >
                  {bots.map((bot) => (
                    <option key={bot.id} value={bot.id}>
                      {bot.name} (#{bot.id})
                    </option>
                  ))}
                </select>
                <button type="button" onClick={() => addFlowBlock("trigger")}>
                  Добавить trigger
                </button>
                <button type="button" onClick={() => addFlowBlock("action")}>
                  Добавить action
                </button>
                <button className="primary" type="button" onClick={saveFlow}>
                  Сохранить схему
                </button>
                <button className="primary" type="button" onClick={publishFlow}>
                  Опубликовать версию
                </button>
              </div>
              {selectedFlowBlock && (
                <div className="flow-inspector">
                  <div className="flow-inspector-title">
                    Редактирование: {selectedFlowBlock.type} ({selectedFlowBlock.id})
                  </div>
                  <div className="row">
                    <input
                      value={selectedFlowBlock.label}
                      onChange={(e) => updateFlowBlockLabel(selectedFlowBlock.id, e.target.value)}
                    />
                    <button type="button" onClick={() => moveFlowBlock(selectedFlowBlock.id, "x", -FLOW_GRID_STEP)}>
                      ←
                    </button>
                    <button type="button" onClick={() => moveFlowBlock(selectedFlowBlock.id, "y", -FLOW_GRID_STEP)}>
                      ↑
                    </button>
                    <button type="button" onClick={() => moveFlowBlock(selectedFlowBlock.id, "y", FLOW_GRID_STEP)}>
                      ↓
                    </button>
                    <button type="button" onClick={() => moveFlowBlock(selectedFlowBlock.id, "x", FLOW_GRID_STEP)}>
                      →
                    </button>
                    <button type="button" onClick={() => removeFlowBlock(selectedFlowBlock.id)}>
                      Удалить блок
                    </button>
                  </div>
                  <div className="muted small">
                    Позиция: x={selectedFlowBlock.x}, y={selectedFlowBlock.y}
                  </div>

                  {selectedFlowBlock.type === "trigger" && (
                    <>
                      <div className="row">
                        <button type="button" onClick={() => addTriggerPath(selectedFlowBlock.id)}>
                          Добавить путь
                        </button>
                        <select
                          value={triggerConnectPathByBlockId[selectedFlowBlock.id] ?? "fallback"}
                          onChange={(e) =>
                            setTriggerConnectPathByBlockId((prev) => ({
                              ...prev,
                              [selectedFlowBlock.id]: e.target.value,
                            }))
                          }
                        >
                          {(selectedFlowBlock.trigger_paths ?? []).map((path) => (
                            <option key={path.id} value={path.id}>
                              {path.name}
                            </option>
                          ))}
                          <option value="fallback">fallback</option>
                        </select>
                      </div>
                      {(selectedFlowBlock.trigger_paths ?? []).map((path) => (
                        <div className="flow-trigger-path-editor" key={path.id}>
                          <div className="row">
                            <input
                              value={path.name}
                              onChange={(e) => updateTriggerPath(selectedFlowBlock.id, path.id, { name: e.target.value })}
                              placeholder="Имя пути"
                            />
                            <button type="button" onClick={() => removeTriggerPath(selectedFlowBlock.id, path.id)}>
                              Удалить путь
                            </button>
                          </div>
                          <div className="row">
                            <input
                              value={path.regex}
                              onChange={(e) => updateTriggerPath(selectedFlowBlock.id, path.id, { regex: e.target.value })}
                              placeholder="Regex пути"
                            />
                          </div>
                          <div className="row">
                            <input
                              placeholder="Тестовая строка для regex"
                              value={triggerTestTextByPathId[path.id] ?? ""}
                              onChange={(e) => updateTriggerTestText(path.id, e.target.value)}
                            />
                            <span className={`regex-badge regex-badge-${String(getTriggerPathRegexMatch(path))}`}>
                              {getTriggerPathRegexMatch(path) === true
                                ? "match=true"
                                : getTriggerPathRegexMatch(path) === false
                                  ? "match=false"
                                  : "invalid regex"}
                            </span>
                          </div>
                        </div>
                      ))}
                      <div className="row">
                        <input
                          placeholder="Fallback-ответ, если ветка не найдена"
                          value={selectedFlowBlock.fallback_action_value ?? ""}
                          onChange={(e) => updateFlowBlockFallbackValue(selectedFlowBlock.id, e.target.value)}
                        />
                      </div>
                      <div className="flow-paths">
                        <div className="flow-paths-title">Связанные пути trigger</div>
                        {flowEdges
                          .filter((edge) => edge.from_block_id === selectedFlowBlock.id)
                          .map((edge, index) => {
                            const targetBlock = getFlowBlockById(edge.to_block_id);
                            return (
                              <div key={`${edge.to_block_id}_${index}`} className="flow-path-item">
                                [{getEdgeLabel(edge)}] -&gt; {targetBlock?.label ?? edge.to_block_id}
                              </div>
                            );
                          })}
                      </div>
                    </>
                  )}

                  {selectedFlowBlock.type === "action" && (
                    <>
                      <div className="row">
                        <select
                          value={selectedFlowBlock.action_type ?? "return_string"}
                          onChange={(e) => updateFlowActionType(selectedFlowBlock.id, e.target.value as "return_string")}
                        >
                          <option value="return_string">return_string</option>
                        </select>
                      </div>
                      <div className="row">
                        <input
                          placeholder="Строка ответа"
                          value={selectedFlowBlock.action_value ?? ""}
                          onChange={(e) => updateFlowActionValue(selectedFlowBlock.id, e.target.value)}
                        />
                      </div>
                    </>
                  )}
                </div>
              )}

              <div className="row">
                <button type="button" onClick={() => setConnectFromBlockId(null)}>
                  Сбросить режим связи
                </button>
                <span className="muted small">
                  Редактирование только на карте: выберите блок кликом. Связь: "Связать" у 1-го, затем у 2-го.
                </span>
              </div>
              <div
                className="flow-canvas"
                ref={flowCanvasRef}
                onMouseMove={handleCanvasMouseMove}
                onMouseUp={stopDragging}
                onMouseLeave={stopDragging}
                onDoubleClick={handleCanvasDoubleClick}
              >
                <svg className="flow-lines" width="100%" height="320" viewBox="0 0 760 320">
                  {flowEdges.map((edge, index) => {
                    const from = flowBlocks.find((block) => block.id === edge.from_block_id);
                    const to = flowBlocks.find((block) => block.id === edge.to_block_id);
                    if (!from || !to) return null;
                    const x1 = from.x + 120;
                    const y1 = from.y + 28;
                    const x2 = to.x;
                    const y2 = to.y + 28;
                    return (
                      <g key={`line_${index}`}>
                        <line
                          x1={x1}
                          y1={y1}
                          x2={x2}
                          y2={y2}
                          stroke="#2563eb"
                          strokeWidth="2"
                          className="flow-line"
                          onClick={(event) => {
                            event.stopPropagation();
                            removeEdgeByIds(edge.from_block_id, edge.to_block_id);
                          }}
                        />
                        <text
                          x={(x1 + x2) / 2}
                          y={(y1 + y2) / 2 - 6}
                          textAnchor="middle"
                          className={`flow-edge-label flow-edge-label-${edge.when ?? "always"}`}
                        >
                          {getEdgeLabel(edge)}
                        </text>
                      </g>
                    );
                  })}
                </svg>
                {flowBlocks.map((block) => (
                  <div
                    key={`canvas_${block.id}`}
                    className={`flow-node flow-node-${block.type} ${selectedFlowBlockId === block.id ? "flow-node-selected" : ""}`}
                    style={{ left: `${block.x}px`, top: `${block.y}px` }}
                    onMouseDown={(event) => handleNodeMouseDown(event, block)}
                    onClick={() => setSelectedFlowBlockId(block.id)}
                  >
                    <button
                      type="button"
                      className="flow-node-delete"
                      aria-label="Удалить блок"
                      onClick={(event) => {
                        event.stopPropagation();
                        removeFlowBlock(block.id);
                      }}
                    >
                      x
                    </button>
                    <div className="flow-node-type">{block.type}</div>
                    <div className="flow-node-label">
                      {block.type === "action" ? block.action_value || block.label : block.label}
                    </div>
                    <div className="flow-node-actions">
                      <button
                        type="button"
                        className={connectFromBlockId === block.id ? "active-connect" : ""}
                        onClick={(event) => {
                          event.stopPropagation();
                          startNodeConnect(block.id);
                        }}
                      >
                        Связать
                      </button>
                    </div>
                    {block.type === "trigger" && (
                      <div className="flow-node-paths">
                        {(block.trigger_paths ?? []).map((path) => (
                          <button
                            key={path.id}
                            type="button"
                            className={`flow-node-path-btn ${
                              triggerConnectPathByBlockId[block.id] === path.id ? "active-connect" : ""
                            }`}
                            onClick={(event) => {
                              event.stopPropagation();
                              startPathConnect(block.id, path.id);
                            }}
                            title={path.regex}
                          >
                            {path.name}
                          </button>
                        ))}
                        <button
                          type="button"
                          className={`flow-node-path-btn ${
                            triggerConnectPathByBlockId[block.id] === "fallback" ? "active-connect" : ""
                          }`}
                          onClick={(event) => {
                            event.stopPropagation();
                            startPathConnect(block.id, "fallback");
                          }}
                        >
                          fallback
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <div className="muted small">
                Версии: {flowVersions.map((version) => `v${version.version}`).join(", ") || "ещё нет"}
              </div>
            </>
          )}

          <pre>{output || "Результат операций будет показан здесь."}</pre>
        </div>
      </main>
    </div>
  );
}

export default App;
