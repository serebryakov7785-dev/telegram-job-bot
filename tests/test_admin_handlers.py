import os
import sys
from typing import Any, Dict
from unittest.mock import ANY, MagicMock, mock_open, patch

import pytest

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import logging  # noqa: E402, F401

import database  # noqa: E402, F401
import database.backup  # noqa: E402, F401
import database.core  # noqa: E402, F401
import database.users  # noqa: E402, F401
import utils  # noqa: E402, F401
from handlers.admin import AdminHandlers  # noqa: E402, F401


class TestAdminHandlers:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return AdminHandlers(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 123456  # Matches ADMIN_IDS in conftest.py
        msg.from_user.first_name = "Admin"
        msg.text = "Test"
        return msg

    @pytest.fixture(autouse=True)
    def mock_lang(self):
        with patch("localization.get_user_language", return_value="ru"):
            yield

    @pytest.fixture(autouse=True)
    def mock_admin_check(self):
        """Fixture to grant admin privileges for all tests in this class."""
        with patch("config.Config.ADMIN_IDS", [123456]):
            yield

    def test_handle_backup_command_not_admin(self, handler, message):
        """Тест вызова /backup не-администратором"""
        message.from_user.id = 999  # Not an admin
        with patch("config.Config.ADMIN_IDS", [123456]), patch.object(
            handler, "handle_create_backup"
        ) as mock_create_backup:
            handler.handle_backup_command(message)
            handler.bot.send_message.assert_called_with(
                message.chat.id, "❌ У вас нет прав доступа."
            )
            mock_create_backup.assert_not_called()

    def test_handle_logs_not_admin(self, handler, message):
        """Тест вызова /logs не-администратором"""
        message.from_user.id = 999  # Not an admin
        with patch("config.Config.ADMIN_IDS", [123456]):
            handler.handle_logs(message)
            # The function should just return, no message sent
            handler.bot.reply_to.assert_not_called()

    def test_handle_logs_empty_file(self, handler, message):
        """Тест /logs, когда лог-файл пуст"""
        m = mock_open(read_data="")
        with patch("os.path.exists", return_value=True), patch("builtins.open", m):
            handler.handle_logs(message)
            handler.bot.reply_to.assert_called_with(message, "📭 Лог пуст.")

    def test_handle_logs_success_json(self, handler, message):
        """Тест /logs с валидными JSON-логами"""
        log_content = (
            '{"time": "2023-10-27 12:30:00,123", "level": "ERROR", "message": "Test error"}\n'
            '{"time": "2023-10-27 12:31:00,123", "level": "INFO", "message": "Test info"}\n'
        )
        m = mock_open(read_data=log_content)
        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", m
        ), patch("utils.escape_markdown", side_effect=lambda x: x):
            handler.handle_logs(message)
            handler.bot.reply_to.assert_called()
            text = handler.bot.reply_to.call_args[0][1]
            assert "🔴" in text
            assert "12:30:00" in text
            assert "*ERROR*: Test error" in text
            assert "ℹ️" in text
            assert "12:31:00" in text
            assert "*INFO*: Test info" in text

    def test_handle_statistics(self, handler, message):
        """Тест отображения статистики"""
        # Patch execute_query in handlers.admin_stats because it likely uses direct SQL
        # Mock return values for: seekers count, employers count
        with patch("handlers.admin_stats.execute_query") as mock_query:
            mock_query.side_effect = [{"cnt": 10}, {"cnt": 5}]
            handler.handle_statistics(message)

            handler.bot.send_message.assert_called_once()
            text = handler.bot.send_message.call_args[0][1]
            assert "Соискатели: 10" in text
            assert "Работодатели: 5" in text
            assert "Всего пользователей: 15" in text

    def test_handle_broadcast_start(self, handler, message):
        """Тест начала рассылки"""
        with patch("handlers.admin_broadcast.set_user_state") as mock_set_state:
            handler.handle_broadcast_start(message)

            mock_set_state.assert_called_with(
                123456, {"step": "admin_broadcast_message"}
            )
            handler.bot.send_message.assert_called()
            assert "Создание рассылки" in handler.bot.send_message.call_args[0][1]

    def test_process_broadcast_message_cancel(self, handler, message):
        """Отмена рассылки"""
        message.text = "Отмена"
        with patch("utils.cancel_request", return_value=True):
            with patch("handlers.admin_broadcast.clear_user_state") as mock_clear:
                handler.process_broadcast_message(message)

                mock_clear.assert_called_with(123456)
                handler.bot.send_message.assert_called()
                assert "Рассылка отменена" in handler.bot.send_message.call_args[0][1]

    def test_process_broadcast_confirm_send(self, handler, message):
        """Подтверждение и отправка рассылки"""
        message.text = "✅ Да, отправить"
        user_state: Dict[str, Any] = {"broadcast_message": "Hello World"}

        with patch(
            "handlers.admin_broadcast.get_user_state", return_value=user_state
        ), patch("handlers.admin_broadcast.clear_user_state") as mock_clear, patch(
            "handlers.admin_broadcast.execute_query"
        ) as mock_query:

            # Мокаем получение пользователей (соискатели, затем работодатели)
            mock_query.side_effect = [
                [{"telegram_id": 111}],  # seekers
                [{"telegram_id": 222}],  # employers
            ]

            handler.process_broadcast_confirm(message)

            mock_clear.assert_called_with(123456)

            # Проверяем, что сообщения отправлялись
            # bot.send_message вызывается для админа (статус) и для пользователей
            calls = handler.bot.send_message.call_args_list
            recipients = [call[0][0] for call in calls]

            assert 111 in recipients
            assert 222 in recipients
            assert 123456 in recipients  # Админ

    def test_handle_list_seekers(self, handler, message):
        """Тест списка соискателей"""
        users = [
            {
                "telegram_id": 1,
                "name": "John Doe",
                "full_name": "John Doe",
                "phone": "123",
                "created_at": "2023-01-01",
            }
        ]
        with patch("handlers.admin_users.execute_query", return_value=users):
            handler.handle_list_seekers(message)
            handler.bot.send_message.assert_called()
            assert "John Doe" in handler.bot.send_message.call_args[0][1]

    def test_process_search_user(self, handler, message):
        """Тест поиска пользователя"""
        message.text = "John"
        with patch("utils.cancel_request", return_value=False), patch(
            "handlers.admin_users.execute_query"
        ) as mock_query:

            # Мокаем поиск: сначала по соискателям, потом по работодателям
            mock_query.side_effect = [
                1,  # for _ensure_blocked_table
                [
                    {  # seekers result
                        "telegram_id": 1,
                        "name": "John Doe",
                        "full_name": "John Doe",
                        "phone": "123",
                        "type": "seeker",
                    }
                ],
                [],  # employers result
                None,  # blocked_until check
            ]

            handler.process_search_user(message)

            handler.bot.send_message.assert_called()
            messages = [args[0][1] for args in handler.bot.send_message.call_args_list]
            assert any("Результаты поиска" in m for m in messages)
            assert any("John Doe" in m for m in messages)

    def test_process_search_user_not_found(self, handler, message):
        """Тест поиска: пользователь не найден"""
        message.text = "Ghost"
        with patch("utils.cancel_request", return_value=False), patch(
            "handlers.admin_users.execute_query", return_value=[]
        ):  # Ничего не найдено

            handler.process_search_user(message)

            handler.bot.send_message.assert_called()
            assert "Пользователи не найдены" in handler.bot.send_message.call_args[0][1]

    def test_process_search_user_blocked(self, handler, message):
        """Тест поиска заблокированного пользователя"""
        message.text = "BlockedUser"

        user_found = [
            {"telegram_id": 999, "name": "Bad Guy", "phone": "000", "type": "seeker"}
        ]
        blocked_info = {"blocked_until": "forever"}

        with patch("handlers.admin_users.execute_query") as mock_query:
            mock_query.side_effect = [
                1,  # for _ensure_blocked_table
                user_found,
                [],
                blocked_info,
            ]

            handler.process_search_user(message)

            handler.bot.send_message.assert_called()
            # Check if "ЗАБЛОКИРОВАН" is in the message
            args = handler.bot.send_message.call_args_list
            found_blocked_msg = False
            for call in args:
                if "ЗАБЛОКИРОВАН" in call[0][1]:
                    found_blocked_msg = True
                    break
            assert found_blocked_msg

    def test_process_search_user_cancel(self, handler, message):
        """Тест отмены поиска пользователя"""
        message.text = "Отмена"
        with patch("utils.cancel_request", return_value=True), patch(
            "handlers.admin_users.clear_user_state"
        ) as mock_clear:
            handler.process_search_user(message)
            mock_clear.assert_called_with(123456)
            assert (
                "Управление пользователями" in handler.bot.send_message.call_args[0][1]
            )

    def test_process_search_user_sql_injection_attempt(self, handler, message):
        """Тест попытки SQL-инъекции при поиске пользователя"""
        message.text = "' OR 1=1; --"
        with patch("utils.cancel_request", return_value=False), patch(
            "handlers.admin_users.execute_query"
        ) as mock_query:

            # Мокаем, что ничего не найдено, чтобы тест не упал на дальнейшей логике
            mock_query.return_value = []

            handler.process_search_user(message)

            # Проверяем, что параметры передаются корректно, а не встраиваются в запрос
            expected_params = ("%' OR 1=1; --%", "%' OR 1=1; --%", "%' OR 1=1; --%")

            # Первый вызов - _ensure_blocked_table, второй - поиск соискателей
            seeker_call = mock_query.call_args_list[1]
            # Проверяем второй аргумент (params) в вызове execute_query
            assert seeker_call[0][1] == expected_params

    def test_handle_create_backup_success(self, handler, message):
        """Тест успешного создания бэкапа"""
        with patch(
            "handlers.admin_stats.create_backup", return_value=(True, "backups/test.db")
        ), patch("builtins.open", mock_open(read_data=b"data")), patch(
            "os.path.basename", return_value="test.db"
        ):

            handler.handle_create_backup(message)

            handler.bot.send_document.assert_called()
            args = handler.bot.send_document.call_args
            assert args[0][0] == 123  # chat_id
            assert "Бэкап успешно создан" in args[1]["caption"]

    def test_process_broadcast_confirm_invalid_choice(self, handler, message):
        """Test invalid choice during broadcast confirmation."""
        message.text = "Maybe"
        user_state: Dict[str, Any] = {"broadcast_message": "Hello"}
        with patch("handlers.admin_broadcast.get_user_state", return_value=user_state):
            handler.process_broadcast_confirm(message)
            handler.bot.send_message.assert_called_with(  # noqa
                message.chat.id, "Пожалуйста, выберите один из вариантов."  # noqa
            )

    def test_process_broadcast_confirm_no_message(self, handler, message):
        """Test broadcast confirmation when message is missing from state."""
        message.text = "✅ Да, отправить"
        user_state: Dict[str, Any] = {}  # No broadcast_message
        with patch(
            "handlers.admin_broadcast.get_user_state", return_value=user_state
        ), patch("handlers.admin_broadcast.clear_user_state") as mock_clear:
            handler.process_broadcast_confirm(message)
            mock_clear.assert_called_with(message.from_user.id)
            handler.bot.send_message.assert_called()
            assert (
                "Ошибка: сообщение для рассылки не найдено"
                in handler.bot.send_message.call_args[0][1]
            )

    def test_broadcast_send_failure(self, handler, message):
        """Test broadcast when sending to a user fails."""
        message.text = "✅ Да, отправить"
        user_state: Dict[str, Any] = {"broadcast_message": "msg"}
        with patch(
            "handlers.admin_broadcast.get_user_state", return_value=user_state
        ), patch(
            "handlers.admin_broadcast.execute_query",
            side_effect=[[{"telegram_id": 111}], [{"telegram_id": 222}]],
        ), patch(
            "handlers.admin_broadcast.clear_user_state"
        ) as mock_clear:

            # Simulate failure for one user
            handler.bot.send_message.side_effect = [
                None,
                Exception("Blocked"),
                None,
                None,
            ]

            handler.process_broadcast_confirm(message)

            # Check final status message
            mock_clear.assert_called_with(message.from_user.id)
            final_call = handler.bot.send_message.call_args
            assert "Рассылка завершена" in final_call[0][1]
            assert "Отправлено: 1" in final_call[0][1]
            assert "Ошибок: 1" in final_call[0][1]

    def test_handle_list_seekers_empty(self, handler, message):
        """Test listing seekers when the list is empty."""
        with patch("handlers.admin_users.execute_query", return_value=[]):
            handler.handle_list_seekers(message)
            handler.bot.send_message.assert_called_with(message.chat.id, "Список пуст.")

    def test_handle_list_employers_empty(self, handler, message):
        """Test listing employers when the list is empty."""
        with patch("handlers.admin_users.execute_query", return_value=[]):
            handler.handle_list_employers(message)
            handler.bot.send_message.assert_called_with(message.chat.id, "Список пуст.")

    def test_handle_list_employers_with_data(self, handler, message):
        """Тест списка работодателей с данными"""
        users = [
            {
                "telegram_id": 1,
                "name": "Test Corp",
                "company_name": "Test Corp",
                "phone": "123",
                "created_at": "2023-01-01",
            }
        ]
        with patch("handlers.admin_users.execute_query", return_value=users):
            handler.handle_list_employers(message)
            handler.bot.send_message.assert_called()
            assert "Test Corp" in handler.bot.send_message.call_args[0][1]

    def test_handle_create_backup_send_fail(self, handler, message):
        """Test backup creation when sending the file fails."""
        with patch(
            "handlers.admin_stats.create_backup", return_value=(True, "backups/test.db")
        ), patch("builtins.open", mock_open(read_data=b"data")):

            handler.bot.send_document.side_effect = Exception("Telegram API error")

            handler.handle_create_backup(message)

            # Should send a text message instead of a document
            handler.bot.send_message.assert_called()
            assert "Бэкап создан" in handler.bot.send_message.call_args[0][1]
            assert (
                "не удалось отправить файл" in handler.bot.send_message.call_args[0][1]
            )

    def test_handle_create_backup_fail(self, handler, message):
        """Тест ошибки создания бэкапа"""
        with patch(
            "handlers.admin_stats.create_backup", return_value=(False, "Disk error")
        ):
            handler.handle_create_backup(message)
            handler.bot.send_message.assert_called()
            # The handler sends a "Starting..." message first. Check the last call.
            last_call_text = handler.bot.send_message.call_args_list[-1][0][1]
            assert "Ошибка при создании бэкапа" in last_call_text

    def test_handle_logs_file_not_found(self, handler, message):
        """Тест /logs, когда файл не существует"""
        with patch("os.path.exists", return_value=False):
            handler.handle_logs(message)
            handler.bot.reply_to.assert_called_with(message, "❌ Лог-файл не найден.")

    def test_handle_logs_read_error(self, handler, message):
        """Тест /logs, ошибка чтения файла"""
        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", side_effect=Exception("Read Error")
        ):
            handler.handle_logs(message)
            handler.bot.reply_to.assert_called_with(
                message, "❌ Ошибка доступа к файлу логов."
            )

    def test_handle_logs_truncation(self, handler, message):
        """Тест /logs, обрезка длинного сообщения"""
        # Создаем длинный лог
        long_msg = "a" * 5000
        log_entry = f'{{"time": "t", "level": "INFO", "message": "{long_msg}"}}\n'

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=log_entry)
        ), patch("utils.escape_markdown", side_effect=lambda x: x):

            handler.handle_logs(message)

            handler.bot.reply_to.assert_called()
            sent_text = handler.bot.reply_to.call_args[0][1]
            # Проверяем, что текст обрезан (последние 4000 символов + заголовок)
            assert len(sent_text) <= 4050

    def test_handle_logs_invalid_json_line(self, handler, message):
        """Тест /logs с некорректной строкой JSON"""
        log_content = (
            'Invalid JSON Line\n{"time": "t", "level": "INFO", "message": "ok"}\n'
        )

        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data=log_content)
        ), patch("utils.escape_markdown", side_effect=lambda x: x):

            handler.handle_logs(message)

            handler.bot.reply_to.assert_called()
            text = handler.bot.reply_to.call_args[0][1]
            assert "Invalid JSON Line" in text
            assert "INFO" in text

    def test_register(self, handler, bot):
        """Тест регистрации обработчиков"""
        handler.register(bot)
        assert bot.register_message_handler.call_count > 0
        assert bot.register_callback_query_handler.call_count > 0


class TestAdminComplaints:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return AdminHandlers(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 123456
        msg.from_user.first_name = "Admin"
        msg.text = "Test"
        return msg

    @pytest.fixture(autouse=True)
    def mock_lang(self):
        with patch("localization.get_user_language", return_value="ru"):
            yield

    @pytest.fixture(autouse=True)
    def mock_admin_check(self):
        """Fixture to grant admin privileges for all tests in this class."""
        with patch("config.Config.ADMIN_IDS", [123456]):
            yield

    def test_handle_complaints_empty(self, handler, message):
        """Тест просмотра пустого списка жалоб"""
        pragma_result = [
            {"name": "id"},
            {"name": "user_id"},
            {"name": "user_name"},
            {"name": "type"},
            {"name": "message"},
            {"name": "photo_id"},
            {"name": "status"},
            {"name": "is_replied"},
            {"name": "created_at"},
        ]
        with patch(
            "handlers.admin_complaints.execute_query", side_effect=[pragma_result, []]
        ) as mock_query:
            handler.handle_complaints(message)
            assert mock_query.call_count == 2
            handler.bot.send_message.assert_called_with(
                message.chat.id, "📭 Список жалоб пуст."
            )

    def test_handle_complaints_with_data(self, handler, message):
        """Тест просмотра списка жалоб с данными (без фото)"""
        complaints = [
            {
                "id": 1,
                "user_id": 10,
                "user_name": "User",
                "type": "Bug",
                "message": "It is broken",
                "photo_id": None,
                "status": "new",
                "created_at": "2023-10-27 10:00:00",
                "is_replied": 0,
            }
        ]
        user_info = {"phone": "123", "email": "a@a.com", "full_name": "User"}
        pragma_result = [
            {"name": "id"},
            {"name": "user_id"},
            {"name": "user_name"},
            {"name": "type"},
            {"name": "message"},
            {"name": "photo_id"},
            {"name": "status"},
            {"name": "is_replied"},
            {"name": "created_at"},
        ]
        with patch(
            "handlers.admin_complaints.execute_query",
            side_effect=[pragma_result, complaints],
        ), patch("handlers.admin_complaints.get_user_by_id", return_value=user_info):
            handler.handle_complaints(message)
            assert handler.bot.send_message.call_count == 2
            # Check that a card is sent
            text = handler.bot.send_message.call_args_list[1][0][1]
            assert "ID: `1`" in text
            assert "User (ID: `10`)" in text
            assert "It is broken" in text

    def test_handle_resolve_complaint(self, handler):
        """Тест пометки жалобы как решенной"""
        call = MagicMock()
        call.data = "admin_resolve_complaint_5"
        call.message.text = "Complaint text"
        call.message.caption = None
        call.message.photo = None
        with patch("handlers.admin_complaints.execute_query") as mock_query:
            handler.handle_resolve_complaint(call)
            mock_query.assert_called()
            handler.bot.answer_callback_query.assert_called_with(
                call.id, "✅ Жалоба решена"
            )
            handler.bot.edit_message_text.assert_called()

    def test_process_reply_message_success(self, handler, message):
        """Тест отправки ответа пользователю"""
        message.text = "Your issue is resolved."
        state: Dict[str, Any] = {
            "step": "admin_reply_message",
            "target_user_id": 789,
            "complaint_id": 10,
            "complaint_msg_id": 100,
            "complaint_chat_id": 123,
        }
        with patch(
            "handlers.admin_complaints.get_user_state", return_value=state
        ), patch("handlers.admin_complaints.clear_user_state") as mock_clear, patch(
            "handlers.admin_complaints.execute_query"
        ) as mock_update:
            handler.process_reply_message(message)
            # Check message sent to user
            handler.bot.send_message.assert_any_call(
                789,
                "🔔 *Сообщение от администрации:*\n\nYour issue is resolved.",
                parse_mode="Markdown",
            )
            # Check confirmation to admin
            handler.bot.send_message.assert_any_call(
                message.chat.id, "✅ Сообщение отправлено.", reply_markup=ANY
            )
            # Check DB update
            mock_update.assert_called_with(
                "UPDATE complaints SET is_replied = 1 WHERE id = ?", (10,), commit=True
            )
            # Check original message edit
            handler.bot.edit_message_reply_markup.assert_called()
            mock_clear.assert_called_with(message.from_user.id)

    def test_handle_users(self, handler, message):
        """Тест меню пользователей"""
        handler.handle_users(message)
        handler.bot.send_message.assert_called()
        assert "Управление пользователями" in handler.bot.send_message.call_args[0][1]

    def test_handle_admin_settings(self, handler, message):
        """Тест настроек админа"""
        handler.handle_admin_settings(message)
        handler.bot.send_message.assert_called()
        assert "Настройки бота" in handler.bot.send_message.call_args[0][1]

    def test_handle_search_user_prompt(self, handler, message):
        """Тест промпта поиска"""
        with patch("handlers.admin_users.set_user_state") as mock_set:
            handler.handle_search_user_prompt(message)
            mock_set.assert_called()
            assert mock_set.call_args[0][1]["step"] == "admin_search_user"
            handler.bot.send_message.assert_called()
            assert "Введите Telegram ID" in handler.bot.send_message.call_args[0][1]

    def test_process_broadcast_message_success(self, handler, message):
        """Тест ввода сообщения для рассылки"""
        message.text = "Broadcast Text"
        with patch("handlers.admin_broadcast.get_user_state", return_value={}), patch(
            "handlers.admin_broadcast.set_user_state"
        ) as mock_set:
            handler.process_broadcast_message(message)
            mock_set.assert_called()
            assert mock_set.call_args[0][1]["step"] == "admin_broadcast_confirm"
            assert mock_set.call_args[0][1]["broadcast_message"] == "Broadcast Text"
            handler.bot.send_message.assert_called()
            assert "Подтверждение рассылки" in handler.bot.send_message.call_args[0][1]

    def test_handle_reply_prompt_exception(self, handler):
        """Тест обработки ошибки при запросе ответа"""
        call = MagicMock()
        call.data = (
            "admin_reply_invalid_user"  # Split length ok, but int conversion fails
        )
        with patch("logging.error"), pytest.raises(ValueError):
            handler.handle_reply_prompt(call)
        # mock_log.assert_called() # The handler doesn't catch ValueError, so it propagates

    def test_process_reply_message_cancel(self, handler, message):
        """Тест отмены ответа пользователю"""
        message.text = "Отмена"
        with patch("utils.cancel_request", return_value=True), patch(
            "handlers.admin_complaints.clear_user_state"
        ) as mock_clear:
            handler.process_reply_message(message)
            mock_clear.assert_called()
            handler.bot.send_message.assert_called()
            assert "Отменено" in handler.bot.send_message.call_args[0][1]

    def test_handle_complaints_migration_error(self, handler, message):
        """Тест ошибки миграции таблицы жалоб"""
        with patch(
            "handlers.admin_complaints.execute_query",
            side_effect=[Exception("Migration Error"), []],
        ), patch("logging.error") as mock_log:
            handler.handle_complaints(message)
            mock_log.assert_called()
            handler.bot.send_message.assert_called_with(
                message.chat.id, "📭 Список жалоб пуст."
            )

    def test_handle_complaints_photo_error(self, handler, message):
        """Тест ошибки отправки фото жалобы"""
        complaints = [
            {
                "id": 1,
                "user_id": 10,
                "user_name": "User",
                "type": "Bug",
                "message": "Msg",
                "photo_id": "photo_123",
                "status": "new",
                "created_at": "2023-01-01",
                "is_replied": 0,
            }
        ]
        user_info = {"phone": "123", "email": "e", "full_name": "U"}

        # Mock PRAGMA, then complaints query
        pragma_result = [
            {"name": "photo_id"},
            {"name": "status"},
            {"name": "is_replied"},
        ]

        with patch(
            "handlers.admin_complaints.execute_query",
            side_effect=[pragma_result, complaints],
        ), patch(
            "handlers.admin_complaints.get_user_by_id", return_value=user_info
        ), patch.object(
            handler.bot, "send_photo", side_effect=Exception("Photo Error")
        ), patch(
            "logging.error"
        ):

            handler.handle_complaints(message)

            # Should fallback to text message
            handler.bot.send_message.assert_called()
            assert (
                "Не удалось загрузить фото"
                in handler.bot.send_message.call_args_list[-1][0][1]
            )

    def test_process_reply_message_send_fail(self, handler, message):
        """Тест ошибки отправки ответа пользователю"""
        message.text = "Reply"
        state: Dict[str, Any] = {
            "step": "admin_reply_message",
            "target_user_id": 789,
            "complaint_id": 10,
        }
        with patch(
            "handlers.admin_complaints.get_user_state", return_value=state
        ), patch("handlers.admin_complaints.clear_user_state"):

            # First call fails (to user), second succeeds (error to admin)
            effects = [Exception("Send Error"), None]

            def mock_send_message(*args, **kwargs):
                effect = effects.pop(0)
                if isinstance(effect, Exception):
                    raise effect
                return effect

            handler.bot.send_message.side_effect = mock_send_message

            handler.process_reply_message(message)
            # Должен попытаться отправить сообщение об ошибке админу
            assert handler.bot.send_message.call_count == 2

    def test_handle_block_menu(self, handler):
        """Тест меню блокировки"""
        call = MagicMock()
        call.data = "admin_block_menu_123"
        call.message.chat.id = 111
        call.message.message_id = 222

        with patch("handlers.admin_users.execute_query") as mock_query:
            handler.handle_block_menu(call)
            mock_query.assert_called()  # ensure table exists
            handler.bot.edit_message_reply_markup.assert_called()

    def test_handle_block_confirm(self, handler):
        """Тест подтверждения блокировки"""
        call = MagicMock()
        call.data = "admin_block_123_1h"
        call.message.chat.id = 111
        call.message.message_id = 222
        call.message.text = "User info"

        with patch("handlers.admin_users.execute_query") as mock_query:
            handler.handle_block_confirm(call)

            # Check insert
            assert "INSERT OR REPLACE INTO blocked_users" in mock_query.call_args[0][0]
            handler.bot.answer_callback_query.assert_called_with(
                call.id, "✅ Пользователь заблокирован"
            )
            handler.bot.edit_message_text.assert_called()

    def test_handle_block_confirm_cancel(self, handler):
        """Тест отмены блокировки"""
        call = MagicMock()
        call.data = "admin_block_123_cancel"
        call.message.chat.id = 1
        call.message.message_id = 2

        handler.handle_block_confirm(call)
        handler.bot.edit_message_reply_markup.assert_called()

    def test_handle_unblock_user(self, handler):
        """Тест разблокировки"""
        call = MagicMock()
        call.data = "admin_unblock_123"
        call.message.chat.id = 111
        call.message.message_id = 222

        with patch("handlers.admin_users.execute_query") as mock_query:
            handler.handle_unblock_user(call)

            assert "DELETE FROM blocked_users" in mock_query.call_args[0][0]
            handler.bot.answer_callback_query.assert_called_with(
                call.id, "✅ Пользователь разблокирован"
            )

    def test_handle_write_prompt(self, handler):
        """Тест запроса сообщения пользователю"""
        call = MagicMock()
        call.data = "admin_write_123"
        call.from_user.id = 456
        call.message.chat.id = 456

        with patch("handlers.admin_users.set_user_state") as mock_set:
            handler.handle_write_prompt(call)

            mock_set.assert_called_with(
                456, {"step": "admin_write_user", "target_user_id": 123}
            )
            handler.bot.send_message.assert_called()
            handler.bot.answer_callback_query.assert_called()

    def test_process_write_message_success(self, handler, message):
        """Тест успешной отправки сообщения пользователю от админа"""
        message.text = "Hello user"
        user_state = {"step": "admin_write_user", "target_user_id": 777}

        with patch(
            "handlers.admin_users.get_user_state", return_value=user_state
        ), patch("handlers.admin_users.clear_user_state") as mock_clear:

            handler.process_write_message(message)

            handler.bot.send_message.assert_any_call(
                777,
                "🔔 *Сообщение от администрации:*\n\nHello user",
                parse_mode="Markdown",
                reply_markup=ANY,
            )
            mock_clear.assert_called_with(message.from_user.id)

    def test_process_write_message_exception(self, handler, message):
        """Тест ошибки отправки сообщения пользователю от админа"""
        message.text = "Hello"
        user_state = {"step": "admin_write_user", "target_user_id": 777}

        with patch(
            "handlers.admin_users.get_user_state", return_value=user_state
        ), patch("handlers.admin_users.clear_user_state"), patch.object(
            handler.bot, "send_message", side_effect=[Exception("Block"), None]
        ):

            handler.process_write_message(message)

            # Should send error message to admin
            args = handler.bot.send_message.call_args
            assert "Ошибка отправки" in args[0][1]

    @pytest.mark.parametrize(
        "callback_data, handler_name",
        [
            ("admin_resolve_complaint_1", "handle_resolve_complaint"),
            ("admin_reply_1", "handle_reply_prompt"),
            ("admin_block_menu_1", "handle_block_menu"),
            ("admin_block_1_1h", "handle_block_confirm"),
            ("admin_unblock_1", "handle_unblock_user"),
            ("admin_write_1", "handle_write_prompt"),
        ],
    )
    def test_handle_admin_callbacks_routing(self, handler, callback_data, handler_name):
        """Тест роутинга в handle_admin_callbacks"""
        call = MagicMock()
        call.data = callback_data
        with patch.object(handler, handler_name) as mock_target_handler:
            handler.handle_admin_callbacks(call)
            mock_target_handler.assert_called_with(call)

    def test_handle_admin_callbacks_exception(self, handler):
        """Тест обработки исключения в handle_admin_callbacks"""
        call = MagicMock()
        call.data = "admin_resolve_complaint_1"
        call.id = "call123"
        with patch.object(
            handler, "handle_resolve_complaint", side_effect=Exception("Handler Error")
        ), patch("logging.error") as mock_log:
            handler.handle_admin_callbacks(call)
            mock_log.assert_called()
            handler.bot.answer_callback_query.assert_called_with(
                "call123", "❌ Произошла ошибка"
            )

    def test_handle_logs_generic_exception(self, handler, message):
        """Тест /logs с общей ошибкой в конце"""
        with patch("os.path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data="{}")
        ), patch.object(
            handler.bot, "reply_to", side_effect=[Exception("API Error"), None]
        ), patch(
            "logging.error"
        ) as mock_log:
            handler.handle_logs(message)
            # The exception is caught and logged
            mock_log.assert_called()
            # A reply with an error message is sent
            assert "Произошла ошибка" in handler.bot.reply_to.call_args[0][1]
