# Gorzdrav Auto Appointments Bot

Бот для автоматической записи на прием в систему ГосЗдрав.

## Особенности

-   Автоматическая запись на прием
-   Планировщик задач
-   Логирование в файлы с ротацией
-   Docker контейнеризация
-   Монтирование базы данных и логов

## Логирование

Бот настроен для записи логов в файлы с автоматической ротацией:

-   **Основные логи**: `logs/bot_YYYY-MM-DD.log` (ротация каждый день, хранение 30 дней)
-   **Логи ошибок**: `logs/errors_YYYY-MM-DD.log` (ротация каждый день, хранение 90 дней)
-   **Консоль**: Логи уровня INFO и выше

## Установка и запуск

### С помощью Docker Compose (рекомендуется)

1. **Клонируйте репозиторий:**

    ```bash
    git clone <repository-url>
    cd gorzdrav_autoappointments
    ```

2. **Первый запуск:**

    ```bash
    make first-run
    ```

3. **Управление контейнером:**
    ```bash
    make up      # Запустить
    make down    # Остановить
    make logs    # Просмотр логов
    make restart # Перезапустить
    make shell   # Войти в контейнер
    ```

### Ручная установка

1. **Установите зависимости:**

    ```bash
    poetry install
    ```

2. **Создайте необходимые директории:**

    ```bash
    mkdir -p logs
    ```

3. **Запустите бота:**
    ```bash
    python -m bot
    ```

## Структура проекта

```
├── bot/                    # Основной код бота
│   ├── api/               # API клиент для ГосЗдрав
│   ├── database/          # Модели и репозитории БД
│   ├── routers/           # Роутеры для команд
│   ├── settings/          # Настройки (включая логирование)
│   └── utils/             # Утилиты
├── logs/                  # Директория для логов
├── requests/              # Примеры API запросов
├── docker-compose.yml     # Docker Compose конфигурация
├── Dockerfile            # Docker образ
└── Makefile              # Команды для управления
```

## Docker

### Монтирование

-   **База данных**: `./gorzdrav_bot.db:/app/gorzdrav_bot.db`
-   **Логи**: `./logs:/app/logs`
-   **Запросы**: `./requests:/app/requests`

### Команды Docker

```bash
# Сборка образа
docker-compose build

# Запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f gorzdrav-bot

# Остановка
docker-compose down
```

## Настройка

### Переменные окружения

Создайте файл `.env` в корне проекта:

```env
BOT_TOKEN=your_telegram_bot_token
```

### Логирование

Настройки логирования находятся в `bot/settings/logging.py`:

-   Уровень логирования: DEBUG для файлов, INFO для консоли
-   Ротация: ежедневная
-   Сжатие: ZIP
-   Кодировка: UTF-8

## Лицензия

MIT
