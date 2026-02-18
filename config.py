import logging
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

if not os.path.exists(".env"):
    print(f"⚠️  ВНИМАНИЕ: Файл .env не найден в папке {os.getcwd()}")

# Коды операторов Узбекистана
UZBEK_OPERATORS = [
    "90",
    "91",
    "93",
    "94",
    "95",
    "97",
    "98",
    "99",
    "88",
    "77",
    "33",
    "50",
    "55",
]


class Config:
    # Токен бота
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    # ID администраторов. Устанавливается в .env файле (ADMIN_IDS=your_id,another_id)
    ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
    ADMIN_IDS = [
        int(admin_id.strip())
        for admin_id in ADMIN_IDS_STR.split(",")
        if admin_id.strip().isdigit()
    ]

    # Мониторинг
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", 8000))

    # Настройки базы данных
    DB_NAME = os.getenv("DB_PATH", "jobs_database.db")

    # Коды операторов Узбекистана
    UZBEK_OPERATORS = UZBEK_OPERATORS

    # Настройки безопасности
    PASSWORD_MIN_LENGTH = 6
    LOGIN_MIN_LENGTH = 3

    # Версия бота
    BOT_VERSION = "2.1.0"


def init_config():
    """Инициализация конфигурации"""
    if not Config.TOKEN:
        logging.error("❌ Ошибка: Токен бота не найден!")
        logging.error("Создайте файл .env с содержанием:")
        logging.error("TELEGRAM_BOT_TOKEN=ваш_токен")
        exit(1)

    if not Config.ADMIN_IDS:
        logging.warning("⚠️ Внимание: ADMIN_IDS не установлен в .env файле.")
        logging.warning("  Команда /admin будет недоступна.")

    logging.info("✅ Конфигурация загружена")
    logging.info(f"   База данных: {Config.DB_NAME}")
    logging.info(f"   Администраторы: {Config.ADMIN_IDS}")
    return True
