import pytest
from unittest.mock import MagicMock, patch
from handlers.auth.login_auth import LoginAuth
import keyboards

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
        
        with patch('database.clear_user_state') as mock_clear, \
             patch('keyboards.main_menu') as mock_menu:
            
            mock_kb = MagicMock()
            mock_menu.return_value = mock_kb
            
            handler.cancel_login(chat_id, user_id, text)
            
            mock_clear.assert_called_with(user_id)
            handler.bot.send_message.assert_called_with(
                chat_id,
                f"❌ *{text}*",
                parse_mode='Markdown',
                reply_markup=mock_kb
            )