// Тонкий клиент для API бэкенда: хранит токены, сам обновляет access-токен по refresh.

const STORAGE_KEY = "taskstracker.auth";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

let auth = readAuth();

function readAuth() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY));
  } catch {
    return null;
  }
}

function saveAuth(value) {
  auth = value;
  try {
    if (value) localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* хранилище недоступно — живём в памяти */
  }
}

export const isAuthed = () => Boolean(auth?.access_token);
export const currentLogin = () => auth?.login ?? "";

async function safeFetch(url, options) {
  try {
    return await fetch(url, options);
  } catch {
    throw new ApiError(0, "Не удалось связаться с сервером");
  }
}

async function toError(res) {
  let detail;
  try {
    detail = (await res.json()).detail;
  } catch {
    /* тело не JSON */
  }
  if (Array.isArray(detail)) detail = detail.map((d) => d.msg).join("; ");
  if (typeof detail !== "string" || !detail) detail = `Ошибка сервера (${res.status})`;
  return new ApiError(res.status, detail);
}

let refreshing = null;

function refreshTokens() {
  if (!auth?.refresh_token) return Promise.resolve(false);
  // Несколько параллельных запросов получат 401 — обновляем токен один раз.
  refreshing ??= (async () => {
    try {
      const res = await fetch("/token/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: auth.refresh_token }),
      });
      if (!res.ok) return false;
      const t = await res.json();
      saveAuth({ ...auth, access_token: t.access_token, refresh_token: t.refresh_token });
      return true;
    } catch {
      return false;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

async function request(method, path, { query, body } = {}, retry = true) {
  let url = path;
  if (query) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== "") params.set(k, v);
    }
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }

  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth?.access_token) headers.Authorization = `Bearer ${auth.access_token}`;

  const res = await safeFetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    if (retry && (await refreshTokens())) return request(method, path, { query, body }, false);
    saveAuth(null);
    window.dispatchEvent(new Event("auth:expired"));
    throw new ApiError(401, "Сессия истекла, войдите снова");
  }
  if (!res.ok) throw await toError(res);
  return res.status === 204 ? null : res.json();
}

// ---------- Авторизация

export async function login(loginValue, password) {
  const res = await safeFetch("/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: loginValue, password }),
  });
  if (res.status === 401) throw new ApiError(401, "Неверный логин или пароль");
  if (!res.ok) throw await toError(res);
  const t = await res.json();
  saveAuth({
    access_token: t.access_token,
    refresh_token: t.refresh_token,
    login: loginValue.toLowerCase(),
  });
}

export async function register(loginValue, password) {
  const res = await safeFetch("/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login: loginValue, password }),
  });
  if (!res.ok) throw await toError(res);
  await login(loginValue, password);
}

export async function logout() {
  const refresh_token = auth?.refresh_token;
  saveAuth(null);
  if (!refresh_token) return;
  try {
    await fetch("/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token }),
    });
  } catch {
    /* локально уже вышли */
  }
}

// ---------- Ресурсы

const MAX_LIMIT = 100;

export const projects = {
  async listAll() {
    const all = [];
    for (let offset = 0; ; offset += MAX_LIMIT) {
      const page = await request("GET", "/projects", { query: { limit: MAX_LIMIT, offset } });
      all.push(...page);
      if (page.length < MAX_LIMIT) return all;
    }
  },
  create: (data) => request("POST", "/projects", { body: data }),
  update: (id, data) => request("PUT", `/projects/${id}`, { body: data }),
  remove: (id) => request("DELETE", `/projects/${id}`),
};

export const tasks = {
  list: (query) => request("GET", "/tasks", { query }),
  create: (data) => request("POST", "/tasks", { body: data }),
  update: (id, data) => request("PUT", `/tasks/${id}`, { body: data }),
  remove: (id) => request("DELETE", `/tasks/${id}`),
};
