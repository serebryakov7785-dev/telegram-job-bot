from unittest.mock import patch

import database.vacancies as vacancies


def test_create_vacancy_exception():
    with patch("database.vacancies.execute_query", side_effect=Exception("DB Error")):
        assert (
            vacancies.create_vacancy(
                {"employer_id": 1, "title": "T", "description": "D"}
            )
            is False
        )


def test_update_vacancy_exception():
    with patch("database.vacancies.execute_query", side_effect=Exception("DB Error")):
        assert vacancies.update_vacancy(1, title="New") is False


def test_delete_vacancy_exception():
    with patch("database.vacancies.execute_query", side_effect=Exception("DB Error")):
        assert vacancies.delete_vacancy(1) is False


def test_get_employer_vacancies_exception():
    with patch("database.vacancies.execute_query", side_effect=Exception("DB Error")):
        assert vacancies.get_employer_vacancies(1) == []


def test_get_all_vacancies_exception():
    with patch("database.vacancies.execute_query", side_effect=Exception("DB Error")):
        assert vacancies.get_all_vacancies() == []


def test_get_seeker_applications_exception():
    with patch("database.vacancies.execute_query", side_effect=Exception("DB Error")):
        assert vacancies.get_seeker_applications(1) == []


def test_create_application_exception():
    with patch("database.vacancies.execute_query", side_effect=Exception("DB Error")):
        assert vacancies.create_application(1, 1) is False


def test_check_application_exists_exception():
    with patch("database.vacancies.execute_query", side_effect=Exception("DB Error")):
        assert vacancies.check_application_exists(1, 1) is False


def test_get_employer_statistics_exception():
    with patch("database.vacancies.execute_query", side_effect=Exception("DB Error")):
        stats = vacancies.get_employer_statistics(1)
        assert stats["total_vacancies"] == 0
        assert stats["active_vacancies"] == 0
        assert stats["total_applications"] == 0
