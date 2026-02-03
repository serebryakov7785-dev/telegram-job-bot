import pytest
import sqlite3
from unittest.mock import MagicMock, patch
import database.core


def test_get_connection():
    """Тест получения соединения"""
    # Очищаем thread local хранилище перед тестом
    if hasattr(database.core._local, 'conn'):
        database.core._local.conn = None

    with patch('sqlite3.connect') as mock_connect:
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
    with patch('database.core.get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        database.core.execute_query("INSERT INTO test VALUES (1)")

        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()


def test_execute_query_rollback_on_error():
    """Тест отката транзакции при ошибке"""
    with patch('database.core.get_connection') as mock_get_conn:
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
    database.core.set_user_state(1, {'step': 'test'})
    state = database.core.get_user_state(1)
    assert state['step'] == 'test'
    database.core.clear_user_state(1)
    assert database.core.get_user_state(1) == {}


def test_execute_query_sqlite_error_no_commit():
    """Тест отката транзакции при ошибке SQLite без коммита"""
    with patch('database.core.get_connection') as mock_get_conn:
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
    with patch('database.core.get_connection') as mock_get_conn:
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
    with patch('database.core.get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = {'id': 1}

        result = database.core.execute_query("SELECT 1", fetchone=True)

        assert result == {'id': 1}
        mock_cursor.fetchone.assert_called_once()


def test_execute_query_fetchall():
    """Тест execute_query с fetchone=False (по умолчанию)"""
    with patch('database.core.get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [{'id': 1}, {'id': 2}]

        result = database.core.execute_query("SELECT *", fetchall=True)

        assert result == [{'id': 1}, {'id': 2}]
        mock_cursor.fetchall.assert_called_once()


def test_execute_query_insert_lastrowid():
    """Тест execute_query для INSERT (возврат lastrowid)"""
    # Проверяем, что функция не падает при INSERT
    with patch('database.core.get_connection') as mock_get_conn:
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
    with patch('database.core.get_connection') as mock_get_conn, \
         patch('builtins.print') as mock_print:

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.Error("DB Error")

        with pytest.raises(sqlite3.Error):
            database.core.execute_query("SELECT 1", suppress_error=True)

        # Print не должен вызываться для ошибки
        mock_print.assert_not_called()


def test_execute_query_generic_exception_print():
    """Тест вывода print при общей ошибке (покрытие строк 106-107)"""
    with patch('database.core.get_connection') as mock_get_conn, \
         patch('builtins.print') as mock_print:

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Generic Error")

        with pytest.raises(Exception):
            database.core.execute_query("SELECT 1")

        assert mock_print.call_count > 0
        mock_conn.rollback.assert_called()


def test_execute_query_with_params():
    """Тест выполнения запроса с параметрами"""
    with patch('database.core.get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        database.core.execute_query("INSERT INTO table VALUES (?)", (1,))

        mock_cursor.execute.assert_called_with("INSERT INTO table VALUES (?)", (1,))


def test_close_all_connections_none():
    """Тест закрытия соединений, когда их нет"""
    if hasattr(database.core._local, 'conn'):
        database.core._local.conn = None

    database.core.close_all_connections()
    assert getattr(database.core._local, 'conn', None) is None
