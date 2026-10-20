# Automation Hub — учебный проект

Распределённая система для сбора данных с устройств промышленной и домашней
автоматизации, их хранения на сервере и управления со смартфона Huawei.

Проект учебный: главная цель — освоить полный цикл разработки
(сбор данных → сервер → мобильный клиент), а не промышленная надёжность.

## Компоненты

| Компонент | Стек | Роль |
|---|---|---|
| `server/` | Python 3.8 + FastAPI + SQLite | REST API, хранение телеметрии, очередь команд |
| `desktop/` | Python 3.8 + requests | Опрос устройств (пока — заглушка), отправка данных на сервер |
| `mobile/` | ArkTS + DevEco Studio | Отображение данных и управление (в разработке) |

Подробное описание архитектуры, потоков данных и roadmap — в
[`ARCHITECTURE.md`](ARCHITECTURE.md).

## Выпуск версии

## Требования

| Параметр | Значение |
|---|---|
| Python | 3.8.10 (последняя версия, поддерживающая Windows 7) |
| ОС | Windows 7 и выше |
| [uv](https://github.com/astral-sh/uv) | 0.11.7 (рекомендуется, но не обязателен) |


### 2. Настройка окружения

#### 2.1 Создание виртуального окружения для server-приложения (VSCode)

```bash
cd server
bash scripts_server/recreate_env.sh
```

#### 2.2 Создание виртуального окружения для desktop-приложения (VSCode)

```bash
cd desktop
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

#### 3.1 запуск server 

##### c uv

```bash
uv run python init_db.py     - скрипт для инициализации БД

uv run uvicorn app.main:app --reload --port 3000

http://localhost:3000/docs  -> Swagger UI
```

##### без uv

```bash
bash server/run_server_pip.sh
```

#### 3.1 запуск decktop 

##### c uv

```bash
uv run python init_db.py     - скрипт для инициализации БД

uv run uvicorn app.main:app --reload --port 3000

http://localhost:3000/docs  -> Swagger UI
```

##### без uv

```bash
cd desktop
bash scripts_server/recreate_env.sh
source .venv/Scripts/activate
python main.py
```

## Запуск приложения (Windows — exe)
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


smart_house/
├── ARCHITECTURE.md          # Архитектура и roadmap
├── Readme.md                # этот файл
├── server/                  # FastAPI-сервер
│   ├── app/
│   ├── scripts_server/
│   ├── init_db.py
│   ├── requirements.txt
│   └── run_server_pip.sh
└── desktop/                 # Python-сборщик данных
    ├── main.py
    ├── requirements.txt
    └── scripts_server/
│   └── run_desktop_pip.sh