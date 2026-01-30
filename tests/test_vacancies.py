import pytest
import time
import sqlite3
from unittest.mock import patch
from database.vacancies import (
    create_vacancy,
    update_vacancy,
    delete_vacancy,
    get_employer_vacancies,
    get_all_vacancies,
    create_application,
    check_application_exists,
    get_seeker_applications,
    get_employer_statistics,
    invalidate_vacancies_cache,
    _vacancies_cache,
    VACANCY_CACHE_TTL
)
from database.users import create_employer, create_job_seeker, get_user_by_id, get_all_seekers, update_seeker_profile

class TestVacancies:
    
    @pytest.fixture(autouse=True)
    def setup_data(self, test_db):
        """Создание тестовых данных (работодатель и соискатель)"""
        # Создаем работодателя
        emp_data = {
            'telegram_id': 100,
            'password': 'Pass1!',
            'company_name': 'Test Co',
            'contact_person': 'Boss',
            'phone': '+998901000000',
            'email': 'emp@test.uz',
            'city': 'Tashkent'
        }
        create_employer(emp_data)
        self.employer = get_user_by_id(100)
        
        # Создаем соискателя
        seeker_data = {
            'telegram_id': 200,
            'password': 'Pass1!',
            'phone': '+998902000000',
            'email': 'seeker@test.uz',
            'full_name': 'Worker',
            'age': 25,
            'city': 'Tashkent'
        }
        create_job_seeker(seeker_data)
        self.seeker = get_user_by_id(200)
        
        # Очищаем кэш перед каждым тестом
        invalidate_vacancies_cache()

    def test_create_vacancy(self):
        """Тест создания вакансии"""
        vac_data = {
            'employer_id': self.employer['id'],
            'title': 'Python Dev',
            'description': 'Good job',
            'salary': '1000$',
            'job_type': 'Remote'
        }
        assert create_vacancy(vac_data) is True
        
        vacs = get_employer_vacancies(self.employer['id'])
        assert len(vacs) == 1
        assert vacs[0]['title'] == 'Python Dev'

    def test_update_vacancy(self):
        """Тест обновления вакансии"""
        # Создаем вакансию
        create_vacancy({
            'employer_id': self.employer['id'],
            'title': 'Old Title',
            'description': 'Old Desc',
            'salary': '100$',
            'job_type': 'Office'
        })
        vacs = get_employer_vacancies(self.employer['id'])
        vac_id = vacs[0]['id']

        # Обновляем
        assert update_vacancy(vac_id, title='New Title', salary='200$') is True
        
        # Проверяем
        updated_vacs = get_employer_vacancies(self.employer['id'])
        assert updated_vacs[0]['title'] == 'New Title'
        assert updated_vacs[0]['salary'] == '200$'
        assert updated_vacs[0]['description'] == 'Old Desc' # Не изменилось

    def test_delete_vacancy(self):
        """Тест удаления вакансии"""
        # Создаем вакансию
        create_vacancy({
            'employer_id': self.employer['id'],
            'title': 'To Delete',
            'description': 'Desc'
        })
        vacs = get_employer_vacancies(self.employer['id'])
        vac_id = vacs[0]['id']

        # Удаляем
        assert delete_vacancy(vac_id) is True
        
        # Проверяем, что список пуст
        assert len(get_employer_vacancies(self.employer['id'])) == 0

    def test_delete_vacancy_with_applications(self):
        """Тест удаления вакансии с откликами (проверка каскадного удаления)"""
        # 1. Создаем вакансию и отклик
        create_vacancy({
            'employer_id': self.employer['id'],
            'title': 'To Delete With Apps',
            'description': 'Desc'
        })
        vacs = get_employer_vacancies(self.employer['id'])
        vac_id = vacs[0]['id']
        create_application(vac_id, self.seeker['id'])

        # Проверяем, что отклик создан
        assert len(get_seeker_applications(self.seeker['id'])) == 1

        # 2. Удаляем вакансию
        assert delete_vacancy(vac_id) is True

        # 3. Проверяем, что отклик тоже удален
        assert len(get_seeker_applications(self.seeker['id'])) == 0

    def test_update_vacancy_not_found(self):
        """Тест обновления несуществующей вакансии"""
        assert update_vacancy(999999, title="New Title") is False

    def test_delete_vacancy_non_existent(self):
        """Тест удаления несуществующей вакансии"""
        assert delete_vacancy(9999) is False

    def test_update_vacancy_no_data(self):
        """Тест обновления вакансии без данных"""
        create_vacancy({
            'employer_id': self.employer['id'],
            'title': 'Test', 'description': 'Test'
        })
        vacs = get_employer_vacancies(self.employer['id'])
        vac_id = vacs[0]['id']
        
        # Пустой kwargs
        assert update_vacancy(vac_id) is False
        # Недопустимый ключ
        assert update_vacancy(vac_id, invalid_key='some_value') is False

    def test_get_all_vacancies_caching(self):
        """Тест получения всех вакансий и кэширования"""
        # Создаем вакансию
        create_vacancy({
            'employer_id': self.employer['id'],
            'title': 'Cached Job',
            'description': 'Desc',
            'salary': '500$',
            'job_type': 'Office'
        })
        
        # Первый запрос (из БД)
        vacs1 = get_all_vacancies()
        assert len(vacs1) == 1
        assert vacs1[0]['title'] == 'Cached Job'
        
        # Проверяем, что попало в кэш
        cache_key = (20, 0) # limit=20, offset=0
        assert cache_key in _vacancies_cache
        
        # Второй запрос (должен быть из кэша)
        # Модифицируем кэш вручную, чтобы проверить, что берется именно он
        timestamp, cached_data = _vacancies_cache[cache_key]
        cached_data[0]['title'] = 'Modified in Cache'
        _vacancies_cache[cache_key] = (timestamp, cached_data)
        
        vacs2 = get_all_vacancies()
        assert vacs2[0]['title'] == 'Modified in Cache'

    def test_get_all_vacancies_cache_expiration(self, test_db):
        """Тест истечения срока действия кэша вакансий"""
        create_vacancy({
            'employer_id': self.employer['id'],
            'title': 'Job 1', 'description': 'D'
        })
        
        # 1. Заполняем кэш
        get_all_vacancies()
        cache_key = (20, 0)
        assert cache_key in _vacancies_cache
        
        # 2. "Перематываем" время и меняем данные в кэше
        timestamp, cached_data = _vacancies_cache[cache_key]
        _vacancies_cache[cache_key] = (timestamp - VACANCY_CACHE_TTL - 1, cached_data) # Делаем кэш просроченным
        
        # 3. Создаем новую вакансию, чтобы данные в БД изменились
        create_vacancy({
            'employer_id': self.employer['id'],
            'title': 'Job 2', 'description': 'D'
        })
        
        # 4. Запрашиваем снова, должны получить свежие данные из БД
        vacs = get_all_vacancies()
        assert len(vacs) == 2
        assert 'Job 2' in [v['title'] for v in vacs]

    def test_applications_flow(self):
        """Тест полного цикла отклика"""
        # 1. Создаем вакансию
        create_vacancy({
            'employer_id': self.employer['id'],
            'title': 'Job for Apply',
            'description': 'Desc'
        })
        vacs = get_employer_vacancies(self.employer['id'])
        vac_id = vacs[0]['id']
        
        # 2. Проверяем, что отклика нет
        assert check_application_exists(vac_id, self.seeker['id']) is False
        
        # 3. Создаем отклик
        assert create_application(vac_id, self.seeker['id'], "Hello") is True
        
        # 4. Проверяем, что отклик появился
        assert check_application_exists(vac_id, self.seeker['id']) is True
        
        # 5. Проверяем список откликов соискателя
        apps = get_seeker_applications(self.seeker['id'])
        assert len(apps) == 1
        assert apps[0]['title'] == 'Job for Apply'
        assert apps[0]['company_name'] == 'Test Co'

    def test_create_application_no_message(self):
        """Тест создания отклика без сопроводительного сообщения"""
        create_vacancy({'employer_id': self.employer['id'], 'title': 'Job', 'description': 'D'})
        vacs = get_employer_vacancies(self.employer['id'])
        vac_id = vacs[0]['id']
        assert create_application(vac_id, self.seeker['id']) is True # Вызов без message

    def test_get_seeker_applications_db_error(self):
        """Тест ошибки БД при получении откликов соискателя"""
        with patch('database.vacancies.execute_query', side_effect=Exception("DB Error")):
            result = get_seeker_applications(self.seeker['id'])
            assert result == []

    def test_check_application_exists_db_error(self):
        """Тест ошибки БД при проверке отклика"""
        with patch('database.vacancies.execute_query', side_effect=Exception("DB Error")):
            assert check_application_exists(1, 1) is False

    def test_employer_statistics(self):
        """Тест статистики работодателя"""
        # Изначально пусто
        stats = get_employer_statistics(self.employer['id'])
        assert stats['total_vacancies'] == 0
        
        # Создаем 2 вакансии
        vac_data = {'employer_id': self.employer['id'], 'title': 'J', 'description': 'D'}
        create_vacancy(vac_data)
        create_vacancy(vac_data)
        
        # Создаем отклик на первую
        vacs = get_employer_vacancies(self.employer['id'])
        create_application(vacs[0]['id'], self.seeker['id'])
        
        # Проверяем статистику
        stats = get_employer_statistics(self.employer['id'])
        assert stats['total_vacancies'] == 2
        assert stats['active_vacancies'] == 2
        assert stats['total_applications'] == 1

    def test_employer_statistics_no_apps(self):
        """Тест статистики работодателя без откликов"""
        create_vacancy({'employer_id': self.employer['id'], 'title': 'J', 'description': 'D'})
        
        stats = get_employer_statistics(self.employer['id'])
        assert stats['total_vacancies'] == 1
        assert stats['active_vacancies'] == 1
        assert stats['total_applications'] == 0

    def test_create_vacancy_error(self):
        """Тест ошибки при создании вакансии (неполные данные)"""
        # Отсутствует обязательное поле title
        bad_data = {
            'employer_id': self.employer['id'],
            'description': 'No title'
        }
        assert create_vacancy(bad_data) is False

    def test_find_candidates_logic(self):
        """Тест логики поиска кандидатов (фильтрация активных)"""
        # self.seeker уже создан в setup_data и он active по умолчанию
        
        # Создаем второго соискателя, который "Нашел работу" (inactive)
        inactive_seeker_data = {
            'telegram_id': 300,
            'password': 'Pass',
            'phone': '+998903000000',
            'email': 'inactive@test.uz',
            'full_name': 'Inactive User',
            'age': 30,
            'city': 'Tashkent'
        }
        create_job_seeker(inactive_seeker_data)
        update_seeker_profile(300, status='inactive')

        # Получаем всех соискателей
        all_seekers = get_all_seekers(limit=100)
        
        # Эмулируем логику фильтрации из хендлера
        active_seekers = [s for s in all_seekers if s.get('status') == 'active']
        
        # Должен остаться только self.seeker (Worker)
        assert len(active_seekers) == 1
        assert active_seekers[0]['full_name'] == 'Worker'
        
        # Проверяем, что Inactive User есть в общем списке, но не в активном
        names = [s['full_name'] for s in all_seekers]
        assert 'Inactive User' in names

    def test_get_employer_vacancies_db_error(self, test_db):
        """Тест ошибки БД при получении вакансий работодателя"""
        with patch('database.vacancies.execute_query', side_effect=Exception("DB connection failed")):
            result = get_employer_vacancies(self.employer['id'])
            assert result == [] # Должен вернуть пустой список

    def test_create_vacancy_exception(self):
        """Тест исключения при создании вакансии"""
        vac_data = {'employer_id': 1, 'title': 'T', 'description': 'D'}
        with patch('database.vacancies.execute_query', side_effect=Exception("DB Error")):
            assert create_vacancy(vac_data) is False

    def test_update_vacancy_exception(self):
        """Тест исключения при обновлении вакансии"""
        with patch('database.vacancies.execute_query', side_effect=Exception("DB Error")):
            assert update_vacancy(1, title="New") is False

    def test_delete_vacancy_exception(self):
        """Тест исключения при удалении вакансии"""
        with patch('database.vacancies.execute_query', side_effect=Exception("DB Error")):
            assert delete_vacancy(1) is False

    def test_get_all_vacancies_exception(self):
        """Тест исключения при получении всех вакансий"""
        with patch('database.vacancies.execute_query', side_effect=Exception("DB Error")):
            assert get_all_vacancies() == []

    def test_create_application_exception(self):
        """Тест исключения при создании отклика"""
        with patch('database.vacancies.execute_query', side_effect=Exception("DB Error")):
            assert create_application(1, 1) is False

    def test_get_employer_statistics_exception(self):
        """Тест исключения при получении статистики"""
        with patch('database.vacancies.execute_query', side_effect=Exception("DB Error")):
            stats = get_employer_statistics(1)
            assert stats['total_vacancies'] == 0

    def test_create_vacancy_integrity_error(self):
        """Тест ошибки целостности при создании вакансии"""
        vac_data = {'employer_id': 1, 'title': 'T', 'description': 'D'}
        with patch('database.vacancies.execute_query', side_effect=sqlite3.IntegrityError("FK failed")):
            assert create_vacancy(vac_data) is False

    def test_create_vacancy_db_error(self):
        """Тест ошибки БД при создании вакансии (print error)"""
        vac_data = {'employer_id': 1, 'title': 'T', 'description': 'D'}
        with patch('database.vacancies.execute_query', side_effect=Exception("DB Error")), \
             patch('builtins.print') as mock_print:
            
            assert create_vacancy(vac_data) is False
            mock_print.assert_called()