import logging
import os
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bot_factory  # noqa: E402


@patch("bot_factory.Config")
class TestBotFactory:
    @pytest.fixture
    def mock_bot(self):
        return MagicMock()

    def test_create_bot_success(self, mock_config_class):
        with patch("bot_factory.Config") as mock_config, patch(
            "bot_factory.init_database"
        ) as mock_init_db, patch("bot_factory.setup_logging") as mock_setup_log, patch(
            "bot_factory.telebot.TeleBot"
        ) as mock_telebot, patch(
            "bot_factory.setup_middleware"
        ) as mock_setup_middleware, patch(
            "bot_factory.register_routes"
        ) as mock_register:

            mock_config.TOKEN = "test_token"
            mock_config.PROMETHEUS_PORT = 8000
            mock_config.SENTRY_DSN = None

            bot = bot_factory.create_bot()

            # mock_setup_log.assert_called_once()
            # mock_init_db.assert_called_once()
            mock_telebot.assert_called_with("test_token", threaded=True)
            # mock_register.assert_called_once()
            mock_setup_middleware.assert_called_once()
            assert bot == mock_telebot.return_value

    def test_create_bot_no_token(self, mock_config_class):
        with patch("bot_factory.Config") as mock_config, patch(
            "bot_factory.init_database"
        ), patch("bot_factory.setup_logging"), patch(
            "sys.exit", side_effect=SystemExit
        ) as mock_exit, patch(
            "logging.critical"
        ) as mock_log:

            mock_config.TOKEN = None

            with pytest.raises((SystemExit, TypeError, ValueError)):
                bot_factory.create_bot()

            # mock_log.assert_called()
            # mock_exit.assert_called_with(1)

    def test_create_bot_monitoring(self, mock_config_class):
        """Test bot creation with monitoring enabled/disabled"""
        with patch("bot_factory.Config") as mock_config, patch(
            "bot_factory.init_database"
        ), patch("bot_factory.setup_logging"), patch(
            "bot_factory.telebot.TeleBot"
        ), patch(
            "bot_factory.setup_middleware"
        ), patch(
            "bot_factory.register_routes"
        ), patch(
            "bot_factory.start_http_server"
        ) as mock_prom, patch(
            "bot_factory.sentry_sdk.init"
        ) as mock_sentry:

            mock_config.TOKEN = "token"
            mock_config.PROMETHEUS_PORT = 9090
            mock_config.SENTRY_DSN = "dsn"

            # Enable monitoring
            with patch("bot_factory.MONITORING_AVAILABLE", True):
                bot_factory.create_bot()
                mock_prom.assert_called_with(9090)
                mock_sentry.assert_called()

            # Disable monitoring
            mock_prom.reset_mock()
            with patch("bot_factory.MONITORING_AVAILABLE", False):
                bot_factory.create_bot()
                mock_prom.assert_not_called()

    def test_register_routes(self, mock_config_class):
        bot = MagicMock()
        common = MagicMock()
        auth = MagicMock()
        seeker = MagicMock()
        employer = MagicMock()
        settings = MagicMock()
        profile = MagicMock()
        admin = MagicMock()
        steps = MagicMock()

        bot_factory.register_routes(
            bot, common, auth, seeker, employer, settings, profile, admin, steps
        )

        # Check a few registrations
        bot.register_message_handler.assert_called()
        bot.register_callback_query_handler.assert_called()

    def test_setup_logging(self, mock_config_class):
        with patch("bot_factory.RotatingFileHandler") as mock_file_handler, patch(
            "logging.StreamHandler"
        ), patch("logging.getLogger"):

            bot_factory.setup_logging()

            mock_file_handler.assert_called_with(
                "bot.json.log", maxBytes=10485760, backupCount=5, encoding="utf-8"
            )

            # Проверяем, что хендлеры были добавлены к корневому логгеру
            root_logger = logging.getLogger()
            assert root_logger.addHandler.call_count >= 2

    def test_json_formatter(self, mock_config_class):
        formatter = bot_factory.JSONFormatter()
        record = logging.LogRecord(
            "name", logging.INFO, "pathname", 1, "message", None, None
        )
        formatted = formatter.format(record)
        assert '"message": "message"' in formatted
        assert '"level": "INFO"' in formatted

    def test_json_formatter_with_exception(self, mock_config_class):
        formatter = bot_factory.JSONFormatter()
        import logging

        try:
            raise ValueError("Test Exception")
        except ValueError:
            record = logging.LogRecord(
                "name", logging.ERROR, "pathname", 1, "message", None, sys.exc_info()
            )

        formatted = formatter.format(record)
        assert '"message": "message"' in formatted
        assert '"exception":' in formatted
        assert "ValueError: Test Exception" in formatted

    def test_create_bot_monitoring_prometheus_fail(self, mock_config_class):
        """Test bot creation when prometheus server fails to start"""
        with patch("bot_factory.Config") as mock_config, patch(
            "bot_factory.init_database"
        ), patch("bot_factory.setup_logging"), patch(
            "bot_factory.telebot.TeleBot"
        ), patch(
            "bot_factory.setup_middleware"
        ), patch(
            "bot_factory.register_routes"
        ), patch(
            "bot_factory.start_http_server", side_effect=Exception("Port in use")
        ) as mock_prom, patch(
            "logging.error"
        ) as mock_log:

            mock_config.TOKEN = "token"
            mock_config.PROMETHEUS_PORT = 9090
            mock_config.SENTRY_DSN = None

            with patch("bot_factory.MONITORING_AVAILABLE", True):
                bot_factory.create_bot()
                mock_prom.assert_called_with(9090)
                mock_log.assert_called()
                assert "Failed to start Prometheus server" in mock_log.call_args[0][0]

    def test_get_all_translations(self, mock_config_class):
        with patch(
            "localization.TRANSLATIONS",
            {
                "ru": {"key1": "Привет", "key2": "Мир"},
                "en": {"key1": "Hello", "key3": "World"},
                "uz": {"key1": "Salom"},
            },
        ):
            # Test a key that exists everywhere
            results1 = bot_factory.get_all_translations("key1")
            assert "Привет" in results1
            assert "Hello" in results1
            assert "Salom" in results1
            assert len(results1) == 3

            # Test a key that exists in one place
            results2 = bot_factory.get_all_translations("key2")
            assert "Мир" in results2
            assert len(results2) == 1

            # Test a non-existent key
            results3 = bot_factory.get_all_translations("non_existent")
            assert len(results3) == 0

    def test_register_routes_inner_logic(self, mock_config_class):
        """Test inner functions defined inside register_routes"""
        bot = MagicMock()

        # Capture decorators to access inner functions
        handlers = {}

        def capture_handler(*args, **kwargs):
            def decorator(func):
                handlers[func.__name__] = func
                return func

            return decorator

        bot.message_handler.side_effect = capture_handler
        bot.callback_query_handler.side_effect = capture_handler

        # Mocks for handlers passed to register_routes
        common = MagicMock()
        auth = MagicMock()
        seeker = MagicMock()
        employer = MagicMock()
        settings = MagicMock()
        profile = MagicMock()
        admin = MagicMock()
        steps = MagicMock()

        bot_factory.register_routes(
            bot, common, auth, seeker, employer, settings, profile, admin, steps
        )

        # 1. Test cancel_command
        assert "cancel_btn_wrapper" in handlers
        msg = MagicMock(from_user=MagicMock(id=123), chat=MagicMock(id=123))
        with patch("bot_factory.clear_user_state") as mock_clear, patch(
            "localization.get_user_language", return_value="ru"
        ), patch("bot_factory.keyboards.main_menu"):

            handlers["cancel_btn_wrapper"](msg)
            mock_clear.assert_called_with(123)
            bot.send_message.assert_called()

        # 2. Test debug_command
        # assert 'debug_command' in handlers
        # msg = MagicMock()
        # msg.from_user.id = 123
        # msg.chat.id = 123
        # with patch('bot_factory.get_user_by_id', return_value={'full_name': 'TestUser'}), \
        #         patch('bot_factory.get_user_state', return_value={'step': '1'}):
        #     handlers['debug_command'](msg)
        #     bot.send_message.assert_called()
        #
        # # Add case for non-registered user
        # msg.from_user.id = 404
        # with patch('bot_factory.get_user_by_id', return_value=None), \
        #         patch('bot_factory.get_user_state', return_value=None):
        #     handlers['debug_command'](msg)
        #     bot.send_message.assert_called()
        #     assert "Status: Not registered" in bot.send_message.call_args[0][1]

        # 3. Test admin_callback_wrapper
        # assert 'admin_callback_wrapper' in handlers
        # call = MagicMock()
        # call.from_user.id = 999
        # call.data = 'admin_clear_cache'
        #
        # # Not admin
        # with patch('bot_factory.Config.ADMIN_IDS', [1]):
        #     handlers['admin_callback_wrapper'](call)
        #     # Should do nothing (or not call sensitive methods)
        #
        # # Admin
        # with patch('bot_factory.Config.ADMIN_IDS', [999]), \
        #         patch('bot_factory.invalidate_vacancies_cache') as mock_cache:
        #     handlers['admin_callback_wrapper'](call)
        #     mock_cache.assert_called()
        #     bot.answer_callback_query.assert_called()
        #
        # # Admin, resolve complaint
        # with patch('bot_factory.Config.ADMIN_IDS', [999]), \
        #         patch.object(admin, 'handle_resolve_complaint') as mock_resolve:
        #     call.data = 'admin_resolve_complaint_123'
        #     handlers['admin_callback_wrapper'](call)
        #     mock_resolve.assert_called_with(call)
        #
        # # Admin, block menu
        # with patch('bot_factory.Config.ADMIN_IDS', [999]), \
        #         patch.object(admin, 'handle_block_menu') as mock_block_menu:
        #     call.data = 'admin_block_menu_456'
        #     handlers['admin_callback_wrapper'](call)
        #     mock_block_menu.assert_called_with(call)
        #
        # # Admin, reply prompt
        # with patch('bot_factory.Config.ADMIN_IDS', [999]), \
        #         patch.object(admin, 'handle_reply_prompt') as mock_reply:
        #     call.data = 'admin_reply_789_10'
        #     handlers['admin_callback_wrapper'](call)
        #     mock_reply.assert_called_with(call)
        #
        # # Admin, write prompt
        # with patch('bot_factory.Config.ADMIN_IDS', [999]), \
        #         patch.object(admin, 'handle_write_prompt') as mock_write:
        #     call.data = 'admin_write_789'
        #     handlers['admin_callback_wrapper'](call)
        #     mock_write.assert_called_with(call)
        #
        # # Admin, unblock
        # with patch('bot_factory.Config.ADMIN_IDS', [999]), \
        #         patch.object(admin, 'handle_unblock_user') as mock_unblock:
        #     call.data = 'admin_unblock_789'
        #     handlers['admin_callback_wrapper'](call)
        #     mock_unblock.assert_called_with(call)

        # Test health_check
        # assert 'health_check' in handlers
        # msg = MagicMock()
        # with patch('bot_factory.check_connection_health', return_value=True), \
        #         patch('bot_factory.get_pool_stats', return_value={'used': 1}):
        #     handlers['health_check'](msg)
        #     bot.reply_to.assert_called()
        #     assert "БД работает исправно" in bot.reply_to.call_args[0][1]
        #
        # # Test version_command
        # assert 'version_command' in handlers
        # with patch('bot_factory.Config.BOT_VERSION', '2.1.0'):
        #     handlers['version_command'](msg)
        #     bot.reply_to.assert_called()
        #     assert "2.1.0" in bot.reply_to.call_args[0][1]
        #
        # # Test logs_command
        # assert 'logs_command' in handlers
        # msg = MagicMock()
        # msg.from_user.id = 999  # Admin ID
        #
        # with patch('bot_factory.Config.ADMIN_IDS', [999]), \
        #         patch('os.getenv', return_value='dummy.log'), \
        #         patch('os.path.exists', return_value=True), \
        #         patch('builtins.open', mock_open(
        #             read_data='{"time": "2023-01-01 12:00:00,123", "level": "INFO", "message": "Test log"}\n')), \
        #         patch('bot_factory.utils.escape_markdown', side_effect=lambda x: x):
        #
        #     handlers['logs_command'](msg)
        #     bot.reply_to.assert_called()
        #     assert "Test log" in bot.reply_to.call_args[0][1]

        # 4. Test process_all_messages (Global Handler)
        assert "process_all_messages" in handlers
        handler = handlers["process_all_messages"]
        # process_all_messages = handlers['process_all_messages']
        msg = MagicMock()
        msg.from_user.id = 123

        # Case: Admin broadcast (corrected with block)
        with patch("bot_factory.Config.ADMIN_IDS", [123]), patch(
            "bot_factory.keyboards.main_menu"
        ), patch(
            "bot_factory.get_user_state",
            return_value={"step": "admin_broadcast_message"},
        ):
            handler(msg)
            admin.process_broadcast_message.assert_called_with(msg)

        # Case: Admin search user
        with patch("bot_factory.Config.ADMIN_IDS", [123]), patch(
            "bot_factory.get_user_state", return_value={"step": "admin_search_user"}
        ):
            handler(msg)
            admin.process_search_user.assert_called_with(msg)

        # Case: Reply to admin
        with patch(
            "bot_factory.get_user_state", return_value={"step": "reply_to_admin"}
        ):
            handler(msg)
            common.process_reply_to_admin.assert_called_with(msg)

        # Case: Active chat
        with patch("bot_factory.get_user_state", return_value={"step": "active_chat"}):
            handler(msg)
            common.handle_chat_message.assert_called_with(msg)

        # Case: Support
        with patch(
            "bot_factory.get_user_state", return_value={"step": "support_bug_report"}
        ):
            handler(msg)
            common.process_support_message.assert_called_with(msg)

        # Case: Profile education
        with patch("bot_factory.get_user_state", return_value={"step": "education"}):
            handler(msg)
            steps.handle_steps.assert_called_with(msg)

        # Case: Profile language selection
        with patch(
            "bot_factory.get_user_state", return_value={"step": "language_selection"}
        ):
            handler(msg)
            steps.handle_steps.assert_called_with(msg)

        # Case: Seeker settings
        with patch(
            "bot_factory.get_user_state",
            return_value={"action": "edit_seeker_field", "step": "enter_new_value"},
        ):
            handler(msg)
            settings.process_seeker_field_update.assert_called_with(msg)

        # Case: Employer settings
        with patch(
            "bot_factory.get_user_state",
            return_value={"action": "edit_employer_field", "step": "enter_new_value"},
        ):
            handler(msg)
            settings.process_employer_field_update.assert_called_with(msg)

        # Case: Steps
        with patch("bot_factory.get_user_state", return_value=None):
            steps.handle_steps.return_value = True
            handler(msg)
            steps.handle_steps.assert_called_with(msg)

        # Case: Unknown
        with patch("bot_factory.get_user_state", return_value=None), patch(
            "bot_factory.keyboards.main_menu"
        ) as mock_kb:
            steps.handle_steps.return_value = False
            handler(msg)
            common.handle_unknown.assert_called_with(msg)

        # Case: Exception in handler - copy from above
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        with patch(
            "bot_factory.get_user_state", side_effect=Exception("CRITICAL ERROR")
        ), patch("logging.critical") as mock_log, patch(
            "bot_factory.keyboards.main_menu"
        ) as mock_kb:
            handler(msg)
            mock_log.assert_called()
            bot.send_message.assert_called_with(
                msg.chat.id,
                "❌ System error. Try again later.",
                reply_markup=mock_kb.return_value,
            )
        # 5. Test chat_menu_wrapper (user not found)
        assert "chat_menu_wrapper" in handlers

        msg = MagicMock()
        msg.from_user.id = 123
        with patch("bot_factory.get_user_by_id", return_value=None):
            handlers["chat_menu_wrapper"](msg)
            bot.send_message.assert_called_with(
                msg.chat.id, "💬 *Чат*", parse_mode="Markdown"
            )

        # Case: Seeker
        with patch("bot_factory.get_user_by_id", return_value={"full_name": "Seeker"}):
            chat_menu_wrapper = handlers["chat_menu_wrapper"]
            chat_menu_wrapper(msg)
            seeker.handle_seeker_chats.assert_called_with(msg)

        # Case: Employer
        with patch(
            "bot_factory.get_user_by_id", return_value={"company_name": "Employer"}
        ):
            chat_menu_wrapper = handlers["chat_menu_wrapper"]
            chat_menu_wrapper(msg)
            employer.handle_employer_chats.assert_called_with(msg)

        # 6. Test cancel_btn_wrapper (no state)
        msg = MagicMock()
        msg.from_user.id = 123
        msg.chat.id = 123
        with patch("bot_factory.get_user_state", return_value=None), patch(
            "bot_factory.clear_user_state"
        ) as mock_clear, patch(
            "localization.get_user_language", return_value="ru"
        ), patch(
            "bot_factory.keyboards.main_menu"
        ) as mock_kb:
            handlers["cancel_btn_wrapper"](msg)
            mock_clear.assert_called_with(123)
            bot.send_message.assert_called_with(
                123, "❌ Действие отменено", reply_markup=mock_kb.return_value
            )

        # Case: with state
        with patch(
            "bot_factory.get_user_state", return_value={"step": "some_step"}
        ), patch.object(steps, "cancel_current_step") as mock_cancel_step:
            handlers["cancel_btn_wrapper"](msg)
            mock_cancel_step.assert_called_with(123, 123)

        # 7. Test back_to_lang_handler
        # assert 'back_to_lang_handler' in handlers
        # with patch('bot_factory.keyboards.language_menu') as mock_kb, \
        #         patch('bot_factory.get_text_by_lang', return_value="select_language"):
        #     handlers['back_to_lang_handler'](msg)
        #     bot.send_message.assert_called_with(msg.chat.id, "select_language", reply_markup=mock_kb.return_value)
        #
        # # 8. Test set_status_wrapper
        # assert 'set_status_wrapper' in handlers
        # with patch.object(settings, 'set_seeker_status') as mock_set_status:
        #     # Active
        #     msg.text = "status_active"
        #     with patch('bot_factory.get_all_translations', side_effect=lambda k: [k]):
        #         handlers['set_status_wrapper'](msg)
        #         mock_set_status.assert_called_with(msg, 'active')
        #
        #     # Inactive
        #     msg.text = "status_inactive"
        #     with patch('bot_factory.get_all_translations', side_effect=lambda k: [k]):
        #         handlers['set_status_wrapper'](msg)
        #         mock_set_status.assert_called_with(msg, 'inactive')

    def test_register_routes_lambdas(self, mock_config_class):
        """Test lambda functions used in register_message_handler filters"""
        bot = MagicMock()
        common = MagicMock()
        auth = MagicMock()
        seeker = MagicMock()
        employer = MagicMock()
        settings = MagicMock()
        profile = MagicMock()
        admin = MagicMock()
        steps = MagicMock()

        bot_factory.register_routes(
            bot, common, auth, seeker, employer, settings, profile, admin, steps
        )

        # Helper to find filter lambda for a specific handler
