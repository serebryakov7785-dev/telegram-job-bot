import os

# Данные для конфигурации
env_content = """TELEGRAM_BOT_TOKEN=8490899561:AAEQ0DOrN3-0_DP_PUZOaBVMsJb4dP8rZrY
ADMIN_IDS=123456789
PROMETHEUS_PORT=8000
"""

# Путь к файлу .env в текущей папке
file_path = os.path.join(os.getcwd(), '.env')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(env_content)

print(f"✅ Файл конфигурации успешно создан: {file_path}")
print("Теперь можно запускать бота!")
