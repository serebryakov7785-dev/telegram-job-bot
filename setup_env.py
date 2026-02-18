import os

def main():
    print("🛠 Настройка окружения бота")
    
    token = input("Введите токен бота (TELEGRAM_BOT_TOKEN): ").strip()
    admin_ids = input("Введите ID администраторов (через запятую): ").strip()
    prometheus_port = input("Порт Prometheus (Enter для 8000): ").strip() or "8000"

    env_content = f"""TELEGRAM_BOT_TOKEN={token}
ADMIN_IDS={admin_ids}
PROMETHEUS_PORT={prometheus_port}
"""

    file_path = os.path.join(os.getcwd(), ".env")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    print(f"✅ Файл {file_path} успешно создан!")

if __name__ == "__main__":
    main()
