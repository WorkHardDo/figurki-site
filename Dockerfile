# Базовый образ
FROM python:3.11-slim

# Установка рабочих директорий
WORKDIR /app

# Копируем файлы
COPY . /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Запуск приложения
CMD ["python", "main.py"]
