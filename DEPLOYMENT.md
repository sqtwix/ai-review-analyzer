# Универсальное руководство по полному развертыванию AI Review Analyzer

Данное руководство содержит исчерпывающие пошаговые инструкции по развертыванию системы **AI Review Analyzer** на операционных системах **Linux**, **macOS** и **Windows** (включая запуск с локальной языковой моделью через опцию `--local-ai`).

---

## 1. Архитектура системы

Система построена на микросервисной архитектуре и изолирована внутри Docker-сети:

```mermaid
graph TD
    User["Пользователь (Браузер)"] -->|:APP_PORT (по умолч. 80)| Frontend["frontend (Nginx + React 19)"]
    Frontend -->|/api proxy| ApiCore["api-core (.NET 8 Web API)"]
    ApiCore -->|TCP :5432| Postgres[("postgres (PostgreSQL 15)")]
    ApiCore -->|HTTP :8000| AiDriver["ai-driver (FastAPI / Python 3.13)"]
    
    subgraph "AI Providers"
        AiDriver -.->|HTTP :8080 (Profile: local-ai)| QwenLocal["qwen-local (llama.cpp server)"]
        AiDriver -.->|HTTPS| DeepSeek["DeepSeek API (опционально)"]
        AiDriver -.->|HTTPS| GigaChat["GigaChat API (опционально)"]
        AiDriver -.->|Fallback| Programmatic["Детерминированный расчет"]
    end
```

### Сервисы:
- **`frontend`** — SPA на React 19 / Vite под управлением Nginx (Alpine).
- **`api-core`** — .NET 8 Web API: аутентификация (JWT), валидация и парсинг файлов (`.csv`, `.xlsx`, `.xls`, `.zip`), управление отчетами.
- **`postgres`** — база данных PostgreSQL 15 с сохранением данных в persistent Docker volume `postgres_data`.
- **`ai-driver`** — сервис качественного анализа на Python 3.13 / FastAPI.
- **`qwen-local`** *(опциональный профиль `local-ai`)* — сервер `llama.cpp` с моделью `Qwen3-1.7B-Q4_K_M.gguf`.

---

## 2. Системные требования

### Минимальные аппаратные требования:
| Режим развертывания | CPU | RAM | Свободный диск |
| :--- | :--- | :--- | :--- |
| **Базовый (Base)** (без локальной LLM) | 2 ядра | 4 ГБ | 6 ГБ |
| **С локальной моделью (`--local-ai`)** | 4 ядра | 8–10 ГБ | 12 ГБ (для образов и GGUF-модели ~1.2 ГБ) |

### Программное обеспечение:
- **Docker Engine** 20.10+ и **Docker Compose v2** (`docker compose`) либо Docker Desktop (Windows / macOS).
- **Linux / macOS**: Bash, `curl`, `openssl`, утилиты `sha256sum` (или `shasum`).
- **Windows**: Docker Desktop с бэкендом WSL2, Windows PowerShell 5.1+ или Git Bash.

---

## 3. Подготовка репозитория

Клонируйте проект и перейдите в рабочую директорию:

```bash
git clone https://github.com/sqtwix/ai-review-analyzer.git
cd ai-review-analyzer
```

> [!TIP]
> **Для пользователей Windows**: Репозиторий уже снабжен файлом `.gitattributes`, который сохраняет окончания строк `LF` в `.sh`-скриптах. Если вы клонировали проект ранее, убедитесь, что файлы скриптов не содержат Windows-окончаний `CRLF`.

---

## 4. Сценарии развертывания

### Сценарий А: Полное развертывание с локальной нейросетью (`--local-ai`) [РЕКОМЕНДУЕТСЯ]

В этом режиме система разворачивает полный автономный стек: не требуется внешних API-ключей, баланса на аккаунтах и доступа в интернет (после первоначального скачивания весов модели).

#### 1. Запуск автоматического скрипта:

- **Linux / macOS / WSL / Git Bash:**
  ```bash
  chmod +x deploy.sh
  ./deploy.sh --local-ai
  ```

- **Windows CMD / PowerShell:**
  ```cmd
  deploy.bat --local-ai
  ```

#### Что делает скрипт автоматически:
1. Создает защищенный файл `.env` из `env_example.txt` и генерирует криптостойкие секреты `DB_PASSWORD` и `JWT_SECRET`.
2. Проверяет наличие директории `models/` и файла модели `Qwen3-1.7B-Q4_K_M.gguf`.
3. Скачивает модель через `curl` во временный файл `.part`, валидирует контрольную сумму SHA-256 (`d2387ca2...`) и переименовывает в постоянный файл.
4. Проверяет корректность конфигурации Compose с профилем `local-ai`.
5. Собирает образы (`frontend`, `api-core`, `ai-driver`) и запускает 5 контейнеров: `postgres`, `ai-driver`, `qwen-local`, `api-core`, `frontend`.
6. Ожидает успешного прохождения всех проверок работоспособности (Healthcheck).

---

### Сценарий Б: Базовое развертывание (без локальной LLM)

Если ресурсы сервера ограничены (например, менее 8 ГБ RAM) или качественный анализ не требуется:

- **Linux / macOS:**
  ```bash
  ./deploy.sh
  ```

- **Windows:**
  ```cmd
  deploy.bat
  ```

В этом режиме модель не скачивается, сервис `qwen-local` не запускается. Анализ отзывов выполняет детерминированный количественный расчет (NPS, CSAT, тональность по оценкам, статистика по лекторам), а текстовые выводы нейросети корректно помечаются как несформированные.

---

### Сценарий В: Развертывание с облачными моделями (DeepSeek / GigaChat)

Если вы хотите использовать мощные облачные модели вместо локальной:

1. Откройте файл `.env` и впишите соответствующий ключ:
   ```dotenv
   # Для DeepSeek:
   DEEPSEEK_API_KEY=sk-your-deepseek-key
   DEEPSEEK_MODEL=deepseek-chat

   # ИЛИ для GigaChat (Сбер):
   SBERGPT_API_KEY=your-gigachat-auth-data
   SBERGPT_MODEL=GigaChat-Pro
   ```
2. Примените конфигурацию:
   ```bash
   docker compose up -d
   ```

---

## 5. Ручной запуск через Docker Compose (для CI/CD и серверов)

Если развертывание происходит без использования bash/bat скриптов:

1. Создайте `.env` на основе `env_example.txt`:
   ```bash
   cp env_example.txt .env
   # Обязательно сгенерируйте и впишите DB_PASSWORD и JWT_SECRET (>= 32 символов)
   ```

2. Для режима **локальной модели**:
   - Скачайте модель в директорию `models/`:
     ```bash
     mkdir -p models
     curl -L -o models/Qwen3-1.7B-Q4_K_M.gguf "https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF/resolve/daeb8e2d528a760970442092f6bf1e55c3b659eb/Qwen3-1.7B-Q4_K_M.gguf"
     ```
   - Запустите стек с профилем `local-ai`:
     ```bash
     LOCAL_AI_ENABLED=true docker compose --profile local-ai up --build -d
     ```

3. Для **базового режима**:
   ```bash
   LOCAL_AI_ENABLED=false docker compose up --build -d
   ```

---

## 6. Проверка работоспособности и Healthcheck

После завершения развертывания выполните диагностические команды:

### 1. Статус контейнеров
```bash
docker compose ps
```
Все задействованные контейнеры должны иметь статус `Up (healthy)`.

### 2. Проверка веб-интерфейса (Liveness Nginx)
```bash
curl -fsS http://localhost/healthz
# Ожидаемый ответ: healthy
```

### 3. Проверка готовности AI-драйвера и доступности моделей
```bash
docker compose exec ai-driver python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/ready').read().decode())"
```
При развертывании с `--local-ai` поле `model_available` должно возвращать `true`:
```json
{"status":"ready","model_available":true,"providers":{"qwen_local":{"enabled":true,"available":true}}}
```

### 4. Автоматизированный Smoke-тест
Проект содержит встроенный сквозной тест `production_smoke.py`, проверяющий аутентификацию, безопасность, обработку файлов и изоляцию данных:

- Для базового режима:
  ```bash
  python3 scripts/production_smoke.py
  ```
- Для режима `--local-ai`:
  ```bash
  python3 scripts/production_smoke.py --require-local-ai --sample example_files/example_minimal.csv
  ```

---

## 7. Работа с системой

1. Откройте в браузере: **`http://localhost/`** (или `http://<IP_СЕРВЕРА>:<APP_PORT>/`).
2. **Первый вход**: Зарегистрируйте аккаунт через форму регистрации (первый зарегистрированный пользователь может использоваться как основной).
3. **Загрузка данных**:
   - Поддерживаются форматы: `.csv`, `.xlsx`, `.xls`, `.zip` (до 20 файлов суммарно до 50 МБ).
   - Примеры файлов для тестирования находятся в каталоге `example_files/` (`example_minimal.csv` и др.).
4. **Результаты**:
   - Сводные таблицы и интерактивные графики распределения оценок.
   - Выделение сильных сторон и зон роста.
   - Экспорт готового аналитического отчета в форматах **PDF**, **DOCX**, **Excel**.

---

## 8. Управление и обслуживание

### Остановка и запуск:
```bash
# Временная остановка сервисов (без потери данных):
docker compose stop

# Запуск ранее остановленных контейнеров:
docker compose start

# Перезапуск стека:
docker compose restart
```

### Переключение между режимами:
- **Переход из `--local-ai` в базовый режим**:
  Достаточно запустить `./deploy.sh` (или `deploy.bat`). Скрипт корректно остановит контейнер `qwen-local`, сохранив файл модели на диске и данные в БД.
- **Переход из базового режима в `--local-ai`**:
  Запустите `./deploy.sh --local-ai` (или `deploy.bat --local-ai`).

### Просмотр журналов (логов):
```bash
# Все логи:
docker compose logs -f --tail=100

# Логи конкретного сервиса:
docker compose logs -f ai-driver
docker compose logs -f api-core
docker compose logs -f qwen-local
```

### Создание резервной копии базы данных (Backup):
```bash
mkdir -p backups
docker compose exec -T postgres sh -c 'pg_dump --format=custom --no-owner --no-acl --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' > "backups/ai-review-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

---

## 9. Устранение возможных неполадок (Troubleshooting)

### Ошибка 1: `npm error ... Invalid: lock file's nanoid does not satisfy nanoid`
- **Причина**: Несоответствие между `package.json` и `package-lock.json` при сборке фронтенда.
- **Решение**: Выполнить синхронизацию зависимостей в директории `frontend/`:
  ```bash
  cd frontend && npm install --package-lock-only && cd ..
  docker compose build frontend
  ```

### Ошибка 2: `exec /usr/local/bin/api-entrypoint.sh: no such file or directory`
- **Причина**: Файл сохранен с Windows-переводами строк `CRLF` вместо Unix `LF`.
- **Решение**: Убедиться, что в репозитории присутствует файл `.gitattributes`, а в `Dockerfile` для `api-core` присутствует инструкция `RUN sed -i 's/\r$//' ...`.

### Ошибка 3: Порт 80 или 5432 уже занят другим приложением
- **Решение**: Измените внешний порт в файле `.env`:
  ```dotenv
  APP_PORT=8080
  DB_PORT=5433
  ```
  После этого приложение будет доступно на `http://localhost:8080/`.

### Ошибка 4: `qwen-local` падает или завершается по Out-Of-Memory (OOM)
- **Решение**: В Docker Desktop увеличьте лимит оперативной памяти (Settings -> Resources -> Memory: минимум 8-10 ГБ).
  Также можно уменьшить размер контекста в `.env`:
  ```dotenv
  QWEN_CONTEXT_SIZE=2048
  QWEN_BATCH_SIZE=128
  ```
