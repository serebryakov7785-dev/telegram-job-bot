import os
import sys
import time

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from database.users import create_job_seeker  # noqa: E402
from database.vacancies import create_vacancy, get_all_vacancies  # noqa: E402


class TestPerformance:

    def test_bulk_user_creation(self, test_db):
        """Тест производительности массового создания пользователей"""
        start_time = time.time()
        count = 100

        for i in range(count):
            create_job_seeker(
                {
                    "telegram_id": 10000 + i,
                    "password": "p",
                    "phone": f"+99890{i:07d}",
                    "email": f"user{i}@perf.test",
                    "full_name": f"User {i}",
                    "age": 20,
                    "city": "Tashkent",
                }
            )

        duration = time.time() - start_time
        print(f"\nCreated {count} users in {duration:.4f}s")

        # Ожидаем, что 100 вставок займут меньше 1 секунды (в in-memory DB это должно быть очень быстро)
        assert duration < 1.0

    def test_vacancy_search_performance(self, test_db):
        """Тест производительности поиска вакансий"""
        # Подготовка данных
        for i in range(50):
            create_vacancy(
                {
                    "employer_id": 1,  # Предполагаем существование
                    "title": f"Vacancy {i}",
                    "description": "Desc",
                    "salary": "100",
                    "job_type": "Full",
                }
            )

        start_time = time.time()
        # Выполняем поиск 100 раз
        for _ in range(100):
            get_all_vacancies(limit=20)

        duration = time.time() - start_time
        print(f"\nPerformed 100 searches in {duration:.4f}s")

        # С кэшированием это должно быть мгновенно
        assert duration < 0.5
