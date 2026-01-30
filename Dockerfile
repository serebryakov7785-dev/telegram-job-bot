# Используем легкий образ Python
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта
COPY . .

# Создаем директорию для бэкапов, чтобы избежать ошибок прав доступа
RUN mkdir -p backups

# Переменные окружения для Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Открываем порт для Prometheus (если используется)
EXPOSE 8000

# Запускаем бота
CMD ["python", "bot.py"]