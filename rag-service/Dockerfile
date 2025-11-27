FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установка uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Копирование зависимостей
COPY pyproject.toml ./

# Установка зависимостей
RUN uv pip install --system -r pyproject.toml

# Копирование кода
COPY app ./app
COPY migrations ./migrations

# Создание директорий
RUN mkdir -p /app/uploads /app/temp

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
