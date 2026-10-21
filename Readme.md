# Automation Hub — учебный проект

Система сбора телеметрии и передачи команд для домашней и промышленной
автоматизации. Цель — освоить цикл «устройство → сервер → мобильный клиент».

## Текущее состояние

| Компонент | Реализация |
|---|---|
| `server/` | FastAPI + SQLite: телеметрия, последнее значение, очередь команд и подтверждение |
| `desktop/` | PyQt5 GUI + requests: случайные показания, получение и подтверждение команд |
| `mobile/` | Пустой каталог; планируется HarmonyOS-клиент на ArkTS |

Реальный опрос устройств и выполнение команд пока не реализованы.
Архитектура и следующие этапы описаны в [ARCHITECTURE.md](ARCHITECTURE.md).

## Python и зависимости

Целевая версия для Windows 7 — **Python 3.8.10**, последний выпуск Python 3.8
с официальными установщиками Windows. Для разработки на Linux можно использовать
Python 3.12; проверку на Windows 7 нужно проводить отдельно.
Python 3.8 больше не получает обновлений безопасности.
Источник: [Python 3.8.10](https://www.python.org/downloads/release/python-3810/).

Прямые зависимости закреплены в `server/requirements.txt` и
`desktop/requirements.txt`; эти файлы редактируются вручную.
Транзитивные зависимости выбирает установщик с учётом версии Python —
это ещё не полный lock-файл. SQLAlchemy и Alembic пока не используются:
сервер обращается к SQLite через стандартный модуль `sqlite3`.

Для Bash-скриптов нужен Bash: в Windows — Git Bash, в Linux — обычный Bash.
`uv` необязателен; основной способ ниже использует `venv` и `pip`.

## Установка

Команды выполняются из корня репозитория. В Windows используйте `python`
вместо `python3` и `Scripts/python.exe` вместо `bin/python`.
Проверьте версию выбранного интерпретатора командой `python3 --version`.
На Ubuntu для создания окружений может понадобиться пакет `python3-venv`.

```bash
python3 -m venv server/.venv
server/.venv/bin/python -m pip install -r server/requirements.txt

python3 -m venv desktop/.venv
desktop/.venv/bin/python -m pip install -r desktop/requirements.txt
```

Пример для Windows (Git Bash):

```bash
python -m venv server/.venv
server/.venv/Scripts/python.exe -m pip install -r server/requirements.txt
python -m venv desktop/.venv
desktop/.venv/Scripts/python.exe -m pip install -r desktop/requirements.txt
```

Если используете `uv`, вместо создания и установки через pip:

```bash
uv venv --python python3 server/.venv
uv pip install --python server/.venv -r server/requirements.txt
uv venv --python python3 desktop/.venv
uv pip install --python desktop/.venv -r desktop/requirements.txt
```

В Windows замените `--python python3` на `--python python`.
`pyproject.toml` в проекте нет, поэтому `uv sync` не используется.
Работоспособность самого `uv` на Windows 7 здесь не проверена; используйте pip.

Для полного пересоздания окружения доступны вспомогательные скрипты:

```bash
bash server/scripts_server/recreate_env.sh
bash desktop/scripts_server/recreate_env.sh
```

Они **удаляют существующую `.venv` соответствующего компонента**.
Интерпретатор можно указать через `PYTHON_BIN`, например:
`PYTHON_BIN=/usr/bin/python3 bash server/scripts_server/recreate_env.sh`.
Скрипты пишут логи в каталог `logs/` компонента и поддерживают установку
из локального каталога пакетов через `LOCAL_PACKAGES_DIR`.

## Запуск

В первом терминале из корня репозитория:

```bash
bash server/run_server_pip.sh
```

Сервер: http://127.0.0.1:3000, Swagger UI: http://127.0.0.1:3000/docs.
База `server/telemetry.db` и таблицы создаются автоматически при импорте приложения.
Отдельный `init_db.py` не нужен. Путь можно изменить переменной `DB_PATH`;
относительный путь отсчитывается от каталога `server/` при запуске скриптом.

Во втором терминале:

```bash
bash desktop/run_desktop_pip.sh
```

Откроется окно сборщика. Укажите адрес сервера, идентификатор устройства и
интервал, затем нажмите **Запустить**. В окне отображаются последнее успешно
отправленное показание, счётчики и журнал. **Остановить** прекращает сбор;
при активном запросе остановка и закрытие окна ожидают его завершения.
Настройки можно менять после остановки. Команды выполняются в демонстрационном
режиме: записываются в журнал и подтверждаются без управления оборудованием.

GUI использует PyQt5; он устанавливается из `desktop/requirements.txt`.
Версии PyQt5 и Qt закреплены; запуск на Windows 7 требует отдельной проверки.

На вкладке **История из базы** нажмите **Обновить из базы**: приложение получит
список устройств и сохранённые показания через API. Выберите устройство из списка
или введите его ID и снова обновите данные. Таблица показывает ID, время записи
и значение, новые записи сверху. Кнопки **Назад** и **Далее** переключают страницы
по 100 записей; обновление возвращает к первой странице. При поступлении новых
показаний состав страниц может меняться. Просмотр доступен при остановленном
сборщике, но требует работающего сервера с новыми эндпоинтами. Адрес берётся
из поля на вкладке «Сборщик»; прямого доступа к файлу SQLite из GUI нет.

На вкладке **График истории** укажите ID устройства, начало и окончание периода,
затем нажмите **Построить график**. По умолчанию выбран последний день.
Время задаётся по местному времени сервера, включая всю последнюю выбранную
секунду. График на pyqtgraph загружает показания за весь период независимо от
страниц таблицы. Колесо мыши меняет масштаб, перетаскивание перемещает график.
При более чем 50 000 показаний выберите меньший период; данные не обрезаются.
Если показаний нет или сервер недоступен, под графиком появится сообщение.
Перед первым запуском обновите зависимости `desktop/requirements.txt`
(добавлены pyqtgraph и NumPy) и перезапустите сервер.
Для работы без графического окна:

```bash
bash desktop/run_desktop_pip.sh --cli
```

Скрипты используют собственную `.venv`, поддерживают Windows и Linux и могут
вызываться из любого каталога. Остановить процесс можно через `Ctrl+C`.

Настройки сборщика задаются переменными окружения:

| Переменная | Значение по умолчанию |
|---|---|
| `SERVER_URL` | `http://127.0.0.1:3000` |
| `DEVICE_ID` | `demo-sensor-01` |
| `INTERVAL_SEC` | `2` |

Например, в Bash:

```bash
DEVICE_ID=sensor-2 INTERVAL_SEC=5 bash desktop/run_desktop_pip.sh
```

Сервер по умолчанию слушает только локальный интерфейс. Для подключения
с телефона в локальной сети запустите из `server/`:

```bash
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 3000
```

В Windows путь к Python — `.venv/Scripts/python.exe`.
На телефоне укажите локальный IP компьютера; сервер пока не имеет аутентификации.

## Проверка API

При запущенном сервере (Bash с установленным `curl`):

```bash
curl -X POST http://127.0.0.1:3000/api/telemetry \
  -H 'Content-Type: application/json' \
  -d '{"device_id":"demo-sensor-01","value":25.5}'
curl http://127.0.0.1:3000/api/devices/demo-sensor-01/latest
curl http://127.0.0.1:3000/api/devices
curl "http://127.0.0.1:3000/api/devices/demo-sensor-01/history?limit=100&offset=0"

curl -X POST http://127.0.0.1:3000/api/devices/demo-sensor-01/command \
  -H 'Content-Type: application/json' \
  -d '{"action":"pump_on","params":{"speed":50}}'
curl http://127.0.0.1:3000/api/devices/demo-sensor-01/commands
```

Работающий сборщик получает команды и подтверждает их автоматически,
поэтому очередь при последнем запросе уже может оказаться пустой.
Действие `pump_on` только выводится в консоль — оборудование не включается.

## Тесты

Из корня репозитория, без запущенного сервера:

```bash
server/.venv/bin/python -m pytest server/tests desktop/tests -q
```

В Windows: `server/.venv/Scripts/python.exe -m pytest server/tests desktop/tests -q`.
Тесты используют отдельные временные базы данных.

Проверено 2026-10-21: установка закреплённых зависимостей и 7 тестов API
на Linux / Python 3.12.3; подбор бинарных пакетов через pip для Python 3.8 /
Windows x64. Запуск на самой Windows 7 не проверен. На Python 3.12 тесты
выдают предупреждение об устаревшем интерфейсе внутри зависимости TestClient.

## Структура

```text
server/
  app/main.py                   # API, модели запросов и создание таблиц
  tests/                        # тесты телеметрии и команд
  requirements.txt
  run_server_pip.sh
  scripts_server/recreate_env.sh
desktop/
  main.py                       # запуск GUI или --cli
  gui.py                        # окно PyQt5
  history.py                    # просмотр сохранённой телеметрии
  chart.py                      # график истории за период на pyqtgraph
  collector.py                  # сбор данных и обработка демо-команд
  requirements.txt
  run_desktop_pip.sh
  scripts_server/recreate_env.sh
mobile/                         # место для проекта DevEco Studio
```

Сборка и распространение `.exe` пока не настроены.
