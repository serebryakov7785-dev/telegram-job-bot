import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from handlers.chat import ChatMixin


class TestChatHandlers:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        class Handler(ChatMixin):
            def __init__(self, bot):
                self.bot = bot
                self.handle_back_to_profile = MagicMock()

        return Handler(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        return msg

    def test_handle_chat_message_profanity(self, handler, message):
        """Test chat message with profanity"""
        message.text = "badword"
        with patch(
            "handlers.chat.database.get_user_state", return_value={"target_id": 789}
        ), patch(
            "handlers.chat.database.get_user_by_id", return_value={"full_name": "User"}
        ), patch(
            "utils.security.contains_profanity", return_value=True
        ):

            handler.handle_chat_message(message)
            handler.bot.send_message.assert_called_with(
                456, "❌ Сообщение не отправлено: обнаружена нецензурная лексика."
            )

    def test_process_reply_to_admin_cancel(self, handler, message):
        """Test cancel reply to admin"""
        message.text = "отмена"
        with patch("utils.misc.cancel_request", return_value=True), patch(
            "handlers.chat.database.clear_user_state"
        ) as mock_clear:

            handler.process_reply_to_admin(message)
            mock_clear.assert_called_with(456)
            handler.handle_back_to_profile.assert_called_with(message)

    def test_process_reply_to_admin_exception(self, handler, message):
        """Test exception in reply to admin"""
        with patch("utils.misc.cancel_request", return_value=False), patch(
            "handlers.chat.database.get_user_state", return_value={"target_admin_id": 1}
        ), patch(
            "handlers.chat.database.get_user_by_id", side_effect=Exception("DB Error")
        ):

            handler.process_reply_to_admin(message)
            handler.bot.send_message.assert_called_with(123, "❌ Ошибка отправки.")
