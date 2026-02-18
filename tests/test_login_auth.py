from unittest.mock import MagicMock, patch

import pytest

import keyboards  # noqa: F401
from handlers.auth.login_auth import LoginAuth


class TestLoginAuth:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return LoginAuth(bot)

    def test_cancel_login(self, handler):
        """Тест отмены входа"""
        chat_id = 123
        user_id = 456
        text = "Login Cancelled"

        with patch("database.clear_user_state") as mock_clear, patch(
            "keyboards.main_menu"
        ) as mock_menu:

            mock_kb = MagicMock()
            mock_menu.return_value = mock_kb

            handler.cancel_login(chat_id, user_id, text)

            mock_clear.assert_called_with(user_id)
            handler.bot.send_message.assert_called_with(
                chat_id, f"❌ *{text}*", parse_mode="Markdown", reply_markup=mock_kb
            )

    @pytest.mark.parametrize("logout_text", ["🚪 Выйти", "🚪 Chiqish", "🚪 Logout"])
    def test_handle_logout(self, handler, logout_text):
        """Тест выхода из системы: перенос в меню выбора языка"""
        message = MagicMock()
        message.chat.id = 123
        message.from_user.id = 456
        message.text = logout_text

        with patch("database.clear_user_state") as mock_clear, patch(
            "keyboards.main_menu"
        ) as mock_kb, patch(
            "handlers.auth.recovery_flow.get_text_by_lang",
            return_value="Logout message",
        ):
            handler.handle_logout(message)

            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called_once()
            # Проверяем, что отправляется сообщение с выбором языка (как при старте нового пользователя)
            args, kwargs = handler.bot.send_message.call_args
            assert "Logout message" in args[1]
            assert kwargs["reply_markup"] == mock_kb.return_value
