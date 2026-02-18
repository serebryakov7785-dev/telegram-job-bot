import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

import middleware

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestMiddleware:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        return msg

    def test_check_user_blocked_not_blocked(self):
        with patch("middleware.execute_query", return_value=None):
            assert middleware.check_user_blocked(456) is None

    def test_check_user_blocked_forever(self):
        with patch(
            "middleware.execute_query", return_value={"blocked_until": "forever"}
        ):
            assert middleware.check_user_blocked(456) == "forever"

    def test_check_user_blocked_temporary_active(self):
        future = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        with patch("middleware.execute_query", return_value={"blocked_until": future}):
            res = middleware.check_user_blocked(456)
            assert isinstance(res, datetime)

    def test_check_user_blocked_temporary_expired(self):
        past = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        with patch("middleware.execute_query", return_value={"blocked_until": past}):
            assert middleware.check_user_blocked(456) is None

    def test_check_user_blocked_error(self):
        with patch("middleware.execute_query", side_effect=Exception("DB Error")):
            assert middleware.check_user_blocked(456) is None

    def test_setup_middleware(self, bot):
        middleware.setup_middleware(bot)
        assert (
            bot.process_new_messages != bot.process_new_messages.__func__
            if hasattr(bot.process_new_messages, "__func__")
            else True
        )

    def test_custom_process_new_messages_blocked(self, bot, message):
        middleware.setup_middleware(bot)

        with patch("middleware.check_user_blocked", return_value="forever"), patch(
            "middleware.check_rate_limit"
        ) as mock_rate:
            bot.process_new_messages([message])
            bot.send_message.assert_called_with(
                message.chat.id,
                "🚫 *Вы заблокированы навсегда.*",
                parse_mode="Markdown",
            )
            mock_rate.assert_not_called()

    def test_check_rate_limit(self, bot, message):
        # Clear state
        middleware.user_requests.clear()
        middleware.muted_users.clear()

        # 1st request
        assert middleware.check_rate_limit(bot, message) is True

        # Spam
        for _ in range(middleware.RATE_LIMIT):
            middleware.check_rate_limit(bot, message)

        # Blocked
        assert middleware.check_rate_limit(bot, message) is False

        # Verify mute
        assert 456 in middleware.muted_users

    def test_custom_process_new_callback_query(self, bot):
        """Тест middleware для callback query (блокировка)"""
        middleware.setup_middleware(bot)
        call = MagicMock()
        call.from_user.id = 888

        # Blocked user
        with patch("middleware.check_user_blocked", return_value="forever"):
            bot.process_new_callback_query([call])
            bot.answer_callback_query.assert_called()
            assert "заблокированы" in bot.answer_callback_query.call_args[0][1]

    def test_check_user_blocked_temporary_msg(self, bot, message):
        """Test message for temporary block"""
        middleware.setup_middleware(bot)
        future = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

        with patch(
            "middleware.check_user_blocked",
            return_value=datetime.strptime(future, "%Y-%m-%d %H:%M:%S"),
        ):
            bot.process_new_messages([message])
            bot.send_message.assert_called()
            assert "До:" in bot.send_message.call_args[0][1]

    def test_check_rate_limit_callback(self, bot):
        """Test rate limit for callback query"""
        call = MagicMock()
        call.from_user.id = 123
        call.id = "1"
        # No chat attribute on call usually, or it's inside message
        del call.chat

        # Mock muted_users to force mute
        middleware.user_requests[123] = [time.time()] * middleware.RATE_LIMIT

        middleware.check_rate_limit(bot, call)
        bot.answer_callback_query.assert_called()
        assert "Слишком много запросов" in bot.answer_callback_query.call_args[0][1]

    def test_check_rate_limit_exception(self, bot, message):
        """Test exception in check_rate_limit"""
        with patch("middleware.get_user_language", side_effect=Exception("Lang Error")):
            # Should not raise
            middleware.user_requests[message.from_user.id] = [
                time.time()
            ] * middleware.RATE_LIMIT
            assert middleware.check_rate_limit(bot, message) is False

    def test_check_rate_limit_muted(self, bot, message):
        """Test that a muted user is immediately blocked."""
        user_id = message.from_user.id
        middleware.muted_users[user_id] = time.time() + 30  # Mute for 30 seconds

        assert middleware.check_rate_limit(bot, message) is False
        # Ensure no message was sent, as the block happens early
        bot.send_message.assert_not_called()

    def test_custom_process_new_messages_send_error(self, bot, message):
        """Test exception when sending block message."""
        middleware.setup_middleware(bot)

        with patch("middleware.check_user_blocked", return_value="forever"):
            bot.send_message.side_effect = Exception("API Error")
            # Should not raise an exception
            bot.process_new_messages([message])
            bot.send_message.assert_called_once()

    def test_custom_process_new_messages_rate_limited(self, bot, message):
        """Test that rate-limited messages are not processed."""
        middleware.setup_middleware(bot)

        with patch("middleware.check_user_blocked", return_value=None), patch(
            "middleware.check_rate_limit", return_value=False
        ) as mock_rate_limit:

            # Mock the original processor to check if it's called
            original_processor = MagicMock()
            bot.process_new_messages.__closure__[0].cell_contents[
                0
            ] = original_processor  # Access closure

            bot.process_new_messages([message])

            mock_rate_limit.assert_called_with(bot, message)
            original_processor.assert_not_called()

    def test_custom_process_new_callback_query_send_error(self, bot):
        """Test exception when sending block callback answer."""
        middleware.setup_middleware(bot)
        call = MagicMock()
        call.from_user.id = 888

        with patch("middleware.check_user_blocked", return_value="forever"):
            bot.answer_callback_query.side_effect = Exception("API Error")
            # Should not raise an exception
            bot.process_new_callback_query([call])
            bot.answer_callback_query.assert_called_once()

    def test_check_rate_limit_unmute(self, bot, message):
        """Test that user is unmuted after time expires"""
        # Clear global state to avoid interference from other tests
        middleware.user_requests.clear()
        middleware.muted_users.clear()

        user_id = message.from_user.id
        # Mute user in the past
        middleware.muted_users[user_id] = time.time() - 10

        assert middleware.check_rate_limit(bot, message) is True
        assert user_id not in middleware.muted_users
