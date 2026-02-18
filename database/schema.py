import logging

from .core import execute_query, get_connection

# ================= ИНИЦИАЛИЗАЦИЯ БД =================


def init_database():  # noqa: C901
    """Инициализация базы данных"""
    try:
        # Соискатели
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS job_seekers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                gender TEXT,
                age INTEGER NOT NULL CHECK (age >= 16 AND age <= 100),
                city TEXT DEFAULT 'Не указан',
                profession TEXT DEFAULT 'Не указана',
                skills TEXT DEFAULT 'Не указаны',
                experience TEXT DEFAULT 'Нет опыта',
                education TEXT DEFAULT 'Не указано',
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
            commit=False,
        )

        # Работодатели
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS employers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                company_name TEXT NOT NULL,
                contact_person TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                city TEXT DEFAULT 'Не указан',
                description TEXT DEFAULT 'Описание не указано',
                business_activity TEXT DEFAULT 'Не указана',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
            commit=False,
        )

        # Вакансии
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employer_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                salary TEXT DEFAULT 'Не указана',
                gender TEXT DEFAULT 'any',
                job_type TEXT DEFAULT 'Полный день',
                languages TEXT DEFAULT 'Не указаны',
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employer_id) REFERENCES employers (id) ON DELETE CASCADE
            )
        """,
            commit=False,
        )

        # Отклики на вакансии
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vacancy_id INTEGER NOT NULL,
                seeker_id INTEGER NOT NULL,
                message TEXT,
                status TEXT DEFAULT 'pending', -- pending, accepted, rejected
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vacancy_id) REFERENCES vacancies (id) ON DELETE CASCADE,
                FOREIGN KEY (seeker_id) REFERENCES job_seekers (id) ON DELETE CASCADE
            )
        """,
            commit=False,
        )

        # Таблица для истории смены Telegram ID (для аудита)
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS telegram_id_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_type TEXT NOT NULL,  -- 'seeker' или 'employer'
                user_db_id INTEGER NOT NULL,  -- id из job_seekers или employers
                old_telegram_id INTEGER,
                new_telegram_id INTEGER,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
            commit=False,
        )

        # Миграции через PRAGMA (безопасный способ)

        # 1. Проверка job_seekers
        columns_seekers = execute_query("PRAGMA table_info(job_seekers)", fetchall=True)
        if columns_seekers:
            column_names = [col["name"] for col in columns_seekers]

            if "status" not in column_names:
                logging.info("⚠️ Колонка status не найдена в job_seekers, добавляем...")
                execute_query(
                    "ALTER TABLE job_seekers ADD COLUMN status TEXT DEFAULT 'active'",
                    commit=True,
                )

            if "last_login" not in column_names:
                logging.info(
                    "⚠️ Колонка last_login не найдена в job_seekers, добавляем..."
                )
                execute_query(
                    "ALTER TABLE job_seekers ADD COLUMN last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    commit=True,
                )

            if "city" not in column_names:
                logging.info("⚠️ Колонка city не найдена в job_seekers, добавляем...")
                execute_query(
                    "ALTER TABLE job_seekers ADD COLUMN city TEXT DEFAULT 'Не указан'",
                    commit=True,
                )

            if "languages" not in column_names:
                logging.info(
                    "⚠️ Колонка languages не найдена в job_seekers, добавляем..."
                )
                execute_query(
                    "ALTER TABLE job_seekers ADD COLUMN languages TEXT DEFAULT 'Не указаны'",
                    commit=True,
                )

            if "gender" not in column_names:
                logging.info("⚠️ Колонка gender не найдена в job_seekers, добавляем...")
                execute_query(
                    "ALTER TABLE job_seekers ADD COLUMN gender TEXT", commit=True
                )

        # 2. Проверка employers
        columns_employers = execute_query("PRAGMA table_info(employers)", fetchall=True)
        if columns_employers:
            column_names = [col["name"] for col in columns_employers]

            if "last_login" not in column_names:
                logging.info(
                    "⚠️ Колонка last_login не найдена в employers, добавляем..."
                )
                execute_query(
                    "ALTER TABLE employers ADD COLUMN last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    commit=True,
                )

            if "city" not in column_names:
                logging.info("⚠️ Колонка city не найдена в employers, добавляем...")
                execute_query(
                    "ALTER TABLE employers ADD COLUMN city TEXT DEFAULT 'Не указан'",
                    commit=True,
                )

        # 3. Проверка vacancies
        columns_vacancies = execute_query("PRAGMA table_info(vacancies)", fetchall=True)
        if columns_vacancies:
            column_names = [col["name"] for col in columns_vacancies]

            if "languages" not in column_names:
                logging.info("⚠️ Колонка languages не найдена в vacancies, добавляем...")
                execute_query(
                    "ALTER TABLE vacancies ADD COLUMN languages TEXT DEFAULT 'Не указаны'",
                    commit=True,
                )

            if "gender" not in column_names:
                logging.info("⚠️ Колонка gender не найдена в vacancies, добавляем...")
                execute_query(
                    "ALTER TABLE vacancies ADD COLUMN gender TEXT DEFAULT 'any'",
                    commit=True,
                )

            if "city" not in column_names:
                logging.info("⚠️ Колонка city не найдена в vacancies, добавляем...")
                execute_query("ALTER TABLE vacancies ADD COLUMN city TEXT", commit=True)

        # 4. Проверка language_code для всех пользователей
        for table in ["job_seekers", "employers"]:
            cols = execute_query(f"PRAGMA table_info({table})", fetchall=True)
            if cols and "language_code" not in [c["name"] for c in cols]:
                logging.info(
                    f"⚠️ Колонка language_code не найдена в {table}, добавляем..."
                )
                execute_query(
                    f"ALTER TABLE {table} ADD COLUMN language_code TEXT DEFAULT 'ru'",
                    commit=True,
                )

        get_connection().commit()
        logging.info("✅ База данных создана/проверена")
        return True
    except Exception as e:
        logging.error(f"❌ Ошибка инициализации БД: {e}", exc_info=True)
        try:
            get_connection().rollback()
        except Exception:
            pass
        return False
