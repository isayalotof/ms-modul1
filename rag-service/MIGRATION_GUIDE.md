# Migration Guide

## Переименование metadata -> meta_data

SQLAlchemy резервирует имя `metadata`, поэтому поле было переименовано в `meta_data`.

### Если у вас уже запущена база данных с данными

Выполните миграцию:

```bash
# Вариант 1: Через docker-compose
docker-compose exec -T postgres psql -U raguser -d ragdb < migrations/001_rename_metadata_to_meta_data.sql

# Вариант 2: Если используете docker compose (без дефиса)
docker compose exec -T postgres psql -U raguser -d ragdb < migrations/001_rename_metadata_to_meta_data.sql

# Вариант 3: Если работаете напрямую с psql
psql -U raguser -d ragdb -h localhost < migrations/001_rename_metadata_to_meta_data.sql
```

### Если начинаете с нуля

Просто пересоздайте базу данных:

```bash
# Остановить и удалить контейнеры с volumes
docker-compose down -v

# Запустить заново (применится новая схема из init.sql)
docker-compose up -d
```

## Проверка миграции

После применения миграции проверьте структуру таблиц:

```bash
docker-compose exec postgres psql -U raguser -d ragdb -c "\d documents"
docker-compose exec postgres psql -U raguser -d ragdb -c "\d document_chunks"
```

Вы должны увидеть колонку `meta_data` вместо `metadata`.

## Перезапуск сервиса

После применения миграции перезапустите сервис:

```bash
docker-compose restart rag-service
```
