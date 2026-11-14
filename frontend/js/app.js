import * as api from "./api.js";

const PRIORITIES = [
  { value: 1, label: "Низкий" },
  { value: 2, label: "Обычный" },
  { value: 3, label: "Высокий" },
  { value: 4, label: "Срочный" },
];
const priorityLabel = (v) => PRIORITIES.find((p) => p.value === v)?.label ?? v;
const PAGE_SIZE = 20;

const $app = document.getElementById("app");
const $modal = document.getElementById("modal");
const $toasts = document.getElementById("toasts");
const $ = (sel) => $app.querySelector(sel);

const state = {
  projects: [],
  view: { type: "all" },
  tasks: [],
  hasMore: false,
  loading: false,
  error: null,
  search: "",
  priority: "",
};

const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ESC[c]);
const hue = (id) => (id * 137) % 360;

const svg = (d) =>
  `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const icons = {
  plus: svg('<path d="M12 5v14M5 12h14"/>'),
  edit: svg('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>'),
  trash: svg('<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>'),
  menu: svg('<path d="M4 6h16M4 12h16M4 18h16"/>'),
  logout: svg('<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>'),
  list: svg('<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>'),
  close: svg('<path d="M18 6 6 18M6 6l12 12"/>'),
  search: svg('<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>'),
  check: svg('<path d="M20 6 9 17l-5-5"/>'),
};

function toast(message, kind = "error") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = message;
  $toasts.append(el);
  setTimeout(() => {
    el.classList.add("hide");
    setTimeout(() => el.remove(), 300);
  }, 3500);
}

// ---------------------------------------------------------------- Вход / регистрация

function renderAuth(mode = "login") {
  const isLogin = mode === "login";
  $app.innerHTML = `
    <div class="auth">
      <form class="auth-card" novalidate>
        <div class="brand"><span class="logo">${icons.check}</span>Трекер задач</div>
        <h1>${isLogin ? "Вход" : "Регистрация"}</h1>
        <label class="field"><span>Логин</span>
          <input name="login" required maxlength="50" autocomplete="username" autofocus />
        </label>
        <label class="field"><span>Пароль</span>
          <input name="password" type="password" required maxlength="128"
            autocomplete="${isLogin ? "current-password" : "new-password"}" />
        </label>
        ${
          isLogin
            ? ""
            : `<label class="field"><span>Повторите пароль</span>
                 <input name="password2" type="password" required maxlength="128" autocomplete="new-password" />
               </label>`
        }
        <p class="form-error" hidden></p>
        <button class="btn primary wide" type="submit">${isLogin ? "Войти" : "Создать аккаунт"}</button>
        <p class="muted center">
          ${isLogin ? "Нет аккаунта?" : "Уже есть аккаунт?"}
          <a href="#" data-switch>${isLogin ? "Зарегистрироваться" : "Войти"}</a>
        </p>
      </form>
    </div>`;

  const form = $app.querySelector("form");
  const $err = form.querySelector(".form-error");
  const showErr = (msg) => {
    $err.textContent = msg;
    $err.hidden = false;
  };

  form.querySelector("[data-switch]").addEventListener("click", (e) => {
    e.preventDefault();
    renderAuth(isLogin ? "register" : "login");
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const login = fd.get("login").trim();
    const password = fd.get("password");
    if (!login || !password) return showErr("Заполните логин и пароль");
    if (!isLogin && password !== fd.get("password2")) return showErr("Пароли не совпадают");

    const btn = form.querySelector("[type=submit]");
    btn.disabled = true;
    $err.hidden = true;
    try {
      if (isLogin) await api.login(login, password);
      else await api.register(login, password);
      startApp();
    } catch (err) {
      showErr(err.message);
      btn.disabled = false;
    }
  });
}

// ---------------------------------------------------------------- Каркас приложения

function renderShell() {
  $app.innerHTML = `
    <div class="layout">
      <aside class="sidebar">
        <div class="brand"><span class="logo">${icons.check}</span>Трекер задач</div>
        <nav class="nav">
          <a href="#/" class="nav-item" id="nav-all">${icons.list}<span>Все задачи</span></a>
        </nav>
        <div class="section-head">
          <span>Проекты</span>
          <button class="icon-btn sm" data-action="new-project" title="Новый проект" aria-label="Новый проект">${icons.plus}</button>
        </div>
        <ul class="project-list" id="project-list"></ul>
        <div class="sidebar-foot">
          <span class="avatar">${esc(api.currentLogin().slice(0, 1).toUpperCase() || "?")}</span>
          <span class="user truncate">${esc(api.currentLogin())}</span>
          <button class="icon-btn sm" data-action="logout" title="Выйти" aria-label="Выйти">${icons.logout}</button>
        </div>
      </aside>
      <div class="backdrop" data-action="close-sidebar"></div>
      <main class="main">
        <div class="content">
          <header class="main-head" id="main-head"></header>
          <div class="toolbar">
            <label class="search">${icons.search}
              <input type="search" id="search" placeholder="Поиск по названию…" maxlength="200" value="${esc(state.search)}" />
            </label>
            <select id="priority-filter" aria-label="Фильтр по приоритету">
              <option value="">Любой приоритет</option>
              ${PRIORITIES.map((p) => `<option value="${p.value}" ${String(p.value) === state.priority ? "selected" : ""}>${p.label}</option>`).join("")}
            </select>
            <button class="btn primary" data-action="new-task" title="Новая задача (N)">${icons.plus}<span>Задача</span></button>
          </div>
          <ul class="task-list" id="task-list"></ul>
          <div id="list-foot"></div>
        </div>
      </main>
    </div>`;

  let timer;
  $("#search").addEventListener("input", (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      state.search = e.target.value;
      loadTasks();
    }, 300);
  });
  $("#priority-filter").addEventListener("change", (e) => {
    state.priority = e.target.value;
    loadTasks();
  });
}

const currentProject = () =>
  state.view.type === "project" ? state.projects.find((p) => p.id === state.view.id) : null;

function renderSidebar() {
  $("#nav-all").classList.toggle("active", state.view.type === "all");
  $("#project-list").innerHTML = state.projects.length
    ? state.projects
        .map(
          (p) => `
          <li><a href="#/projects/${p.id}" class="nav-item ${state.view.type === "project" && state.view.id === p.id ? "active" : ""}">
            <span class="dot" style="--hue:${hue(p.id)}"></span><span class="truncate">${esc(p.name)}</span>
          </a></li>`,
        )
        .join("")
    : `<li class="sidebar-empty">Проектов пока нет.<br /><a href="#" data-action="new-project">Создать первый</a></li>`;
}

function renderHead() {
  const p = currentProject();
  const title = p ? esc(p.name) : state.view.type === "project" ? "Проект" : "Все задачи";
  const subtitle = p ? (p.description ? esc(p.description) : "") : state.view.type === "all" ? "Задачи из всех проектов" : "";
  $("#main-head").innerHTML = `
    <button class="icon-btn burger" data-action="toggle-sidebar" aria-label="Меню">${icons.menu}</button>
    <div class="head-text">
      <h1>${p ? `<span class="dot lg" style="--hue:${hue(p.id)}"></span>` : ""}${title}</h1>
      ${subtitle ? `<p class="muted">${subtitle}</p>` : ""}
    </div>
    ${
      p
        ? `<div class="head-actions">
             <button class="btn ghost" data-action="edit-project">${icons.edit}<span>Изменить</span></button>
             <button class="btn ghost danger" data-action="delete-project">${icons.trash}<span>Удалить</span></button>
           </div>`
        : ""
    }`;
}

function taskItem(t) {
  const project =
    state.view.type === "all" && t.project_id ? state.projects.find((p) => p.id === t.project_id) : null;
  return `
    <li class="task" style="--prio: var(--p${t.priority})">
      <button class="task-main" data-action="edit-task" data-id="${t.id}">
        <span class="task-title">${esc(t.title)}</span>
        ${t.description ? `<span class="task-desc">${esc(t.description)}</span>` : ""}
        <span class="task-meta">
          <span class="chip prio"><i></i>${priorityLabel(t.priority)}</span>
          ${project ? `<span class="chip"><span class="dot" style="--hue:${hue(project.id)}"></span>${esc(project.name)}</span>` : ""}
        </span>
      </button>
      <div class="task-actions">
        <button class="icon-btn" data-action="edit-task" data-id="${t.id}" title="Редактировать" aria-label="Редактировать">${icons.edit}</button>
        <button class="icon-btn danger" data-action="delete-task" data-id="${t.id}" title="Удалить" aria-label="Удалить">${icons.trash}</button>
      </div>
    </li>`;
}

function renderTasks() {
  const $list = $("#task-list");
  const $foot = $("#list-foot");
  if (!$list) return;
  $list.classList.toggle("dim", state.loading && state.tasks.length > 0);

  if (state.error) {
    $list.innerHTML = "";
    $foot.innerHTML = `<div class="empty"><p>${esc(state.error)}</p><button class="btn" data-action="retry">Повторить</button></div>`;
    return;
  }
  if (!state.tasks.length) {
    if (state.loading) {
      $list.innerHTML = `<li class="skeleton"></li>`.repeat(3);
      $foot.innerHTML = "";
      return;
    }
    $list.innerHTML = "";
    const filtered = state.search.trim() || state.priority;
    $foot.innerHTML = filtered
      ? `<div class="empty"><p class="empty-title">Ничего не найдено</p><p class="muted">Попробуйте изменить поиск или фильтр.</p></div>`
      : `<div class="empty"><p class="empty-title">Задач пока нет</p><p class="muted">Создайте первую — это займёт пару секунд.</p>
           <button class="btn primary" data-action="new-task">${icons.plus}<span>Новая задача</span></button></div>`;
    return;
  }
  $list.innerHTML = state.tasks.map(taskItem).join("");
  $foot.innerHTML = state.hasMore
    ? `<button class="btn ghost wide" data-action="load-more" ${state.loading ? "disabled" : ""}>${state.loading ? "Загрузка…" : "Показать ещё"}</button>`
    : "";
}

// ---------------------------------------------------------------- Загрузка данных

let loadSeq = 0;

// append — догрузить следующую страницу; keep — перезагрузить, сохранив число уже показанных задач.
async function loadTasks({ append = false, keep = false } = {}) {
  const seq = ++loadSeq;
  const size = keep ? Math.min(99, Math.max(PAGE_SIZE, state.tasks.length)) : PAGE_SIZE;
  state.loading = true;
  state.error = null;
  renderTasks();
  try {
    const page = await api.tasks.list({
      limit: size + 1,
      offset: append ? state.tasks.length : 0,
      search: state.search.trim() || undefined,
      priority: state.priority || undefined,
      project_id: state.view.type === "project" ? state.view.id : undefined,
    });
    if (seq !== loadSeq) return;
    state.hasMore = page.length > size;
    const items = page.slice(0, size);
    state.tasks = append ? [...state.tasks, ...items] : items;
  } catch (err) {
    if (seq !== loadSeq || err.status === 401) return;
    if (err.status === 404 && state.view.type === "project") {
      toast("Проект не найден");
      navigate("#/");
      return;
    }
    state.error = err.message;
  } finally {
    if (seq === loadSeq) {
      state.loading = false;
      renderTasks();
    }
  }
}

function parseHash() {
  const m = location.hash.match(/^#\/projects\/(\d+)$/);
  return m ? { type: "project", id: Number(m[1]) } : { type: "all" };
}

function navigate(hash) {
  if (location.hash === hash || (hash === "#/" && !location.hash)) onRoute();
  else location.hash = hash;
}

function onRoute() {
  if (!$("#task-list")) return;
  state.view = parseHash();
  state.tasks = [];
  $(".layout").classList.remove("sidebar-open");
  renderSidebar();
  renderHead();
  loadTasks();
}

window.addEventListener("hashchange", onRoute);

async function startApp() {
  renderShell();
  try {
    state.projects = await api.projects.listAll();
  } catch (err) {
    if (err.status === 401) return;
    toast(err.message);
  }
  onRoute();
}

window.addEventListener("auth:expired", () => {
  if ($modal.open) $modal.close();
  toast("Сессия истекла, войдите снова");
  renderAuth();
});

// ---------------------------------------------------------------- Модальные окна

$modal.addEventListener("click", (e) => {
  if (e.target === $modal || e.target.closest("[data-close]")) $modal.close();
});

function openForm(html, onSubmit) {
  $modal.innerHTML = html;
  const form = $modal.querySelector("form");
  const $err = form.querySelector(".form-error");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = form.querySelector("[type=submit]");
    btn.disabled = true;
    $err.hidden = true;
    try {
      await onSubmit(new FormData(form));
      $modal.close();
    } catch (err) {
      if (err.status === 401) return;
      $err.textContent = err.message;
      $err.hidden = false;
    } finally {
      btn.disabled = false;
    }
  });
  $modal.showModal();
  form.querySelector("input:not([type=radio]), textarea")?.focus();
}

const modalHead = (title) => `
  <header class="modal-head">
    <h2>${title}</h2>
    <button type="button" class="icon-btn" data-close aria-label="Закрыть">${icons.close}</button>
  </header>`;

const modalFoot = (label, cls = "primary") => `
  <p class="form-error" hidden></p>
  <footer class="modal-foot">
    <button type="button" class="btn ghost" data-close>Отмена</button>
    <button type="submit" class="btn ${cls}">${label}</button>
  </footer>`;

function confirmDialog({ title, html, confirm = "Удалить" }) {
  return new Promise((resolve) => {
    let ok = false;
    $modal.innerHTML = `<form class="modal-form">${modalHead(title)}<p class="confirm-text">${html}</p>${modalFoot(confirm, "danger-solid")}</form>`;
    const form = $modal.querySelector("form");
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      ok = true;
      $modal.close();
    });
    $modal.addEventListener("close", () => resolve(ok), { once: true });
    $modal.showModal();
    form.querySelector("[type=submit]").focus();
  });
}

function openTaskForm(task) {
  const isEdit = Boolean(task);
  const projectId = task ? task.project_id : state.view.type === "project" ? state.view.id : null;
  const prio = task?.priority ?? 2;
  openForm(
    `<form class="modal-form">
      ${modalHead(isEdit ? "Редактировать задачу" : "Новая задача")}
      <label class="field"><span>Название</span>
        <input name="title" required maxlength="200" autocomplete="off" value="${esc(task?.title)}" placeholder="Что нужно сделать?" />
      </label>
      <label class="field"><span>Описание</span>
        <textarea name="description" maxlength="1000" rows="4" placeholder="Необязательно">${esc(task?.description)}</textarea>
      </label>
      <fieldset class="field">
        <legend>Приоритет</legend>
        <div class="segmented">
          ${PRIORITIES.map(
            (p) => `<label style="--prio: var(--p${p.value})">
              <input type="radio" name="priority" value="${p.value}" ${p.value === prio ? "checked" : ""} />
              <span><i></i>${p.label}</span>
            </label>`,
          ).join("")}
        </div>
      </fieldset>
      <label class="field"><span>Проект</span>
        <select name="project_id">
          <option value="">Без проекта</option>
          ${state.projects.map((p) => `<option value="${p.id}" ${p.id === projectId ? "selected" : ""}>${esc(p.name)}</option>`).join("")}
        </select>
      </label>
      ${modalFoot(isEdit ? "Сохранить" : "Создать")}
    </form>`,
    async (fd) => {
      const data = {
        title: fd.get("title").trim(),
        description: fd.get("description").trim() || null,
        priority: Number(fd.get("priority")),
        project_id: fd.get("project_id") ? Number(fd.get("project_id")) : null,
      };
      if (!data.title) throw new Error("Введите название задачи");
      if (isEdit) await api.tasks.update(task.id, data);
      else await api.tasks.create(data);
      toast(isEdit ? "Задача сохранена" : "Задача создана", "success");
      loadTasks({ keep: true });
    },
  );
}

function openProjectForm(project) {
  const isEdit = Boolean(project);
  openForm(
    `<form class="modal-form">
      ${modalHead(isEdit ? "Редактировать проект" : "Новый проект")}
      <label class="field"><span>Название</span>
        <input name="name" required maxlength="200" autocomplete="off" value="${esc(project?.name)}" placeholder="Например, «Ремонт»" />
      </label>
      <label class="field"><span>Описание</span>
        <textarea name="description" maxlength="1000" rows="3" placeholder="Необязательно">${esc(project?.description)}</textarea>
      </label>
      ${modalFoot(isEdit ? "Сохранить" : "Создать")}
    </form>`,
    async (fd) => {
      const data = { name: fd.get("name").trim(), description: fd.get("description").trim() || null };
      if (!data.name) throw new Error("Введите название проекта");
      if (isEdit) {
        const saved = await api.projects.update(project.id, data);
        state.projects = state.projects.map((p) => (p.id === saved.id ? saved : p));
        renderSidebar();
        renderHead();
        toast("Проект сохранён", "success");
      } else {
        const created = await api.projects.create(data);
        state.projects.push(created);
        toast("Проект создан", "success");
        navigate(`#/projects/${created.id}`);
      }
    },
  );
}

// ---------------------------------------------------------------- Действия

$app.addEventListener("click", async (e) => {
  const el = e.target.closest("[data-action]");
  if (!el) return;
  e.preventDefault();
  const task = el.dataset.id ? state.tasks.find((t) => t.id === Number(el.dataset.id)) : null;
  const layout = $(".layout");

  switch (el.dataset.action) {
    case "new-task":
      return openTaskForm();
    case "edit-task":
      return task && openTaskForm(task);
    case "delete-task": {
      if (!task) return;
      const ok = await confirmDialog({
        title: "Удалить задачу?",
        html: `Задача «<b>${esc(task.title)}</b>» будет удалена без возможности восстановления.`,
      });
      if (!ok) return;
      try {
        await api.tasks.remove(task.id);
        toast("Задача удалена", "success");
        loadTasks({ keep: true });
      } catch (err) {
        if (err.status !== 401) toast(err.message);
      }
      return;
    }
    case "new-project":
      return openProjectForm();
    case "edit-project":
      return currentProject() && openProjectForm(currentProject());
    case "delete-project": {
      const p = currentProject();
      if (!p) return;
      const ok = await confirmDialog({
        title: "Удалить проект?",
        html: `Проект «<b>${esc(p.name)}</b>» и <b>все его задачи</b> будут удалены без возможности восстановления.`,
      });
      if (!ok) return;
      try {
        await api.projects.remove(p.id);
        state.projects = state.projects.filter((x) => x.id !== p.id);
        toast("Проект удалён", "success");
        navigate("#/");
      } catch (err) {
        if (err.status !== 401) toast(err.message);
      }
      return;
    }
    case "load-more":
      return loadTasks({ append: true });
    case "retry":
      return loadTasks();
    case "toggle-sidebar":
      return layout?.classList.toggle("sidebar-open");
    case "close-sidebar":
      return layout?.classList.remove("sidebar-open");
    case "logout":
      await api.logout();
      Object.assign(state, { projects: [], tasks: [], search: "", priority: "" });
      return renderAuth();
  }
});

// N — быстрая новая задача
document.addEventListener("keydown", (e) => {
  if (e.key.toLowerCase() !== "n" && e.key.toLowerCase() !== "т") return;
  if (e.metaKey || e.ctrlKey || e.altKey || $modal.open || !$("#task-list")) return;
  if (e.target.closest("input, textarea, select, [contenteditable]")) return;
  e.preventDefault();
  openTaskForm();
});

// ---------------------------------------------------------------- Старт

if (api.isAuthed()) startApp();
else renderAuth();
