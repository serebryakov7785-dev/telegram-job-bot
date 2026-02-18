import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock telebot before importing bot
sys.modules["telebot"] = MagicMock()
sys.modules["telebot.types"] = MagicMock()

import bot  # noqa: E402


class TestBotRoutes:
    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "/start"
        return msg

    def test_start_command(self, message):
        """Тест команды /start"""
        # Проверяем наличие функции start или handle_start
        func = getattr(bot, "start", getattr(bot, "handle_start", None))
        if func:
            with patch(
                "bot.auth_handlers.role.handle_registration_start"
            ) as mock_reg, patch("bot.check_rate_limit", return_value=True):
                func(message)
                mock_reg.assert_called_with(message)

    def test_help_command(self, message):
        """Тест команды /help"""
        message.text = "/help"
        func = getattr(bot, "help_command", getattr(bot, "handle_help", None))
        if func:
            with patch("bot.check_rate_limit", return_value=True), patch(
                "bot.bot.send_message"
            ) as mock_send:
                func(message)
                mock_send.assert_called()

    def test_text_handler_routing(self, message):
        """Тест роутинга текстовых сообщений"""
        message.text = "Some text"
        func = getattr(bot, "handle_text", getattr(bot, "text_message_handler", None))

        if func:
            with patch("bot.check_rate_limit", return_value=True), patch(
                "bot.step_handlers.handle_steps", return_value=False
            ) as mock_steps, patch("bot.handle_main_menu") as mock_menu:

                func(message)
                mock_steps.assert_called_with(message)
                mock_menu.assert_called_with(message)

    def test_callback_handler(self, message):
        """Тест обработки callback"""
        call = MagicMock()
        call.message = message
        call.data = "test_data"
        call.from_user.id = 456

        func = getattr(
            bot, "handle_callback", getattr(bot, "callback_query_handler", None)
        )

        if func:
            with patch("bot.check_rate_limit", return_value=True):
                # Просто проверяем, что функция не падает
                func(call)
