# Используем официальный Python образ
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей
COPY pyproject.toml poetry.lock ./

# Устанавливаем Poetry
RUN pip install poetry

# Настраиваем Poetry для работы в контейнере
RUN poetry config virtualenvs.create false

# Устанавливаем зависимости
RUN poetry install --no-dev --no-interaction --no-ansi

# Создаем необходимые директории
RUN mkdir -p /app/logs

# Копируем исходный код
COPY . .

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Команда по умолчанию
CMD ["python", "-m", "bot"]
