# Анализ отзывов слушателей

Система принимает Excel/CSV-выгрузки анкет, рассчитывает количественные показатели и, когда доступна модель, формирует качественный анализ. В состав входят React/Nginx frontend, .NET API, FastAPI AI driver, PostgreSQL и опциональный llama.cpp server.

```text
Browser :APP_PORT
  -> frontend (Nginx, /api proxy)
     -> api-core (.NET, JWT, parsing, reports)
        -> postgres (users and reports; named volume)
        -> ai-driver (analysis and deterministic fallback)
           -> qwen-local (optional local-ai Compose profile)
```

Frontend публикуется на `APP_PORT` (по умолчанию `80`). PostgreSQL, API, AI driver и модель доступны только внутри Compose network.

За один анализ можно загрузить до 20 файлов `.csv`, `.xlsx`, `.xls` или `.zip` суммарным размером до 50 МБ. Для ZIP дополнительно действуют лимиты 1000 элементов и 100 МБ распакованных поддерживаемых таблиц.

Для защиты от подбора паролей auth API ограничен 20 запросами в минуту на IP, а запуск анализа — 10 загрузками в минуту на пользователя.

## Рекомендуемый запуск

Требуется запущенный Docker Engine с Docker Compose v2 (`docker compose`) или standalone Compose 1.29+ (`docker-compose`). Linux/macOS также требуют Bash и OpenSSL. Для режима `--local-ai` нужны `curl` и `sha256sum` либо `shasum`. На Windows нужны Docker Desktop и Windows PowerShell 5.1+.

Linux/macOS:

```bash
git clone https://github.com/sqtwix/ai-review-analyzer.git
cd ai-review-analyzer
./deploy.sh
```

Windows CMD или PowerShell:

```bat
git clone https://github.com/sqtwix/ai-review-analyzer.git
cd ai-review-analyzer
deploy.bat
```

Это единственный рекомендуемый happy path. Он запускает базовую платформу без локальной модели, не скачивает GGUF и не требует API key. При первой установке скрипт создаёт постоянный `.env` из `env_example.txt` и генерирует `DB_PASSWORD` и `JWT_SECRET`, не выводя их. На следующих запусках скрипт сохраняет существующие значения и секреты, добавляя только отсутствующие non-secret defaults из шаблона.

По умолчанию приложение открывается на [http://localhost:80/](http://localhost:80/). Если в `.env` изменён `APP_PORT`, используйте `http://localhost:<APP_PORT>/`.

Без доступного провайдера приложение остаётся готовым к работе. Анализ создаёт документированный детерминированный количественный отчёт; качественные темы, тональность, цитаты и рекомендации в нём явно отмечены как несформированные. Это не ошибка очереди и не подмена данных результатом модели.

## Локальная модель

Локальная модель выключена по умолчанию. Её запуск требует явного opt-in `--local-ai`: скрипт передаёт `LOCAL_AI_ENABLED=true` и активирует Compose profile `local-ai` только на этот запуск.

```bash
./deploy.sh --local-ai
```

```bat
deploy.bat --local-ai
```

В этом режиме требуется около 4 ГБ свободного места для модели и не менее 8 ГБ RAM. Скрипт проверяет имя, URL и SHA-256, скачивает отсутствующий GGUF во временный `.part`-файл, проверяет checksum и только затем переименовывает его. Существующий файл модели проверяется, но не перезаписывается.

Обратный переход выполняется обычным базовым запуском. Он останавливает только устаревший `qwen-local`; `.env`, файл модели, named volumes, базу и отчёты сохраняет. Скрипты не вызывают `compose down`, `down -v`, удаление models или очистку Docker images.

Для ручного Compose вызова model flow также требует обоих условий:

```bash
LOCAL_AI_ENABLED=true docker compose --profile local-ai up --build -d
```

Базовый manual flow должен оставлять профиль отключённым. Если ранее запускался `local-ai`, сначала остановите его контейнер: Compose не останавливает уже запущенный профиль автоматически.

```bash
LOCAL_AI_ENABLED=true docker compose --profile local-ai stop qwen-local
LOCAL_AI_ENABLED=false docker compose up --build -d
```

Ручные Compose-команды не создают `.env`, не генерируют секреты и не скачивают модель. Перед ними подготовьте валидный `.env`; для profile `local-ai` заранее разместите указанный GGUF в `models/`. Для обычной установки используйте deploy entrypoint выше.

## Конфигурация

`env_example.txt` содержит публичные defaults. `DB_PASSWORD`, `JWT_SECRET`, `DEEPSEEK_API_KEY` и `SBERGPT_API_KEY` являются секретными значениями: существующий `.env` ими не дополняется и не меняется. Если обязательные `DB_PASSWORD` или `JWT_SECRET` пусты, либо значения boolean/port/checksum некорректны, deploy завершается до Compose build/up с понятной ошибкой.

При обновлении репозитория повторно запустите тот же deploy entrypoint. Он безопасно добавит в существующий `.env` новые non-secret параметры из шаблона, не меняя уже заданные значения. Ручное копирование `env_example.txt` поверх `.env` не требуется.

`LOCAL_AI_ENABLED=false` в `.env` является безопасным значением по умолчанию. `--local-ai` временно передаёт `true` только в Compose process и не меняет пользовательский файл.

## Health и диагностика

Deploy проверяет Compose config до build/up и после запуска ждёт healthy `postgres`, `ai-driver`, `api-core` и `frontend`; в local-AI режиме дополнительно ждёт `qwen-local`. Это одинаково работает с Compose, поддерживающим `--wait`, и без него. При неуспехе скрипт выводит `compose ps` и последние логи обязательных сервисов. Docker logs ограничены пятью файлами по 10 МБ на сервис.

```bash
curl -fsS http://localhost:80/healthz
docker compose ps
docker compose exec ai-driver python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/ready').read().decode())"
```

Если `APP_PORT` изменён, замените `80` в первом запросе его фактическим значением.

- frontend `/healthz`: liveness Nginx
- api-core `/health`: API и PostgreSQL connectivity
- ai-driver `/health`: liveness процесса
- ai-driver `/ready`: readiness платформы; `model_available` отдельно показывает доступность провайдера
- `/api/v1/analysis/availability`: тот же статус для авторизованного UI
- qwen-local `/health`: readiness локальной модели

## Проверки разработки

```bash
bash -n deploy.sh
bash ai-driver/tests/test_deploy_env.sh
docker compose config --quiet
docker compose --profile local-ai config --quiet
dotnet build api-core/ApiCore/ApiCore.sln -c Release
cd ai-driver && python -m unittest discover -s tests -v
cd frontend && npm ci && npm test && npm run lint && npm run build
```

Для Python-тестов на host сначала установите `ai-driver/requirements.txt` в виртуальное окружение Python 3.13. После production build тот же набор можно прогнать без host-установки:

```bash
docker compose exec ai-driver python -m unittest discover -s tests -v
```

Frontend-проверки требуют Node.js 20+ и `npm`.

После запуска всего стека end-to-end smoke без внешних Python-зависимостей проверяет защиту API, регистрацию/вход и негативные auth-кейсы, валидацию загрузок, анализ реального файла, историю, переименование, архив и межпользовательскую изоляцию. Он создаёт технических smoke-пользователей и отчёт в текущей БД:

```bash
python3 scripts/production_smoke.py
python3 scripts/production_smoke.py --require-local-ai --sample example_files/example_minimal.csv
```

Порядок обновления, backup, пробного и боевого restore описан в [OPERATIONS.md](./OPERATIONS.md).

Workflow `.github/workflows/ci.yml` повторяет обязательные build/test/lint/audit/Compose-проверки на каждом pull request и push в `main`.

API и AI driver запускают приложение непривилегированными пользователями, с read-only root filesystem и `no-new-privileges`; временные загрузки API изолированы в отдельном служебном volume и очищаются при старте. Для остальных контейнеров не заявляются полные non-root/read-only гарантии: PostgreSQL требует writeable database storage, а Nginx/llama.cpp требуют дополнительной адаптации runtime paths. Для внешней публикации остаются обязательными TLS/reverse proxy, централизованное управление секретами, закрепление image digests, миграции БД, автоматические off-host backups и нагрузочные проверки на целевой инфраструктуре.
