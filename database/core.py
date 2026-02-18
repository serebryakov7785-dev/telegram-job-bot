import atexit
import hashlib
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =================
# Храним подключения для каждого потока
_local = threading.local()

# Глобальный словарь для состояний пользователей (в памяти)
_user_states: Dict[int, Dict[str, Any]] = {}
_user_states_lock = threading.Lock()

# Глобальный пул соединений PostgreSQL
_pg_pool = None

# Попытка импорта psycopg2 для PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    PSYCOPG2_AVAILABLE = True
    DBError = (sqlite3.Error, psycopg2.Error)
except ImportError:
    PSYCOPG2_AVAILABLE = False
    DBError = sqlite3.Error


# ================= ФУНКЦИИ ПОДКЛЮЧЕНИЯ =================
def _create_sqlite_connection():
    """Создание SQLite соединения"""
    conn = sqlite3.connect(
        os.getenv("SQLITE_PATH", "jobs_database.db"),
        check_same_thread=False,
        timeout=10,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # Для лучшей конкурентности
    return conn


def init_postgres_pool():
    """Инициализация пула PostgreSQL"""
    global _pg_pool
    if _pg_pool is None and os.getenv("DATABASE_URL") and PSYCOPG2_AVAILABLE:
        try:
            minconn = int(os.getenv("DB_POOL_MIN", 1))
            maxconn = int(os.getenv("DB_POOL_MAX", 20))

            # Проверяем соединение перед созданием пула
            test_conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            test_conn.close()

            _pg_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn, maxconn, dsn=os.getenv("DATABASE_URL")
            )
            logger.info(
                f"✅ PostgreSQL пул инициализирован (min={minconn}, max={maxconn})"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации пула PostgreSQL: {e}")
            _pg_pool = None
    return _pg_pool


def get_connection():
    """Безопасное получение соединения для текущего потока"""
    init_postgres_pool()

    if not hasattr(_local, "conn") or _local.conn is None:
        if _pg_pool:
            try:
                _local.conn = _pg_pool.getconn()
            except Exception as e:
                logger.error(f"❌ Ошибка получения соединения из пула: {e}")
                raise
        else:
            _local.conn = _create_sqlite_connection()
    return _local.conn


def close_connection():
    """Закрытие соединения текущего потока"""
    if hasattr(_local, "conn") and _local.conn:
        try:
            if _pg_pool:
                _pg_pool.putconn(_local.conn)
            else:
                _local.conn.close()
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии соединения: {e}")
        finally:
            _local.conn = None


def close_all_connections():
    """Закрытие всех соединений при завершении"""
    close_connection()


def close_pool():
    """Закрытие пула PostgreSQL"""
    global _pg_pool
    if _pg_pool:
        try:
            _pg_pool.closeall()
            logger.info("✅ Пул PostgreSQL закрыт")
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии пула: {e}")
        finally:
            _pg_pool = None


@contextmanager
def db_transaction():
    """Контекстный менеджер для транзакций"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        close_connection()


# Регистрируем закрытие при выходе
atexit.register(close_all_connections)
atexit.register(close_pool)


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


def set_user_state(user_id: int, state: Dict[str, Any]) -> None:
    """Установка состояния пользователя"""
    with _user_states_lock:
        _user_states[user_id] = state.copy() if state else {}


def clear_user_state(user_id: int) -> None:
    """Очистка состояния пользователя"""
    with _user_states_lock:
        if user_id in _user_states:
            del _user_states[user_id]


# ================= ОБЩИЕ ФУНКЦИИ БД =================
def execute_query(
    query: str,
    params: tuple = (),
    fetchone: bool = False,
    fetchall: bool = False,
    commit: bool = True,
    suppress_error: bool = False,
) -> Any:  # noqa: C901, E501
    """Универсальная функция выполнения запросов с обработкой ошибок"""
    conn = get_connection()

    # Адаптация плейсхолдеров для PostgreSQL
    using_postgres = _pg_pool is not None
    if using_postgres:
        query = query.replace("?", "%s")

    if using_postgres:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()

    try:
        cursor.execute(query, params)

        if fetchone:
            result = cursor.fetchone()
            if result:
                return dict(result) if result else None
            return None
        elif fetchall:
            results = cursor.fetchall()
            return [dict(row) for row in results]
        else:
            if commit:
                conn.commit()
            return cursor.rowcount
    except DBError as e:
        if not suppress_error:
            logger.error(f"❌ Ошибка БД в execute_query: {e}")
            logger.error(f"   Запрос: {query}")
            logger.error(f"   Параметры: {params}")
        if commit and not fetchone and not fetchall:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    except Exception as e:
        logger.error(f"❌ Неизвестная ошибка в execute_query: {e}")
        if commit and not fetchone and not fetchall:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        try:
            cursor.close()
        except Exception:
            pass

        if not fetchone and not fetchall and not commit:
            # Для SELECT без необходимости в транзакции
            close_connection()


def get_pool_stats() -> Optional[Dict[str, Any]]:
    """Получение статистики пула соединений"""
    if _pg_pool:
        try:
            return {
                "min": _pg_pool.minconn,
                "max": _pg_pool.maxconn,
                "used": len(_pg_pool._used) if hasattr(_pg_pool, "_used") else 0,
                "available": len(_pg_pool._pool) if hasattr(_pg_pool, "_pool") else 0,
            }
        except Exception:
            return None
    return None


def check_connection_health() -> bool:
    """Проверка здоровья соединения"""
    try:
        if _pg_pool:
            conn = _pg_pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            finally:
                _pg_pool.putconn(conn)
        else:
            conn = _create_sqlite_connection()
            try:
                conn.execute("SELECT 1")
            finally:
                conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Проверка здоровья БД не удалась: {e}")
        return False
