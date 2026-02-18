import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import database  # noqa: E402, F401
import database.core  # noqa: E402, F401
import utils  # noqa: E402, F401
from handlers.common import CommonHandlers  # noqa: E402


class TestCommonHandlers:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return CommonHandlers(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.from_user.first_name = "TestUser"
        msg.text = "/start"
        msg.caption = None
        msg.photo = None
        return msg

    @pytest.fixture(autouse=True)
    def mock_lang(self):
        with patch("localization.get_user_language", return_value="ru"):
            yield

    @pytest.fixture(autouse=True)
    def mock_get_text(self):
        """Mock get_text_by_lang to return the key itself for consistent testing."""
        with patch(
            "handlers.common.get_text_by_lang", side_effect=lambda key, lang: key
        ), patch(
            "handlers.support.get_text_by_lang", side_effect=lambda key, lang: key
        ):
            yield

    def test_handle_start_new_user(self, handler, message):
        """Тест /start для нового пользователя"""
        with patch("handlers.common.database.clear_user_state") as mock_clear, patch(
            "handlers.common.database.get_user_by_id", return_value=None
        ):

            handler.handle_start(message)

            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            # Проверяем, что отправлено меню выбора языка
            args = handler.bot.send_message.call_args
            assert "select_language" in args[0][1]

    def test_handle_start_existing_seeker(self, handler, message):
        """Тест /start для существующего соискателя"""
        user_data = {"full_name": "John Doe", "id": 1}
        with patch("handlers.common.database.clear_user_state"), patch(
            "handlers.common.database.get_user_by_id", return_value=user_data
        ):

            handler.handle_start(message)

            handler.bot.send_message.assert_called()
            args = handler.bot.send_message.call_args
            assert "welcome_back" in args[0][1]

    def test_handle_start_existing_employer(self, handler, message):
        """Тест /start для существующего работодателя"""
        user_data = {"company_name": "Tech Corp", "id": 2}
        with patch("handlers.common.database.clear_user_state"), patch(
            "handlers.common.database.get_user_by_id", return_value=user_data
        ):

            handler.handle_start(message)

            handler.bot.send_message.assert_called()
            args = handler.bot.send_message.call_args
            assert "welcome_back" in args[0][1]

    def test_handle_health_ok(self, handler, message):
        """Тест /health, когда БД в порядке"""
        with patch("handlers.common.check_connection_health", return_value=True), patch(
            "handlers.common.get_pool_stats", return_value={"used": 1}
        ):
            handler.handle_health(message)
            handler.bot.reply_to.assert_called()
            text = handler.bot.reply_to.call_args[0][1]
            assert "✅ БД работает исправно" in text
            assert "Статистика пула" in text

    def test_handle_health_fail(self, handler, message):
        """Тест /health, когда есть проблемы с БД"""
        with patch("handlers.common.check_connection_health", return_value=False):
            handler.handle_health(message)
            handler.bot.reply_to.assert_called_with(
                message, "❌ Проблемы с подключением к БД!"
            )

    def test_handle_version(self, handler, message):
        """Тест команды /version"""
        with patch("handlers.common.Config.BOT_VERSION", "2.1.0"):
            handler.handle_version(message)
            handler.bot.reply_to.assert_called_with(
                message, "🤖 Версия бота: `2.1.0`", parse_mode="Markdown"
            )

    def test_handle_cancel(self, handler, message):
        """Тест команды /cancel"""
        with patch("handlers.common.database.clear_user_state") as mock_clear, patch(
            "keyboards.main_menu"
        ) as mock_kb:
            handler.handle_cancel(message)
            mock_clear.assert_called_with(message.from_user.id)
            handler.bot.send_message.assert_called_with(
                message.chat.id,
                "❌ Действие отменено",
                reply_markup=mock_kb.return_value,
            )

    def test_handle_debug_registered_seeker(self, handler, message):
        """Тест /debug для зарегистрированного соискателя"""
        user_data = {"full_name": "Debug User", "id": 1}
        user_state = {"step": "some_step", "value": "abc"}
        with patch(
            "handlers.common.database.get_user_by_id", return_value=user_data
        ), patch("handlers.common.get_user_state", return_value=user_state):
            handler.handle_debug(message)
            handler.bot.send_message.assert_called()
            text = handler.bot.send_message.call_args[0][1]
            assert "Debug Info" in text
            assert f"ID: `{message.from_user.id}`" in text
            assert "Role: Seeker" in text
            assert "Name: Debug User" in text
            assert "State:" in text
            assert "step: some_step" in text

    def test_handle_help(self, handler, message):
        """Тест команды /help"""
        handler.handle_help(message)
        handler.bot.send_message.assert_called()
        assert "help_text" in handler.bot.send_message.call_args[0][1]

    def test_handle_unknown_command(self, handler, message):
        """Тест неизвестной команды"""
        message.text = "/unknown"
        handler.handle_unknown(message)
        handler.bot.send_message.assert_called()
        assert "unknown_command" in handler.bot.send_message.call_args[0][1]

    def test_handle_unknown_text_not_logged_in(self, handler, message):
        """Тест неизвестного текста (не залогинен)"""
        message.text = "Just text"
        with patch("handlers.common.database.get_user_by_id", return_value=None):
            handler.handle_unknown(message)
            handler.bot.send_message.assert_called()
            assert (
                "unknown_message_not_logged_in"
                in handler.bot.send_message.call_args[0][1]
            )

    def test_handle_back_to_main(self, handler, message):
        """Тест возврата в главное меню"""
        with patch("handlers.common.database.clear_user_state") as mock_clear, patch(
            "handlers.common.database.get_user_by_id", return_value={"id": 1}
        ):
            handler.handle_back_to_main(message)
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            text = handler.bot.send_message.call_args[0][1]
            assert "main_menu" in text

    def test_handle_back_to_main_no_lang_set(self, handler, message):
        """Тест возврата в главное меню без установленного языка"""
        with patch("handlers.common.database.get_user_by_id", return_value=None), patch(
            "handlers.common.get_user_state", return_value={}
        ), patch("handlers.common.database.clear_user_state"):

            handler.handle_back_to_main(message)

            handler.bot.send_message.assert_called()
            # Должно быть отправлено меню выбора языка
            assert "select_language" in handler.bot.send_message.call_args[0][1]

    def test_handle_back_to_lang(self, handler, message):
        """Тест возврата к выбору языка"""
        with patch("keyboards.language_menu") as mock_kb:
            handler.handle_back_to_lang(message)
            handler.bot.send_message.assert_called()
            text = handler.bot.send_message.call_args[0][1]
            assert "select_language" in text
            assert (
                handler.bot.send_message.call_args[1]["reply_markup"]
                == mock_kb.return_value
            )

    def test_handle_back_to_main_with_lang_in_state(self, handler, message):
        """Тест возврата в главное меню с языком во временном состоянии"""
        with patch("handlers.common.database.get_user_by_id", return_value=None), patch(
            "handlers.common.get_user_state", return_value={"language_code": "uz"}
        ), patch("handlers.common.get_user_language", return_value="uz"), patch(
            "handlers.common.database.clear_user_state"
        ), patch(
            "handlers.common.database.set_user_state"
        ) as mock_set_state:
            handler.handle_back_to_main(message)
            # Проверяем, что язык восстанавливается в состоянии после очистки
            mock_set_state.assert_called_with(
                message.from_user.id, {"language_code": "uz"}
            )

    def test_handle_back_to_profile_seeker(self, handler, message):
        """Тест возврата в профиль соискателя"""
        user_data = {"full_name": "John"}
        with patch("handlers.common.database.get_user_by_id", return_value=user_data):
            handler.handle_back_to_profile(message)
            handler.bot.send_message.assert_called()
            assert "back_to_seeker_panel" in handler.bot.send_message.call_args[0][1]

    def test_handle_back_to_profile_employer(self, handler, message):
        """Тест возврата в профиль работодателя"""
        user_data = {"company_name": "Corp"}
        with patch("handlers.common.database.get_user_by_id", return_value=user_data):
            handler.handle_back_to_profile(message)
            handler.bot.send_message.assert_called()
            assert "back_to_employer_panel" in handler.bot.send_message.call_args[0][1]

    def test_handle_back_to_profile_not_found(self, handler, message):
        """Тест возврата в профиль, когда пользователь не найден в БД"""
        with patch(
            "handlers.common.database.get_user_by_id", return_value=None
        ), patch.object(handler, "handle_back_to_main") as mock_back_to_main:
            handler.handle_back_to_profile(message)
            # Должен перенаправить на главный экран
            mock_back_to_main.assert_called_with(message)

    def test_handle_about(self, handler, message):
        """Тест команды /about"""
        handler.handle_about(message)
        handler.bot.send_message.assert_called()
        assert "about_bot_text" in handler.bot.send_message.call_args[0][1]

    def test_handle_support(self, handler, message):
        """Тест команды /support"""
        handler.handle_support(message)
        handler.bot.send_message.assert_called()
        assert "support_header" in handler.bot.send_message.call_args[0][1]

    def test_handle_admin(self, handler, message):
        """Тест админ-панели"""
        # handle_admin uses direct execute_query calls
        with patch("handlers.common.database.execute_query") as mock_query, patch(
            "config.Config.ADMIN_IDS", [456]
        ):
            # Mock returns for seekers count and employers count
            mock_query.side_effect = [{"cnt": 10}, {"cnt": 5}]
            handler.handle_admin(message)
            handler.bot.send_message.assert_called()
            text = handler.bot.send_message.call_args[0][1]
            assert "Панель администратора" in text
            assert "Соискатели: 10" in text
            assert "Работодатели: 5" in text

    def test_handle_admin_not_admin(self, handler, message):
        """Тест вызова /admin не-администратором"""
        with patch(
            "config.Config.ADMIN_IDS", [999]
        ):  # Admin ID is not message.from_user.id
            handler.handle_admin(message)
            handler.bot.send_message.assert_called_with(
                message.chat.id, "❌ У вас нет прав доступа."
            )

    def test_handle_unknown_text_logged_in_seeker(self, handler, message):
        """Тест неизвестного текста (залогинен соискатель)"""
        message.text = "Just text"
        user_data = {"full_name": "John"}
        with patch("handlers.common.database.get_user_by_id", return_value=user_data):
            handler.handle_unknown(message)
            handler.bot.send_message.assert_called()
            assert (
                "unknown_message_logged_in" in handler.bot.send_message.call_args[0][1]
            )
            # Check for correct keyboard
            assert handler.bot.send_message.call_args[1]["reply_markup"] is not None

    def test_handle_start_chat_success(self, handler):
        """Тест начала чата"""
        call = MagicMock()
        call.data = "start_chat_789"
        call.from_user.id = 456

        target_user = {"company_name": "Target Corp"}
        with patch(
            "handlers.chat.database.get_user_by_id", return_value=target_user
        ), patch("handlers.chat.database.set_user_state") as mock_set:

            handler.handle_start_chat(call)

            mock_set.assert_called()
            state = mock_set.call_args[0][1]
            assert state["step"] == "active_chat"
            assert state["target_id"] == 789
            assert state["target_name"] == "Target Corp"

            handler.bot.send_message.assert_called()
            assert "Чат с Target Corp" in handler.bot.send_message.call_args[0][1]

    def test_handle_chat_message_success(self, handler, message):
        """Тест отправки сообщения в чате"""
        user_state = {"step": "active_chat", "target_id": 789}
        sender_data = {"full_name": "Sender"}

        with patch(
            "handlers.chat.database.get_user_state", return_value=user_state
        ), patch("handlers.chat.database.get_user_by_id", return_value=sender_data):

            handler.handle_chat_message(message)

            # Проверяем отправку получателю
            recipient_call = handler.bot.send_message.call_args_list[0]
            assert recipient_call[0][0] == 789  # target_id
            assert "Сообщение от Sender" in recipient_call[0][1]

            # Проверяем подтверждение отправителю
            sender_call = handler.bot.send_message.call_args_list[1]
            assert sender_call[0][0] == 123  # chat_id
            assert "Сообщение отправлено" in sender_call[0][1]

    def test_handle_stop_chat(self, handler, message):
        """Тест завершения чата"""
        user_data = {"full_name": "John"}
        with patch("handlers.chat.database.clear_user_state") as mock_clear, patch(
            "handlers.chat.database.get_user_by_id", return_value=user_data
        ):

            handler.handle_stop_chat(message)

            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Чат завершен" in handler.bot.send_message.call_args[0][1]

    def test_handle_start_chat_user_not_found(self, handler):
        """Тест начала чата с несуществующим пользователем"""
        call = MagicMock()
        call.data = "start_chat_999"  # non-existent user
        call.from_user.id = 456
        call.id = "call_id_1"

        with patch("handlers.chat.database.get_user_by_id", return_value=None):
            handler.handle_start_chat(call)
            handler.bot.answer_callback_query.assert_called_with(
                call.id, "❌ Пользователь не найден"
            )

    def test_handle_chat_message_api_error(self, handler, message):
        """Тест ошибки API при отправке сообщения в чате"""
        user_state = {"step": "active_chat", "target_id": 789}
        sender_data = {"full_name": "Sender"}

        with patch(
            "handlers.chat.database.get_user_state", return_value=user_state
        ), patch("handlers.chat.database.get_user_by_id", return_value=sender_data):

            # Мокаем ошибку при отправке получателю
            handler.bot.send_message.side_effect = [Exception("API Error"), None]

            handler.handle_chat_message(message)

            # Проверяем, что было 2 вызова send_message (попытка получателю и сообщение об ошибке отправителю)
            assert handler.bot.send_message.call_count == 2
            error_call = handler.bot.send_message.call_args_list[1]
            assert error_call[0][0] == 123  # chat_id
            assert "Не удалось отправить сообщение" in error_call[0][1]

    def test_handle_admin_exception(self, handler, message):
        """Тест обработки ошибки в handle_admin"""
        with patch(
            "handlers.common.database.execute_query", side_effect=Exception("DB Error")
        ), patch("config.Config.ADMIN_IDS", [456]), patch("logging.error") as mock_log:

            handler.handle_admin(message)

            mock_log.assert_called()
            handler.bot.send_message.assert_called()
            assert "Произошла ошибка" in handler.bot.send_message.call_args[0][1]

    def test_handle_report_bug(self, handler, message):
        """Тест начала сообщения об ошибке"""
        with patch("handlers.support.database.set_user_state") as mock_set:
            handler.handle_report_bug(message)
            mock_set.assert_called_with(456, {"step": "support_bug_report"})
            handler.bot.send_message.assert_called()
            assert "report_bug_header" in handler.bot.send_message.call_args[0][1]

    def test_handle_complaint(self, handler, message):
        """Тест начала подачи жалобы"""
        with patch("handlers.support.database.set_user_state") as mock_set:
            handler.handle_complaint(message)
            mock_set.assert_called_with(456, {"step": "support_complaint"})
            handler.bot.send_message.assert_called()
            assert "complaint_header" in handler.bot.send_message.call_args[0][1]

    def test_process_support_message_success(self, handler, message):
        """Тест успешной отправки сообщения в поддержку"""
        message.text = "Something is wrong"
        user_state = {"step": "support_bug_report"}

        # Mock execute_query to handle language check and insert
        def query_side_effect(query, *args, **kwargs):
            if "SELECT language_code" in query:
                return {"language_code": "ru"}
            return None

        with patch(
            "handlers.support.database.get_user_state", return_value=user_state
        ), patch(
            "handlers.support.database.execute_query", side_effect=query_side_effect
        ) as mock_query, patch(
            "handlers.support.database.clear_user_state"
        ) as mock_clear, patch(
            "handlers.support.database.get_user_by_id",
            return_value={"full_name": "test"},
        ):
            handler.process_support_message(message)
            # Check DB insert
            mock_query.assert_any_call(
                "INSERT INTO complaints (user_id, user_name, type, message, photo_id) VALUES (?, ?, ?, ?, ?)",
                (456, "TestUser", "Ошибка", "Something is wrong", None),
                commit=True,
            )
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert (
                "support_message_accepted" in handler.bot.send_message.call_args[0][1]
            )

    def test_handle_start_chat_exception(self, handler):
        """Тест обработки ошибки в handle_start_chat"""
        call = MagicMock()
        call.data = "start_chat_789"
        call.from_user.id = 456

        with patch(
            "handlers.chat.database.get_user_by_id", side_effect=Exception("DB Error")
        ), patch("logging.error") as mock_log:

            handler.handle_start_chat(call)

            mock_log.assert_called()
            handler.bot.answer_callback_query.assert_called_with(call.id, "❌ Ошибка")

    def test_process_support_message_photo_no_caption(self, handler, message):
        """Тест сообщения в поддержку: фото без подписи"""
        message.text = None
        message.caption = None
        message.photo = [MagicMock(file_id="123")]
        user_state = {"step": "support_bug_report"}

        with patch(
            "handlers.support.database.get_user_state", return_value=user_state
        ), patch("handlers.support.database.execute_query") as mock_query, patch(
            "handlers.support.database.clear_user_state"
        ), patch(
            "handlers.support.database.get_user_by_id",
            return_value={"full_name": "User"},
        ):

            handler.process_support_message(message)

            # Проверяем, что использовался дефолтный текст
            args = mock_query.call_args_list[-1][0]  # Last call is INSERT
            assert "support_no_description_photo" in args[1][3]  # params

    def test_process_support_message_no_text_no_photo(self, handler, message):
        """Тест сообщения в поддержку: пустое сообщение"""
        message.text = None
        message.caption = None
        message.photo = None

        with patch(
            "handlers.support.database.get_user_state",
            return_value={"step": "support_bug_report"},
        ):
            handler.process_support_message(message)
            handler.bot.send_message.assert_called()
            assert (
                "support_no_text_no_photo" in handler.bot.send_message.call_args[0][1]
            )

    def test_process_support_message_profanity(self, handler, message):
        """Тест сообщения в поддержку: мат"""
        message.text = "bad word"

        with patch(
            "handlers.support.database.get_user_state",
            return_value={"step": "support_bug_report"},
        ), patch(
            "handlers.support.security.contains_profanity", return_value=True
        ), patch(
            "handlers.support.database.execute_query"
        ) as mock_query:

            handler.process_support_message(message)
            handler.bot.send_message.assert_any_call(
                message.chat.id, "support_profanity_error"
            )
            # Ensure the complaint was not actually saved to the DB
            mock_query.assert_not_called()

    def test_process_support_message_complaint_type(self, handler, message):
        """Тест сообщения в поддержку: тип Жалоба"""
        message.text = "Complaint"
        user_state = {"step": "support_complaint"}

        with patch(
            "handlers.support.database.get_user_state", return_value=user_state
        ), patch("handlers.support.database.execute_query") as mock_query, patch(
            "handlers.support.database.clear_user_state"
        ), patch(
            "handlers.support.database.get_user_by_id",
            return_value={"full_name": "User"},
        ):

            handler.process_support_message(message)

            # Проверяем тип в INSERT
            args = mock_query.call_args_list[-1][0]
            # params is args[1]
            # (user_id, user_name, type, message, photo_id)
            assert args[1][2] == "Жалоба"

    def test_process_support_message_migration_error(self, handler, message):
        """Тест ошибки миграции в process_support_message"""
        message.text = "Bug"
        user_state = {"step": "support_bug_report"}

        with patch(
            "handlers.support.database.get_user_state", return_value=user_state
        ), patch("handlers.support.database.execute_query") as mock_query, patch(
            "handlers.support.database.clear_user_state"
        ), patch(
            "handlers.support.database.get_user_by_id",
            return_value={"full_name": "User"},
        ), patch(
            "logging.error"
        ) as mock_log:

            # Настраиваем side_effect для имитации ошибки только при PRAGMA запросе
            def side_effect(query, *args, **kwargs):
                if "PRAGMA" in query:
                    raise Exception("Migration Error")
                return None

            mock_query.side_effect = side_effect

            handler.process_support_message(message)

            mock_log.assert_called()
            assert "Ошибка миграции" in mock_log.call_args[0][0]
            # Должен продолжить выполнение и попытаться сделать INSERT
            assert mock_query.call_count >= 2

    def test_handle_reply_admin_prompt(self, handler):
        """Тест запроса ответа админу"""
        call = MagicMock()
        call.data = "reply_admin_123"
        call.from_user.id = 456
        call.message.chat.id = 456

        with patch("handlers.chat.database.set_user_state") as mock_set:
            handler.handle_reply_admin_prompt(call)

            mock_set.assert_called_with(
                456, {"step": "reply_to_admin", "target_admin_id": 123}
            )
            handler.bot.send_message.assert_called()

    def test_process_reply_to_admin(self, handler, message):
        """Тест отправки ответа админу"""
        message.text = "Reply text"
        user_state = {"step": "reply_to_admin", "target_admin_id": 123}
        user_data = {"full_name": "User"}

        with patch(
            "handlers.chat.database.get_user_state", return_value=user_state
        ), patch(
            "handlers.chat.database.get_user_by_id", return_value=user_data
        ), patch(
            "handlers.chat.database.clear_user_state"
        ) as mock_clear:

            handler.process_reply_to_admin(message)

            # Send to admin
            handler.bot.send_message.assert_any_call(
                123,
                f"📩 *Ответ от User (ID: `{message.from_user.id}`):*\n\nReply text",
                parse_mode="Markdown",
            )
            # Confirm to user
        handler.bot.send_message.assert_any_call(message.chat.id, "✅ Ответ отправлен.")
        mock_clear.assert_called()

    def test_handle_language_selection_new_user(self, handler, message):
        """Тест выбора языка новым пользователем"""
        message.text = "🇷🇺 Русский"
        with patch("handlers.common.database.get_user_by_id", return_value=None), patch(
            "handlers.common.set_user_state"
        ) as mock_set:

            handler.handle_language_selection(message)

            mock_set.assert_called_with(456, {"language_code": "ru"})
            handler.bot.send_message.assert_called()
            assert "welcome" in handler.bot.send_message.call_args[0][1]

    def test_handle_language_selection_existing_seeker(self, handler, message):
        """Тест смены языка существующим соискателем"""
        message.text = "🇺🇿 O'zbekcha"
        user_data = {"id": 1, "full_name": "Seeker", "telegram_id": 456}

        with patch(
            "handlers.common.database.get_user_by_id", return_value=user_data
        ), patch("handlers.common.database.execute_query") as mock_query:

            handler.handle_language_selection(message)

            mock_query.assert_called()
            assert "UPDATE job_seekers" in mock_query.call_args[0][0]
            handler.bot.send_message.assert_called()
            assert "back_to_seeker_panel" in handler.bot.send_message.call_args[0][1]

    def test_process_support_message_cancel(self, handler, message):
        """Тест отмены обращения в поддержку"""
        message.text = "Отмена"
        with patch("utils.misc.cancel_request", return_value=True), patch(
            "handlers.support.database.clear_user_state"
        ) as mock_clear:

            handler.process_support_message(message)

            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "support_cancelled" in handler.bot.send_message.call_args[0][1]

    def test_handle_debug_employer(self, handler, message):
        """Тест /debug для работодателя"""
        user_data = {"company_name": "Tech Corp", "id": 2}
        with patch(
            "handlers.common.database.get_user_by_id", return_value=user_data
        ), patch("handlers.common.get_user_state", return_value={}):
            handler.handle_debug(message)
            text = handler.bot.send_message.call_args[0][1]
            assert "Role: Employer" in text
            assert "Name: Tech Corp" in text

    def test_handle_language_selection_invalid_code(self, handler, message):
        """Тест выбора языка с неверным текстом"""
        message.text = "Invalid Lang"
        handler.handle_language_selection(message)
        # Ничего не должно произойти (return)
        handler.bot.send_message.assert_not_called()

    def test_handle_language_selection_existing_employer(self, handler, message):
        """Тест смены языка существующим работодателем"""
        message.text = "🇺🇿 O'zbekcha"
        user_data = {"id": 2, "company_name": "Corp", "telegram_id": 456}

        with patch(
            "handlers.common.database.get_user_by_id", return_value=user_data
        ), patch("handlers.common.database.execute_query") as mock_query:

            handler.handle_language_selection(message)

            mock_query.assert_called()
            assert "UPDATE employers" in mock_query.call_args[0][0]
            handler.bot.send_message.assert_called()
            assert "back_to_employer_panel" in handler.bot.send_message.call_args[0][1]

    def test_is_initial_language_selection(self, handler):
        """Тест фильтра _is_initial_language_selection"""
        msg = MagicMock()
        msg.from_user.id = 123
        msg.text = "🇷🇺 Русский"

        with patch(
            "handlers.common.get_user_state",
            return_value={"step": "language_selection"},
        ):
            assert handler._is_initial_language_selection(msg) is False

        with patch("handlers.common.get_user_state", return_value={}):
            assert handler._is_initial_language_selection(msg) is True
