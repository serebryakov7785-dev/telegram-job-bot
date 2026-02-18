from unittest.mock import MagicMock, patch

import pytest

from handlers.auth.login_auth import LoginAuth


class TestRecoveryFlow:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return LoginAuth(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        return msg

    def test_handle_password_recovery(self, handler, message):
        """Test starting the password recovery process."""
        with patch("database.set_user_state") as mock_set_state:
            handler.handle_password_recovery(message)
            mock_set_state.assert_called_with(
                message.from_user.id, {"step": "recovery"}
            )
            handler.bot.send_message.assert_called()
            assert "Восстановление пароля" in handler.bot.send_message.call_args[0][1]

    def test_process_recovery_cancel(self, handler, message):
        """Test cancellation of the recovery process."""
        message.text = "отмена"
        with patch("utils.cancel_request", return_value=True), patch(
            "database.clear_user_state"
        ) as mock_clear:
            handler.process_recovery(message)
            mock_clear.assert_called_with(message.from_user.id)
            handler.bot.send_message.assert_called()
            assert "Восстановление отменено" in handler.bot.send_message.call_args[0][1]

    def test_process_recovery_user_not_found(self, handler, message):
        """Test recovery when the user is not found."""
        message.text = "nonexistent@user.com"
        with patch("utils.cancel_request", return_value=False), patch(
            "database.get_user_by_credentials", return_value=(None, "")
        ), patch("database.clear_user_state") as mock_clear:
            handler.process_recovery(message)
            mock_clear.assert_called_with(message.from_user.id)
            handler.bot.send_message.assert_called()
            assert "Пользователь не найден" in handler.bot.send_message.call_args[0][1]

    def test_process_recovery_success(self, handler, message):
        """Test successful recovery process."""
        message.text = "found@user.com"
        user_data = {"email": "found@user.com", "phone": "+998901234567"}
        with patch("utils.cancel_request", return_value=False), patch(
            "database.get_user_by_credentials", return_value=(user_data, "seeker")
        ), patch("database.clear_user_state") as mock_clear:
            handler.process_recovery(message)
            mock_clear.assert_called_with(message.from_user.id)
            handler.bot.send_message.assert_called()
            text = handler.bot.send_message.call_args[0][1]
            assert "Инструкции отправлены" in text
            assert "fou***@user.com" in text  # Check email masking
