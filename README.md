# Leicester City Analytics

> **SAVE-SAFETY BLOCK (2026-10-29):** do not run any repository Lua script in a
> career that must be preserved. A second manual `0.3.0` diagnostic session,
> which traversed optional Live Editor DB tables, was followed by a reproducible
> reload crash. `diagnostic.lua`, event probes and callback collection are now
> disabled by default. Use already archived JSON, screenshots, or an
> out-of-process parser while this boundary is investigated.

Локальный аналитический дашборд для карьеры EA FC 24. Python 3.12 + FastAPI / SQLAlchemy / Alembic / SQLite; React + TypeScript + Vite / Tailwind / локальные shadcn-style компоненты / TanStack / Recharts. Интерфейс на русском, облако и Docker не нужны.

**Диагностический Gate P0 проверен на Windows с реальными EA FC 24 и Live Editor.** Подтверждены сезонные счётчики до/после сыгранного матча и быстрой симуляции, запись внешних файлов и импорт watcher-ом. Автоматический callback-collector признан небезопасным на проверенной сборке: saves после event-handler сессий повторяемо не загружались, тогда как diagnostic-only save загружался. Поэтому `Collector: not verified`, `collector.experimental.lua` жёстко выключен, а Gate P2 заблокирован до другой, отложенной за пределы callback архитектуры. Историческое приложение и файловая обработка работают независимо. Скриншоты использовались только как контроль P0; регулярной загрузки скриншотов, OCR или ручного ввода статистики нет.

## Демо со стабовыми данными — Mac

Игра и Live Editor не нужны. Откройте **`Start Demo.command` двойным кликом в Finder** или выполните:

```bash
cd /Users/elshimin/PycharmProjects/FootballCareerDashboard
./"Start Demo.command"
```

При первом запуске нужны Python 3.12+ и Node.js 22+; скрипт сам создаст окружение, установит зависимости и соберёт интерфейс, если это требуется. Первоначальная установка требует интернета. При последующих запусках готовый интерфейс и зависимости используются повторно. Браузер откроется на **http://127.0.0.1:8001**. Остановить сервер: Ctrl+C в его окне Terminal. Если macOS запрещает исполнение файла после скачивания, запустите `bash "Start Demo.command"` из Terminal.

Демо содержит две карьеры, 22 вымышленных игрока в основной карьере, восемь сезонов, три синтетических турнира, заметки и изменения между снимками. Жёлтая плашка и source/quality=`demo` явно отмечают искусственные данные. Кнопка **«Следующий демоснимок»** отправляет новый синтетический JSON через локальную очередь; watcher принимает его, интерфейс обновляется автоматически (обычно до 5 секунд).

Демо хранится отдельно в **`data-demo/`**, настоящая история — в `data/`. Запуск демо не изменяет реальную базу. Существующая база без demo-маркера не может стать демобазой. Игровой `verified_live` остаётся false. Демо не является проверкой Live Editor и не подделывает недоступные xG, оценки или результаты матчей.

Если окружение уже установлено, можно также запустить `.venv/bin/python -m app.demo`. Дополнительные параметры: `--no-browser`, `--port 8002`. Настоящий исторический режим по-прежнему запускается через `.venv/bin/python -m app.main` на 8000; в нём демоданные не создаются.

## Графики и локальный доступ

На обзоре доступны сезонная динамика, лидеры по голам и ассистам, распределение голов по позициям и график результативности относительно числа выступлений. Все графики используют те же фильтры карьеры/сезона/турнира, что и таблицы. Неизвестные значения не заменяются нулями. Демо автоматически дополняется тремя ранними синтетическими сезонами один раз, без изменения существующей истории и настоящей базы.

Cloudflared, Cloudflare Tunnel, ngrok и другие внешние туннели приложением не используются и не запускаются. Backend слушает только `127.0.0.1`; frontend обращается к API этого же локального сервера. Шрифты, иконки и графики не требуют внешних сервисов. Интернет нужен для первоначальной установки пакетов и отправки исходников в GitHub, а не для работы дашборда.

## Быстрый запуск — Windows

Для передачи подготовки Windows-агенту Codex: [полное задание до запуска игры](WINDOWS_CODEX_PRE_GAME.md).

Нужны Python **3.12+**, Node.js **22 LTS** и npm. Откройте PowerShell в корне проекта:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.lock
.\.venv\Scripts\python -m pip install -e backend --no-deps
.\.venv\Scripts\python -m app.cli migrate
.\.venv\Scripts\python -m app.cli seed
npm --prefix frontend ci
npm --prefix frontend run build
.\.venv\Scripts\python -m app.main
```

Откройте **http://127.0.0.1:8000**. Backend обслуживает готовую SPA и автоматически запускает один watcher. `seed` импортирует только реальный включённый Excel, лист `Все сезоны`, и допускает безопасный повтор. Можно пропустить seed и создать карьеру/импортировать файл в интерфейсе. Тестовые снимки никогда не подмешиваются при запуске.

Повторный запуск после настройки из корня: `.\.venv\Scripts\python -m app.main`. Остановить: Ctrl+C. Один процесс API/один watcher на DATA_DIR; не запускайте несколько Uvicorn workers.

## macOS / Linux

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock
.venv/bin/python -m pip install -e backend --no-deps
.venv/bin/python -m app.cli migrate
.venv/bin/python -m app.cli seed
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m app.main
```

На Mac работают веб-приложение, Excel и очередь JSON. Live Editor на macOS не обещается. LAN не включён: приложение привязано к loopback и проверяет Host/Origin.

## Разработка

Backend: `python -m app.main` с активированной `.venv`. В другом терминале: `npm --prefix frontend run dev`, затем http://127.0.0.1:5173. Vite проксирует `/api` на 8000. API-документация: http://127.0.0.1:8000/docs.

Конфигурация: скопируйте `.env.example` в `.env` по необходимости. `DATA_DIR` по умолчанию — `data/` рядом с README, независимо от cwd. Там находятся БД, `spool/`, `raw/`, `processed/`, `quarantine/`. Не коммитьте эти папки. Для переноса/backup остановите API и скопируйте весь DATA_DIR; не копируйте только SQLite-файл во время записи WAL.

## Настройка Live Editor — сначала Phase 0

1. Используйте ту же **Windows-машину** для игры и приложения, offline manager career и тестовую копию save. Сверьте совместимость Live Editor с вашей сборкой EA FC 24 по [источнику автора](https://github.com/xAranaktu/FC-24-Live-Editor). У автора есть предупреждения об античите; приложение не реализует обход античита и не предназначено для online.
2. В «Синхронизация» один раз создайте binding save, скопируйте `instance_key` в локальный `config.lua`, созданный из `collectors/fc24-live-editor/config.example.lua`. Настройте существующий `DATA_DIR/spool` абсолютным Windows-путём.
3. Выполните [точную последовательность P0](docs/manual-game-validation.md): diagnostic → event_probe → сыгранный матч → быстрая симуляция → повторное событие → reload/откат → смена сезона. Сохраните raw before/after и версии. `python scripts/diagnose_snapshots.py before.json after.json` показывает изменения за период.
4. Подтвердите реальный автоматический season_reader для установленного API, события после окончательного обновления статистики, файловый канал и автозапуск. Здесь нет догадки «сезон меняется 1 июля» и выдуманных event ID. Если источник контекста недоступен, gate остаётся закрытым.
5. Не включайте verification flags и не запускайте `collector.experimental.lua` на проверенной сборке: реальный тест показал, что работа внутри CareerModeEvent callback нарушает save/reload безопасность. Следующая реализация должна только ставить лёгкий сигнал в callback, выполнять чтение позднее вне callback и заново пройти тест на одноразовой карьере.
6. `verified_live` в binding можно подтвердить через API `/saves/bind` только с текстом evidence (версии, сценарий). Для полного Live TOTAL дополнительно нужна подтверждённая полнота турниров в snapshot. Без этого выбирайте отдельный турнир; неизвестные общие суммы показываются как `—`.

UID не обязателен: явный instance_key безопаснее непроверенного UID. Ключ нельзя оставлять прежним при переключении на другую карьеру/save. Unknown save/сезон/команда → NEEDS_BINDING, без случайного назначения. Исправленные контекстные данные доставляются новым корректным снимком; raw не редактируется.

## Работа с данными

- История: `Careers → XLSX/CSV → предпросмотр → подтвердить`. Из Excel читается **только «Все сезоны»**. Сезонные дубли и «За всю карьеру» игнорируются. `Г+П` пересчитывается. История помечена `PARTIAL_SCREENSHOT`.
- Повторный файл не меняет суммы. Противоречащие строки показываются и заменяются только явно. Предпросмотр имеет срок 24 часа и проверку устаревания.
- Live: файлы автоматически читаются из `spool/`. Сначала проверяются устойчивые размер/mtime/checksum, затем схема; нормализованные записи и событие коммитятся одной транзакцией. Оригиналы сохраняются по SHA-256. Невалидный файл → quarantine. После исправления binding нажмите «Повторить очередь».
- Snapshot — накопительное наблюдение, а не добавление голов. Аналитика берёт последнее значение каждого ключа игрок+команда+турнир в выбранном сезоне/ветке. Отсутствующий игрок не обнуляется. Оценка `avg` хранится raw и не выдаётся за проверенную среднюю.
- Исторический TOTAL и Live одного сезона не складываются. По умолчанию приоритет истории; на странице Sync есть явное сопоставление playerid и выбор источника выбранного сезона. Совпадение фамилий ничего не склеивает.
- Откат счётчиков/даты или нарушенный порядок → CONFLICT и новая pending-ветка. Последующие снимки удерживаются. В Sync явно примите новую ветку либо сохраните прежнюю. Принятие переключает Live-представление на новую ветку; предыдущая история физически сохраняется и доступна в snapshots.
- Несколько bindings в карьере требуют выбора save в глобальном фильтре. Разные saves и карьеры не суммируются. `as_of` ограничивает Live-наблюдения; исторический Excel не имеет внутрисезонных дат.
- `appearances` — выступления игроков, не число матчей команды. Дельты подписаны «Между снимками», даже при `app_delta=1`. Оценки матчей, результаты, xG, владение, минуты и трансферные данные не генерируются.
- Notes необязательны; можно привязать к интервалу или оставить общей заметкой. Сбор не зависит от заметок.

## Проверки

```bash
# Из корня после установки зависимостей:
cd backend
../.venv/bin/python -m pytest -q
../.venv/bin/ruff check app tests
cd ..
npm --prefix frontend test
npm --prefix frontend run build
```

В Windows используйте `..\.venv\Scripts\python -m pytest -q` и `..\.venv\Scripts\ruff check app tests` из backend. Lua harness использует отдельный `lupa`, а не настоящий Live Editor. Искусственные значения находятся в tests/ и явно включаемом изолированном деморежиме; обычный app.main их не создаёт.

Браузерная проверка: сначала seed и запущенный production API, затем `cd frontend`, `npx playwright install chromium`, `npm run test:e2e`. Этот smoke-сценарий рассчитан на отдельный DATA_DIR с одной seeded исторической карьерой и без Live-снимков. Для реальной игровой проверки следуйте manual-game-validation, не Playwright.

Подробности: [архитектура](docs/architecture.md), [контракт данных](docs/data-contracts.md), [capability matrix](docs/capability-matrix.md), [отчёт проверок](docs/verification-report.md).

Проверка демо в Chromium: запустите демо, затем `npm --prefix frontend run test:demo` (предварительно `cd frontend && npx playwright install chromium`).
