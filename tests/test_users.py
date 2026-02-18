import sqlite3
import time
from typing import Any, Dict, cast

from database.core import verify_password
from database.users import (
    _seekers_cache,
    _user_cache,
    create_employer,
    create_job_seeker,
    delete_employer_account,
    delete_seeker_account,
    get_all_employers,
    get_all_seekers,
    get_statistics,
    get_user_by_credentials,
    get_user_by_id,
    invalidate_seekers_cache,
    invalidate_user_cache,
    update_employer_profile,
    update_seeker_profile,
    update_telegram_id,
)


class TestUserOperations:

    def test_create_and_get_seeker(self, test_db):
        user_data = {
            "telegram_id": 1001,
            "password": "SecurePassword1!",
            "phone": "+998901234567",
            "email": "seeker@test.uz",
            "full_name": "Test Seeker",
            "age": 25,
            "city": "Tashkent",
        }

        # 1. Создание
        assert create_job_seeker(user_data) is True

        # 2. Поиск по ID
        user = get_user_by_id(1001)
        assert user is not None
        assert user is not None
        assert user["full_name"] == "Test Seeker"
        assert user["role"] == "seeker"

        # 3. Проверка хэша пароля (безопасность)
        assert user["password_hash"] != "SecurePassword1!"
        assert verify_password(user["password_hash"], "SecurePassword1!") is True

    def test_create_employer(self, test_db):
        user_data = {
            "telegram_id": 2002,
            "password": "CompanyPass1!",
            "company_name": "Test Corp",
            "contact_person": "Director",
            "phone": "+998931234567",
            "email": "corp@test.uz",
            "city": "Samarkand",
            "description": "A great place to work",
            "business_activity": "Software Development",
        }

        assert create_employer(user_data) is True

        user = get_user_by_id(2002)
        assert user is not None
        assert user is not None
        assert user["company_name"] == "Test Corp"
        assert user["role"] == "employer"
        assert user["description"] == "A great place to work"
        assert user["business_activity"] == "Software Development"

        # Проверка хэша пароля
        assert user["password_hash"] != "CompanyPass1!"
        assert verify_password(user["password_hash"], "CompanyPass1!") is True

    def test_duplicate_registration(self, test_db):
        user_data = {
            "telegram_id": 1001,
            "password": "Pass",
            "phone": "+998900000000",
            "email": "dup@test.uz",
            "full_name": "User",
            "age": 20,
            "city": "Tashkent",
        }

        assert create_job_seeker(user_data) is True
        # Попытка создать с тем же ID
        assert create_job_seeker(user_data) is False

    def test_update_seeker_profile(self, test_db):
        """Тест обновления профиля соискателя"""
        # Создаем пользователя
        create_job_seeker(
            {
                "telegram_id": 3003,
                "password": "P",
                "phone": "998901112233",
                "email": "u@u.uz",
                "full_name": "Old Name",
                "age": 20,
                "city": "Tashkent",
            }
        )

        # Обновляем
        updates = {"full_name": "New Name", "age": 21}
        assert update_seeker_profile(3003, **updates) is True

        # Проверяем
        user = get_user_by_id(3003)
        assert user is not None
        assert user is not None
        assert user["full_name"] == "New Name"
        assert user["age"] == 21

    def test_update_employer_profile(self, test_db):
        """Тест обновления профиля работодателя"""
        # Создаем работодателя
        create_employer(
            {
                "telegram_id": 4004,
                "password": "P",
                "company_name": "Old Company",
                "contact_person": "Old Person",
                "phone": "998904445566",
                "email": "e@e.uz",
                "city": "Bukhara",
            }
        )

        # Обновляем
        updates = {
            "company_name": "New Company",
            "city": "Tashkent",
            "description": "Updated description",
        }
        assert update_employer_profile(4004, **updates) is True

        # Проверяем
        user = get_user_by_id(4004)
        assert user is not None
        assert user is not None
        assert user["company_name"] == "New Company"
        assert user["city"] == "Tashkent"
        assert user["description"] == "Updated description"
        # Проверяем, что другие поля не изменились
        assert user["contact_person"] == "Old Person"
        assert user is not None

    def test_get_all_seekers_pagination(self, test_db):
        """Тест пагинации для списка соискателей"""
        # Создаем 15 соискателей
        for i in range(15):
            create_job_seeker(
                {
                    "telegram_id": 5000 + i,
                    "password": "p",
                    "phone": f"9989050000{i:02d}",
                    "email": f"s{i}@test.uz",
                    "full_name": f"Seeker {i}",
                    "age": 20,
                    "city": "T",
                }
            )

        # Получаем первую страницу
        page1 = get_all_seekers(limit=10, offset=0)
        assert len(page1) == 10
        # Проверяем порядок (DESC по created_at, т.е. последние созданные первыми)
        assert page1[0]["full_name"] == "Seeker 14"
        assert page1[9]["full_name"] == "Seeker 5"

        # Получаем вторую страницу
        page2 = get_all_seekers(limit=10, offset=10)
        assert len(page2) == 5
        assert page2[0]["full_name"] == "Seeker 4"
        assert page2[4]["full_name"] == "Seeker 0"

        # Получаем пустую страницу
        page3 = get_all_seekers(limit=10, offset=20)
        assert len(page3) == 0

    def test_get_statistics(self, test_db):
        """Тест получения общей статистики"""
        # Начальное состояние
        stats = get_statistics()
        assert stats["seekers"] == 0
        assert stats["employers"] == 0
        assert stats["total"] == 0

        # Добавляем 3 соискателей
        for i in range(3):
            create_job_seeker(
                {
                    "telegram_id": 6000 + i,
                    "password": "p",
                    "phone": f"9989060000{i:02d}",
                    "email": f"stat_s{i}@test.uz",
                    "full_name": f"Stat Seeker {i}",
                    "age": 20,
                    "city": "T",
                }
            )

        # Добавляем 2 работодателей
        for i in range(2):
            create_employer(
                {
                    "telegram_id": 7000 + i,
                    "password": "p",
                    "company_name": f"Stat Co {i}",
                    "contact_person": "CP",
                    "phone": f"9989070000{i:02d}",
                    "email": f"stat_e{i}@test.uz",
                    "city": "T",
                }
            )

        # Проверяем статистику снова
        stats = get_statistics()
        assert stats["seekers"] == 3
        assert stats["employers"] == 2
        assert stats["total"] == 5

    def test_create_seeker_duplicate_phone(self, test_db):
        """Тест создания соискателя с дубликатом телефона"""
        create_job_seeker(
            {
                "telegram_id": 8001,
                "password": "p",
                "phone": "+998908000001",
                "email": "user1@test.com",
                "full_name": "User One",
                "age": 20,
                "city": "T",
            }
        )
        # Попытка создать второго с тем же телефоном
        result = create_job_seeker(
            {
                "telegram_id": 8002,
                "password": "p",
                "phone": "+998908000001",
                "email": "user2@test.com",
                "full_name": "User Two",
                "age": 20,
                "city": "T",
            }
        )
        assert result is False

    def test_create_seeker_duplicate_email(self, test_db):
        """Тест создания соискателя с дубликатом email"""
        create_job_seeker(
            {
                "telegram_id": 8003,
                "password": "p",
                "phone": "+998908000003",
                "email": "duplicate@test.com",
                "full_name": "User Three",
                "age": 20,
                "city": "T",
            }
        )
        # Попытка создать второго с тем же email
        result = create_job_seeker(
            {
                "telegram_id": 8004,
                "password": "p",
                "phone": "+998908000004",
                "email": "duplicate@test.com",
                "full_name": "User Four",
                "age": 20,
                "city": "T",
            }
        )
        assert result is False

    def test_get_user_by_id_caching(self, test_db):
        """Тест кэширования для get_user_by_id"""
        user_data = {
            "telegram_id": 12001,
            "password": "p",
            "phone": "12001",
            "email": "cache@test.com",
            "full_name": "Cache User",
            "age": 20,
            "city": "T",
        }
        create_job_seeker(user_data)

        # 1. Первый вызов - из БД
        user1 = get_user_by_id(12001)
        assert user1 is not None
        assert user1["full_name"] == "Cache User"
        assert user1 is not None
        assert 12001 in _user_cache

        # 2. Модифицируем кэш, чтобы убедиться, что второй вызов идет из него
        _user_cache[12001] = (
            time.time(),
            {"full_name": "Cached Name", "role": "seeker"},
        )
        user2 = get_user_by_id(12001)
        assert user2 is not None
        assert user2["full_name"] == "Cached Name"

        # 3. Сбрасываем кэш и проверяем, что данные снова из БД
        invalidate_user_cache(12001)
        assert 12001 not in _user_cache
        user3 = get_user_by_id(12001)
        assert user3 is not None
        assert user3["full_name"] == "Cache User"

    def test_get_all_seekers_caching(self, test_db):
        """Тест кэширования для get_all_seekers"""
        create_job_seeker(
            {
                "telegram_id": 13001,
                "password": "p",
                "phone": "13001",
                "email": "13001@a.a",
                "full_name": "Seeker A",
                "age": 20,
                "city": "T",
            }
        )

        # 1. Первый вызов - из БД
        seekers1 = get_all_seekers(limit=10, offset=0)
        assert len(seekers1) == 1
        cache_key = (10, 0, None, None)
        assert cache_key in _seekers_cache

        # 2. Модифицируем кэш
        timestamp, cached_data = _seekers_cache[cache_key]
        cached_data[0]["full_name"] = "Cached Seeker"
        _seekers_cache[cache_key] = (timestamp, cached_data)
        seekers2 = get_all_seekers(limit=10, offset=0)
        assert seekers2[0]["full_name"] == "Cached Seeker"

        # 3. Инвалидация кэша
        invalidate_seekers_cache()
        assert cache_key not in _seekers_cache
        seekers3 = get_all_seekers(limit=10, offset=0)
        assert seekers3[0]["full_name"] == "Seeker A"

    def test_update_seeker_profile_invalid_age(self, test_db):
        """Тест обновления профиля с невалидным возрастом"""
        create_job_seeker(
            {
                "telegram_id": 14001,
                "password": "p",
                "phone": "14001",
                "email": "14001@a.a",
                "full_name": "Age Test",
                "age": 30,
                "city": "T",
            }
        )
        assert update_seeker_profile(14001, age="abc") is False
        assert update_seeker_profile(14001, age=15) is False
        user = get_user_by_id(14001)
        assert user is not None
        # Mypy needs help narrowing Optional types
        user = cast(Dict[str, Any], user)
        assert user["age"] == 30

    def test_get_all_employers(self, test_db):
        """Тест получения списка работодателей"""
        create_employer(
            {
                "telegram_id": 9001,
                "password": "p",
                "company_name": "Co 1",
                "contact_person": "CP",
                "phone": "998909000001",
                "email": "co1@test.com",
                "city": "T",
            }
        )
        create_employer(
            {
                "telegram_id": 9002,
                "password": "p",
                "company_name": "Co 2",
                "contact_person": "CP",
                "phone": "998909000002",
                "email": "co2@test.com",
                "city": "T",
            }
        )
        employers = get_all_employers(limit=5)
        assert len(employers) == 2
        assert employers[0]["company_name"] == "Co 2"  # Sorted by created_at desc

    def test_delete_accounts(self, test_db):
        """Тест удаления аккаунтов"""
        # Создаем
        create_job_seeker(
            {
                "telegram_id": 10001,
                "password": "p",
                "phone": "10001",
                "email": "10001@a.a",
                "full_name": "del",
                "age": 20,
                "city": "T",
            }
        )
        create_employer(
            {
                "telegram_id": 10002,
                "password": "p",
                "company_name": "del_co",
                "contact_person": "CP",
                "phone": "10002",
                "email": "10002@a.a",
                "city": "T",
            }
        )

        # Проверяем, что созданы
        assert get_user_by_id(10001) is not None
        assert get_user_by_id(10002) is not None
        assert get_user_by_id(10002) is not None
        assert get_user_by_id(10002) is not None
        assert get_user_by_id(10002) is not None

        # Удаляем
        assert delete_seeker_account(10001) is True
        assert delete_employer_account(10002) is True

        # Проверяем, что удалены
        assert get_user_by_id(10001) is None
        assert get_user_by_id(10002) is None
        # Проверяем, что удаление несуществующего вернет False
        assert delete_seeker_account(10001) is False

        # Проверяем для работодателя
        assert delete_employer_account(10002) is False

    def test_update_telegram_id(self, test_db):
        """Тест обновления telegram_id"""
        # Создаем
        create_job_seeker(
            {
                "telegram_id": 11001,
                "password": "p",
                "phone": "11001",
                "email": "11001@a.a",
                "full_name": "upd",
                "age": 20,
                "city": "T",
            }
        )
        user = get_user_by_credentials("11001@a.a")[0]
        # Обновляем
        assert update_telegram_id(11001, 11002, "seeker", user["id"]) is True
        # Проверяем
        assert get_user_by_id(11001) is None
        new_user = get_user_by_id(11002)
        assert new_user is not None
        assert new_user is not None
        if new_user:
            assert new_user["full_name"] == "upd"

    def test_update_telegram_id_integrity_error(self, test_db):
        """Тест ошибки обновления telegram_id при дубликате"""
        # Создаем
        create_job_seeker(
            {
                "telegram_id": 11001,
                "password": "p",
                "phone": "11001",
                "email": "11001@a.a",
                "full_name": "upd",
                "age": 20,
                "city": "T",
            }
        )
        user = get_user_by_credentials("11001@a.a")[0]
        # Создаем второго пользователя с ID, на который будем обновлять
        create_job_seeker(
            {
                "telegram_id": 11002,
                "password": "p",
                "phone": "11002",
                "email": "11002@a.a",
                "full_name": "existing",
                "age": 20,
                "city": "T",
            }
        )
        # Пытаемся обновить telegram_id первого пользователя на ID второго (уже занят)
        assert update_telegram_id(11001, 11002, "seeker", user["id"]) is False

    def test_get_user_by_credentials_not_found(self, test_db):
        """Тест поиска по несуществующим данным"""
        user, role = get_user_by_credentials("nonexistent@user.com")
        assert user is None
        assert role == ""

    def test_get_user_by_id_exception(self, test_db):
        """Тест ошибки БД при получении пользователя"""
        from unittest.mock import patch

        with patch("database.users.execute_query", side_effect=Exception("DB Error")):
            user = get_user_by_id(999)
            assert user is None

    def test_get_user_by_credentials_seeker(self, test_db):
        """Тест поиска соискателя по email"""
        create_job_seeker(
            {
                "telegram_id": 15001,
                "password": "p",
                "phone": "+998901500001",
                "email": "cred_seeker@test.com",
                "full_name": "Cred Seeker",
                "age": 20,
                "city": "T",
            }
        )
        user, role = get_user_by_credentials("cred_seeker@test.com")
        assert user is not None
        user = cast(Dict[str, Any], user)
        assert role == "seeker"
        assert user["full_name"] == "Cred Seeker"

    def test_get_user_by_credentials_employer(self, test_db):
        """Тест поиска работодателя по телефону"""
        create_employer(
            {
                "telegram_id": 15002,
                "password": "p",
                "company_name": "Cred Co",
                "contact_person": "CP",
                "phone": "+998901500002",
                "email": "cred_emp@test.com",
                "city": "T",
            }
        )
        user, role = get_user_by_credentials("+998901500002")
        assert user is not None
        user = cast(Dict[str, Any], user)
        assert role == "employer"
        assert user["company_name"] == "Cred Co"

    def test_get_user_by_credentials_exception(self, test_db):
        """Тест ошибки БД при поиске по учетным данным"""
        from unittest.mock import patch

        with patch("database.users.execute_query", side_effect=Exception("DB Error")):
            user, role = get_user_by_credentials("any")
            assert user is None
            assert role == ""

    def test_update_telegram_id_no_last_login_column(self, test_db):
        """Тест обновления telegram_id в таблице без last_login"""
        from unittest.mock import patch

        create_job_seeker(
            {
                "telegram_id": 16001,
                "password": "p",
                "phone": "16001",
                "email": "16001@a.a",
                "full_name": "upd",
                "age": 20,
                "city": "T",
            }
        )
        user = get_user_by_credentials("16001@a.a")[0]

        with patch("database.users.execute_query") as mock_execute:
            mock_execute.side_effect = [
                sqlite3.OperationalError("no such column: last_login"),
                1,
                1,
            ]

            assert update_telegram_id(16001, 16002, "seeker", user["id"]) is True
            assert mock_execute.call_count == 3
            assert "last_login" not in mock_execute.call_args_list[1][0][0]

    def test_update_seeker_profile_no_updates(self, test_db):
        """Тест обновления профиля соискателя без данных для обновления"""
        assert update_seeker_profile(3003) is False

    def test_update_employer_profile_no_updates(self, test_db):
        """Тест обновления профиля работодателя без данных для обновления"""
        assert update_employer_profile(4004) is False

    def test_update_seeker_profile_not_found(self, test_db):
        """Тест обновления несуществующего соискателя"""
        assert update_seeker_profile(9999, full_name="Ghost") is False

    def test_update_employer_profile_not_found(self, test_db):
        """Тест обновления несуществующего работодателя"""
        assert update_employer_profile(9999, company_name="Ghost Inc.") is False

    def test_get_all_seekers_exception(self, test_db):
        """Тест ошибки БД при получении всех соискателей"""
        from unittest.mock import patch

        with patch("database.users.execute_query", side_effect=Exception("DB Error")):
            result = get_all_seekers()
            assert result == []

    def test_get_all_employers_exception(self, test_db):
        """Тест ошибки БД при получении всех работодателей"""
        from unittest.mock import patch

        with patch("database.users.execute_query", side_effect=Exception("DB Error")):
            result = get_all_employers()
            assert result == []

    def test_get_statistics_exception(self, test_db):
        """Тест ошибки БД при получении статистики"""
        from unittest.mock import patch

        with patch("database.users.execute_query", side_effect=Exception("DB Error")):
            stats = get_statistics()
            assert stats == {"seekers": 0, "employers": 0, "total": 0}

    def test_delete_seeker_exception(self, test_db):
        """Тест ошибки БД при удалении соискателя"""
        from unittest.mock import patch

        with patch("database.users.execute_query", side_effect=Exception("DB Error")):
            assert delete_seeker_account(10001) is False

    def test_delete_employer_exception(self, test_db):
        """Тест ошибки БД при удалении работодателя"""
        from unittest.mock import patch

        with patch("database.users.execute_query", side_effect=Exception("DB Error")):
            assert delete_employer_account(10002) is False

    def test_update_telegram_id_generic_exception(self, test_db):
        """Тест общей ошибки при обновлении telegram_id"""
        from unittest.mock import patch

        with patch(
            "database.users.execute_query", side_effect=Exception("Generic Error")
        ):
            assert update_telegram_id(1, 2, "seeker", 1) is False

    def test_create_job_seeker_fail_result(self, test_db):
        """Тест неудачного создания соискателя (result <= 0)"""
        from unittest.mock import patch

        # Mock execute_query to return 0 (no rows affected)
        with patch("database.users.execute_query", return_value=0):
            assert (
                create_job_seeker(
                    {
                        "telegram_id": 1,
                        "password": "p",
                        "phone": "1",
                        "email": "e",
                        "full_name": "n",
                        "age": 20,
                        "city": "c",
                    }
                )
                is False
            )

    def test_create_job_seeker_integrity_error_email(self, test_db):
        """Тест ошибки уникальности email соискателя"""
        import sqlite3
        from unittest.mock import patch

        with patch(
            "database.users.execute_query",
            side_effect=sqlite3.IntegrityError(
                "UNIQUE constraint failed: job_seekers.email"
            ),
        ):
            assert (
                create_job_seeker(
                    {
                        "telegram_id": 1,
                        "password": "p",
                        "phone": "1",
                        "email": "e",
                        "full_name": "n",
                        "age": 20,
                        "city": "c",
                    }
                )
                is False
            )

    def test_create_employer_fail_result(self, test_db):
        """Тест неудачного создания работодателя (result <= 0)"""
        from unittest.mock import patch

        with patch("database.users.execute_query", return_value=0):
            assert (
                create_employer(
                    {
                        "telegram_id": 1,
                        "password": "p",
                        "company_name": "c",
                        "contact_person": "cp",
                        "phone": "1",
                        "email": "e",
                        "city": "c",
                    }
                )
                is False
            )

    def test_create_employer_integrity_error_phone(self, test_db):
        """Тест ошибки уникальности телефона работодателя"""
        import sqlite3
        from unittest.mock import patch

        with patch(
            "database.users.execute_query",
            side_effect=sqlite3.IntegrityError(
                "UNIQUE constraint failed: employers.phone"
            ),
        ):
            assert (
                create_employer(
                    {
                        "telegram_id": 1,
                        "password": "p",
                        "company_name": "c",
                        "contact_person": "cp",
                        "phone": "1",
                        "email": "e",
                        "city": "c",
                    }
                )
                is False
            )

    def test_create_employer_integrity_error_email(self, test_db):
        """Тест ошибки уникальности email работодателя"""
        import sqlite3
        from unittest.mock import patch

        with patch(
            "database.users.execute_query",
            side_effect=sqlite3.IntegrityError(
                "UNIQUE constraint failed: employers.email"
            ),
        ):
            assert (
                create_employer(
                    {
                        "telegram_id": 1,
                        "password": "p",
                        "company_name": "c",
                        "contact_person": "cp",
                        "phone": "1",
                        "email": "e",
                        "city": "c",
                    }
                )
                is False
            )

    def test_create_employer_duplicate(self, test_db):
        """Тест создания дубликата работодателя (покрытие строк 199-200)"""
        data = {
            "telegram_id": 20001,
            "password": "p",
            "company_name": "C",
            "contact_person": "P",
            "phone": "20001",
            "email": "20001@e.e",
            "city": "C",
        }
        create_employer(data)
        assert create_employer(data) is False

    def test_update_seeker_profile_age_error(self, test_db):
        """Тест ошибки преобразования возраста (покрытие строк 288-290)"""
        create_job_seeker(
            {
                "telegram_id": 1,
                "password": "p",
                "phone": "1",
                "email": "e",
                "full_name": "n",
                "age": 20,
                "city": "c",
            }
        )
        # Передаем некорректный возраст И валидное поле.
        # Функция должна проигнорировать возраст (continue в except) и обновить имя.
        assert update_seeker_profile(1, age="invalid", full_name="Updated Name") is True

        user = get_user_by_id(1)
        assert user is not None
        assert user["age"] == 20  # Не изменился
        assert user["full_name"] == "Updated Name"  # Изменился

    def test_update_employer_profile_no_valid_fields(self, test_db):
        """Тест обновления работодателя без валидных полей (покрытие 327-329)"""
        create_employer(
            {
                "telegram_id": 2,
                "password": "p",
                "company_name": "C",
                "contact_person": "P",
                "phone": "2",
                "email": "e",
                "city": "C",
            }
        )
        # Передаем только недопустимое поле или None
        assert update_employer_profile(2, invalid_field="val") is False

    def test_update_telegram_id_raise_exception(self, test_db):
        """Тест проброса исключения в update_telegram_id (покрытие 132-133)"""
        import sqlite3
        from unittest.mock import patch

        # Мокаем execute_query чтобы он выбросил ошибку, отличную от "no such column"
        with patch(
            "database.users.execute_query",
            side_effect=sqlite3.OperationalError("Some other error"),
        ):
            assert update_telegram_id(1, 2, "seeker", 1) is False

    def test_update_employer_profile_loop(self, test_db):
        """Тест цикла обновления профиля работодателя (покрытие строк 327-329)"""
        create_employer(
            {
                "telegram_id": 2,
                "password": "p",
                "company_name": "c",
                "contact_person": "cp",
                "phone": "2",
                "email": "e",
                "city": "c",
            }
        )
        # Передаем None и недопустимое поле
        assert (
            update_employer_profile(2, company_name=None, invalid_field="val") is False
        )
        # Передаем валидное поле
        assert update_employer_profile(2, company_name="New Co") is True

    def test_create_employer_generic_exception(self, test_db):
        """Тест общей ошибки при создании работодателя"""
        from unittest.mock import patch

        with patch(
            "database.users.execute_query", side_effect=Exception("Generic Error")
        ):
            assert (
                create_employer(
                    {
                        "telegram_id": 1,
                        "password": "p",
                        "company_name": "c",
                        "contact_person": "cp",
                        "phone": "1",
                        "email": "e",
                        "city": "c",
                    }
                )
                is False
            )

    def test_update_seeker_profile_fail_result(self, test_db):
        """Тест неудачного обновления профиля соискателя (result <= 0)"""
        from unittest.mock import patch

        with patch("database.users.execute_query", return_value=0):
            assert update_seeker_profile(1, full_name="New") is False

    def test_update_employer_profile_fail_result(self, test_db):
        """Тест неудачного обновления профиля работодателя (result <= 0)"""
        from unittest.mock import patch

        with patch("database.users.execute_query", return_value=0):
            assert update_employer_profile(1, company_name="New") is False

    def test_create_seeker_integrity_errors(self, test_db):
        """Тест различных ошибок целостности при создании соискателя"""
        from unittest.mock import patch

        # 1. Duplicate ID
        with patch(
            "database.users.execute_query",
            side_effect=sqlite3.IntegrityError(
                "UNIQUE constraint failed: job_seekers.telegram_id"
            ),
        ):
            assert create_job_seeker({"telegram_id": 1}) is False

        # 2. Duplicate Phone
        with patch(
            "database.users.execute_query",
            side_effect=sqlite3.IntegrityError(
                "UNIQUE constraint failed: job_seekers.phone"
            ),
        ):
            assert create_job_seeker({"telegram_id": 1, "phone": "123"}) is False

        # 3. Duplicate Email
        with patch(
            "database.users.execute_query",
            side_effect=sqlite3.IntegrityError(
                "UNIQUE constraint failed: job_seekers.email"
            ),
        ):
            assert create_job_seeker({"telegram_id": 1, "email": "a@a.a"}) is False

    def test_create_employer_integrity_errors(self, test_db):
        """Тест различных ошибок целостности при создании работодателя"""
        from unittest.mock import patch

        # 1. Duplicate ID
        with patch(
            "database.users.execute_query",
            side_effect=sqlite3.IntegrityError(
                "UNIQUE constraint failed: employers.telegram_id"
            ),
        ):
            assert create_employer({"telegram_id": 1}) is False

        # 2. Duplicate Phone
        with patch(
            "database.users.execute_query",
            side_effect=sqlite3.IntegrityError(
                "UNIQUE constraint failed: employers.phone"
            ),
        ):
            assert create_employer({"telegram_id": 1, "phone": "123"}) is False

        # 3. Duplicate Email
        with patch(
            "database.users.execute_query",
            side_effect=sqlite3.IntegrityError(
                "UNIQUE constraint failed: employers.email"
            ),
        ):
            assert create_employer({"telegram_id": 1, "email": "a@a.a"}) is False
