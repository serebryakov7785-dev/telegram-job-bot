import os
import sqlite3
import sys
from unittest.mock import MagicMock

import pytest

# Добавляем корневую директорию проекта в путь импорта, чтобы видеть модули
# __file__ is tests/conftest.py, so '..' is the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Устанавливаем переменные окружения ДО импорта модулей проекта,
# чтобы config.py инициализировался корректно и не вызывал exit(1)
os.environ["TELEGRAM_BOT_TOKEN"] = "123:test_token"
os.environ["ADMIN_IDS"] = "123456"

# Глобальный мок для telebot, если библиотека не установлена
try:
    import telebot  # noqa: F401
except ImportError:
    sys.modules["telebot"] = MagicMock()
    sys.modules["telebot.types"] = MagicMock()

import database.core  # noqa: E402
import database.schema  # noqa: E402


@pytest.fixture(scope="function")
def test_db(monkeypatch):
    """
    Фикстура для создания изолированной базы данных в памяти для каждого теста.
    """
    # Создаем соединение с БД в памяти
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Патчим функцию get_connection в database.core,
    # чтобы она возвращала наше тестовое соединение вместо реального
    monkeypatch.setattr(database.core, "get_connection", lambda: conn)

    # Также патчим get_connection в database.schema, так как он импортируется там напрямую
    monkeypatch.setattr(database.schema, "get_connection", lambda: conn)

    # Инициализируем схему БД (создаем таблицы)
    database.schema.init_database()

    # Ensure language_code column exists (fix for tests if migration is skipped)
    try:
        conn.execute(
            "ALTER TABLE job_seekers ADD COLUMN language_code TEXT DEFAULT 'ru'"
        )
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE employers ADD COLUMN language_code TEXT DEFAULT 'ru'")
    except sqlite3.OperationalError:
        pass

    yield conn

    # Очистка после теста
    conn.close()


@pytest.fixture(autouse=True)
def clear_caches():
    """Очистка кэшей перед каждым тестом"""
    import database.users
    import database.vacancies

    database.users.invalidate_seekers_cache()
    database.users._user_cache.clear()

    # Clear any cache dictionaries in vacancies module
    for attr in dir(database.vacancies):
        if attr.endswith("_cache") and isinstance(
            getattr(database.vacancies, attr), (dict, list)
        ):
            getattr(database.vacancies, attr).clear()
