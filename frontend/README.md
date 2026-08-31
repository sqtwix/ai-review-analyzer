# Frontend

React/Vite-интерфейс системы анализа отзывов. Production image собирается многостадийным `frontend/Dockerfile` и отдаётся Nginx; запросы `/api/` проксируются в `api-core`.

Основной production-запуск выполняется из корня репозитория через `./deploy.sh` или `deploy.bat`. Отдельно запускать frontend для production не требуется.

## Локальная разработка

```bash
npm ci
npm run dev -- --host 127.0.0.1
```

В обычном dev-режиме frontend ожидает API на `http://127.0.0.1:5000/api/v1`. Это подходит для локально запущенного `.NET` backend. Чтобы использовать backend из уже поднятого Compose-стека, направьте Vite через опубликованный Nginx:

```bash
VITE_API_URL=http://localhost/api/v1 npm run dev -- --host 127.0.0.1
```

При недоступном backend интерфейс показывает ошибку и не создаёт mock-отчёт.

## Build flags

- `VITE_ENABLE_DEMO_MODE=false` — production-режим с реальным API; значение по умолчанию.
- `VITE_ENABLE_DEMO_MODE=true` — изолированный demo-flow через `localStorage`, только для локальной проверки интерфейса.
- `VITE_OFFLINE_MODE` оставлен для обратной совместимости и не должен использоваться для production mock-сборки.

Demo-режим включается только явно:

```bash
VITE_ENABLE_DEMO_MODE=true npm run dev -- --host 127.0.0.1
```

В production Compose оба frontend-флага по умолчанию равны `false` и берутся из `.env` на этапе Docker build.

## Проверки

```bash
npm test
npm run lint
npm run build
```

Production build может вывести предупреждение Vite о крупных чанках библиотек экспорта. Это предупреждение не означает ошибку сборки.

Полный runtime и deployment flow описан в корневом [README](../README.md). Подробный frontend regression checklist находится в [VERIFICATION.md](./VERIFICATION.md).
