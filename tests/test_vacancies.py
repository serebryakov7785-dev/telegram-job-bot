import time
from unittest.mock import patch

import database.vacancies as vacancies


def test_create_vacancy(test_db):
    # Setup
    test_db.execute(
        "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, contact_person, city) "
        "VALUES (1, 123, 'Comp', '998901234567', 'e@mail.com', 'hash', 'Contact', 'Tashkent')"
    )

    data = {
        "employer_id": 1,
        "title": "Dev",
        "description": "Code",
        "salary": "1000",
        "job_type": "Remote",  # noqa
    }
    assert vacancies.create_vacancy(data) is True

    res = test_db.execute("SELECT * FROM vacancies").fetchall()
    assert len(res) == 1
    assert res[0]["title"] == "Dev"  # noqa


def test_create_vacancy_defaults(test_db):
    """Тест значений по умолчанию (зарплата, тип)"""
    test_db.execute(
        "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, contact_person, city) "
        "VALUES (1, 123, 'Comp', '998901234567', 'e@mail.com', 'hash', 'Contact', 'Tashkent')"
    )
    data = {"employer_id": 1, "title": "Minimal", "description": "Desc"}
    assert vacancies.create_vacancy(data) is True
    res = test_db.execute("SELECT * FROM vacancies WHERE title='Minimal'").fetchone()
    assert res["salary"] == "Не указана"
    assert res["job_type"] == "Полный день"


def test_update_vacancy(test_db):
    test_db.execute(
        "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, contact_person, city) "
        "VALUES (1, 123, 'Comp', '998901234567', 'e@mail.com', 'hash', 'Contact', 'Tashkent')"
    )
    test_db.execute(
        "INSERT INTO vacancies (id, employer_id, title, description, status) VALUES (1, 1, 'Old', 'Desc', 'active')"
    )

    assert vacancies.update_vacancy(1, title="New") is True

    res = test_db.execute("SELECT * FROM vacancies WHERE id=1").fetchone()
    assert res["title"] == "New"

    # Invalid update (no allowed keys)
    assert vacancies.update_vacancy(1, invalid_field="X") is False
    # Update non-existent vacancy
    assert vacancies.update_vacancy(999, title="Ghost") is False


def test_update_vacancy_no_updates_call(test_db):
    """Проверка, что БД не вызывается, если нет валидных полей для обновления"""
    with patch("database.vacancies.execute_query") as mock_query:
        # Передаем только невалидные поля
        assert vacancies.update_vacancy(1, invalid_field="X") is False
        # execute_query НЕ должен быть вызван
        mock_query.assert_not_called()


def test_delete_vacancy(test_db):
    test_db.execute(
        "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, contact_person, city) "
        "VALUES (1, 123, 'Comp', '998901234567', 'e@mail.com', 'hash', 'Contact', 'Tashkent')"
    )
    test_db.execute(
        "INSERT INTO vacancies (id, employer_id, title, description, status) VALUES (1, 1, 'Old', 'Desc', 'active')"
    )

    assert vacancies.delete_vacancy(1) is True
    res = test_db.execute("SELECT * FROM vacancies").fetchall()
    assert len(res) == 0

    # Delete non-existent
    assert vacancies.delete_vacancy(999) is False


def test_get_all_vacancies_and_cache(test_db):
    test_db.execute(
        "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, contact_person, city) "
        "VALUES (1, 123, 'Comp', '998901234567', 'e@mail.com', 'hash', 'Contact', 'Tashkent')"
    )
    test_db.execute(
        "INSERT INTO vacancies (id, employer_id, title, description, status) VALUES (1, 1, 'V1', 'D1', 'active')"
    )

    # First call - DB hit
    res = vacancies.get_all_vacancies()
    assert len(res) == 1
    assert res[0]["title"] == "V1"

    # Second call - Cache hit (simulated by checking if it works without DB change)
    res2 = vacancies.get_all_vacancies()
    assert len(res2) == 1

    # Invalidate cache via create
    vacancies.create_vacancy({"employer_id": 1, "title": "V2", "description": "D2"})
    res3 = vacancies.get_all_vacancies()
    assert len(res3) == 2


def test_application_flow(test_db):
    test_db.execute(
        "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, contact_person, city) "
        "VALUES (1, 123, 'Comp', '998901234567', 'e@mail.com', 'hash', 'Contact', 'Tashkent')"
    )
    test_db.execute(
        "INSERT INTO job_seekers (id, telegram_id, full_name, phone, email, password_hash, age, city) "
        "VALUES (10, 456, 'Seeker', '998901112233', 's@mail.com', 'hash', 25, 'Tashkent')"
    )
    test_db.execute(
        "INSERT INTO vacancies (id, employer_id, title, description, status) VALUES (1, 1, 'Job', 'Desc', 'active')"
    )

    assert vacancies.create_application(1, 10, "Hello") is True
    assert vacancies.check_application_exists(1, 10) is True

    apps = vacancies.get_seeker_applications(10)
    assert len(apps) == 1
    assert apps[0]["message"] == "Hello"

    stats = vacancies.get_employer_statistics(1)
    assert stats["total_applications"] == 1
    assert stats["active_vacancies"] == 1


def test_error_handling(test_db):
    # Mock execute_query to raise exception
    with patch("database.vacancies.execute_query", side_effect=Exception("DB Error")):
        assert vacancies.create_vacancy({}) is False
        assert vacancies.get_all_vacancies() == []
        assert vacancies.get_employer_statistics(1)["total_vacancies"] == 0


def test_get_employer_vacancies(test_db):
    """Тест получения вакансий конкретного работодателя"""
    # Создаем работодателя
    test_db.execute(
        "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, contact_person, city) "
        "VALUES (1, 123, 'Comp', '998901234567', 'e@mail.com', 'hash', 'Contact', 'Tashkent')"
    )

    # Создаем вакансии (одна активная, одна закрытая, чтобы проверить, что возвращаются все)
    test_db.execute(
        "INSERT INTO vacancies (id, employer_id, title, description, status) VALUES (1, 1, 'V1', 'D1', 'active')"
    )
    test_db.execute(
        "INSERT INTO vacancies (id, employer_id, title, description, status) VALUES (2, 1, 'V2', 'D2', 'closed')"
    )

    # Получаем вакансии
    res = vacancies.get_employer_vacancies(1)
    assert len(res) == 2
    assert (
        res[0]["title"] == "V2"
    )  # Проверка сортировки (ORDER BY created_at DESC, id DESC)
    assert res[1]["title"] == "V1"

    # Проверяем для несуществующего работодателя
    res_empty = vacancies.get_employer_vacancies(999)
    assert res_empty == []


def test_get_all_vacancies_cache_expiration(test_db):
    """Тест истечения времени жизни кэша"""
    test_db.execute(
        "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, contact_person, city) "
        "VALUES (1, 123, 'Comp', '998901234567', 'e@mail.com', 'hash', 'Contact', 'Tashkent')"
    )
    test_db.execute(
        "INSERT INTO vacancies (id, employer_id, title, description, status) VALUES (1, 1, 'V1', 'D1', 'active')"
    )

    # 1. Заполняем кэш
    vacancies.get_all_vacancies()

    # 2. Модифицируем БД напрямую (в обход функций, чтобы не сбросить кэш)
    test_db.execute("UPDATE vacancies SET title = 'V1_Updated' WHERE id = 1")

    # 3. Проверяем, что данные берутся из кэша (старые)
    res = vacancies.get_all_vacancies()
    assert res[0]["title"] == "V1"

    # 4. Имитируем истечение времени (патчим time.time)
    # VACANCY_CACHE_TTL = 60
    with patch("time.time", return_value=time.time() + 61):
        res_expired = vacancies.get_all_vacancies()
        # Теперь должны получить обновленные данные
        assert res_expired[0]["title"] == "V1_Updated"


def test_cache_ttl_boundary(test_db):
    """Строгая проверка границы TTL кэша (убивает мутантов, меняющих константу 60)"""
    test_db.execute(
        "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, contact_person, city) "
        "VALUES (1, 123, 'Comp', '998901234567', 'e@mail.com', 'hash', 'Contact', 'Tashkent')"
    )
    test_db.execute(
        "INSERT INTO vacancies (id, employer_id, title, description, status) VALUES (1, 1, 'Original', 'D', 'active')"
    )

    # 1. Заполняем кэш
    vacancies.get_all_vacancies()

    # 2. Обновляем БД
    test_db.execute("UPDATE vacancies SET title = 'Updated' WHERE id = 1")

    # 3. Проверяем ровно через 60.1 секунду (TTL = 60)
    # Если мутант изменил TTL на 61, то вернется старое значение ('Original')
    with patch("time.time", return_value=time.time() + 60.1):
        res = vacancies.get_all_vacancies()
        assert res[0]["title"] == "Updated"


def test_get_employer_statistics_empty(test_db):
    """Тест статистики для нового работодателя (покрывает нули)"""
    test_db.execute(
        "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, contact_person, city) "
        "VALUES (1, 123, 'Comp', '998901234567', 'e@mail.com', 'hash', 'Contact', 'Tashkent')"
    )
    stats = vacancies.get_employer_statistics(1)
    assert stats["total_vacancies"] == 0
    assert stats["active_vacancies"] == 0
    assert stats["total_applications"] == 0


def test_check_application_exists_false(test_db):
    assert vacancies.check_application_exists(1, 10) is False


def test_get_seeker_applications_empty(test_db):
    assert vacancies.get_seeker_applications(10) == []
