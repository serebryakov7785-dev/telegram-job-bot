from unittest.mock import MagicMock, patch

import pytest

from handlers.auth.base_auth import AuthHandlers


class TestAuthHandlers:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        # Патчим импорты внутри __init__, чтобы изолировать тесты
        with patch("handlers.auth.role_auth.RoleAuth") as MockRole, patch(
            "handlers.auth.seeker_auth.SeekerAuth"
        ) as MockSeeker, patch(
            "handlers.auth.employer_auth.EmployerAuth"
        ) as MockEmployer, patch(
            "handlers.auth.login_auth.LoginAuth"
        ) as MockLogin:

            handler = AuthHandlers(bot)
            # Сохраняем моки для проверок
            handler.mock_role = MockRole.return_value  # type: ignore
            handler.mock_seeker = MockSeeker.return_value  # type: ignore
            handler.mock_employer = MockEmployer.return_value  # type: ignore
            handler.mock_login = MockLogin.return_value  # type: ignore
            return handler

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        return msg

    def test_init(self, bot):
        """Проверка инициализации и связывания обработчиков"""
        with patch("handlers.auth.role_auth.RoleAuth") as MockRole, patch(
            "handlers.auth.seeker_auth.SeekerAuth"
        ) as MockSeeker, patch(
            "handlers.auth.employer_auth.EmployerAuth"
        ) as MockEmployer, patch(
            "handlers.auth.login_auth.LoginAuth"
        ) as MockLogin:

            handler = AuthHandlers(bot)

            MockRole.assert_called_with(bot)
            MockSeeker.assert_called_with(bot)
            MockEmployer.assert_called_with(bot)
            MockLogin.assert_called_with(bot)

            # Проверяем, что set_handlers был вызван для role_auth
            handler.role.set_handlers.assert_called_with(handler.seeker, handler.employer)  # type: ignore

    def test_delegation_role(self, handler, message):
        """Проверка делегирования в RoleAuth"""
        handler.handle_role_selection(message)
        handler.mock_role.handle_role_selection.assert_called_with(message)

        handler.handle_registration_start(message)
        handler.mock_role.handle_registration_start.assert_called_with(message)

    def test_delegation_seeker(self, handler, message):
        """Проверка делегирования в SeekerAuth"""
        handler.process_seeker_phone(message)
        handler.mock_seeker.process_seeker_phone.assert_called_with(message)

        handler.process_seeker_email(message)
        handler.mock_seeker.process_seeker_email.assert_called_with(message)

        handler.process_seeker_name(message)
        handler.mock_seeker.process_seeker_name.assert_called_with(message)

        handler.process_seeker_region(message)
        handler.mock_seeker.process_seeker_region.assert_called_with(message)

        handler.process_seeker_city_selection(message)
        handler.mock_seeker.process_seeker_city_selection.assert_called_with(message)

        handler.finish_seeker_registration(message)
        handler.mock_seeker.finish_seeker_registration.assert_called_with(message)

    def test_delegation_employer(self, handler, message):
        """Проверка делегирования в EmployerAuth"""
        handler.process_employer_name(message)
        handler.mock_employer.process_employer_name.assert_called_with(message)

        handler.process_employer_phone(message)
        handler.mock_employer.process_employer_phone.assert_called_with(message)

        handler.process_employer_email(message)
        handler.mock_employer.process_employer_email.assert_called_with(message)

        handler.process_employer_contact(message)
        handler.mock_employer.process_employer_contact.assert_called_with(message)

        handler.process_employer_region(message)
        handler.mock_employer.process_employer_region.assert_called_with(message)

        handler.process_employer_city_selection(message)
        handler.mock_employer.process_employer_city_selection.assert_called_with(
            message
        )

        handler.process_business_activity(message)
        handler.mock_employer.process_business_activity.assert_called_with(message)

    def test_delegation_login(self, handler, message):
        """Проверка делегирования в LoginAuth"""
        handler.handle_password_recovery(message)
        handler.mock_login.handle_password_recovery.assert_called_with(message)

        handler.process_recovery(message)
        handler.mock_login.process_recovery.assert_called_with(message)

        handler.handle_logout(message)
        handler.mock_login.handle_logout.assert_called_with(message)

    def test_cancel_registration(self, handler):
        """Проверка отмены регистрации"""
        chat_id = 123
        user_id = 456
        text = "Cancel Reason"

        with patch("database.clear_user_state") as mock_clear:
            handler.cancel_registration(chat_id, user_id, text)

            mock_clear.assert_called_with(user_id)
            handler.bot.send_message.assert_called()
            # Проверяем, что текст причины передается в сообщение
            assert text in handler.bot.send_message.call_args[0][1]
