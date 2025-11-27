# Visual Service - REST API Микросервис

REST API микросервис для генерации изображений и графиков с использованием S3-совместимого хранилища (MinIO).

## Возможности

- 🎨 **Генерация изображений** с использованием OpenAI DALL-E 3
- 📊 **Создание графиков из текстовых описаний** с помощью Claude Sonnet 4.5 (агентный режим)
- 📈 **Создание графиков из структурированных данных** (линейные, столбчатые, круговые, точечные, гистограммы)
- 🔧 **Генерация графиков из Python кода** для продвинутых сценариев
- ☁️ **Хранение файлов** в S3-совместимом хранилище (MinIO)
- 🤖 **Улучшение промптов** с помощью Anthropic Claude
- 🌐 **Поддержка прокси** для всех внешних API
- 📖 **RESTful API** с автоматической документацией (Swagger UI)
- ✅ **Health check и метрики**

## Технологический стек

- **Python 3.11+**
- **FastAPI** - современный веб-фреймворк
- **OpenAI DALL-E 3** - генерация изображений
- **Claude Sonnet 4.5** - агентная генерация графиков из текста
- **matplotlib & seaborn** - построение графиков
- **MinIO** - S3-совместимое хранилище
- **aioboto3** - асинхронный S3 клиент
- **Docker** - контейнеризация

## Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)

### Запуск с Docker Compose

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd visual-service
```

2. Создайте `.env` файл:
```bash
cp .env.example .env
```

3. Настройте переменные окружения в `.env` (опционально):
```bash
ANTHROPIC_API_KEY=your_api_key_here
```

4. Запустите сервисы:
```bash
docker-compose up --build -d
```

5. Проверьте статус:
```bash
curl http://localhost:8000/health
```

### Локальная разработка

1. Установите uv (если еще не установлен):
```bash
pip install uv
```

2. Создайте виртуальное окружение и установите зависимости:
```bash
uv venv
source .venv/bin/activate  # Linux/macOS
# или .venv\Scripts\activate  # Windows

uv pip install -r pyproject.toml
```

3. Запустите MinIO отдельно:
```bash
docker-compose up minio -d
```

4. Запустите сервис:
```bash
uvicorn app.main:app --reload
```

## API Документация

После запуска сервиса документация доступна по адресам:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Основные эндпоинты

#### 1. Генерация изображения

```bash
POST /api/v1/visual/generate-image
```

Пример запроса:
```bash
curl -X POST "http://localhost:8000/api/v1/visual/generate-image" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene mountain landscape at sunset",
    "style": "realistic",
    "size": "1024x1024",
    "user_id": "user_123"
  }'
```

#### 2. Генерация графика

```bash
POST /api/v1/visual/generate-chart
```

Пример запроса:
```bash
curl -X POST "http://localhost:8000/api/v1/visual/generate-chart" \
  -H "Content-Type: application/json" \
  -d '{
    "chart_type": "line",
    "data": {
      "x": [1, 2, 3, 4, 5],
      "y": [10, 15, 13, 18, 20],
      "labels": ["Jan", "Feb", "Mar", "Apr", "May"]
    },
    "title": "Monthly Sales",
    "options": {
      "xlabel": "Month",
      "ylabel": "Sales (K)",
      "color": "blue"
    },
    "user_id": "user_123"
  }'
```

#### 3. Генерация графика из кода

```bash
POST /api/v1/visual/generate-chart-from-code
```

Пример запроса:
```bash
curl -X POST "http://localhost:8000/api/v1/visual/generate-chart-from-code" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import matplotlib.pyplot as plt\nimport numpy as np\nx = np.linspace(0, 10, 100)\ny = np.sin(x)\nplt.plot(x, y)\nplt.title(\"Sine Wave\")\nplt.savefig(filepath)",
    "user_id": "user_123"
  }'
```

#### 4. Генерация графика из текстового описания (🔥 NEW!)

```bash
POST /api/v1/visual/generate-chart-from-text
```

Использует **Claude Sonnet 4.5** в агентном режиме для создания графиков из естественного языка.

Пример запроса:
```bash
curl -X POST "http://localhost:8000/api/v1/visual/generate-chart-from-text" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Создай красивый линейный график, показывающий рост продаж компании за последние 12 месяцев. Начни с 100K в январе и покажи рост до 500K к декабрю с небольшими колебаниями. Используй синий цвет и добавь сетку.",
    "user_id": "user_123"
  }'
```

Другие примеры описаний:
- "Круговая диаграмма распределения бюджета: Маркетинг 30%, Разработка 40%, Продажи 20%, Операции 10%"
- "Столбчатая диаграмма сравнения температур в разных городах: Москва -5°C, Лондон +8°C, Нью-Йорк 0°C, Токио +12°C"
- "Heatmap корреляционной матрицы для 5 переменных с случайными корреляциями"
- "График распределения нормального распределения с mu=0 и sigma=1"

#### 5. Получение информации о файле

```bash
GET /api/v1/visual/file/{file_key}
```

Пример:
```bash
curl "http://localhost:8000/api/v1/visual/file/images/550e8400-e29b-41d4-a716-446655440000.png"
```

#### 5. Удаление файла

```bash
DELETE /api/v1/visual/file/{file_key}
```

#### 6. Health Check

```bash
GET /health
```

#### 7. Метрики

```bash
GET /metrics
```

## Структура проекта

```
visual-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI приложение
│   ├── config.py            # Конфигурация
│   ├── api/
│   │   ├── routes.py        # API маршруты
│   │   └── schemas.py       # Pydantic модели
│   ├── services/
│   │   ├── image_generator.py    # Генерация изображений
│   │   ├── chart_generator.py    # Генерация графиков
│   │   ├── s3_client.py          # S3 клиент
│   │   └── anthropic_client.py   # Anthropic API
│   └── utils/
│       └── logger.py        # Логирование
├── tests/                   # Тесты
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Конфигурация

Основные настройки через переменные окружения:

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `S3_ENDPOINT` | URL MinIO/S3 | `http://minio:9000` |
| `S3_BUCKET` | Имя bucket | `visual-storage` |
| `ANTHROPIC_API_KEY` | API ключ Anthropic (Claude) | - |
| `OPENAI_API_KEY` | API ключ OpenAI (DALL-E 3) | - |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

Полный список настроек см. в `.env.example`.

### Конфигурация прокси

Сервис поддерживает использование HTTP/HTTPS прокси для всех внешних API запросов:

```bash
# В .env файле
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
NO_PROXY=localhost,127.0.0.1
```

Прокси применяется к:
- **OpenAI API** (DALL-E 3) - для генерации изображений
- **Anthropic API** (Claude) - для улучшения промптов и генерации кода графиков

## Особенности реализации

### 🎨 Генерация изображений (DALL-E 3)

**Модель**: **OpenAI DALL-E 3** через официальный API

**Процесс генерации**:
1. 💬 Промпт опционально улучшается через Claude Sonnet 4.5
2. 🖼️ Отправка запроса в OpenAI DALL-E 3 API
3. ⬇️ Скачивание сгенерированного изображения
4. ☁️ Загрузка в S3/MinIO
5. 🔗 Возврат публичного URL

**Поддерживаемые стили**:
- `vivid` - яркие, драматичные изображения (по умолчанию)
- `natural` - более естественные, реалистичные изображения

**Поддерживаемые размеры**:
- `1024x1024` - квадратное (по умолчанию)
- `1024x1792` - вертикальное
- `1792x1024` - горизонтальное

**Настройка**:
```bash
OPENAI_API_KEY=sk-your-api-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here  # опционально, для улучшения промптов
```

### 📊 Генерация графиков (3 способа)

#### 1. **Из текстового описания** (🔥 Рекомендуется!)

**Технология**: **Claude Sonnet 4.5** в агентном режиме

Claude анализирует естественный язык и генерирует оптимальный Python код для matplotlib:

**Процесс**:
1. 📝 Пользователь описывает желаемый график текстом
2. 🤖 Claude Sonnet 4.5 генерирует Python код для matplotlib
3. ⚙️ Код выполняется в безопасном окружении
4. 📈 График сохраняется в PNG
5. ☁️ Загрузка в S3/MinIO
6. 🔗 Возврат URL

**Преимущества**:
- ✅ Естественный язык вместо кода
- ✅ Автоматическая генерация красивых графиков
- ✅ Поддержка сложных визуализаций
- ✅ Адаптация под описание

**Примеры запросов**:
- "График продаж по месяцам с трендом"
- "Тепловая карта корреляций между переменными"
- "Сравнение метрик с группировкой по категориям"

#### 2. **Из структурированных данных**

**Реализация**: Локально через matplotlib + seaborn

Графики создаются на сервере без внешних API вызовов:

**Поддерживаемые типы**:
- `line` - линейные графики
- `bar` - столбчатые диаграммы
- `scatter` - точечные диаграммы
- `pie` - круговые диаграммы
- `histogram` - гистограммы

**Преимущества**:
- ✅ Быстрая генерация (нет сетевых запросов)
- ✅ Предсказуемый формат данных
- ✅ Никаких внешних зависимостей

#### 3. **Из Python кода**

Для продвинутых сценариев можно отправить готовый Python код с matplotlib.

**Особенности**:
- Полный контроль над визуализацией
- Базовая проверка безопасности кода
- Доступ к plt, np, sns

## Тестирование

Запуск тестов:
```bash
pytest tests/
```

С покрытием:
```bash
pytest --cov=app tests/
```

## MinIO Web Console

MinIO Console доступен по адресу: http://localhost:9001

Логин: `minioadmin`
Пароль: `minioadmin`

## Мониторинг

Сервис предоставляет эндпоинты для мониторинга:
- `/health` - статус сервиса и зависимостей
- `/metrics` - метрики использования

Рекомендуется интегрировать с Prometheus и Grafana для визуализации метрик.

## Безопасность

- Кастомный код проходит базовую проверку на опасные операции
- Рекомендуется использовать SSL для production
- Настройте rate limiting через reverse proxy (nginx, traefik)

## Production Deployment

Для production окружения:

1. Используйте настоящий S3 или защищенный MinIO
2. Включите SSL (`S3_USE_SSL=True`)
3. Настройте secrets management
4. Добавьте reverse proxy с SSL
5. Настройте мониторинг и алертинг
6. Включите rate limiting

## Поддержка

Для вопросов и поддержки создавайте issues в репозитории проекта.

## Лицензия

MIT License
