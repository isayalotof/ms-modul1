FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для matplotlib и Pillow
RUN apt-get update && apt-get install -y \
    build-essential \
    libfreetype6-dev \
    libpng-dev \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Установка uv для быстрой установки зависимостей
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Копирование файла зависимостей
COPY pyproject.toml ./

# Установка зависимостей
RUN uv pip install --system -r pyproject.toml

# Копирование кода приложения
COPY app ./app

# Создание директории для временных файлов
RUN mkdir -p /tmp/visual-service

# Открытие порта
EXPOSE 8000

# Запуск приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
