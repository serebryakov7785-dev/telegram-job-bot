import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import bot  # noqa: F401, E402
import database  # noqa: E402
import middleware  # noqa: E402
from handlers.admin import AdminHandlers  # noqa: E402
from handlers.auth import AuthHandlers  # noqa: E402
from handlers.common import CommonHandlers  # noqa: E402
from handlers.employer import EmployerHandlers  # noqa: E402
from handlers.profile import ProfileHandlers  # noqa: E402
from handlers.seeker import SeekerHandlers  # noqa: E402
from handlers.steps import StepHandlers  # noqa: E402


class TestE2EScenarios:
    @pytest.fixture
    def mock_bot(self):
        return MagicMock()

    @pytest.fixture
    def handlers(self, mock_bot):
        auth = AuthHandlers(mock_bot)
        employer = EmployerHandlers(mock_bot)
        seeker = SeekerHandlers(mock_bot)
        admin = AdminHandlers(mock_bot)
        profile = ProfileHandlers(mock_bot)
        steps = StepHandlers(mock_bot)
        steps.set_auth_handlers(auth)
        steps.set_employer_handlers(employer)
        steps.set_admin_handlers(admin)
        steps.set_profile_handlers(profile)
        return {
            "auth": auth,
            "employer": employer,
            "seeker": seeker,
            "steps": steps,
            "admin": admin,
            "profile": profile,
        }

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        return msg

    def test_employer_full_flow(self, handlers, message, test_db):
        """
        E2E: Регистрация работодателя -> Создание вакансии -> Проверка создания
        """
        user_id = message.from_user.id

        # 1. Начало регистрации
        message.text = "🏢 Я работодатель"
        handlers["auth"].handle_role_selection(message)

        # 1.1 Нажимаем "Зарегистрироваться"
        message.text = "📝 Зарегистрироваться"
        # Mock captcha generation to return fixed value
        with patch("utils.generate_captcha", return_value=("2+2", 4)):
            handlers["auth"].handle_registration_start(message)

        # Проверяем состояние
        state = database.get_user_state(user_id)
        assert state["step"] == "captcha"

        # 1.2 Ввод капчи
        message.text = "4"
        handlers["steps"].handle_steps(message)

        state = database.get_user_state(user_id)
        assert state["step"] == "company_name"

        # 2. Ввод названия компании
        message.text = "Test Corp"
        handlers["steps"].handle_steps(message)
        state = database.get_user_state(user_id)
        assert state["step"] == "phone"
        assert state["registration_data"]["company_name"] == "Test Corp"

        # 3. Ввод телефона
        message.text = "+998901234567"
        handlers["steps"].handle_steps(message)
        state = database.get_user_state(user_id)
        assert state["step"] == "email"

        # 4. Ввод email
        message.text = "corp@test.uz"
        handlers["steps"].handle_steps(message)
        state = database.get_user_state(user_id)
        assert state["step"] == "contact_person"

        # 5. Ввод контактного лица
        message.text = "Boss"
        handlers["steps"].handle_steps(message)
        state = database.get_user_state(user_id)
        assert state["step"] == "region"

        # 6. Выбор региона
        message.text = "Ташкентская обл."
        handlers["steps"].handle_steps(message)
        state = database.get_user_state(user_id)
        assert state["step"] == "city_selection"

        # 7. Выбор района (города)
        message.text = "Ташкент"
        handlers["steps"].handle_steps(message)
        state = database.get_user_state(user_id)
        assert state["step"] == "business_activity"

        # 8. Род деятельности
        message.text = "IT"
        handlers["steps"].handle_steps(message)

        # После ввода рода деятельности регистрация завершается (пароль авто-генерируется)
        # Проверяем, что состояние очищено (регистрация завершена)
        state = database.get_user_state(user_id)
        assert state == {}

        # Проверяем, что пользователь создан
        user = database.get_user_by_id(user_id)
        assert user is not None
        assert user["company_name"] == "Test Corp"

        # 10. Создание вакансии
        handlers["employer"].handle_create_vacancy(message)
        state = database.get_user_state(user_id)
        assert state["step"] == "vacancy_sphere"

        message.text = "IT и Интернет"  # sphere
        handlers["steps"].handle_steps(message)

        message.text = "Backend разработчик"  # profession
        handlers["steps"].handle_steps(message)

        # Now it should ask for description, as title is already set
        state = database.get_user_state(user_id)
        assert state["step"] == "vacancy_description"
        # description
        message.text = "Good code required for this job"
        handlers["steps"].handle_steps(message)

        # New step: Gender
        message.text = "➡️ Далее"  # gender (skip/any)
        handlers["steps"].handle_steps(message)

        message.text = "Пропустить"  # languages
        handlers["steps"].handle_steps(message)

        message.text = "1000"  # salary
        handlers["steps"].handle_steps(message)

        message.text = "Удаленная работа"  # type
        handlers["steps"].handle_steps(message)

        # Проверяем, что бот отправил сообщение об успехе
        # Это поможет понять, если что-то пошло не так (например, валидация)
        last_message = handlers["employer"].bot.send_message.call_args[0][1]
        assert "Вакансия успешно создана" in last_message

        # Проверяем, что вакансия создана
        vacancies = database.get_employer_vacancies(user["id"])
        assert len(vacancies) == 1
        assert vacancies[0]["title"] == "prof_backend"

    def test_seeker_application_flow(self, handlers, message, test_db):
        """
        E2E: Регистрация соискателя -> Поиск вакансии -> Отклик
        """
        # Сначала создадим работодателя и вакансию напрямую в БД
        test_db.execute(
            "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, contact_person) "
            "VALUES (1, 999, 'Corp', '998900000000', 'c@t.uz', 'hash', 'Contact')"
        )

        test_db.execute(
            "INSERT INTO vacancies (id, employer_id, title, description, status) "
            "VALUES (100, 1, 'Java Dev', 'Desc', 'active')"
        )

        user_id = message.from_user.id

        # 1. Регистрация соискателя (упрощенно, через прямой вызов методов, чтобы не дублировать тест выше)
        # Но используем steps для реалистичности
        message.text = "👤 Я ищу работу"
        handlers["auth"].handle_role_selection(message)

        # Пропускаем шаги до финала (симуляция)
        database.set_user_state(
            user_id,
            {
                "step": "age",
                "role": "seeker",
                "registration_data": {
                    "phone": "+998901234567",
                    "email": "s@t.uz",
                    "full_name": "Seeker",
                    "region": "Tashkent",
                    "city": "Center",
                    "password": "dummy_password",
                },
            },
        )

        message.text = "25"
        handlers["steps"].handle_steps(message)  # age -> finish

        # 2. Отклик на вакансию (callback)
        call = MagicMock()
        call.from_user.id = user_id
        call.data = "apply_100"  # vacancy_id = 100

        handlers["seeker"].handle_application_callback(call)

        # Проверяем создание отклика
        user = database.get_user_by_id(user_id)
        assert (
            user is not None
            and database.check_application_exists(100, user["id"]) is True
        )

    def test_employer_search_and_invite_flow(self, handlers, message, test_db):
        """
        E2E: Работодатель ищет сотрудников -> Находит -> Приглашает
        """
        # 1. Создаем соискателя и работодателя
        test_db.execute(
            "INSERT INTO job_seekers (id, telegram_id, full_name, phone, email, password_hash, age, city, profession, status) "
            "VALUES (10, 777, 'John Doe', '998901234567', 'j@d.uz', 'hash', 25, 'Tashkent', 'Developer', 'active')"
        )
        test_db.execute(
            "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, contact_person) "
            "VALUES (20, 888, 'Tech Corp', '998909876543', 'hr@tech.uz', 'hash', 'HR')"
        )
        test_db.commit()

        # Сообщение от работодателя
        message.from_user.id = 888
        message.chat.id = 888

        # 2. Работодатель ищет кандидатов
        handlers["employer"].handle_find_candidates(message)

        # Проверяем, что бот отправил карточку кандидата
        # send_message вызывается: 1 раз заголовок, 1 раз карточка (так как 1 кандидат)
        assert handlers["employer"].bot.send_message.call_count == 2
        args = handlers["employer"].bot.send_message.call_args_list[1]
        assert "John Doe" in args[0][1]
        assert "Developer" in args[0][1]

        # 3. Работодатель приглашает кандидата (имитация нажатия кнопки)
        call = MagicMock()
        call.from_user.id = 888
        call.message.chat.id = 888
        call.data = "invite_777"  # invite_{seeker_telegram_id}
        call.id = "callback_id"
        call.message.text = "Card text"

        # Сбрасываем мок send_message, чтобы проверить отправку приглашения соискателю
        handlers["employer"].bot.send_message.reset_mock()

        handlers["employer"].handle_invitation_callback(call)

        # Проверяем, что соискателю (777) отправлено сообщение
        handlers["employer"].bot.send_message.assert_called()
        # Проверяем аргументы вызова: chat_id=777
        call_args = handlers["employer"].bot.send_message.call_args
        assert call_args[0][0] == 777
        assert "Вас пригласили на собеседование" in call_args[0][1]
        assert "Tech Corp" in call_args[0][1]

    def test_vacancy_lifecycle_flow(self, handlers, message, test_db):
        """
        E2E: Жизненный цикл вакансии: Создание (в БД) -> Просмотр -> Редактирование -> Удаление
        """
        # 1. Создаем работодателя и вакансию
        test_db.execute(
            "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, "
            "contact_person) "
            "VALUES (30, 999, 'Soft LLC', '998901112233', 'hr@soft.uz', 'hash', 'Manager')"
        )
        test_db.execute(
            "INSERT INTO vacancies (id, employer_id, title, description, salary, job_type, status) "
            "VALUES (100, 30, 'Junior Dev', 'Need junior', '500$', 'Office', 'active')"
        )
        test_db.commit()

        message.from_user.id = 999
        message.chat.id = 999

        # 2. Просмотр вакансий
        handlers["employer"].handle_my_vacancies(message)

        # Проверяем вывод
        assert handlers["employer"].bot.send_message.call_count == 1
        text = handlers["employer"].bot.send_message.call_args[0][1]
        assert "Junior Dev" in text
        assert "500$" in text

        # 3. Редактирование вакансии (изменение зарплаты)
        # Имитируем нажатие "Изменить" -> "Зарплата" (в текущей реализации это пошаговый процесс)
        # handle_edit_vacancy запускает процесс
        call = MagicMock()
        call.from_user.id = 999
        call.message.chat.id = 999
        call.data = "edit_vac_100"

        handlers["employer"].handle_edit_vacancy(call, 100)

        # Проходим по шагам редактирования
        # Пропускаем изменение названия
        message.text = "."
        handlers["steps"].handle_steps(message)
        # Пропускаем изменение описания
        message.text = "."
        handlers["steps"].handle_steps(message)
        # Пропускаем изменение языков
        message.text = "➡️ Оставить текущие"
        handlers["steps"].handle_steps(message)
        # Меняем зарплату
        message.text = "1000$"
        handlers["steps"].handle_steps(message)
        # Пропускаем тип занятости (завершаем редактирование)
        message.text = "."
        handlers["steps"].handle_steps(message)

        # Проверяем обновление в БД
        vac = test_db.execute("SELECT salary FROM vacancies WHERE id=100").fetchone()
        assert vac["salary"] == "1000$"

        # 4. Удаление вакансии
        call.data = "confirm_del_100"
        call.message.message_id = 12345
        handlers["employer"].handle_confirm_delete(call)

        # Проверяем удаление из БД
        vac = test_db.execute("SELECT * FROM vacancies WHERE id=100").fetchone()
        assert vac is None

    def test_rate_limiting_and_load(self, handlers, message, test_db):
        """Многопользовательская нагрузка и проверка лимитов"""
        # Часть 1: Проверка Rate Limiting (логика из bot.py) # noqa
        # Этот тест имитирует логику, но не является полноценным E2E тестом # noqa
        # rate-limiting'а, так как для этого требуется реальная асинхронная # noqa
        # среда. # noqa
        spammer_id = 9999  # id
        message.from_user.id = spammer_id

        # Clear middleware state directly
        from middleware import muted_users, user_requests

        user_requests.clear()
        muted_users.clear()

        # Имитируем отправку сообщений до лимита
        for _ in range(middleware.RATE_LIMIT):
            assert middleware.check_rate_limit(MagicMock(), message) is True

        # Следующее сообщение должно быть заблокировано
        assert middleware.check_rate_limit(MagicMock(), message) is False
        assert spammer_id in muted_users

        # Очищаем для следующих шагов теста
        if hasattr(middleware, "user_requests"):
            middleware.user_requests.clear()
        else:
            middleware.user_requests = {}

        if hasattr(middleware, "muted_users"):
            middleware.muted_users.clear()
        else:
            middleware.muted_users = {}

        # Часть 2: Создание большого количества данных
        # Создаем 2 работодателей в разных городах
        test_db.execute(  # noqa
            "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, city, "
            "contact_person) VALUES (100, 1001, 'Tashkent Corp', '998901001', 't@c.c', 'h', 'Tashkent', 'Manager 1')"
        )
        test_db.execute(  # noqa
            "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, city, "
            "contact_person) VALUES (200, 1002, 'Samarkand Corp', '998901002', 's@c.c', 'h', 'Samarkand', 'Manager 2')"
        )

        # Создаем 50 соискателей
        for i in range(50):
            city = "Tashkent" if i % 2 == 0 else "Samarkand"
            database.create_job_seeker(
                {
                    "telegram_id": 2000 + i,
                    "password": "p",
                    "phone": f"9989020000{i:02d}",
                    "email": f"load_seeker{i}@test.com",
                    "full_name": f"Load Seeker {i}",
                    "age": 25,
                    "city": city,
                }
            )

        # Создаем 100 вакансий (60 в Ташкенте, 40 в Самарканде)
        for i in range(60):
            database.create_vacancy(
                {
                    "employer_id": 100,
                    "title": f"Tashkent Vacancy {i}",
                    "description": "d",
                    "salary": "s",
                    "job_type": "t",
                }
            )
        for i in range(40):
            database.create_vacancy(
                {
                    "employer_id": 200,
                    "title": f"Samarkand Vacancy {i}",
                    "description": "d",
                    "salary": "s",
                    "job_type": "t",
                }
            )

        # Проверяем, что все создано
        assert len(database.get_all_vacancies(limit=150)) == 100
        assert database.get_statistics()["seekers"] == 50

        # Часть 3: Тестирование фильтрации с большим количеством данных
        # Имитируем поиск от имени соискателя
        seeker_id = 2000
        message.from_user.id = seeker_id
        message.chat.id = seeker_id

        # Сбрасываем мок, чтобы считать вызовы для этого теста
        handlers["seeker"].bot.send_message.reset_mock()

        # Ищем вакансии в Ташкенте. Должно найтись 60, но показать только 20 (из-за LIMIT)
        handlers["seeker"].show_vacancies(message, city="Tashkent")

        # Проверяем, что было отправлено 21 сообщение (1 заголовок + 20 вакансий)
        assert handlers["seeker"].bot.send_message.call_count == 21
        # Проверяем, что все показанные вакансии - из Ташкента # noqa
        for call in handlers["seeker"].bot.send_message.call_args_list[1:]:  # noqa
            card_text = call[0][1]
            assert "Tashkent Corp" in card_text
            assert "Samarkand Corp" not in card_text

        # Сбрасываем мок и ищем в Самарканде
        handlers["seeker"].bot.send_message.reset_mock()
        handlers["seeker"].show_vacancies(message, city="Samarkand")

        # Проверяем, что было отправлено 21 сообщение (1 заголовок + 20 вакансий)
        assert handlers["seeker"].bot.send_message.call_count == 21
        for call in handlers["seeker"].bot.send_message.call_args_list[1:]:
            card_text = call[0][1]
            assert "Samarkand Corp" in card_text
            assert "Tashkent Corp" not in card_text

        # Примечание: Пагинация не тестируется, так как функция show_vacancies
        # имеет жесткий LIMIT 20 и не поддерживает постраничный вывод.

    def test_real_notification_delivery(self, handlers, message, test_db):
        """Проверка реальной доставки уведомлений между пользователями"""
        # 1. Работодатель создает вакансию (подготовка данных)
        employer_tg_id = 12345
        seeker_tg_id = 67890

        test_db.execute(
            "INSERT INTO employers (id, telegram_id, company_name, phone, email, "
            "password_hash, contact_person) "
            "VALUES (10, ?, 'Real Corp', '998901111111', 'real@corp.uz', 'hash', 'HR')",  # noqa
            (employer_tg_id,),
        )
        test_db.execute(
            "INSERT INTO vacancies (id, employer_id, title, description, salary, job_type, status) "
            "VALUES (100, 10, 'Real Job', 'Real Desc', '1000$', 'Office', 'active')"
        )

        test_db.execute(
            "INSERT INTO job_seekers (id, telegram_id, full_name, phone, email, "
            "password_hash, age, city, profession, status) "
            "VALUES (20, ?, 'Real Seeker', '998902222222', 'real@seeker.uz', 'hash', 25, 'Tashkent', 'Dev', 'active')",  # noqa
            (seeker_tg_id,),
        )
        test_db.commit()

        # 2. Соискатель откликается
        call_apply = MagicMock()
        call_apply.from_user.id = seeker_tg_id
        call_apply.message.chat.id = seeker_tg_id
        call_apply.data = "apply_100"

        handlers["seeker"].handle_application_callback(call_apply)

        # Проверяем, что отклик в базе
        assert database.check_application_exists(100, 20) is True

        # 3. Проверяем, что работодатель получил реальное сообщение в Telegram
        # (Эмулируем просмотр откликов, так как пуш-уведомлений нет)
        call_responses = MagicMock()
        call_responses.from_user.id = employer_tg_id
        call_responses.message.chat.id = employer_tg_id
        call_responses.data = "responses_vac_100"

        handlers["employer"].bot.send_message.reset_mock()
        handlers["employer"].handle_vacancy_responses(call_responses, 100)

        # Проверяем отправку сообщения работодателю
        assert handlers["employer"].bot.send_message.call_count >= 1
        calls = handlers["employer"].bot.send_message.call_args_list
        # Ищем сообщение с именем соискателя
        assert any("Real Seeker" in c[0][1] for c in calls)

        # 4. Работодатель отвечает (приглашает)
        call_invite = MagicMock()
        call_invite.from_user.id = employer_tg_id
        call_invite.message.chat.id = employer_tg_id
        call_invite.data = f"invite_{seeker_tg_id}_100"
        call_invite.message.text = "Some text"

        handlers["employer"].bot.send_message.reset_mock()
        handlers["employer"].handle_invitation_callback(call_invite)

        # 5. Проверяем, что соискатель получил ответ
        calls = handlers["employer"].bot.send_message.call_args_list
        seeker_msg = next((c for c in calls if c[0][0] == seeker_tg_id), None)

        assert seeker_msg is not None
        assert "Вас пригласили на собеседование" in seeker_msg[0][1]
        assert "Real Corp" in seeker_msg[0][1]

    def test_admin_broadcast_flow(self, handlers, message, test_db):
        """E2E: Админ делает рассылку всем пользователям"""
        # 1. Подготовка пользователей (получателей)
        test_db.execute(
            "INSERT INTO job_seekers (telegram_id, full_name, phone, email, password_hash, age, city) "
            "VALUES (101, 'S1', '1', 'e1', 'h', 25, 'Tashkent')"
        )
        test_db.execute(
            "INSERT INTO employers (telegram_id, company_name, phone, email, password_hash, city, contact_person) "
            "VALUES (102, 'E1', '2', 'e2', 'h', 'Tashkent', 'Contact')"
        )
        test_db.commit()

        # Админ
        message.from_user.id = 123456
        message.chat.id = 123456

        # 2. Старт рассылки
        handlers["admin"].handle_broadcast_start(message)

        # 3. Ввод сообщения
        message.text = "Важное сообщение для всех"
        handlers["admin"].process_broadcast_message(message)

        # 4. Подтверждение
        message.text = "✅ Да, отправить"

        # Сбрасываем мок, чтобы проверить отправку
        handlers["admin"].bot.send_message.reset_mock()

        handlers["admin"].process_broadcast_confirm(message)

        # Проверяем, что сообщение ушло пользователям (101, 102) и админу (отчет)
        calls = handlers["admin"].bot.send_message.call_args_list
        recipients = [c[0][0] for c in calls]

        assert 101 in recipients
        assert 102 in recipients
        assert 123456 in recipients  # Отчет админу

    def test_seeker_full_flow(self, handlers, message, test_db):
        """
        E2E: Регистрация соискателя -> Заполнение профиля -> Поиск вакансии -> Отклик
        """
        # 0. Подготовка: создаем вакансию, на которую будем откликаться
        test_db.execute(
            "INSERT INTO employers (id, telegram_id, company_name, phone, email, password_hash, contact_person) "
            "VALUES (1, 999, 'Test Employer Inc.', '998900000000', 'c@t.uz', 'hash', 'Contact')"
        )
        test_db.execute(
            "INSERT INTO vacancies (id, employer_id, title, description, status, city) "
            "VALUES (500, 1, 'Awesome Job', 'An awesome job description.', 'active', 'Tashkent')"
        )
        test_db.commit()

        user_id = message.from_user.id

        # 1. Регистрация (упрощенно, как в другом тесте, чтобы не дублировать)
        message.text = "👤 Я ищу работу"
        handlers["auth"].handle_role_selection(message)
        database.set_user_state(
            user_id,
            {
                "step": "age",
                "role": "seeker",
                "registration_data": {
                    "phone": "+998901234567",
                    "email": "full_seeker@test.uz",
                    "full_name": "Full Seeker",
                    "region": "Tashkent",
                    "city": "Tashkent",
                    "password": "dummy_password",
                },
            },
        )
        message.text = "28"
        handlers["steps"].handle_steps(
            message
        )  # age -> finish registration & start profile setup

        # 2. Заполнение профиля (проходим по шагам)
        # handlers['steps'] будет вызван после каждого сообщения
        # Шаг 1: Образование
        message.text = "Высшее"
        handlers["steps"].handle_steps(message)
        # Шаг 2: Сфера
        message.text = "IT и Интернет"
        handlers["steps"].handle_steps(message)
        # Шаг 3: Профессия
        message.text = "Backend разработчик"
        handlers["steps"].handle_steps(message)
        # Шаг 4: Языки (выбираем один и жмем "Далее")
        message.text = "🇷🇺 Русский"
        handlers["steps"].handle_steps(message)  # Выбор языка
        message.text = "Свободный"
        handlers["steps"].handle_steps(message)  # Выбор уровня
        message.text = "➡️ Далее"
        handlers["steps"].handle_steps(message)  # Завершение выбора языков
        # Шаг 5: Опыт
        message.text = "3 года"
        handlers["steps"].handle_steps(message)
        # Шаг 6: Навыки (финальный шаг)
        message.text = "Python, Django, SQL"
        handlers["steps"].handle_steps(message)

        # Проверяем, что профиль обновлен в БД
        seeker_db = database.get_user_by_id(user_id)
        assert seeker_db is not None
        assert seeker_db["experience"] == "3 года"
        assert "Python" in seeker_db["skills"]

        # 3. Поиск вакансии
        handlers["seeker"].bot.send_message.reset_mock()
        message.text = "🔍 Найти вакансии"
        handlers["seeker"].handle_find_vacancies(message)

        # Проверяем, что бот нашел и отправил нашу вакансию
        assert (
            handlers["seeker"].bot.send_message.call_count >= 2
        )  # Заголовок + карточка
        vacancy_card_args = handlers["seeker"].bot.send_message.call_args_list[1]
        vacancy_card_text = vacancy_card_args[0][1]
        vacancy_card_kb = vacancy_card_args[1]["reply_markup"]
        assert "Awesome Job" in vacancy_card_text
        assert "Test Employer Inc." in vacancy_card_text
        assert "apply_500" in vacancy_card_kb.keyboard[0][0].callback_data

        # 4. Отклик на вакансию
        apply_call = MagicMock()
        apply_call.from_user.id = user_id
        apply_call.data = "apply_500"  # vacancy_id = 500

        with patch(
            "handlers.seeker_responses.SeekerResponseMixin._notify_employer_with_pdf"
        ) as mock_notify:
            handlers["seeker"].handle_application_callback(apply_call)
            # Проверяем, что отклик успешен
            handlers["seeker"].bot.answer_callback_query.assert_called_with(
                apply_call.id, "✅ Отклик отправлен!"
            )
            # Проверяем, что было вызвано уведомление работодателя
            mock_notify.assert_called_once()

        # Проверяем отклик в БД
        assert database.check_application_exists(500, seeker_db["id"]) is True

    def test_admin_complaint_to_block_flow(self, handlers, message, test_db):
        """
        E2E: Пользователь жалуется -> Админ видит жалобу -> Админ находит и блокирует пользователя
        """
        # 1. Подготовка: создаем пользователя, который будет жаловаться
        seeker_tg_id = 67890
        test_db.execute(
            "INSERT INTO job_seekers (id, telegram_id, full_name, phone, email, password_hash, age, city) "
            "VALUES (20, ?, 'Complainer User', '998902222222', 'complainer@seeker.uz', 'hash', 25, 'Tashkent')",
            (seeker_tg_id,),
        )
        test_db.commit()

        # 2. Пользователь отправляет жалобу
        complaint_message = MagicMock(
            text="This is a serious complaint.", photo=None, caption=None
        )
        complaint_message.from_user = MagicMock(
            id=seeker_tg_id, first_name="Complainer User"
        )
        complaint_message.chat = MagicMock(id=seeker_tg_id)
        common_handler = CommonHandlers(handlers["admin"].bot)
        with patch(
            "handlers.support.database.get_user_state",
            return_value={"step": "support_complaint"},
        ):
            common_handler.process_support_message(complaint_message)

        # 3. Админ просматривает жалобы
        admin_tg_id = 123456
        message.from_user.id = admin_tg_id
        message.chat.id = admin_tg_id
        with patch("config.Config.ADMIN_IDS", [admin_tg_id]):
            handlers["admin"].handle_complaints(message)

            # 4. Админ ищет пользователя по ID и блокирует его
            search_message = MagicMock(
                text=str(seeker_tg_id),
                from_user=MagicMock(id=admin_tg_id),
                chat=MagicMock(id=admin_tg_id),
            )
            handlers["admin"].process_search_user(search_message)

            # 5. Эмулируем нажатие кнопки блокировки
            block_call = MagicMock(
                data=f"admin_block_{seeker_tg_id}_forever", message=MagicMock()
            )
            handlers["admin"].handle_block_confirm(block_call)

            # 6. Проверяем, что пользователь заблокирован в БД
            blocked_user_db = test_db.execute(
                "SELECT * FROM blocked_users WHERE telegram_id = ?", (seeker_tg_id,)
            ).fetchone()
            assert blocked_user_db is not None
            assert blocked_user_db["blocked_until"] == "forever"
