FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей (предполагается наличие requirements.txt)
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Переменная для вывода логов в реальном времени
ENV PYTHONUNBUFFERED=1

# Запускаем бота
CMD ["python", "bot.py"]
