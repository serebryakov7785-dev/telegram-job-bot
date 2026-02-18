from unittest.mock import MagicMock

import pytest

from database.users import create_employer, create_job_seeker, get_user_by_id
from database.vacancies import (
    check_application_exists,
    create_application,
    create_vacancy,
    get_all_vacancies,
)


class TestIntegrationFlow:

    @pytest.fixture
    def mock_bot(self):
        return MagicMock()

    def test_full_hiring_flow(self, test_db, mock_bot):
        """
        Интеграционный тест полного цикла найма:
        1. Регистрация работодателя
        2. Создание вакансии
        3. Регистрация соискателя
        4. Поиск вакансий соискателем
        5. Отклик на вакансию
        """

        # 1. Регистрация работодателя
        employer_data = {
            'telegram_id': 1001,
            'password': 'Pass',
            'company_name': 'Integration Corp',
            'contact_person': 'HR Manager',
            'phone': '+998901111111',
            'email': 'hr@corp.uz',
            'city': 'Tashkent',
            'business_activity': 'IT'
        }
        assert create_employer(employer_data) is True
        employer = get_user_by_id(1001)
        assert employer is not None

        # 2. Создание вакансии
        vacancy_data = {
            'employer_id': employer['id'],
            'title': 'Senior Python Developer',
            'description': 'We need a rockstar developer',
            'salary': '3000$',
            'job_type': 'Remote'
        }
        assert create_vacancy(vacancy_data) is True

        # Проверяем, что вакансия появилась в общем поиске
        vacancies = get_all_vacancies()
        assert len(vacancies) == 1
        assert vacancies[0]['title'] == 'Senior Python Developer'
        vacancy_id = vacancies[0]['id']

        # 3. Регистрация соискателя
        seeker_data = {
            'telegram_id': 2002,
            'password': 'Pass',
            'phone': '+998902222222',
            'email': 'dev@seeker.uz',
            'full_name': 'John Python',
            'age': 28,
            'city': 'Tashkent'
        }
        assert create_job_seeker(seeker_data) is True
        seeker = get_user_by_id(2002)
        assert seeker is not None

        # 4. Соискатель находит вакансию (эмуляция через БД)
        # (В реальном боте это делает SeekerHandlers.handle_find_vacancies)
        found_vacancies = get_all_vacancies()
        target_vacancy = next((v for v in found_vacancies if v['id'] == vacancy_id), None)
        assert target_vacancy is not None

        # 5. Отклик на вакансию
        # Проверяем, что отклика еще нет
        assert check_application_exists(vacancy_id, seeker['id']) is False

        # Создаем отклик
        assert create_application(vacancy_id, seeker['id']) is True

        # Проверяем, что отклик появился
        assert check_application_exists(vacancy_id, seeker['id']) is True

        # Проверяем, что работодатель видит отклик (через статистику или список)
        from database.vacancies import get_employer_statistics
        stats = get_employer_statistics(employer['id'])
        assert stats['total_applications'] == 1
