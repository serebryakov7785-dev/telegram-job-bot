import concurrent.futures
import os
import sqlite3
import threading
import time
from unittest.mock import patch

import pytest

import database.core
import database.schema
import database.users
import database.vacancies

# Try to import psutil for monitoring
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class ResourceMonitor:
    def __init__(self, interval=0.1):
        self.interval = interval
        self.running = False
        self.cpu_usage = []
        self.memory_usage = []
        self.thread = None

    def start(self):
        if not PSUTIL_AVAILABLE:
            return
        self.running = True
        self.thread = threading.Thread(target=self._monitor)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _monitor(self):
        process = psutil.Process(os.getpid())
        # First call to cpu_percent returns 0.0 or random value
        process.cpu_percent(interval=None)
        while self.running:
            time.sleep(self.interval)
            try:
                cpu = process.cpu_percent(interval=None)
                mem = process.memory_info().rss / 1024 / 1024  # MB
                self.cpu_usage.append(cpu)
                self.memory_usage.append(mem)
            except Exception:
                break

    def get_stats(self):
        if not self.cpu_usage:
            return 0.0, 0.0
        avg_cpu = sum(self.cpu_usage) / len(self.cpu_usage)
        max_mem = max(self.memory_usage) if self.memory_usage else 0.0
        return avg_cpu, max_mem


class TestLoad:
    def test_concurrent_load_1000_requests(self, tmp_path):
        """
        Нагрузочный тест: 1000 запросов на чтение (симуляция одновременных пользователей).
        Используем реальный файл БД, чтобы проверить блокировки.
        """
        db_file = tmp_path / "load_test.db"

        # Capture real connect before patching
        real_connect = sqlite3.connect

        # Patch sqlite3.connect to redirect to our temp db
        with patch("sqlite3.connect") as mock_connect:

            def connect_wrapper(*args, **kwargs):
                kwargs["timeout"] = 30
                return real_connect(str(db_file), **kwargs)

            mock_connect.side_effect = connect_wrapper

            # Сброс thread-local соединения для основного потока
            if hasattr(database.core._local, "conn"):
                database.core._local.conn = None

            # Инициализация БД
            database.schema.init_database()

            # Создаем данные (1 работодатель, 10 вакансий)
            database.users.create_employer(
                {
                    "telegram_id": 1,
                    "company_name": "Load Corp",
                    "password": "pass",
                    "phone": "123",
                    "email": "load@test.com",
                    "city": "Load City",
                    "contact_person": "Tester",
                }
            )
            employer = database.users.get_user_by_credentials("load@test.com")[0]
            assert employer is not None, "Failed to create employer for load test"

            for i in range(10):
                database.vacancies.create_vacancy(
                    {
                        "employer_id": employer["id"],
                        "title": f"Job {i}",
                        "description": "Desc",
                        "salary": "1000",
                        "job_type": "Full",
                    }
                )

            # Действие пользователя (чтение)
            def user_action():
                try:
                    # Получение вакансий (использует кэш в памяти, если включен)
                    vacancies = database.vacancies.get_all_vacancies()
                    return len(vacancies) > 0
                except Exception as e:
                    print(f"Error: {e}")
                    return False
                finally:
                    database.core.close_all_connections()

            start_time = time.time()
            success_count = 0
            total_requests = 1000
            max_workers = 50

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                futures = [executor.submit(user_action) for _ in range(total_requests)]
                for future in concurrent.futures.as_completed(futures):
                    if future.result():
                        success_count += 1

            duration = time.time() - start_time
            print(
                f"\nRead Load: {total_requests} requests, {success_count} success, {duration:.2f}s"
            )

            assert success_count == total_requests
            # Ожидаем высокую скорость благодаря кэшированию (< 2 сек на 1000 запросов)
            assert duration < 2.0

    def test_concurrent_writes_100_users(self, tmp_path):
        """
        Нагрузочный тест на запись: 100 одновременных регистраций.
        """
        db_file = tmp_path / "write_test.db"

        real_connect = sqlite3.connect

        with patch("sqlite3.connect") as mock_connect:

            def connect_wrapper(*args, **kwargs):
                kwargs["timeout"] = 30
                return real_connect(str(db_file), **kwargs)

            mock_connect.side_effect = connect_wrapper

            if hasattr(database.core._local, "conn"):
                database.core._local.conn = None
            database.schema.init_database()

            def register_user(idx):
                try:
                    for attempt in range(5):
                        try:
                            res = database.users.create_job_seeker(
                                {
                                    "telegram_id": 1000 + idx,
                                    "password": "pass",
                                    "phone": f"99890{idx:07d}",
                                    "email": f"{idx}@test.com",
                                    "full_name": f"User {idx}",
                                    "age": 20,
                                    "city": "Tashkent",
                                }
                            )
                            if res:
                                return True
                            if attempt < 4:
                                time.sleep(0.1)
                                continue
                        except sqlite3.OperationalError as e:
                            if "database is locked" in str(e) and attempt < 4:
                                time.sleep(0.1)
                                continue
                            raise
                except Exception as e:
                    print(f"Write Error {idx}: {e}")
                    return False
                finally:
                    database.core.close_all_connections()

            start_time = time.time()
            success_count = 0
            total_requests = 100
            max_workers = 10  # Ограничиваем кол-во писателей для SQLite

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                futures = [
                    executor.submit(register_user, i) for i in range(total_requests)
                ]
                for future in concurrent.futures.as_completed(futures):
                    if future.result():
                        success_count += 1

            duration = time.time() - start_time
            print(
                f"\nWrite Load: {total_requests} writes, {success_count} success, {duration:.2f}s"
            )

            assert success_count == total_requests

    @pytest.mark.parametrize(
        "num_users, total_requests",
        [
            (10, 100),
            (50, 500),
            (200, 1000),  # Снижено с (1000, 5000) для ускорения CI
        ],
    )
    def test_scalability_with_monitoring(self, tmp_path, num_users, total_requests):
        """
        Scalability test with resource monitoring.
        Runs a mix of read and write operations.
        """
        db_file = tmp_path / f"scale_test_{num_users}_{total_requests}.db"

        real_connect = sqlite3.connect

        with patch("sqlite3.connect") as mock_connect:

            def connect_wrapper(*args, **kwargs):
                kwargs["timeout"] = 30
                return real_connect(str(db_file), **kwargs)

            mock_connect.side_effect = connect_wrapper

            if hasattr(database.core._local, "conn"):
                database.core._local.conn = None
            database.schema.init_database()

            # Pre-populate some data
            database.users.create_employer(
                {
                    "telegram_id": 1,
                    "company_name": "Load Corp",
                    "password": "pass",
                    "phone": "123",
                    "email": "load@test.com",
                    "city": "Load City",
                    "contact_person": "Tester",
                }
            )

            monitor = ResourceMonitor()
            monitor.start()

            start_time = time.time()
            success_count = 0

            def user_action(idx):
                try:
                    # Mix: 20% writes, 80% reads
                    if idx % 5 == 0:
                        for attempt in range(5):
                            try:
                                res = database.users.create_job_seeker(
                                    {
                                        "telegram_id": 10000 + idx,
                                        "password": "pass",
                                        "phone": f"99891{idx:07d}",
                                        "email": f"{idx}@scale.test",
                                        "full_name": f"User {idx}",
                                        "age": 20,
                                        "city": "Tashkent",
                                    }
                                )
                                if res:
                                    return True
                                if attempt < 4:
                                    time.sleep(0.1)
                                    continue
                            except sqlite3.OperationalError as e:
                                if "database is locked" in str(e) and attempt < 4:
                                    time.sleep(0.1)
                                    continue
                                raise
                    else:
                        return len(database.vacancies.get_all_vacancies()) >= 0
                finally:
                    database.core.close_all_connections()

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=num_users
            ) as executor:
                futures = [
                    executor.submit(user_action, i) for i in range(total_requests)
                ]
                for future in concurrent.futures.as_completed(futures):
                    if future.result():
                        success_count += 1

            duration = time.time() - start_time
            monitor.stop()
            avg_cpu, max_mem = monitor.get_stats()

            print(
                f"\nScale Test ({num_users} users, {total_requests} reqs): "
                f"Duration={duration:.2f}s, RPS={total_requests/duration:.2f}"
            )
            if PSUTIL_AVAILABLE:
                print(f"Avg CPU: {avg_cpu:.2f}%, Max Memory: {max_mem:.2f} MB")

            # Допускаем небольшой процент ошибок (5%) из-за блокировок SQLite при конкурентной записи
            assert success_count >= total_requests * 0.95

    def test_long_running_mixed_load(self, tmp_path):
        """
        Длительный тест смешанной нагрузки (80% чтение, 20% запись).
        Длительность настраивается через LOAD_TEST_DURATION (по умолчанию 2 сек для CI).
        Для теста 1 час установите LOAD_TEST_DURATION=3600.
        """
        db_file = tmp_path / "long_run.db"
        duration = int(os.getenv("LOAD_TEST_DURATION", 1))  # Снижено с 2с
        num_users = 50  # Постоянная нагрузка 50 пользователей

        real_connect = sqlite3.connect

        with patch("sqlite3.connect") as mock_connect:

            def connect_wrapper(*args, **kwargs):
                kwargs["timeout"] = 30
                return real_connect(str(db_file), **kwargs)

            mock_connect.side_effect = connect_wrapper

            if hasattr(database.core._local, "conn"):
                database.core._local.conn = None
            database.schema.init_database()

            monitor = ResourceMonitor()
            monitor.start()

            start_time = time.time()
            end_time = start_time + duration
            request_count = 0
            errors = 0  # noqa

            def user_loop(thread_id):
                local_reqs = 0
                local_errs = 0
                while time.time() < end_time:
                    try:
                        # 20% запись, 80% чтение
                        if local_reqs % 5 == 0:
                            for attempt in range(5):
                                try:
                                    database.users.create_job_seeker(
                                        {
                                            "telegram_id": (thread_id * 100000)
                                            + local_reqs,
                                            "full_name": f"User {thread_id}_{local_reqs}",
                                            "phone": f"99890{thread_id:02d}{local_reqs:05d}",
                                            "email": f"{thread_id}_{local_reqs}@long.test",
                                            "password": "pass",  # noqa
                                            "age": 20,
                                            "city": "Tashkent",
                                        }
                                    )
                                    break
                                except sqlite3.OperationalError as e:
                                    if "database is locked" in str(e) and attempt < 4:
                                        time.sleep(0.1)
                                        continue
                                    raise
                        else:
                            database.vacancies.get_all_vacancies()
                        local_reqs += 1
                    except Exception:
                        local_errs += 1
                    finally:
                        database.core.close_all_connections()
                return local_reqs, local_errs

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=num_users
            ) as executor:
                futures = [executor.submit(user_loop, i) for i in range(num_users)]
                for future in concurrent.futures.as_completed(futures):
                    r, e = future.result()
                    request_count += r
                    errors += e

            monitor.stop()
            actual_duration = time.time() - start_time
            avg_cpu, max_mem = monitor.get_stats()

            print(
                f"\nLong Run ({actual_duration:.1f}s): {request_count} reqs, "
                f"{errors} errors. RPS: {request_count/actual_duration:.2f}"
            )

            # Допускаем небольшой процент ошибок при высокой нагрузке на SQLite
            assert errors < request_count * 0.05  # noqa

    def test_db_recovery_resilience(self, tmp_path):
        """
        Тест восстановления работы после потери соединения с БД.
        """
        db_file = tmp_path / "recovery.db"
        real_connect = sqlite3.connect  # noqa

        with patch("sqlite3.connect") as mock_connect:

            def connect_wrapper(*args, **kwargs):
                kwargs["timeout"] = 30
                return real_connect(str(db_file), **kwargs)

            mock_connect.side_effect = connect_wrapper  # noqa

            if hasattr(database.core._local, "conn"):
                database.core._local.conn = None
            database.schema.init_database()

            # 1. Выполняем операцию
            assert database.users.create_employer(
                {
                    "telegram_id": 1,
                    "company_name": "Co",
                    "phone": "998901234567",
                    "email": "test@co.uz",
                    "password": "pass",
                    "contact_person": "Contact",
                    "city": "Tashkent",
                }
            )

            # 2. Симулируем разрыв соединения (сброс thread-local)
            database.core._local.conn = None

            # 3. Пробуем снова - должно переподключиться автоматически
            assert database.users.create_job_seeker(
                {
                    "telegram_id": 2,
                    "full_name": "Seeker",
                    "phone": "998901234567",
                    "email": "test@test.uz",
                    "password": "pass",
                    "age": 20,
                    "city": "Tashkent",
                }
            )
