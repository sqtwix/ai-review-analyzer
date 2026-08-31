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

## Рекомендуемый запуск

Требуется Docker Engine с Docker Compose v2 (`docker compose`) или standalone Compose 1.29+ (`docker-compose`). Linux/macOS также требуют Bash и OpenSSL. Для режима `--local-ai` нужны `curl` и `sha256sum` либо `shasum`. На Windows нужны Docker Desktop и Windows PowerShell 5.1+.

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

Базовый manual flow должен оставлять профиль отключённым:

```bash
LOCAL_AI_ENABLED=false docker compose up --build -d
```

Ручные Compose-команды не создают `.env`, не генерируют секреты и не скачивают модель. Перед ними подготовьте валидный `.env`; для profile `local-ai` заранее разместите указанный GGUF в `models/`. Для обычной установки используйте deploy entrypoint выше.

## Конфигурация

`env_example.txt` содержит публичные defaults. `DB_PASSWORD`, `JWT_SECRET`, `DEEPSEEK_API_KEY` и `SBERGPT_API_KEY` являются секретными значениями: существующий `.env` ими не дополняется и не меняется. Если обязательные `DB_PASSWORD` или `JWT_SECRET` пусты, либо значения boolean/port/checksum некорректны, deploy завершается до Compose build/up с понятной ошибкой.

При обновлении репозитория повторно запустите тот же deploy entrypoint. Он безопасно добавит в существующий `.env` новые non-secret параметры из шаблона, не меняя уже заданные значения. Ручное копирование `env_example.txt` поверх `.env` не требуется.

`LOCAL_AI_ENABLED=false` в `.env` является безопасным значением по умолчанию. `--local-ai` временно передаёт `true` только в Compose process и не меняет пользовательский файл.

## Health и диагностика

Deploy проверяет Compose config до build/up и после запуска ждёт healthy `postgres`, `ai-driver`, `api-core` и `frontend`; в local-AI режиме дополнительно ждёт `qwen-local`. Это одинаково работает с Compose, поддерживающим `--wait`, и без него. При неуспехе скрипт выводит `compose ps` и последние логи обязательных сервисов.

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

Контейнеры по-прежнему используют стандартные образы и не заявляют полноценных non-root/read-only гарантий: API временно принимает файлы, PostgreSQL требует writeable database storage, а Nginx/llama.cpp требуют дополнительной адаптации runtime paths. Для внешней публикации остаются обязательными TLS/reverse proxy, backup/restore PostgreSQL, управление секретами, закрепление image digests, миграции БД и нагрузочные проверки на целевой инфраструктуре.
