from unittest.mock import MagicMock, patch

import pytest

import keyboards
from handlers.steps import StepHandlers


class TestStepHandlers:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def auth_handlers(self):
        return MagicMock()

    @pytest.fixture
    def employer_handlers(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot, auth_handlers, employer_handlers):
        handler = StepHandlers(bot, auth_handlers)
        handler.set_employer_handlers(employer_handlers)
        return handler

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        return msg

    def test_handle_steps_no_state(self, handler, message):
        """Тест: нет состояния"""
        with patch("database.get_user_state", return_value={}):
            assert handler.handle_steps(message) is False

    def test_handle_steps_cancel(self, handler, message):
        """Тест: отмена действия"""
        message.text = "❌ Отмена"
        with patch(
            "database.get_user_state", return_value={"step": "some_step"}
        ), patch("utils.cancel_request", return_value=True), patch.object(
            handler, "cancel_current_step"
        ) as mock_cancel:

            assert handler.handle_steps(message) is True
            mock_cancel.assert_called_with(456, 123)

    def test_handle_steps_captcha(self, handler, message):
        """Тест: шаг капчи"""
        with patch("database.get_user_state", return_value={"step": "captcha"}):
            assert handler.handle_steps(message) is True
            handler.auth_handlers.role.process_captcha.assert_called_with(message)

    def test_handle_steps_vacancy(self, handler, message):
        """Тест: шаги вакансии"""
        with patch("database.get_user_state", return_value={"step": "vacancy_title"}):
            assert handler.handle_steps(message) is True
            handler.employer_handlers.process_vacancy_title.assert_called_with(message)

    def test_handle_steps_seeker_registration(self, handler, message):
        """Тест: шаги регистрации соискателя"""
        user_state = {"step": "phone", "role": "seeker"}
        with patch("database.get_user_state", return_value=user_state):
            assert handler.handle_steps(message) is True
            handler.auth_handlers.process_seeker_phone.assert_called_with(message)

    def test_handle_steps_employer_registration(self, handler, message):
        """Тест: шаги регистрации работодателя"""
        user_state = {"step": "company_name", "role": "employer"}
        with patch("database.get_user_state", return_value=user_state):
            assert handler.handle_steps(message) is True
            handler.auth_handlers.process_employer_name.assert_called_with(message)

    def test_handle_steps_unknown_step(self, handler, message):
        """Тест: неизвестный шаг"""
        user_state = {"step": "unknown_step", "role": "seeker"}
        with patch("database.get_user_state", return_value=user_state):
            assert handler.handle_steps(message) is False

    def test_cancel_current_step_vacancy(self, handler):
        """Тест отмены: создание вакансии"""
        user_state = {"step": "vacancy_title"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.clear_user_state"
        ) as mock_clear:

            handler.cancel_current_step(456, 123)

            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert (
                "Создание вакансии отменено" in handler.bot.send_message.call_args[0][1]
            )

    def test_cancel_current_step_registration(self, handler):
        """Тест отмены: регистрация"""
        user_state = {"step": "phone"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.clear_user_state"
        ):

            handler.cancel_current_step(456, 123)

            # mock_clear.assert_called_with(456)
            handler.auth_handlers.role.cancel_registration.assert_called_with(
                123, 456, "Регистрация отменена"
            )

    def test_cancel_current_step_settings(self, handler):
        """Тест отмены: редактирование настроек"""
        user_state = {"step": "enter_new_value", "action": "edit_seeker_field"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.clear_user_state"
        ) as mock_clear:

            handler.cancel_current_step(456, 123)

            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Изменение отменено" in handler.bot.send_message.call_args[0][1]

    def test_cancel_current_step_no_action(self, handler):
        """Тест отмены шага настроек без 'action' в состоянии"""
        user_state = {"step": "enter_new_value"}  # 'action' отсутствует
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.clear_user_state"
        ):
            handler.cancel_current_step(456, 123)
            assert "Изменение отменено" in handler.bot.send_message.call_args[0][1]

    def test_handle_steps_back_button_city(self, handler, message):
        """Тест кнопки Назад на шаге выбора города"""
        message.text = "⬅️ Назад"
        user_state = {"step": "city_selection", "role": "seeker"}
        with patch("database.get_user_state", return_value=user_state):
            assert handler.handle_steps(message) is True
            handler.auth_handlers.process_seeker_city_selection.assert_called_with(
                message
            )

    def test_handle_steps_edit_vacancy(self, handler, message):
        """Тест шагов редактирования вакансии"""
        user_state = {"step": "edit_vacancy_title"}
        with patch("database.get_user_state", return_value=user_state):
            assert handler.handle_steps(message) is True
            handler.employer_handlers.process_edit_title.assert_called_with(message)

    def test_handle_steps_auth_exception(self, handler, message):
        """Тест обработки исключения внутри auth handler"""
        user_state = {"step": "phone", "role": "seeker"}
        with patch("database.get_user_state", return_value=user_state), patch.object(
            handler.auth_handlers,
            "process_seeker_phone",
            side_effect=Exception("Auth Error"),
        ), patch("database.clear_user_state") as mock_clear:

            assert handler.handle_steps(message) is True
            mock_clear.assert_called()
            handler.bot.send_message.assert_called()

    def test_handle_vacancy_steps_all(self, handler, message):
        """Тест всех шагов вакансии"""
        steps = [
            ("vacancy_description", "process_vacancy_description"),
            ("vacancy_salary", "process_vacancy_salary"),
            ("vacancy_type", "process_vacancy_type"),
            ("edit_vacancy_desc", "process_edit_desc"),
            ("edit_vacancy_salary", "process_edit_salary"),
            ("edit_vacancy_type", "process_edit_type"),
        ]

        for step_name, method_name in steps:
            with patch("database.get_user_state", return_value={"step": step_name}):
                assert handler.handle_steps(message) is True
                getattr(handler.employer_handlers, method_name).assert_called_with(
                    message
                )

    def test_handle_steps_seeker_all(self, handler, message):
        """Тест всех шагов соискателя"""
        steps = [
            ("email", "process_seeker_email"),
            ("full_name", "process_seeker_name"),
            ("region", "process_seeker_region"),
            ("age", "finish_seeker_registration"),
        ]

        for step_name, method_name in steps:
            user_state = {"step": step_name, "role": "seeker"}
            with patch("database.get_user_state", return_value=user_state):
                assert handler.handle_steps(message) is True
                getattr(handler.auth_handlers, method_name).assert_called_with(message)

    def test_handle_steps_employer_all(self, handler, message):
        """Тест всех шагов работодателя"""
        steps = [
            ("phone", "process_employer_phone"),
            ("email", "process_employer_email"),
            ("contact_person", "process_employer_contact"),
            ("region", "process_employer_region"),
            ("city_selection", "process_employer_city_selection"),
            ("business_activity", "process_business_activity"),
        ]

        for step_name, method_name in steps:
            user_state = {"step": step_name, "role": "employer"}
            with patch("database.get_user_state", return_value=user_state):
                assert handler.handle_steps(message) is True
                getattr(handler.auth_handlers, method_name).assert_called_with(message)

    def test_handle_steps_registration_no_role(self, handler, message):
        """Тест шага регистрации без указания роли в состоянии"""
        user_state = {"step": "phone"}  # 'role' отсутствует
        with patch("database.get_user_state", return_value=user_state):
            # Ожидаем, что обработчик вернет False, т.к. не сможет найти нужный метод
            assert handler.handle_steps(message) is False

    def test_handle_steps_admin_broadcast(self, handler, message):
        """Тест шагов админской рассылки"""
        steps = [
            ("admin_broadcast_message", "process_broadcast_message"),
            ("admin_broadcast_confirm", "process_broadcast_confirm"),
        ]

        handler.admin_handlers = MagicMock()

        for step_name, method_name in steps:
            with patch("database.get_user_state", return_value={"step": step_name}):
                assert handler.handle_steps(message) is True
                getattr(handler.admin_handlers, method_name).assert_called_with(message)

    def test_handle_steps_admin_search(self, handler, message):
        """Тест шага поиска пользователя админом"""
        handler.admin_handlers = MagicMock()
        with patch(
            "database.get_user_state", return_value={"step": "admin_search_user"}
        ):
            assert handler.handle_steps(message) is True
            handler.admin_handlers.process_search_user.assert_called_with(message)

    def test_handle_steps_login(self, handler, message):
        """Тест шагов входа"""
        steps = [
            ("login_email", "process_login_email"),
            ("login_password", "process_login_password"),
        ]

        handler.auth_handlers = MagicMock()

        for step_name, method_name in steps:
            with patch("database.get_user_state", return_value={"step": step_name}):
                assert handler.handle_steps(message) is True
                getattr(handler.auth_handlers.login, method_name).assert_called_with(
                    message
                )

    def test_handle_steps_recovery_code(self, handler, message):
        """Тест шага ввода кода восстановления"""
        handler.auth_handlers = MagicMock()
        with patch("database.get_user_state", return_value={"step": "recovery_code"}):
            assert handler.handle_steps(message) is True
            handler.auth_handlers.login.process_recovery_code.assert_called_with(
                message
            )


class TestStepHandlerFallbacks:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        return msg

    def test_handle_vacancy_steps_no_handler(self, bot, message):
        """Тест шагов вакансии без установленного обработчика"""
        handler = StepHandlers(bot)  # No employer_handlers
        user_state = {"step": "vacancy_title"}
        with patch("database.get_user_state", return_value=user_state):
            assert handler.handle_steps(message) is False

    def test_cancel_current_step_no_auth_handler(self, bot, message):
        """Тест отмены регистрации без установленного auth_handler"""
        handler = StepHandlers(bot, auth_handlers=None)
        user_state = {"step": "phone"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.clear_user_state"
        ) as mock_clear:

            handler.cancel_current_step(message.from_user.id, message.chat.id)

            mock_clear.assert_called_with(message.from_user.id)
            bot.send_message.assert_called()
            assert "Регистрация отменена" in bot.send_message.call_args[0][1]

    def test_cancel_current_step_unknown(self, bot, message):
        """Тест отмены неизвестного шага"""
        handler = StepHandlers(bot)
        user_state = {"step": "some_unknown_step"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.clear_user_state"
        ) as mock_clear:

            handler.cancel_current_step(message.from_user.id, message.chat.id)

            mock_clear.assert_called_with(message.from_user.id)
            bot.send_message.assert_called()
            assert "Действие отменено" in bot.send_message.call_args[0][1]

    def test_handle_steps_fallback_recovery(self, bot, message):
        """Тест fallback логики для восстановления пароля"""
        handler = StepHandlers(bot, auth_handlers=None)
        user_state = {"step": "recovery"}

        with patch("database.get_user_state", return_value=user_state), patch(
            "handlers.auth.login_auth.LoginAuth"
        ) as MockLoginAuth:

            mock_login = MockLoginAuth.return_value
            assert handler.handle_steps(message) is True
            mock_login.process_recovery.assert_called_with(message)

    def test_handle_steps_catches_exception(self, bot, message):
        """Тест, что главный обработчик шагов ловит исключения из дочерних."""
        # Используем хендлер без моков, чтобы проверить реальную интеграцию
        from handlers.auth import AuthHandlers

        auth_handlers = AuthHandlers(bot)
        handler = StepHandlers(bot, auth_handlers)

        user_state = {"step": "phone", "role": "seeker"}

        # Мокаем функцию, которая вызовется внутри и вызовет ошибку
        with patch("database.get_user_state", return_value=user_state), patch.object(
            auth_handlers.seeker,
            "process_seeker_phone",
            side_effect=Exception("Test Error"),
        ), patch("database.clear_user_state") as mock_clear:

            assert handler.handle_steps(message) is True

            mock_clear.assert_called_with(456)
            bot.send_message.assert_called()
            assert "Произошла ошибка" in bot.send_message.call_args[0][1]

    def test_cancel_current_step_no_state(self, bot, message):
        """Тест отмены, когда у пользователя нет состояния"""
        handler = StepHandlers(bot)
        with patch("database.get_user_state", return_value={}):
            handler.cancel_current_step(message.from_user.id, message.chat.id)
            # Проверяем, что метод был вызван
            bot.send_message.assert_called_once()
            # Получаем аргументы вызова
            args, kwargs = bot.send_message.call_args
            # Проверяем простые аргументы
            assert args == (message.chat.id, "❌ Действие отменено")
            assert kwargs.get("parse_mode") == "Markdown"
            # Сравниваем клавиатуры по их содержимому (JSON)
            assert "reply_markup" in kwargs
            assert kwargs["reply_markup"].to_json() == keyboards.main_menu().to_json()

    def test_handle_steps_fallback_seeker(self, bot, message):
        """Тест fallback для соискателя"""
        handler = StepHandlers(bot, auth_handlers=None)
        user_state = {"step": "full_name", "role": "seeker"}

        with patch("database.get_user_state", return_value=user_state), patch(
            "handlers.auth.seeker_auth.SeekerAuth"
        ) as MockSeeker:

            mock_inst = MockSeeker.return_value
            assert handler.handle_steps(message) is True
            mock_inst.process_seeker_name.assert_called_with(message)

    def test_handle_steps_fallback_employer(self, bot, message):
        """Тест fallback для работодателя"""
        handler = StepHandlers(bot, auth_handlers=None)
        user_state = {"step": "contact_person", "role": "employer"}

        with patch("database.get_user_state", return_value=user_state), patch(
            "handlers.auth.employer_auth.EmployerAuth"
        ) as MockEmployer:

            mock_inst = MockEmployer.return_value
            assert handler.handle_steps(message) is True
            mock_inst.process_employer_contact.assert_called_with(message)

    def test_handle_steps_recovery(self, bot, message):
        """Тест шага восстановления пароля"""
        handler = StepHandlers(bot)
        # Mock auth_handlers
        handler.auth_handlers = MagicMock()

        user_state = {"step": "recovery"}
        with patch("database.get_user_state", return_value=user_state):
            assert handler.handle_steps(message) is True
            handler.auth_handlers.process_recovery.assert_called_with(message)

    def test_handle_steps_settings_ignored(self, bot, message):
        """Тест игнорирования шагов настроек (обрабатываются в bot.py)"""
        handler = StepHandlers(bot)
        user_state = {"step": "enter_new_value", "action": "edit_seeker_field"}
        with patch("database.get_user_state", return_value=user_state):
            assert handler.handle_steps(message) is False

    def test_handle_steps_auth_exception_logging(self, bot, message):
        """Тест логирования исключения в handle_steps_with_auth_handlers"""
        handler = StepHandlers(bot)
        handler.auth_handlers = MagicMock()

        user_state = {"step": "phone", "role": "seeker"}
        with patch("database.get_user_state", return_value=user_state), patch.object(
            handler.auth_handlers,
            "process_seeker_phone",
            side_effect=Exception("Auth Error"),
        ), patch("database.clear_user_state"), patch("logging.error") as mock_log:

            handler.handle_steps(message)
            mock_log.assert_called()

    def test_cancel_current_step_settings_action(self, bot, message):
        """Тест отмены редактирования настроек"""
        handler = StepHandlers(bot)
        user_state = {"action": "edit_seeker_field"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.clear_user_state"
        ):
            handler.cancel_current_step(123, 456)
            bot.send_message.assert_called()
            assert "Изменение отменено" in bot.send_message.call_args[0][1]
