# RAG Service

REST API микросервис для семантического поиска по документам с использованием векторной базы данных PostgreSQL + pgvector.

## Возможности

- 📄 **Загрузка и индексация документов** (PDF, DOCX, TXT, MD)
- 🔍 **Семантический поиск** по векторным эмбеддингам
- 🤖 **RAG (Retrieval Augmented Generation)** с Claude API
- 📊 **Статистика и аналитика** использования
- 🚀 **Streaming API** для реал-тайм ответов
- 🔒 **Изоляция данных** по пользователям
- 🐳 **Docker-ready** с полной контейнеризацией

## Технологический стек

- **Python 3.11+**
- **FastAPI** - REST API фреймворк
- **PostgreSQL 15+** с **pgvector** - векторная база данных
- **SQLAlchemy 2.0** - async ORM
- **Sentence Transformers** - генерация эмбеддингов
- **Anthropic Claude** - генерация ответов
- **Docker & Docker Compose** - контейнеризация

## Быстрый старт

### Требования

- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)
- Anthropic API Key

### Запуск с Docker

1. Клонируйте репозиторий:
```bash
cd rag-service
```

2. Создайте файл `.env`:
```bash
cp .env.example .env
```

3. Отредактируйте `.env` и укажите ваш `ANTHROPIC_API_KEY`

4. Запустите сервисы:
```bash
docker-compose up -d
```

5. Проверьте работоспособность:
```bash
curl http://localhost:8000/health
```

API документация доступна по адресу: http://localhost:8000/docs

### Локальная разработка

1. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

2. Установите зависимости:
```bash
pip install -r pyproject.toml
```

3. Запустите PostgreSQL с pgvector:
```bash
docker run -d \
  --name postgres-pgvector \
  -e POSTGRES_USER=raguser \
  -e POSTGRES_PASSWORD=ragpassword \
  -e POSTGRES_DB=ragdb \
  -p 5432:5432 \
  pgvector/pgvector:pg15
```

4. Примените миграции:
```bash
psql -U raguser -d ragdb -h localhost -f migrations/init.sql
```

5. Запустите сервис:
```bash
uvicorn app.main:app --reload
```

## API Endpoints

### Документы

- `POST /api/v1/rag/documents/upload` - Загрузка документа
- `POST /api/v1/rag/documents/batch-upload` - Пакетная загрузка
- `GET /api/v1/rag/documents` - Список документов
- `GET /api/v1/rag/documents/{id}` - Информация о документе
- `DELETE /api/v1/rag/documents/{id}` - Удаление документа
- `POST /api/v1/rag/documents/{id}/reindex` - Переиндексация

### Поиск и RAG

- `POST /api/v1/rag/search` - Семантический поиск
- `POST /api/v1/rag/query` - RAG запрос с ответом
- `POST /api/v1/rag/query/stream` - RAG запрос со streaming

### Аналитика

- `GET /api/v1/rag/statistics` - Статистика использования
- `GET /health` - Health check

## Примеры использования

### Загрузка документа

```bash
curl -X POST "http://localhost:8000/api/v1/rag/documents/upload" \
  -F "file=@document.pdf" \
  -F "user_id=user_123" \
  -F 'metadata={"category": "technical"}'
```

### Семантический поиск

```bash
curl -X POST "http://localhost:8000/api/v1/rag/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Как использовать декораторы?",
    "user_id": "user_123",
    "top_k": 5
  }'
```

### RAG запрос

```bash
curl -X POST "http://localhost:8000/api/v1/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Объясни декораторы в Python",
    "user_id": "user_123",
    "context_size": 5
  }'
```

### Streaming RAG

```bash
curl -X POST "http://localhost:8000/api/v1/rag/query/stream" \
  -H "Content-Type: application/json" \
  -N \
  -d '{
    "query": "Объясни декораторы",
    "user_id": "user_123"
  }'
```

## Конфигурация

Все настройки задаются через переменные окружения в файле `.env`:

- `ANTHROPIC_API_KEY` - API ключ Anthropic (обязательно)
- `DATABASE_URL` - URL подключения к PostgreSQL
- `EMBEDDING_MODEL` - модель для эмбеддингов
- `CHUNK_SIZE` - размер чанков при разбиении документов
- `MAX_FILE_SIZE` - максимальный размер файла
- И другие (см. `.env.example`)

## Архитектура

```
┌─────────────────────────────────┐
│  RAG Service (FastAPI)          │
│  ┌──────────────────────────┐  │
│  │   API Layer              │  │
│  └──────────────────────────┘  │
│  ┌──────────────────────────┐  │
│  │   Services Layer         │  │
│  │  - Document Processor    │  │
│  │  - Embedding Service     │  │
│  │  - Vector Store          │  │
│  │  - RAG Pipeline          │  │
│  └──────────────────────────┘  │
│  ┌──────────────────────────┐  │
│  │   Database Layer         │  │
│  │  - SQLAlchemy Models     │  │
│  └──────────────────────────┘  │
└─────────────────────────────────┘
         ↓              ↓
   PostgreSQL       Anthropic API
   + pgvector       (Claude)
```

## Тестирование

Запуск тестов:

```bash
pytest tests/
```

С покрытием:

```bash
pytest --cov=app tests/
```

## Мониторинг

Health check endpoint предоставляет информацию о состоянии сервиса:

```bash
curl http://localhost:8000/health
```

## Безопасность

- ✅ Валидация типов и размеров файлов
- ✅ Изоляция данных по пользователям
- ✅ SQL injection защита (SQLAlchemy)
- ✅ Rate limiting (опционально)
- ⚠️ JWT аутентификация (планируется)

## Лицензия

MIT License

## Поддержка

Для вопросов и предложений создавайте issues в репозитории.
