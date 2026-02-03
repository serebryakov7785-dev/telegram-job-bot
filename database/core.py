import sqlite3
import hashlib
import threading
import atexit
from typing import Dict, Any

# ================= ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =================
# Храним подключения для каждого потока
_local = threading.local()

# Глобальный словарь для состояний пользователей (в памяти)
_user_states = {}
_user_states_lock = threading.Lock()


# ================= ФУНКЦИИ ПОДКЛЮЧЕНИЯ =================
def get_connection():
    """Безопасное получение соединения для текущего потока"""
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(
            'jobs_database.db',
            check_same_thread=False,
            timeout=10
        )
        _local.conn.row_factory = sqlite3.Row
        # Включаем foreign keys
        _local.conn.execute("PRAGMA foreign_keys = ON")
    return _local.conn


def close_all_connections():
    """Закрытие всех соединений при завершении"""
    if hasattr(_local, 'conn') and _local.conn:
        try:
            _local.conn.close()
        except Exception:
            pass
        _local.conn = None


# Регистрируем закрытие при выходе
atexit.register(close_all_connections)


# ================= УТИЛИТЫ =================
def hash_password(pwd: str) -> str:
    """Хэширование пароля"""
    return hashlib.sha256(pwd.encode()).hexdigest()


def verify_password(stored_hash: str, password: str) -> bool:
    """Проверка пароля"""
    return stored_hash == hash_password(password)


# ================= ФУНКЦИИ СОСТОЯНИЙ =================
def get_user_state(user_id: int) -> Dict[str, Any]:
    """Получение состояния пользователя"""
    with _user_states_lock:
        state = _user_states.get(user_id, {})
        return state.copy() if state else {}


def set_user_state(user_id: int, state: Dict[str, Any]):
    """Установка состояния пользователя"""
    with _user_states_lock:
        _user_states[user_id] = state.copy() if state else {}


def clear_user_state(user_id: int):
    """Очистка состояния пользователя"""
    with _user_states_lock:
        if user_id in _user_states:
            del _user_states[user_id]


# ================= ОБЩИЕ ФУНКЦИИ БД =================
def execute_query(query: str, params: tuple = (), fetchone: bool = False, fetchall: bool = False, commit: bool = True, suppress_error: bool = False):  # noqa: C901, E501
    """Универсальная функция выполнения запросов с обработкой ошибок"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(query, params)

        if fetchone:
            result = cursor.fetchone()
            if result:
                return dict(result)
            return None
        elif fetchall:
            results = cursor.fetchall()
            return [dict(row) for row in results]
        else:
            if commit:
                conn.commit()
            return cursor.rowcount
    except sqlite3.Error as e:
        if not suppress_error:
            print(f"❌ Ошибка SQLite в execute_query: {e}")
            print(f"   Запрос: {query}")
            print(f"   Параметры: {params}")
        if commit:
            conn.rollback()
        raise
    except Exception as e:
        print(f"❌ Неизвестная ошибка в execute_query: {e}")
        if commit:
            conn.rollback()
        raise
    finally:
        try:
            cursor.close()
        except Exception:
            pass
