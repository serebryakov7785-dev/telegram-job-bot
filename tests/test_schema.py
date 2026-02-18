import logging
import sqlite3
from unittest.mock import patch

import database.schema


def test_migration_add_languages_to_seekers(test_db):
    """Test migration that adds the 'languages' column to job_seekers."""
    # 1. Create the table WITHOUT the 'languages' column
    test_db.execute("DROP TABLE IF EXISTS job_seekers")
    test_db.execute(
        """
        CREATE TABLE job_seekers (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE NOT NULL
        )
    """
    )
    test_db.commit()

    # 2. Run the init_database function which should perform the migration
    database.schema.init_database()

    # 3. Check if the column was added
    cursor = test_db.cursor()
    cursor.execute("PRAGMA table_info(job_seekers)")
    columns = [row["name"] for row in cursor.fetchall()]

    assert "languages" in columns


def test_migration_add_city_to_employers(test_db):
    """Test migration that adds the 'city' column to employers."""
    # 1. Create the table WITHOUT the 'city' column
    test_db.execute("DROP TABLE IF EXISTS employers")
    test_db.execute(
        "CREATE TABLE employers (id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE NOT NULL)"
    )
    test_db.commit()

    # 2. Run the init_database function
    database.schema.init_database()

    # 3. Check if the column was added
    cursor = test_db.cursor()
    cursor.execute("PRAGMA table_info(employers)")
    columns = [row["name"] for row in cursor.fetchall()]

    assert "city" in columns


def test_init_database_exception_handling(caplog):
    """Test that init_database handles exceptions gracefully."""
    caplog.set_level(logging.ERROR)
    with patch(
        "database.schema.execute_query", side_effect=sqlite3.Error("Test DB Error")
    ):
        result = database.schema.init_database()
        assert result is False
        assert "Ошибка инициализации БД" in caplog.text
