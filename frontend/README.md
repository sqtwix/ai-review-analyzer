# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

## Демо-режим без backend

По умолчанию frontend обращается к backend. Если backend недоступен, пользователь видит ошибку, а готовый mock-отчет не создается.

Для отдельной демо-сборки можно явно включить локальный режим. В этом режиме авторизация, история отчетов, создание и редактирование отчетов работают через `localStorage`, а данные помечаются в интерфейсе как демонстрационные.

Для запуска dev-сервера:

```bash
VITE_ENABLE_DEMO_MODE=true npm run dev
```

После запуска откройте адрес, который покажет Vite, обычно `http://127.0.0.1:5173`.

Для production-сборки демо-режим должен включаться только отдельным явным флагом:

```bash
VITE_ENABLE_DEMO_MODE=true npm run build
```

Важно: `VITE_OFFLINE_MODE=true` в production больше не включает mock-режим. Старый флаг работает только в dev для обратной совместимости. Переменные `VITE_*` встраиваются Vite во время build.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.
