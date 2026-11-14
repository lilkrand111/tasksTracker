# Трекер задач

Веб-приложение для управления задачами: REST API на **FastAPI** + **PostgreSQL** и лёгкий веб-интерфейс на чистом JavaScript, который отдаётся тем же сервером.

Пользователь регистрируется, входит по логину и паролю, создаёт проекты и задачи. Каждый видит только свои данные.

## Возможности

- **Аутентификация**: регистрация, вход по OAuth2 password flow, JWT access-токен и refresh-токен с ротацией, выход с отзывом refresh-токена.
- **Проекты**: создание, просмотр, редактирование и удаление, поиск по названию, пагинация.
- **Задачи**: CRUD, приоритет от 1 до 4, необязательная привязка к проекту, фильтры по приоритету, проекту и подстроке в названии, пагинация.
- **Изоляция данных**: любой запрос к чужой задаче или проекту возвращает `404`.
- **Веб-интерфейс**: вход и регистрация, боковая панель проектов, фильтры, модальные формы, уведомления, клавиша `N` для быстрого создания задачи. Access-токен обновляется сам.

## Стек

| Слой | Технологии |
|---|---|
| API | FastAPI, Pydantic v2, pydantic-settings |
| БД | PostgreSQL 16, SQLAlchemy 2 (async) + psycopg 3 |
| Миграции | Alembic |
| Безопасность | PyJWT (HS256), pwdlib (Argon2) |
| Фронтенд | HTML + CSS + JS-модули, без сборки и зависимостей |
| Окружение | Python 3.12, [uv](https://docs.astral.sh/uv/), Docker Compose (для БД) |

## Структура проекта

```
taskstracker/
├── backend/
│   ├── main.py          # создание приложения, подключение роутеров и статики
│   ├── config.py        # настройки из .env (pydantic-settings)
│   ├── database.py      # async engine, фабрика сессий, Base
│   ├── models.py        # ORM-модели: User, Task, Project, RefreshToken
│   ├── schemas.py       # Pydantic-схемы запросов и ответов
│   ├── security.py      # хеширование паролей, JWT, refresh-токены, текущий пользователь
│   ├── deps.py          # получение задачи/проекта с проверкой владельца
│   └── routers/
│       ├── auth.py      # /register, /token, /token/refresh, /logout
│       ├── projects.py  # /projects
│       └── tasks.py     # /tasks
├── alembic/             # миграции БД
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── js/
│       ├── api.js       # клиент API: хранение токенов, авто-refresh
│       └── app.js       # интерфейс, роутинг по hash, формы
├── docker-compose.yml   # PostgreSQL для локальной разработки
├── alembic.ini
├── pyproject.toml
└── .env.example
```

## Быстрый старт

### 1. Зависимости

Нужны Python 3.12, [uv](https://docs.astral.sh/uv/getting-started/installation/) и Docker.

```bash
uv sync
```

### 2. База данных

```bash
docker compose up -d
```

Поднимается PostgreSQL 16 на `localhost:5432`: пользователь `tasks`, пароль `tasks`, база `taskstracker`.

### 3. Переменные окружения

Скопируйте шаблон и заполните его:

```bash
cp .env.example .env
```

| Переменная | Описание | Пример |
|---|---|---|
| `DB_URL` | строка подключения SQLAlchemy (драйвер psycopg) | `postgresql+psycopg://tasks:tasks@localhost:5432/taskstracker` |
| `SECRET_KEY` | ключ подписи JWT | вывод `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | время жизни access-токена, мин | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | время жизни refresh-токена, дни | `30` |

Один и тот же `DB_URL` читают и приложение, и Alembic.

### 4. Миграции

```bash
uv run alembic upgrade head
```

### 5. Запуск

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

- Веб-интерфейс: <http://localhost:8000/>
- Swagger UI: <http://localhost:8000/docs>. Кнопка **Authorize** работает через `/token`.
- Проверка работоспособности: <http://localhost:8000/health>

## API

Все эндпоинты `/projects` и `/tasks` требуют заголовок `Authorization: Bearer <access_token>`.

### Аутентификация

| Метод | Путь | Тело | Ответ |
|---|---|---|---|
| `POST` | `/register` | JSON `{login, password}` | `201` `{id, login}`; `409`, если логин занят |
| `POST` | `/token` | form-data `username`, `password` | `{access_token, refresh_token, token_type}` |
| `POST` | `/token/refresh` | JSON `{refresh_token}` | новая пара токенов; старый refresh-токен перестаёт работать |
| `POST` | `/logout` | JSON `{refresh_token}` | `204`, refresh-токен удаляется |

Логин хранится в нижнем регистре, поэтому вход не зависит от регистра букв.

### Проекты: `/projects`

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/projects` | создать проект `{name, description?}` |
| `GET` | `/projects` | список; параметры `limit` (1–100, по умолчанию 20), `offset`, `search` |
| `GET` | `/projects/{id}` | получить проект |
| `PUT` | `/projects/{id}` | заменить `name` и `description` |
| `DELETE` | `/projects/{id}` | удалить проект **вместе со всеми его задачами** |

### Задачи: `/tasks`

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/tasks` | создать задачу `{title, description?, priority?, project_id?}` |
| `GET` | `/tasks` | список; параметры `limit`, `offset`, `priority` (1–4), `search`, `project_id` |
| `GET` | `/tasks/{id}` | получить задачу |
| `PUT` | `/tasks/{id}` | заменить все поля задачи |
| `DELETE` | `/tasks/{id}` | удалить задачу |

Приоритеты: `1` низкий, `2` обычный (по умолчанию), `3` высокий, `4` срочный.

Если указать в `project_id` чужой или несуществующий проект, сервер вернёт `404`.

### Пример через curl

```bash
# регистрация
curl -X POST localhost:8000/register \
  -H 'Content-Type: application/json' \
  -d '{"login": "alice", "password": "secret"}'

# получение токена
TOKEN=$(curl -s -X POST localhost:8000/token \
  -d 'username=alice&password=secret' | python -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')

# создание задачи
curl -X POST localhost:8000/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title": "Написать README", "priority": 3}'

# задачи с высоким приоритетом
curl "localhost:8000/tasks?priority=3" -H "Authorization: Bearer $TOKEN"
```

## Модель данных

```
users ─┬─< projects ─< tasks
       ├─< tasks            (задача может быть без проекта)
       └─< refresh_tokens
```

- `users`: `id`, `login` (уникальный, до 50 символов), `hashed_password`.
- `projects`: `id`, `name`, `description`, `user_id`.
- `tasks`: `id`, `title`, `description`, `priority` (CHECK 1–4, по умолчанию 2), `user_id`, `project_id` (может быть пустым).
- `refresh_tokens`: `id`, `user_id`, `token_hash` (SHA-256), `expires_at`.

Все внешние ключи заданы с `ON DELETE CASCADE`. При удалении пользователя удаляются его проекты, задачи и токены, при удалении проекта — его задачи.

## Безопасность

- Пароли хешируются Argon2 (`pwdlib`). Хеширование вынесено в отдельный поток, чтобы не блокировать event loop.
- Если пользователь не найден, всё равно проверяется фиктивный хеш. Так время ответа не выдаёт, существует ли логин.
- Refresh-токен — случайная строка. В базе хранится только её SHA-256-хеш. При каждом обновлении токен меняется.
- Веб-клиент хранит токены в `localStorage`. На `401` он один раз пробует обновить токен, параллельные запросы при этом используют общий refresh.

## Миграции

Создать новую миграцию по изменениям в `backend/models.py`:

```bash
uv run alembic revision --autogenerate -m "описание изменений"
uv run alembic upgrade head
```

Откатить последнюю миграцию:

```bash
uv run alembic downgrade -1
```
