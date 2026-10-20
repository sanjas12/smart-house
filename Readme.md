# Title

✅ Дашборд — статистика и последние неисправности

✅ Проекты — управление проектами (CRUD)

✅ Неисправности — таблица с фильтрами и пагинацией

✅ Детальная страница — с комментариями и историей

✅ Kanban доска — визуальное управление задачами


## Работа интерфейса без CDN

Bootstrap 5.1.3, Bootstrap Icons 1.8.1 и Axios 1.7.9 хранятся в
`app/static/vendor` и раздаются самим приложением. Для отображения интерфейса и
авторизации доступ к `cdn.jsdelivr.net` не требуется. Лицензии библиотек находятся
рядом с соответствующими файлами.

## Выпуск версии

Из Git Bash выполните `bash scripts/release.sh`. Скрипт проверяет Python-код в
`app`, тесты, pre-commit и согласованность версии в `pyproject.toml` и
`_version.py`; при неуспешной проверке релиз не создаётся.
Настройки Commitizen находятся в секции `[tool.commitizen]` файла `pyproject.toml`.


## Запуск приложения (из репозитория)

### 1. Требования

| Параметр | Значение |
|---|---|
| Python | 3.8.10 |
| ОС | Windows 7 и выше |
| [uv](https://github.com/astral-sh/uv) | 0.11.7 |

### 2. Настройка окружения

#### 2.1 Создание виртуального окружения для server-приложения (VSCode)

```bash
cd server
bash scripts_server/recreate_env.sh
```

#### 2.2 Установка зависимостей (если скрипт из пункта 2.1 не сработал)

Рекомендуется — через [uv](https://github.com/astral-sh/uv):

```bash
uv sync
```

Без uv:

```bash
pip install -r requirements.txt
```

> `requirements.txt` генерируется из `pyproject.toml` — не редактировать вручную.

### 3. Запуск из исходников

#### 3.1 server c uv

```bash
uv run python init_db.py     - скрипт для инициализации БД

uv run uvicorn app.main:app --reload --port 3000

http://localhost:3000/docs  -> Swagger UI
```

#### 3.2 server Без uv

```bash
cd server
bash run_server_pip.sh
```

---

## Запуск приложения (Windows — exe)

### Требования

- [Visual C++ Redistributable 2015–2022](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- ОС: Windows 7 и выше

## help

TODO
# Рекомендация: замените init_db.py и migrate_db.py на Alembic (для обучения)
Так как вы учитесь, сейчас самое время освоить Alembic — это профессиональный инструмент для миграций (как Liquibase в Java).

Как перейти на Alembic (пошагово):

Установите Alembic (если еще нет):
uv pip install alembic

Инициализируйте Alembic в папке backend/:
alembic init -t async migrations
(Если используете синхронный SQLAlchemy, то просто alembic init migrations)

В файле alembic.ini поправьте строку:
sqlalchemy.url = sqlite:///./faults.db

В migrations/env.py укажите вашу Base (чтобы Alembic видел модели):
target_metadata = [Base.metadata] (импортируйте из app.models.all_models)

Создайте первую миграцию:
alembic revision --autogenerate -m "Initial tables"

Примените:
alembic upgrade head

Преимущество: Теперь структура БД будет меняться контролируемо, и вы сможете откатывать изменения.


39_Faults/
    ├── app/                          # Весь код приложения

    ├── migrations/                   # Миграции Alembic (не меняется)
    ├── scripts/                      # Вспомогательные скрипты (не меняется)
    │   ├── init_env.sh
    │   ├── run.sh
    │   └── toexe.sh
    ├── tests/                        # Тесты (не меняется)
    ├── .python-version               # Версия Python (не меняется)
    ├── faults.db                     # Файл SQLite базы (не меняется)
    ├── init_db.py                    # Скрипт инициализации БД (не меняется)
    ├── migrate_db.py                 # Скрипт миграции БД (не меняется)
    ├── pyproject.toml                # Зависимости uv (не меняется)
    ├── requirements.txt              # Зависимости pip (не меняется)
    ├── seed_data.py                  # НОВО! Скрипт для наполнения тестовыми данными
    ├── uv.lock                       # Lock-файл uv (не меняется)
    ├── Readme.md                     # Документация (не меняется)
    └── _version.py                   # Версия проекта (не меняется)
