from unittest.mock import MagicMock, patch

import pytest
from telebot import types

import database  # noqa: F401
from handlers.seeker import SeekerHandlers


class TestSeekerHandlers:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return SeekerHandlers(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        return msg

    @pytest.fixture
    def callback(self):
        call = MagicMock()
        call.id = "call_id"
        call.from_user.id = 456
        call.message.chat.id = 123
        call.message.message_id = 789
        call.data = "apply_1"
        return call

    @pytest.fixture(autouse=True)
    def mock_lang(self):
        with patch("localization.get_user_language", return_value="ru"):
            yield

    def test_handle_find_vacancies_not_authorized(self, handler, message):
        """Поиск вакансий без авторизации"""
        with patch("handlers.seeker_search.database.get_user_by_id", return_value=None):
            handler.handle_find_vacancies(message)
            handler.bot.send_message.assert_called()
            # Теперь гостевой режим разрешен, поэтому проверяем, что поиск выполняется
            assert (
                "Сначала зарегистрируйтесь"
                not in handler.bot.send_message.call_args[0][1]
            )

    def test_handle_find_vacancies_no_vacancies(self, handler, message):
        """Поиск вакансий: список пуст"""
        user_data = {
            "id": 1,
            "full_name": "Test Seeker",
            "role": "seeker",
            "telegram_id": 456,
        }
        with patch(
            "handlers.seeker_search.database.get_user_by_id", return_value=user_data
        ), patch("handlers.seeker_search.execute_query", return_value=[]):
            handler.handle_find_vacancies(message)
            handler.bot.send_message.assert_called()
            assert "нет активных вакансий" in handler.bot.send_message.call_args[0][1]

    def test_handle_find_vacancies_success(self, handler, message):
        """Успешный поиск вакансий"""
        user_data = {
            "id": 1,
            "full_name": "Test Seeker",
            "role": "seeker",
            "telegram_id": 456,
        }
        vacancies = [
            {
                "id": 101,
                "title": "Python Dev",
                "company_name": "Tech Corp",
                "city": "Tashkent",
                "salary": "2000$",
                "job_type": "Remote",
                "description": "Good job",
                "languages": "En",
            }
        ]
        with patch(
            "handlers.seeker_search.database.get_user_by_id", return_value=user_data
        ), patch("handlers.seeker_search.execute_query", return_value=vacancies):
            handler.handle_find_vacancies(message)

            # Должно быть 2 сообщения: заголовок и карточка
            assert handler.bot.send_message.call_count == 2

            # Проверяем карточку вакансии
            card_args = handler.bot.send_message.call_args_list[1]
            text = card_args[0][1]
            assert "Python Dev" in text
            assert "Tech Corp" in text

    def test_handle_application_callback_success(self, handler, callback):
        """Успешный отклик на вакансию"""
        user_data = {
            "id": 1,
            "full_name": "Test Seeker",
            "role": "seeker",
            "telegram_id": 456,
        }
        with patch(
            "handlers.seeker_search.database.get_user_by_id", return_value=user_data
        ), patch(
            "handlers.seeker_responses.database.check_application_exists",
            return_value=False,
        ), patch(
            "handlers.seeker_responses.database.create_application", return_value=True
        ):

            handler.handle_application_callback(callback)

            handler.bot.answer_callback_query.assert_called_with(
                callback.id, "✅ Отклик отправлен!"
            )
            handler.bot.send_message.assert_called()

    def test_handle_application_callback_already_applied(self, handler, callback):
        """Повторный отклик"""
        user_data = {
            "id": 1,
            "full_name": "Test Seeker",
            "role": "seeker",
            "telegram_id": 456,
        }
        with patch(
            "handlers.seeker_search.database.get_user_by_id", return_value=user_data
        ), patch(
            "handlers.seeker_responses.database.check_application_exists",
            return_value=True,
        ):

            handler.handle_application_callback(callback)

            handler.bot.answer_callback_query.assert_called()
            assert (
                "уже откликнулись" in handler.bot.answer_callback_query.call_args[0][1]
            )

    def test_handle_my_resume(self, handler, message):
        """Просмотр резюме"""
        user_data = {
            "id": 1,
            "full_name": "Test Seeker",
            "city": "Tashkent",
            "age": 25,
            "phone": "+998901234567",
            "email": "test@test.uz",
            "profession": "Dev",
            "education": "High",
            "languages": "Ru, En",
            "skills": "Python",
            "experience": "5 years",
            "status": "active",
            "telegram_id": 456,
            "role": "seeker",
        }
        with patch(
            "handlers.seeker_profile.database.get_user_by_id", return_value=user_data
        ):
            handler.handle_my_resume(message)

            handler.bot.send_message.assert_called()
            # Resume is sent before the menu, so we check call_args_list
            text = handler.bot.send_message.call_args_list[-2][0][1]
            assert "ВАШЕ РЕЗЮМЕ" in text
            assert "Test Seeker" in text
            assert "Dev" in text

    def test_handle_my_responses(self, handler, message):
        """Просмотр откликов"""
        user_data = {
            "id": 1,
            "full_name": "Test Seeker",
            "role": "seeker",
            "telegram_id": 456,
        }
        applications = [
            {
                "title": "Java Dev",
                "company_name": "Soft LLC",
                "salary": "1500$",
                "created_at": "2023-10-10 10:00:00",
                "status": "pending",
            }
        ]
        with patch(
            "handlers.seeker_responses.database.get_user_by_id", return_value=user_data
        ), patch(
            "handlers.seeker_responses.database.get_seeker_applications",
            return_value=applications,
        ):

            handler.handle_my_responses(message)

            # Заголовок + 1 карточка
            assert handler.bot.send_message.call_count == 2
            text = handler.bot.send_message.call_args_list[1][0][1]
            assert "Java Dev" in text
            assert "Soft LLC" in text

    def test_handle_find_vacancies_send_error(self, handler, message):
        """Тест ошибки при отправке карточки вакансии"""
        user_data = {
            "id": 1,
            "full_name": "Test Seeker",
            "role": "seeker",
            "telegram_id": 456,
        }
        vacancies = [
            {
                "id": 101,
                "title": "Dev",
                "company_name": "Co",
                "city": "C",
                "salary": "S",
                "job_type": "T",
                "description": "D",
                "languages": "L",
            }
        ]  # noqa: E501

        with patch(
            "handlers.seeker_search.database.get_user_by_id", return_value=user_data
        ), patch("handlers.seeker_search.execute_query", return_value=vacancies):

            # Мокаем ошибку при второй отправке сообщения (карточки)
            handler.bot.send_message.side_effect = [None, Exception("Send Error")]

            handler.handle_find_vacancies(message)

            # Проверяем, что было 2 попытки отправки
            assert handler.bot.send_message.call_count == 2

    def test_handle_application_callback_unauthorized(self, handler, callback):
        """Тест отклика без авторизации (не соискатель)"""
        user_data = {
            "id": 1,
            "company_name": "Employer Co",
            "role": "employer",
        }  # Это работодатель
        with patch(
            "handlers.seeker_search.database.get_user_by_id", return_value=user_data
        ):
            handler.handle_application_callback(callback)
            handler.bot.answer_callback_query.assert_called_with(
                callback.id, "❌ Сначала зарегистрируйтесь или войдите как соискатель!"
            )

    def test_handle_application_callback_db_error(self, handler, callback):
        """Тест ошибки БД при отклике"""
        user_data = {
            "id": 1,
            "full_name": "Test Seeker",
            "role": "seeker",
            "telegram_id": 456,
        }
        with patch(
            "handlers.seeker_search.database.get_user_by_id", return_value=user_data
        ), patch(
            "handlers.seeker_responses.database.check_application_exists",
            return_value=False,
        ), patch(
            "handlers.seeker_responses.database.create_application", return_value=False
        ):  # DB error

            handler.handle_application_callback(callback)
            handler.bot.answer_callback_query.assert_called_with(
                callback.id, "❌ Ошибка при отправке отклика."
            )

    def test_handle_application_callback_general_exception(self, handler, callback):
        """Тест общего исключения при отклике"""
        with patch(
            "handlers.seeker_search.database.get_user_by_id",
            side_effect=Exception("General Error"),
        ):
            handler.handle_application_callback(callback)
            handler.bot.answer_callback_query.assert_called_with(
                callback.id, "❌ Произошла ошибка."
            )

    def test_handle_my_resume_no_age(self, handler, message):
        """Тест резюме без указания возраста"""
        user_data = {
            "id": 1,
            "full_name": "Ageless Seeker",
            "age": None,  # No age
            "phone": "p",
            "email": "e",
            "profession": "p",
            "education": "e",
            "languages": "l",
            "skills": "s",
            "experience": "e",
            "status": "active",
            "telegram_id": 456,
            "city": "c",
            "role": "seeker",
        }
        with patch(
            "handlers.seeker_profile.database.get_user_by_id", return_value=user_data
        ):
            handler.handle_my_resume(message)
            handler.bot.send_message.assert_called()
            text = handler.bot.send_message.call_args_list[-2][0][1]
            assert "*Возраст:* Не указан" in text

    def test_handle_my_responses_empty(self, handler, message):
        """Тест просмотра откликов при их отсутствии"""
        user_data = {
            "id": 1,
            "full_name": "Test Seeker",
            "role": "seeker",
            "telegram_id": 456,
        }
        with patch(
            "handlers.seeker_responses.database.get_user_by_id", return_value=user_data
        ), patch(
            "handlers.seeker_responses.database.get_seeker_applications",
            return_value=[],
        ):

            handler.handle_my_responses(message)
            handler.bot.send_message.assert_called()
            assert (
                "У вас пока нет активных откликов"
                in handler.bot.send_message.call_args[0][1]
            )

    def test_handle_seeker_chats_empty(self, handler, message):
        """Тест просмотра чатов при их отсутствии"""
        user_data = {
            "id": 1,
            "full_name": "Test Seeker",
            "role": "seeker",
            "telegram_id": 456,
        }
        with patch(
            "handlers.seeker_responses.database.get_user_by_id", return_value=user_data
        ), patch("handlers.seeker_responses.database.execute_query", return_value=[]):

            handler.handle_seeker_chats(message)
            handler.bot.send_message.assert_called_with(
                message.chat.id, "📭 У вас пока нет активных приглашений (чатов)."
            )

    def test_handle_my_responses_malformed_date(self, handler, message):
        """Тест просмотра откликов с некорректной датой"""
        user_data = {
            "id": 1,
            "full_name": "Test Seeker",
            "role": "seeker",
            "telegram_id": 456,
        }
        applications = [
            {"title": "Job", "company_name": "Co", "created_at": "invalid-date"}
        ]

        with patch(
            "handlers.seeker_responses.database.get_user_by_id", return_value=user_data
        ), patch(
            "handlers.seeker_responses.database.get_seeker_applications",
            return_value=applications,
        ):

            handler.handle_my_responses(message)

            assert handler.bot.send_message.call_count == 2
            text = handler.bot.send_message.call_args_list[1][0][1]

            # Убедимся, что он просто выводит исходную строку, не падая
            assert "Отклик: invalid-date" in text

    def test_process_vacancy_filter_choice_back(self, handler, message):
        """Фильтр вакансий: Назад"""
        message.text = "⬅️ Назад"
        handler.process_vacancy_filter_choice(message)
        handler.bot.send_message.assert_called()

    def test_process_vacancy_filter_choice_city(self, handler, message):
        """Фильтр вакансий: Выбрать город"""
        message.text = "🏙 Выбрать город"
        msg = MagicMock()
        handler.bot.send_message.return_value = msg
        handler.process_vacancy_filter_choice(message)
        handler.bot.register_next_step_handler.assert_called_with(
            msg, handler.process_vacancy_region_choice
        )

    def test_process_vacancy_filter_choice_all(self, handler, message):
        """Фильтр вакансий: Все"""
        message.text = "All"
        with patch.object(handler, "show_vacancies") as mock_show:
            handler.process_vacancy_filter_choice(message)
            mock_show.assert_called_with(message, city=None)

    def test_process_vacancy_region_choice_back(self, handler, message):
        """Выбор региона: Назад"""
        message.text = "⬅️ Назад"
        with patch.object(handler, "handle_find_vacancies") as mock_find:
            handler.process_vacancy_region_choice(message)
            mock_find.assert_called_with(message)

    def test_process_vacancy_region_choice_valid(self, handler, message):
        """Выбор региона: Валидный"""
        message.text = "Ташкентская обл."
        msg = MagicMock()
        handler.bot.send_message.return_value = msg
        handler.process_vacancy_region_choice(message)
        handler.bot.register_next_step_handler.assert_called_with(
            msg, handler.process_vacancy_city_choice
        )

    def test_process_vacancy_region_choice_invalid(self, handler, message):
        """Выбор региона: Невалидный"""
        message.text = "Invalid"
        with patch.object(handler, "process_vacancy_filter_choice") as mock_filter:
            handler.process_vacancy_region_choice(message)
            handler.bot.send_message.assert_called()
            mock_filter.assert_called()

    def test_process_vacancy_city_choice_back(self, handler, message):
        """Выбор города: Назад"""
        message.text = "⬅️ Назад"
        msg = MagicMock()
        handler.bot.send_message.return_value = msg
        handler.process_vacancy_city_choice(message)
        handler.bot.register_next_step_handler.assert_called_with(
            msg, handler.process_vacancy_region_choice
        )

    def test_process_vacancy_city_choice_valid(self, handler, message):
        """Выбор города: Валидный"""
        message.text = "Tashkent"
        with patch.object(handler, "show_vacancies") as mock_show:
            handler.process_vacancy_city_choice(message)
            mock_show.assert_called_with(message, "Tashkent")

    def test_handle_my_resume_formatting(self, handler, message):
        """Тест форматирования данных в резюме"""
        user_data = {
            "id": 1,
            "full_name": "S",
            "role": "seeker",
            "gender": "female",
            "languages": '[{"lang_key": "lang_ru", "level_key": "level_c1"}]',
            "profession": "prof_design",
            "age": 25,
        }
        with patch(
            "handlers.seeker_profile.database.get_user_by_id", return_value=user_data
        ), patch(
            "handlers.seeker_profile.get_text_by_lang",
            side_effect=lambda key, lang: key,
        ):
            handler.handle_my_resume(message)

            handler.bot.send_message.assert_called()
            text = handler.bot.send_message.call_args_list[-2][0][1]
            assert "gender\\_female" in text
            assert "lang\\_ru" in text
            assert "prof\\_design" in text

    def test_register(self, handler, bot):
        """Test registration of handlers and filters"""
        with patch("handlers.seeker.get_all_translations", return_value=["Find Jobs"]):
            handler.register(bot)

            assert bot.register_message_handler.call_count >= 3

            # Проверяем работу лямбда-фильтра для handle_find_vacancies
            found = False
            for call in bot.register_message_handler.call_args_list:
                handler_func = call[0][0]
                kwargs = call[1]
                if handler_func == handler.handle_find_vacancies:
                    filter_func = kwargs.get("func")
                    if filter_func:
                        msg = MagicMock()
                        msg.text = "Find Jobs"
                        assert filter_func(msg) is True
                        msg.text = "Other"
                        assert filter_func(msg) is False
                        found = True
            assert found
