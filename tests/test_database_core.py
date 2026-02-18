import sqlite3
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

import database
import database.core


def test_get_connection():
    """Тест получения соединения"""
    # Очищаем thread local хранилище перед тестом
    if hasattr(database.core._local, "conn"):
        database.core._local.conn = None

    with patch("sqlite3.connect") as mock_connect:
        conn = database.core.get_connection()
        mock_connect.assert_called_once()
        assert conn == mock_connect.return_value
        # Проверяем, что повторный вызов возвращает то же соединение
        conn2 = database.core.get_connection()
        assert conn2 == conn
        assert mock_connect.call_count == 1


def test_close_all_connections():
    """Тест закрытия соединений"""
    # Устанавливаем мок соединения
    mock_conn = MagicMock()
    database.core._local.conn = mock_conn

    database.core.close_all_connections()

    mock_conn.close.assert_called_once()
    assert database.core._local.conn is None


def test_execute_query_commit():
    """Тест выполнения запроса с коммитом"""
    with patch("database.core.get_connection") as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        database.core.execute_query("INSERT INTO test VALUES (1)")

        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()


def test_execute_query_rollback_on_error():
    """Тест отката транзакции при ошибке"""
    with patch("database.core.get_connection") as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("DB Error")

        with pytest.raises(sqlite3.Error):
            database.core.execute_query("SELECT * FROM test")

        mock_conn.rollback.assert_called()


def test_user_state_thread_safety():
    """Тест потокобезопасности состояний (простой)"""
    database.core.set_user_state(1, {"step": "test"})
    state = database.core.get_user_state(1)
    assert state["step"] == "test"
    database.core.clear_user_state(1)
    assert database.core.get_user_state(1) == {}


def test_execute_query_sqlite_error_no_commit():
    """Тест отката транзакции при ошибке SQLite без коммита"""
    with patch("database.core.get_connection") as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("DB Error")

        with pytest.raises(sqlite3.Error):
            # fetchone=True -> commit=False по умолчанию
            database.core.execute_query("SELECT 1", fetchone=True, commit=False)

        mock_conn.rollback.assert_not_called()  # commit=False, rollback не нужен


def test_execute_query_generic_exception():
    """Тест отката транзакции при общей ошибке"""
    with patch("database.core.get_connection") as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Generic Error")
        mock_get_conn.return_value = mock_conn

        with pytest.raises(Exception):
            database.core.execute_query("INSERT 1")
        mock_conn.rollback.assert_called_once()


def test_execute_query_fetchone():
    """Тест execute_query с fetchone=True"""
    with patch("database.core.get_connection") as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = {"id": 1}

        result = database.core.execute_query("SELECT 1", fetchone=True)

        assert result == {"id": 1}
        mock_cursor.fetchone.assert_called_once()


def test_execute_query_fetchall():
    """Тест execute_query с fetchone=False (по умолчанию)"""
    with patch("database.core.get_connection") as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]

        result = database.core.execute_query("SELECT *", fetchall=True)

        assert result == [{"id": 1}, {"id": 2}]
        mock_cursor.fetchall.assert_called_once()


def test_execute_query_insert_lastrowid():
    """Тест execute_query для INSERT (возврат lastrowid)"""
    # Проверяем, что функция не падает при INSERT
    with patch("database.core.get_connection") as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.rowcount = 1
        result = database.core.execute_query("INSERT INTO table VALUES (1)")

        # В текущей реализации execute_query возвращает rowcount
        assert result == 1


def test_close_all_connections_error():
    """Тест ошибки при закрытии соединения"""
    mock_conn = MagicMock()
    mock_conn.close.side_effect = Exception("Close Error")
    database.core._local.conn = mock_conn

    # Не должно вызывать исключение
    database.core.close_all_connections()

    mock_conn.close.assert_called_once()
    assert database.core._local.conn is None


def test_execute_query_suppress_error():
    """Тест подавления ошибки в execute_query"""
    with patch("database.core.get_connection") as mock_get_conn, patch(
        "database.core.logger"
    ) as mock_logger:

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("DB Error")

        with pytest.raises(sqlite3.Error):
            database.core.execute_query("SELECT 1", suppress_error=True)

        # Logger не должен вызываться для ошибки
        mock_logger.error.assert_not_called()


def test_execute_query_generic_exception_print():
    """Тест вывода лога при общей ошибке"""
    with patch("database.core.get_connection") as mock_get_conn, patch(
        "database.core.logger"
    ) as mock_logger:

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Generic Error")

        with pytest.raises(Exception):
            database.core.execute_query("SELECT 1")

        assert mock_logger.error.call_count > 0
        mock_conn.rollback.assert_called()


def test_execute_query_with_params():
    """Тест выполнения запроса с параметрами"""
    with patch("database.core.get_connection") as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        database.core.execute_query("INSERT INTO table VALUES (?)", (1,))

        mock_cursor.execute.assert_called_with("INSERT INTO table VALUES (?)", (1,))


def test_close_all_connections_none():
    """Тест закрытия соединений, когда их нет"""
    if hasattr(database.core._local, "conn"):
        database.core._local.conn = None

    database.core.close_all_connections()
    assert getattr(database.core._local, "conn", None) is None


def test_get_pool_stats_none():
    """Тест статистики пула без PostgreSQL"""
    with patch("database.core._pg_pool", None):
        assert database.core.get_pool_stats() is None


def test_get_pool_stats_mock():
    """Тест статистики пула с моком"""
    mock_pool = MagicMock()
    mock_pool.minconn = 5
    mock_pool.maxconn = 20
    mock_pool._used = {1, 2}
    mock_pool._pool = [3, 4, 5]

    with patch("database.core._pg_pool", mock_pool):
        stats = database.core.get_pool_stats()
        assert stats["min"] == 5
        assert stats["max"] == 20
        assert stats["used"] == 2
        assert stats["available"] == 3


def test_db_transaction_context_manager(test_db):
    """
    Интеграционный тест для контекстного менеджера транзакций.
    Проверяет commit при успехе и rollback при ошибке.
    """
    # 1. Создаем тестовую таблицу
    test_db.execute("CREATE TABLE transaction_test (id INTEGER, name TEXT)")
    test_db.commit()

    # 2. Успешная транзакция (commit)
    try:
        with database.core.db_transaction() as conn:
            conn.execute("INSERT INTO transaction_test VALUES (1, 'Alice')")
    except Exception:
        pytest.fail("Transaction should have succeeded but it failed.")

    # Проверяем, что данные сохранились после выхода из контекста
    cursor = test_db.cursor()
    cursor.execute("SELECT * FROM transaction_test WHERE id = 1")
    assert cursor.fetchone() is not None

    # 3. Неуспешная транзакция (rollback)
    with pytest.raises(ValueError):
        with database.core.db_transaction() as conn:
            conn.execute("INSERT INTO transaction_test VALUES (2, 'Bob')")
            raise ValueError("Simulating an error")

    # Проверяем, что данные НЕ сохранились
    cursor.execute("SELECT * FROM transaction_test WHERE id = 2")
    assert cursor.fetchone() is None


def test_execute_query_rollback_exception():
    """Test exception during rollback."""
    with patch("database.core.get_connection") as mock_get_conn, patch("logging.error"):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = database.core.DBError("DB Error")
        # Simulate another error during rollback
        mock_conn.rollback.side_effect = Exception("Rollback failed")

        with pytest.raises(database.core.DBError):
            database.core.execute_query("INSERT 1")

        # Both should have been called
        mock_conn.rollback.assert_called_once()


def test_execute_query_unknown_error_rollback_exception():
    """Test exception during rollback on an unknown error."""
    with patch("database.core.get_connection") as mock_get_conn, patch("logging.error"):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Generic Error")
        # Simulate another error during rollback
        mock_conn.rollback.side_effect = Exception("Rollback failed")

        with pytest.raises(Exception):
            database.core.execute_query("INSERT 1")

        mock_conn.rollback.assert_called_once()


def test_execute_query_cursor_close_exception():
    """Test exception during cursor close."""
    with patch("database.core.get_connection") as mock_get_conn, patch("logging.error"):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.close.side_effect = Exception("Cursor close failed")

        # Should not raise an exception to the caller
        database.core.execute_query("SELECT 1", fetchone=True)
        mock_cursor.close.assert_called_once()


class TestPostgresConnection:
    @pytest.fixture(autouse=True)
    def setup_postgres_env(self):
        # This fixture will run for all tests in this class
        with patch("os.getenv") as mock_getenv, patch(
            "database.core.psycopg2", create=True
        ) as mock_psycopg2, patch(
            "database.core.RealDictCursor", create=True, new=MagicMock()
        ), patch(
            "database.core.PSYCOPG2_AVAILABLE", True
        ):

            # Default mock for getenv
            def getenv_side_effect(key, default=None):
                if key == "DATABASE_URL":
                    return "dummy_dsn"
                if key == "DB_POOL_MIN":
                    return "1"
                if key == "DB_POOL_MAX":
                    return "10"
                return default

            mock_getenv.side_effect = getenv_side_effect

            # Mock the pool and connection objects
            self.mock_pool = MagicMock()
            self.mock_conn = MagicMock()
            self.mock_cursor = MagicMock()
            self.mock_conn.cursor.return_value = self.mock_cursor
            self.mock_pool.getconn.return_value = self.mock_conn
            mock_psycopg2.pool.ThreadedConnectionPool.return_value = self.mock_pool
            mock_psycopg2.connect.return_value = MagicMock()  # For the initial check

            # Define a dummy Error class for testing
            class MockError(Exception):
                pass

            mock_psycopg2.Error = MockError

            # Reset global pool variable before each test
            database.core._pg_pool = None
            # Reset thread-local connection
            if hasattr(database.core._local, "conn"):
                database.core._local.conn = None

            # Patch DBError to include our MockError so execute_query catches it
            with patch("database.core.DBError", (sqlite3.Error, MockError)):
                yield mock_psycopg2

    def test_init_postgres_pool_success(self, setup_postgres_env):
        """Test successful PostgreSQL pool initialization."""
        pool = database.core.init_postgres_pool()
        assert pool is not None
        setup_postgres_env.pool.ThreadedConnectionPool.assert_called_with(
            1, 10, dsn="dummy_dsn"
        )

    def test_init_postgres_pool_connection_error(self, setup_postgres_env):
        """Test pool initialization failure."""
        setup_postgres_env.connect.side_effect = Exception("Connection failed")
        pool = database.core.init_postgres_pool()
        assert pool is None

    def test_get_pool_stats_exception(self):
        """Test exception in get_pool_stats."""

        class BrokenPool:
            @property
            def minconn(self):
                raise Exception("Stat Error")

        with patch("database.core._pg_pool", BrokenPool()):
            stats = database.core.get_pool_stats()
            assert stats is None


def test_check_connection_health_sqlite():
    """Тест проверки здоровья БД (SQLite)"""
    with patch("database.core._pg_pool", None):
        assert database.core.check_connection_health() is True


def test_check_connection_health_fail():
    """Тест проверки здоровья при ошибке"""
    with patch(
        "database.core._create_sqlite_connection", side_effect=Exception("DB Error")
    ), patch("database.core.logger"):
        with patch("database.core._pg_pool", None):
            assert database.core.check_connection_health() is False
