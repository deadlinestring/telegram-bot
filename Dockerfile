# Используем образ с Python
FROM python:3.9-slim

# Устанавливаем Poetry
RUN pip install poetry

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы pyproject.toml и poetry.lock
COPY pyproject.toml poetry.lock /app/

# Устанавливаем зависимости
RUN poetry install --no-dev

# Копируем весь код проекта
COPY . /app

# Устанавливаем команду для запуска приложения
CMD ["poetry", "run", "python", "Karma_catalog_bot.py"]
