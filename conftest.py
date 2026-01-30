import sys
import os
import pytest
import sqlite3
from unittest.mock import MagicMock

# Добавляем корневую директорию проекта в путь импорта, чтобы видеть модули
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Устанавливаем переменные окружения ДО импорта модулей проекта,
# чтобы config.py инициализировался корректно и не вызывал exit(1)
os.environ["TELEGRAM_BOT_TOKEN"] = "123:test_token"
os.environ["ADMIN_IDS"] = "123456"

# Глобальный мок для telebot, если библиотека не установлена
try:
    import telebot
except ImportError:
    sys.modules['telebot'] = MagicMock()
    sys.modules['telebot.types'] = MagicMock()

import database.core
import database.schema

@pytest.fixture(scope="function")
def test_db(monkeypatch):
    """
    Фикстура для создания изолированной базы данных в памяти для каждого теста.
    """
    # Создаем соединение с БД в памяти
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    # Патчим функцию get_connection в database.core, 
    # чтобы она возвращала наше тестовое соединение вместо реального
    monkeypatch.setattr(database.core, 'get_connection', lambda: conn)
    
    # Также патчим get_connection в database.schema, так как он импортируется там напрямую
    monkeypatch.setattr(database.schema, 'get_connection', lambda: conn)
    
    # Инициализируем схему БД (создаем таблицы)
    # Нам нужно временно подменить get_connection и внутри schema, 
    # хотя schema импортирует его из core, так что патч core должен сработать.
    # Но для надежности вызовем скрипт создания таблиц вручную или через init_database
    
    # Чтобы init_database сработал с нашим conn, патч уже применен
    database.schema.init_database()
    
    yield conn
    
    # Очистка после теста
    conn.close()

@pytest.fixture(autouse=True)
def clear_caches():
    """Очистка кэшей перед каждым тестом"""
    import database.users
    database.users.invalidate_seekers_cache()
    database.users._user_cache.clear()