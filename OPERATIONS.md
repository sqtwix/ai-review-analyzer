# Эксплуатация и восстановление

Этот runbook дополняет [README](./README.md). Команды ниже приведены для Compose v2; при standalone Compose замените `docker compose` на `docker-compose`.

## Обновление

```bash
git pull --ff-only origin main
./deploy.sh
python3 scripts/production_smoke.py
```

Для установки с локальной моделью используйте `./deploy.sh --local-ai`, а затем smoke с минимальным файлом:

```bash
python3 scripts/production_smoke.py --require-local-ai --sample example_files/example_minimal.csv
```

Smoke создаёт технического пользователя и отчёт в текущей БД. На боевой среде запускайте его в согласованное окно проверки.

## Backup PostgreSQL

Создавайте backup перед каждым обновлением и по регламенту заказчика. Custom-format сжат и подходит для `pg_restore`:

```bash
mkdir -p backups
umask 077
docker compose exec -T postgres sh -c 'pg_dump --format=custom --no-owner --no-acl --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' > "backups/ai-review-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

Проверьте, что файл не пуст и его каталог читается:

```bash
test -s backups/ai-review-YYYYMMDDTHHMMSSZ.dump
docker compose exec -T postgres pg_restore --list < backups/ai-review-YYYYMMDDTHHMMSSZ.dump
```

Храните копии вне Docker host и отдельно резервируйте `.env` в защищённом хранилище секретов. Не добавляйте `.env` и dump в Git.

## Пробное восстановление

Эта процедура не трогает рабочую БД и должна регулярно выполняться на копии:

```bash
docker compose exec -T postgres sh -c 'dropdb --if-exists --username "$POSTGRES_USER" ai_review_restore_check'
docker compose exec -T postgres sh -c 'createdb --username "$POSTGRES_USER" --owner "$POSTGRES_USER" ai_review_restore_check'
docker compose exec -T postgres sh -c 'pg_restore --exit-on-error --no-owner --no-acl --username "$POSTGRES_USER" --dbname ai_review_restore_check' < backups/ai-review-YYYYMMDDTHHMMSSZ.dump
docker compose exec -T postgres sh -c 'psql --username "$POSTGRES_USER" --dbname ai_review_restore_check --command "SELECT count(*) FROM users; SELECT count(*) FROM analysis_reports;"'
docker compose exec -T postgres sh -c 'dropdb --username "$POSTGRES_USER" ai_review_restore_check'
```

## Боевое восстановление

Боевое восстановление пересоздаёт рабочую БД и на время останавливает UI/API. Его выполняет администр только после пробного restore и проверки контрольных количеств. Перед началом создайте ещё один свежий backup.

```bash
docker compose stop frontend api-core
docker compose exec -T postgres sh -c 'dropdb --username "$POSTGRES_USER" "$POSTGRES_DB" && createdb --username "$POSTGRES_USER" --owner "$POSTGRES_USER" "$POSTGRES_DB"'
docker compose exec -T postgres sh -c 'pg_restore --exit-on-error --no-owner --no-acl --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' < backups/ai-review-YYYYMMDDTHHMMSSZ.dump
docker compose start api-core frontend
python3 scripts/production_smoke.py
```

Если restore завершился ошибкой, не запускайте UI/API до разбора причины и повторного восстановления из проверенной копии.

## Наблюдение и инциденты

```bash
docker compose ps
docker compose logs --tail=200 frontend api-core ai-driver postgres
curl -fsS http://localhost/healthz
```

Логи каждого сервиса ротируются: пять файлов по 10 МБ. Для внешней публикации обязательны TLS/reverse proxy, мониторинг места на диске и автоматические off-host backups.
