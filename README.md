# Анализ отзывов слушателей

Система принимает выгрузки анкет в Excel/CSV, рассчитывает количественные показатели и формирует качественный анализ через локальную GGUF-модель. В состав входят React/Nginx frontend, .NET API, FastAPI AI driver, PostgreSQL и опциональный llama.cpp server.

## Архитектура запуска

```text
Browser :APP_PORT
  -> frontend (Nginx, /api proxy)
     -> api-core (.NET, JWT, parsing, reports)
        -> postgres (users and reports; named volume)
        -> ai-driver (FastAPI analysis pipeline)
           -> qwen-local (llama.cpp; local-ai profile)
           -> DeepSeek / SberGPT endpoints (API-only optional providers)
```

Frontend публикуется на `APP_PORT` (по умолчанию `80`). Остальные порты доступны только внутри Compose network. `api-core` ждёт healthy PostgreSQL и AI driver; frontend ждёт healthy API. Локальная модель находится в отдельном profile, поэтому базовое приложение и cloud API-flow могут стартовать без GGUF.

Текущий пользовательский интерфейс выбирает только `Qwen Local`. DeepSeek и SberGPT реализованы в backend, но кнопки UI отключены; эти провайдеры нельзя считать проверенным пользовательским flow.

## Требования

- Docker Engine с Docker Compose v2 (`docker compose`) или Compose v1.29+ (`docker-compose`)
- Linux/macOS: Bash, OpenSSL, curl и `sha256sum` либо `shasum`
- Windows 10/11: Docker Desktop и Windows PowerShell 5.1+
- Для локальной модели: не менее 8 ГБ RAM и около 4 ГБ свободного места на модель, образы и рабочий запас
- Для первой установки: сеть для Docker images и GGUF; повторный offline-запуск возможен только при уже закэшированных образах и модели

ARM64 и x86_64 поддерживаются при наличии соответствующих multi-platform Docker images. GPU acceleration в текущем Compose не настроена; llama.cpp работает с настройками образа по умолчанию.

## Полный локальный запуск

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

Скрипт при первой установке создаёт `.env` из `env_example.txt`, генерирует `DB_PASSWORD` и `JWT_SECRET`, скачивает модель во временный `.part`-файл, проверяет SHA-256 и только затем атомарно переименовывает файл. После этого Compose собирает и запускает полный stack с profile `local-ai`.

Повторный запуск не меняет существующий `.env`, модель или named volumes. Существующая модель каждый раз проверяется по SHA-256. `compose down`, `down -v` и очистка Docker images скриптами не выполняются. Контейнеры, оставшиеся от удалённых сервисов этого Compose project, удаляются как orphans; их named volumes сохраняются. При переходе на `--cloud` скрипт дополнительно останавливает только уже запущенный `qwen-local`, потому что профильный сервис не считается Compose orphan; файл модели остаётся на месте.

Приложение: `http://localhost/` либо порт из `APP_PORT`.

## Базовый или cloud-запуск

Без локальной модели:

```bash
./deploy.sh --cloud
```

```bat
deploy.bat cloud
```

Этот режим не скачивает GGUF и не запускает `qwen-local`. Для backend-вызовов DeepSeek или SberGPT задайте соответствующий API key в `.env`. Без локальной модели и без cloud key базовое приложение стартует, `/health` остаётся healthy, а `/ready` AI driver возвращает `503 not_ready`. Анкеты без содержательного свободного текста завершаются обычным количественным отчётом; при необходимости AI driver ждёт модель до `AI_MODEL_READINESS_TIMEOUT_SECONDS`, а затем возвращает детерминированный количественный fallback-отчёт. В fallback качественные темы, тональность, цитаты и рекомендации помечаются как несформированные, а не подменяются данными модели.

## Ручной Compose-flow

Создайте `.env` и обязательно заполните секреты:

```bash
cp env_example.txt .env
# DB_PASSWORD: случайное непустое значение
# JWT_SECRET: случайное значение не короче 32 байт
```

Полный локальный stack с уже размещённой моделью:

```bash
docker compose --profile local-ai config --quiet
docker compose --profile local-ai up --build -d --remove-orphans --wait
```

Базовый stack без локальной модели:

```bash
docker compose config --quiet
docker compose up --build -d --remove-orphans --wait
```

Для standalone Compose замените `docker compose` на `docker-compose`. Если версия не поддерживает `--wait`, уберите этот флаг и проверьте `docker-compose ps` вручную.

Отдельные сервисы:

```bash
docker compose up -d postgres
docker compose up --build -d ai-driver
docker compose --profile local-ai up -d qwen-local
docker compose up --build -d api-core
docker compose up --build -d frontend
```

Compose автоматически запускает объявленные зависимости выбранного сервиса. `qwen-local` запускается отдельно, потому что он не нужен cloud-flow.

## Обновление конфигурации

1. Сравните существующий `.env` с `env_example.txt`; deploy-скрипты намеренно не дописывают и не меняют пользовательский файл.
2. Измените нужные значения в `.env`.
3. Повторно запустите тот же deploy command. Compose пересоздаст только сервисы с изменившейся конфигурацией или image.

Пара `QWEN_GGUF_MODEL_URL`/`QWEN_GGUF_MODEL_SHA256` обязательна для нестандартного имени модели. Filename должен быть обычным именем без пути. Рекомендуемая модель:

```text
Qwen3-1.7B-Q4_K_M.gguf
SHA-256 d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5
```

Источник закреплён на commit `daeb8e2d528a760970442092f6bf1e55c3b659eb`: [ggml-org/Qwen3-1.7B-GGUF](https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF/blob/daeb8e2d528a760970442092f6bf1e55c3b659eb/Qwen3-1.7B-Q4_K_M.gguf).

## Health и диагностика

```bash
curl -fsS http://localhost:${APP_PORT:-80}/healthz
docker compose ps
docker compose exec ai-driver python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
docker compose exec ai-driver python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/ready').read().decode())"
```

- frontend `/healthz`: Nginx liveness
- api-core `/health`: API + PostgreSQL connectivity
- ai-driver `/health`: process liveness
- ai-driver `/ready`: доступный local provider или наличие ключа cloud provider; доступность облачного API и валидность ключа этот маршрут не проверяет
- qwen-local `/health`: llama.cpp model readiness

Остановка без удаления данных:

```bash
docker compose --profile local-ai stop
```

`docker compose down -v` удаляет named volumes с базой и выполнять его следует только при намеренном полном сбросе данных.

## Проверки без Docker

```bash
dotnet build api-core/ApiCore/ApiCore.sln -c Release
cd ai-driver && python -m unittest discover -s tests -v
cd frontend && npm ci && npm test && npm run lint && npm run build
```

## Production-ограничения

Конфигурация ориентирована на повторяемый single-host deployment и сохранение данных, но сама по себе не доказывает production readiness. Перед внешней публикацией остаются обязательными TLS/reverse proxy, централизованное управление секретами, backup/restore PostgreSQL, наблюдаемость, ограничения ресурсов, закрепление Docker images по digest, миграции БД вместо runtime DDL и нагрузочные/аварийные испытания на целевой ОС и hardware.
