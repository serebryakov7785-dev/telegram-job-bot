import logging
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

from .core import clear_user_state, execute_query, hash_password

# ================= КЭШИРОВАНИЕ =================
_user_cache: Dict[int, Tuple[float, Optional[Dict[str, Any]]]] = {}
CACHE_TTL = 60  # Время жизни кэша в секундах
_seekers_cache: Dict[
    Tuple[int, int, Optional[str], Optional[str]], Tuple[float, List[Dict[str, Any]]]
] = {}
SEEKERS_CACHE_TTL = 60


def invalidate_user_cache(user_id: int) -> None:
    """Сброс кэша для пользователя"""
    if user_id in _user_cache:
        del _user_cache[user_id]


def invalidate_seekers_cache():
    """Сброс кэша списка соискателей"""
    _seekers_cache.clear()


# ================= ФУНКЦИИ ПОЛЬЗОВАТЕЛЕЙ =================
def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение пользователя по Telegram ID - разрешаем NULL результат"""
    # Проверка кэша
    if user_id in _user_cache:
        timestamp, cached_user = _user_cache[user_id]
        if time.time() - timestamp < CACHE_TTL:
            # Возвращаем копию, чтобы случайные изменения не затронули кэш
            return cached_user.copy() if cached_user else None

    try:
        # Сначала ищем в соискателях
        user = execute_query(
            "SELECT *, 'seeker' as role FROM job_seekers WHERE telegram_id = ?",
            (user_id,),
            fetchone=True,
        )

        if user:
            logging.debug(
                f"Найден соискатель: {user.get('full_name', 'Unknown')} (ID: {user_id})"
            )
            _user_cache[user_id] = (time.time(), user)
            return user.copy() if user else None

        # Потом в работодателях
        user = execute_query(
            "SELECT *, 'employer' as role FROM employers WHERE telegram_id = ?",
            (user_id,),
            fetchone=True,
        )

        if user:
            logging.debug(
                f"Найден работодатель: {user.get('company_name', 'Unknown')} (ID: {user_id})"
            )
            _user_cache[user_id] = (time.time(), user)
            return user.copy() if user else None

        # Если не нашли - это НЕ ошибка, пользователь может войти с нового аккаунта
        logging.debug(
            f"Пользователь с Telegram ID {user_id} не найден - может войти с нового аккаунта"
        )
        _user_cache[user_id] = (time.time(), None)
        return None
    except Exception as e:
        logging.error(
            f"Ошибка получения пользователя по ID {user_id}: {e}", exc_info=True
        )
        return None


def get_user_by_credentials(identifier: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Поиск пользователя по телефону или email"""
    try:
        identifier_clean = identifier.strip().lower()

        logging.debug(f"Поиск пользователя по идентификатору: {identifier_clean}")

        # Ищем в соискателях
        user = execute_query(
            """
            SELECT *, 'seeker' as role FROM job_seekers
            WHERE email = ? OR phone = ?
        """,
            (identifier_clean, identifier_clean),
            fetchone=True,
        )

        if user:
            logging.debug(f"Найден соискатель: {user.get('full_name', 'Unknown')}")
            return user, "seeker"

        # Ищем в работодателях
        user = execute_query(
            """
            SELECT *, 'employer' as role FROM employers
            WHERE email = ? OR phone = ?
        """,
            (identifier_clean, identifier_clean),
            fetchone=True,
        )

        if user:
            logging.debug(f"Найден работодатель: {user.get('company_name', 'Unknown')}")
            return user, "employer"

        logging.warning(
            f"Пользователь с идентификатором '{identifier_clean}' не найден"
        )
        return None, ""
    except Exception as e:
        logging.error(
            f"Ошибка поиска пользователя по учетным данным {identifier}: {e}",
            exc_info=True,
        )
        return None, ""


def update_telegram_id(
    old_telegram_id: int, new_telegram_id: int, role: str, user_db_id: int
) -> bool:
    """Обновление Telegram ID пользователя"""
    try:
        table = "job_seekers" if role == "seeker" else "employers"

        # Обновляем Telegram ID
        try:
            result = execute_query(
                f"UPDATE {table} SET telegram_id = ?, last_login = CURRENT_TIMESTAMP WHERE id = ?",  # nosec
                (new_telegram_id, user_db_id),
                suppress_error=True,
            )
        except Exception as e:
            if "no such column: last_login" in str(e):
                logging.warning(
                    f"Колонка last_login отсутствует в {table}, обновляем только telegram_id"
                )
                result = execute_query(
                    f"UPDATE {table} SET telegram_id = ? WHERE id = ?",  # nosec
                    (new_telegram_id, user_db_id),
                )
            else:
                raise e

        if result > 0:
            # Сохраняем в историю
            execute_query(
                """
                INSERT INTO telegram_id_history (user_type, user_db_id, old_telegram_id, new_telegram_id)
                VALUES (?, ?, ?, ?)
            """,
                (role, user_db_id, old_telegram_id, new_telegram_id),
            )

            logging.info(
                f"Telegram ID обновлен: {old_telegram_id} -> {new_telegram_id} ({role})"
            )
            invalidate_user_cache(old_telegram_id)
            invalidate_user_cache(new_telegram_id)
            return True
        else:
            logging.warning(
                f"Не удалось обновить Telegram ID для {role} с ID {user_db_id}"
            )
            return False

    except sqlite3.IntegrityError as e:
        logging.error(
            f"Ошибка целостности при обновлении Telegram ID: {e}", exc_info=True
        )
        return False
    except Exception as e:
        logging.error(f"Ошибка обновления Telegram ID: {e}", exc_info=True)
        return False


def create_job_seeker(user_data: Dict[str, Any]) -> bool:
    """Создание соискателя"""
    telegram_id = user_data["telegram_id"]

    # Проверяем, не существует ли уже пользователь
    existing_user = get_user_by_id(telegram_id)
    if existing_user:
        logging.warning(f"Соискатель с Telegram ID {telegram_id} уже существует")
        return False

    try:
        result = execute_query(
            """
            INSERT INTO job_seekers
            (telegram_id, password_hash, phone, email, full_name, age, city)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                telegram_id,
                hash_password(user_data["password"]),
                user_data["phone"],
                user_data["email"],
                user_data["full_name"],
                user_data["age"],
                user_data["city"],
            ),
        )

        if result > 0:
            logging.info(f"Соискатель с Telegram ID {telegram_id} создан")
            invalidate_user_cache(telegram_id)
            invalidate_seekers_cache()
            return True
        else:
            logging.warning(f"Не удалось создать соискателя с ID {telegram_id}")
            return False

    except sqlite3.IntegrityError as e:
        error_msg = str(e)
        logging.error(f"Ошибка целостности данных: {error_msg}")

        if "UNIQUE constraint failed: job_seekers.telegram_id" in error_msg:
            logging.warning(f"Соискатель с Telegram ID {telegram_id} уже существует")
        elif "UNIQUE constraint failed: job_seekers.phone" in error_msg:
            logging.warning(f"Телефон {user_data.get('phone', '')} уже зарегистрирован")
        elif "UNIQUE constraint failed: job_seekers.email" in error_msg:
            logging.warning(f"Email {user_data.get('email', '')} уже зарегистрирован")

        return False
    except Exception as e:
        logging.error(f"Неизвестная ошибка создания соискателя: {e}", exc_info=True)
        return False


def create_employer(user_data: Dict[str, Any]) -> bool:
    """Создание работодателя"""
    telegram_id = user_data["telegram_id"]

    # Проверяем, не существует ли уже пользователь
    existing_user = get_user_by_id(telegram_id)
    if existing_user:
        logging.warning(f"Работодатель с Telegram ID {telegram_id} уже существует")
        return False

    try:
        result = execute_query(
            """
            INSERT INTO employers
            (telegram_id, password_hash, company_name, contact_person, phone, email, description, business_activity, city)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                telegram_id,
                hash_password(user_data["password"]),
                user_data["company_name"],
                user_data["contact_person"],
                user_data["phone"],
                user_data["email"],
                user_data.get("description", "Описание не указано"),
                user_data.get("business_activity", "Не указана"),
                user_data["city"],
            ),
        )

        if result > 0:
            logging.info(f"Работодатель с Telegram ID {telegram_id} создан")
            invalidate_user_cache(telegram_id)
            return True
        else:
            logging.warning(f"Не удалось создать работодателя с ID {telegram_id}")
            return False

    except sqlite3.IntegrityError as e:
        error_msg = str(e)
        logging.error(f"Ошибка целостности данных: {error_msg}")

        if "UNIQUE constraint failed: employers.telegram_id" in error_msg:
            logging.warning(f"Работодатель с Telegram ID {telegram_id} уже существует")
        elif "UNIQUE constraint failed: employers.phone" in error_msg:
            logging.warning(f"Телефон {user_data.get('phone', '')} уже зарегистрирован")
        elif "UNIQUE constraint failed: employers.email" in error_msg:
            logging.warning(f"Email {user_data.get('email', '')} уже зарегистрирован")

        return False
    except Exception as e:
        logging.error(f"Неизвестная ошибка создания работодателя: {e}", exc_info=True)
        return False


# ================= ОБНОВЛЕНИЕ ДАННЫХ =================
def update_seeker_profile(telegram_id: int, **updates: Any) -> bool:  # noqa: C901
    """Обновление профиля соискателя"""
    if not updates:
        return False

    try:
        allowed_fields = {
            "profession",
            "skills",
            "experience",
            "education",
            "languages",
            "full_name",
            "age",
            "phone",
            "email",
            "status",
            "city",
        }

        set_parts = []
        values = []

        for key, value in updates.items():
            if key in allowed_fields and value is not None:
                if key == "age":
                    try:
                        age = int(value)
                        if age < 16 or age > 100:
                            continue
                    except (ValueError, TypeError):
                        continue

                set_parts.append(f"{key} = ?")
                values.append(value)

        if not set_parts:
            return False

        values.append(telegram_id)

        query = f"UPDATE job_seekers SET {', '.join(set_parts)} WHERE telegram_id = ?"  # nosec
        result = execute_query(query, tuple(values))

        if result > 0:
            logging.info(f"Профиль соискателя {telegram_id} обновлен")
            invalidate_user_cache(telegram_id)
            invalidate_seekers_cache()
            return True
        else:
            logging.warning(f"Соискатель с ID {telegram_id} не найден для обновления")
            return False

    except Exception as e:
        logging.error(f"Ошибка обновления профиля соискателя: {e}", exc_info=True)
        return False


def update_employer_profile(telegram_id: int, **updates: Any) -> bool:
    """Обновление профиля работодателя"""
    if not updates:
        return False

    try:
        allowed_fields = {
            "company_name",
            "contact_person",
            "description",
            "business_activity",
            "phone",
            "email",
            "city",
        }

        set_parts = []
        values = []

        for key, value in updates.items():
            if key in allowed_fields and value is not None:
                set_parts.append(f"{key} = ?")
                values.append(value)

        if not set_parts:
            return False

        values.append(telegram_id)

        query = f"UPDATE employers SET {', '.join(set_parts)} WHERE telegram_id = ?"  # nosec
        result = execute_query(query, tuple(values))

        if result > 0:
            logging.info(f"Профиль работодателя {telegram_id} обновлен")
            invalidate_user_cache(telegram_id)
            return True
        else:
            logging.warning(f"Работодатель с ID {telegram_id} не найден для обновления")
            return False

    except Exception as e:
        logging.error(f"Ошибка обновления профиля работодателя: {e}", exc_info=True)
        return False


# ================= ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ =================
def get_all_seekers(
    limit: int = 100,
    offset: int = 0,
    city: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Получение всех соискателей с пагинацией и фильтрами"""
    # Проверка кэша
    cache_key = (limit, offset, city, status)
    if cache_key in _seekers_cache:
        timestamp, cached_seekers = _seekers_cache[cache_key]
        if time.time() - timestamp < SEEKERS_CACHE_TTL:
            return [s.copy() for s in cached_seekers]

    try:
        query = "SELECT * FROM job_seekers WHERE 1=1"
        params: List[Any] = []

        if city:
            query += " AND city LIKE ?"
            params.append(f"%{city}%")

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        result = execute_query(query, tuple(params), fetchall=True)
        _seekers_cache[cache_key] = (time.time(), result)
        return [s.copy() for s in result]
    except Exception as e:
        logging.error(f"Ошибка получения соискателей: {e}", exc_info=True)
        return []


def get_all_employers(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Получение всех работодателей с пагинацией"""
    try:
        return execute_query(  # type: ignore
            "SELECT * FROM employers ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            (limit, offset),
            fetchall=True,
        )
    except Exception as e:
        logging.error(f"Ошибка получения работодателей: {e}", exc_info=True)
        return []


def get_statistics() -> Dict[str, int]:
    """Получение статистики"""
    try:
        seekers_result = execute_query(
            "SELECT COUNT(*) as count FROM job_seekers", fetchone=True
        )
        employers_result = execute_query(
            "SELECT COUNT(*) as count FROM employers", fetchone=True
        )

        seekers_count = seekers_result["count"] if seekers_result else 0
        employers_count = employers_result["count"] if employers_result else 0

        return {
            "seekers": seekers_count,
            "employers": employers_count,
            "total": seekers_count + employers_count,
        }
    except Exception as e:
        logging.error(f"Ошибка получения статистики: {e}", exc_info=True)
        return {"seekers": 0, "employers": 0, "total": 0}


def delete_seeker_account(telegram_id: int) -> bool:
    """Удаление аккаунта соискателя"""
    try:
        clear_user_state(telegram_id)
        result = execute_query(
            "DELETE FROM job_seekers WHERE telegram_id = ?", (telegram_id,)
        )

        if result > 0:
            logging.info(f"Аккаунт соискателя с ID {telegram_id} удален")
            invalidate_user_cache(telegram_id)
            invalidate_seekers_cache()
            return True
        else:
            logging.warning(f"Соискатель с ID {telegram_id} не найден")
            return False

    except Exception as e:
        logging.error(f"Ошибка удаления соискателя: {e}", exc_info=True)
        return False


def delete_employer_account(telegram_id: int) -> bool:
    """Удаление аккаунта работодателя"""
    try:
        clear_user_state(telegram_id)
        result = execute_query(
            "DELETE FROM employers WHERE telegram_id = ?", (telegram_id,)
        )

        if result > 0:
            logging.info(f"Аккаунт работодателя с ID {telegram_id} удален")
            invalidate_user_cache(telegram_id)
            return True
        else:
            logging.warning(f"Работодатель с ID {telegram_id} не найден")
            return False

    except Exception as e:
        logging.error(f"Ошибка удаления работодателя: {e}", exc_info=True)
        return False
