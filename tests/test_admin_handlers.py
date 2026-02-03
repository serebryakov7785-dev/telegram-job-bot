import pytest
import sys
import os
from unittest.mock import MagicMock, patch, mock_open, ANY

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from handlers.admin import AdminHandlers  # noqa: E402


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
        msg.from_user.id = 456
        msg.from_user.first_name = "Admin"
        msg.text = "Test"
        return msg

    def test_handle_statistics(self, handler, message):
        """Тест отображения статистики"""
        with patch('handlers.admin.execute_query') as mock_query:
            # Мокаем результаты запросов: сначала соискатели, потом работодатели
            mock_query.side_effect = [{'cnt': 10}, {'cnt': 5}]

            handler.handle_statistics(message)

            handler.bot.send_message.assert_called_once()
            text = handler.bot.send_message.call_args[0][1]
            assert "Соискатели: 10" in text
            assert "Работодатели: 5" in text
            assert "Всего пользователей: 15" in text

    def test_handle_broadcast_start(self, handler, message):
        """Тест начала рассылки"""
        with patch('handlers.admin.set_user_state') as mock_set_state:
            handler.handle_broadcast_start(message)

            mock_set_state.assert_called_with(456, {'step': 'admin_broadcast_message'})
            handler.bot.send_message.assert_called()
            assert "Создание рассылки" in handler.bot.send_message.call_args[0][1]

    def test_process_broadcast_message_cancel(self, handler, message):
        """Отмена рассылки"""
        message.text = "Отмена"
        with patch('utils.cancel_request', return_value=True), \
             patch('handlers.admin.clear_user_state') as mock_clear:

            handler.process_broadcast_message(message)

            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Рассылка отменена" in handler.bot.send_message.call_args[0][1]

    def test_process_broadcast_confirm_send(self, handler, message):
        """Подтверждение и отправка рассылки"""
        message.text = "✅ Да, отправить"
        user_state = {'broadcast_message': 'Hello World'}

        with patch('handlers.admin.get_user_state', return_value=user_state), \
             patch('handlers.admin.clear_user_state') as mock_clear, \
             patch('handlers.admin.execute_query') as mock_query:

            # Мокаем получение пользователей (соискатели, затем работодатели)
            mock_query.side_effect = [
                [{'telegram_id': 111}],  # seekers
                [{'telegram_id': 222}]   # employers
            ]

            handler.process_broadcast_confirm(message)

            mock_clear.assert_called_with(456)

            # Проверяем, что сообщения отправлялись
            # bot.send_message вызывается для админа (статус) и для пользователей
            calls = handler.bot.send_message.call_args_list
            recipients = [call[0][0] for call in calls]

            assert 111 in recipients
            assert 222 in recipients
            assert 456 in recipients  # Админ

    def test_handle_list_seekers(self, handler, message):
        """Тест списка соискателей"""
        users = [
            {'telegram_id': 1, 'full_name': 'John Doe', 'phone': '123', 'created_at': '2023-01-01'}
        ]
        with patch('handlers.admin.execute_query', return_value=users):
            handler.handle_list_seekers(message)
            handler.bot.send_message.assert_called()
            assert "John Doe" in handler.bot.send_message.call_args[0][1]

    def test_process_search_user(self, handler, message):
        """Тест поиска пользователя"""
        message.text = "John"
        with patch('utils.cancel_request', return_value=False), \
             patch('handlers.admin.execute_query') as mock_query:

            # Мокаем поиск: сначала по соискателям, потом по работодателям
            mock_query.side_effect = [
                [{'type': 'seeker', 'telegram_id': 1, 'name': 'John Doe', 'phone': '123'}],  # seekers result
                []   # employers result
            ]

            handler.process_search_user(message)

            handler.bot.send_message.assert_called()
            text = handler.bot.send_message.call_args[0][1]
            assert "Результаты поиска" in text
            assert "John Doe" in text

    def test_process_search_user_not_found(self, handler, message):
        """Тест поиска: пользователь не найден"""
        message.text = "Ghost"
        with patch('utils.cancel_request', return_value=False), \
             patch('handlers.admin.execute_query', return_value=[]):  # Ничего не найдено

            handler.process_search_user(message)

            handler.bot.send_message.assert_called()
            assert "Пользователи не найдены" in handler.bot.send_message.call_args[0][1]

    def test_process_search_user_cancel(self, handler, message):
        """Тест отмены поиска пользователя"""
        message.text = "Отмена"
        with patch('utils.cancel_request', return_value=True), \
             patch('handlers.admin.clear_user_state') as mock_clear:
            handler.process_search_user(message)
            mock_clear.assert_called_with(456)
            assert "Управление пользователями" in handler.bot.send_message.call_args[0][1]

    def test_handle_create_backup_success(self, handler, message):
        """Тест успешного создания бэкапа"""
        with patch('handlers.admin.create_backup', return_value=(True, 'backups/test.db')), \
             patch('builtins.open', mock_open(read_data=b'data')), \
             patch('os.path.basename', return_value='test.db'):

            handler.handle_create_backup(message)

            handler.bot.send_document.assert_called()
            args = handler.bot.send_document.call_args
            assert args[0][0] == 123  # chat_id
            assert "Бэкап успешно создан" in args[1]['caption']

    def test_process_broadcast_confirm_invalid_choice(self, handler, message):
        """Test invalid choice during broadcast confirmation."""
        message.text = "Maybe"
        user_state = {'broadcast_message': 'Hello'}
        with patch('handlers.admin.get_user_state', return_value=user_state):
            handler.process_broadcast_confirm(message)
            handler.bot.send_message.assert_called_with(message.chat.id, "Пожалуйста, выберите один из вариантов.")

    def test_process_broadcast_confirm_no_message(self, handler, message):
        """Test broadcast confirmation when message is missing from state."""
        message.text = "✅ Да, отправить"
        user_state = {}  # No broadcast_message
        with patch('handlers.admin.get_user_state', return_value=user_state), \
             patch('handlers.admin.clear_user_state') as mock_clear:
            handler.process_broadcast_confirm(message)
            mock_clear.assert_called_with(message.from_user.id)
            handler.bot.send_message.assert_called()
            assert "Ошибка: сообщение для рассылки не найдено" in handler.bot.send_message.call_args[0][1]

    def test_broadcast_send_failure(self, handler, message):
        """Test broadcast when sending to a user fails."""
        message.text = "✅ Да, отправить"
        user_state = {'broadcast_message': 'Hello'}
        with patch('handlers.admin.get_user_state', return_value=user_state), \
             patch('handlers.admin.execute_query', side_effect=[[{'telegram_id': 111}], [{'telegram_id': 222}]]), \
             patch('handlers.admin.clear_user_state'):

            # Simulate failure for one user
            handler.bot.send_message.side_effect = [None, Exception("Blocked"), None, None]

            handler.process_broadcast_confirm(message)

            # Check final status message
            final_call = handler.bot.send_message.call_args
            assert "Рассылка завершена" in final_call[0][1]
            assert "Отправлено: 1" in final_call[0][1]
            assert "Ошибок: 1" in final_call[0][1]

    def test_handle_list_seekers_empty(self, handler, message):
        """Test listing seekers when the list is empty."""
        with patch('handlers.admin.execute_query', return_value=[]):
            handler.handle_list_seekers(message)
            handler.bot.send_message.assert_called_with(message.chat.id, "Список пуст.")

    def test_handle_list_employers_empty(self, handler, message):
        """Test listing employers when the list is empty."""
        with patch('handlers.admin.execute_query', return_value=[]):
            handler.handle_list_employers(message)
            handler.bot.send_message.assert_called_with(message.chat.id, "Список пуст.")

    def test_handle_list_employers_with_data(self, handler, message):
        """Тест списка работодателей с данными"""
        users = [
            {'telegram_id': 1, 'company_name': 'Test Corp', 'phone': '123', 'created_at': '2023-01-01'}
        ]
        with patch('handlers.admin.execute_query', return_value=users):
            handler.handle_list_employers(message)
            handler.bot.send_message.assert_called()
            assert "Test Corp" in handler.bot.send_message.call_args[0][1]

    def test_handle_create_backup_send_fail(self, handler, message):
        """Test backup creation when sending the file fails."""
        with patch('handlers.admin.create_backup', return_value=(True, 'backups/test.db')), \
             patch('builtins.open', mock_open(read_data=b'data')):

            handler.bot.send_document.side_effect = Exception("Telegram API error")

            handler.handle_create_backup(message)

            # Should send a text message instead of a document
            handler.bot.send_message.assert_called()
            assert "Бэкап создан" in handler.bot.send_message.call_args[0][1]
            assert "не удалось отправить файл" in handler.bot.send_message.call_args[0][1]

    def test_handle_create_backup_fail(self, handler, message):
        """Тест ошибки создания бэкапа"""
        with patch('handlers.admin.create_backup', return_value=(False, 'Disk error')):
            handler.handle_create_backup(message)
            handler.bot.send_message.assert_called()
            assert "Ошибка при создании бэкапа" in handler.bot.send_message.call_args[0][1]


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
        msg.from_user.id = 456
        msg.from_user.first_name = "Admin"
        msg.text = "Test"
        return msg

    def test_handle_complaints_empty(self, handler, message):
        """Тест просмотра пустого списка жалоб"""
        pragma_result = [
            {'name': 'id'}, {'name': 'user_id'}, {'name': 'user_name'},
            {'name': 'type'}, {'name': 'message'}, {'name': 'photo_id'},
            {'name': 'status'}, {'name': 'is_replied'}, {'name': 'created_at'}
        ]
        with patch('handlers.admin.execute_query', side_effect=[pragma_result, []]) as mock_query:
            handler.handle_complaints(message)
            assert mock_query.call_count == 2
            handler.bot.send_message.assert_called_with(message.chat.id, "📭 Список жалоб пуст.")

    def test_handle_complaints_with_data(self, handler, message):
        """Тест просмотра списка жалоб с данными (без фото)"""
        complaints = [{
            'id': 1, 'user_id': 10, 'user_name': 'User', 'type': 'Bug',
            'message': 'It is broken', 'photo_id': None, 'status': 'new',
            'created_at': '2023-10-27 10:00:00', 'is_replied': 0
        }]
        user_info = {'phone': '123', 'email': 'a@a.com', 'full_name': 'User'}
        pragma_result = [
            {'name': 'id'}, {'name': 'user_id'}, {'name': 'user_name'},
            {'name': 'type'}, {'name': 'message'}, {'name': 'photo_id'},
            {'name': 'status'}, {'name': 'is_replied'}, {'name': 'created_at'}
        ]
        with patch('handlers.admin.execute_query', side_effect=[pragma_result, complaints]), \
             patch('handlers.admin.get_user_by_id', return_value=user_info):
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
        with patch('handlers.admin.execute_query') as mock_query:
            handler.handle_resolve_complaint(call)
            mock_query.assert_called()
            handler.bot.answer_callback_query.assert_called_with(call.id, "✅ Жалоба помечена как решенная")
            handler.bot.edit_message_text.assert_called()

    def test_process_reply_message_success(self, handler, message):
        """Тест отправки ответа пользователю"""
        message.text = "Your issue is resolved."
        state = {'step': 'admin_reply_message', 'target_user_id': 789, 'complaint_id': 10,
                 'complaint_msg_id': 100, 'complaint_chat_id': 123}
        with patch('handlers.admin.get_user_state', return_value=state), \
             patch('handlers.admin.clear_user_state') as mock_clear, \
             patch('handlers.admin.execute_query') as mock_update:
            handler.process_reply_message(message)
            # Check message sent to user
            handler.bot.send_message.assert_any_call(
                789,
                "🔔 *Сообщение от администрации:*\n\nYour issue is resolved.",
                parse_mode='Markdown'
            )
            # Check confirmation to admin
            handler.bot.send_message.assert_any_call(message.chat.id, "✅ Сообщение успешно отправлено.", reply_markup=ANY)
            # Check DB update
            mock_update.assert_called_with("UPDATE complaints SET is_replied = 1 WHERE id = ?", (10,), commit=True)
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
        with patch('handlers.admin.set_user_state') as mock_set:
            handler.handle_search_user_prompt(message)
            mock_set.assert_called()
            assert mock_set.call_args[0][1]['step'] == 'admin_search_user'
            handler.bot.send_message.assert_called()
            assert "Введите Telegram ID" in handler.bot.send_message.call_args[0][1]

    def test_process_broadcast_message_success(self, handler, message):
        """Тест ввода сообщения для рассылки"""
        message.text = "Broadcast Text"
        with patch('handlers.admin.get_user_state', return_value={}), \
             patch('handlers.admin.set_user_state') as mock_set:
            handler.process_broadcast_message(message)
            mock_set.assert_called()
            assert mock_set.call_args[0][1]['step'] == 'admin_broadcast_confirm'
            assert mock_set.call_args[0][1]['broadcast_message'] == "Broadcast Text"
            handler.bot.send_message.assert_called()
            assert "Подтверждение рассылки" in handler.bot.send_message.call_args[0][1]

    def test_handle_reply_prompt_exception(self, handler):
        """Тест обработки ошибки при запросе ответа"""
        call = MagicMock()
        call.data = "invalid_data"
        with patch('logging.error') as mock_log:
            handler.handle_reply_prompt(call)
            mock_log.assert_called()

    def test_process_reply_message_cancel(self, handler, message):
        """Тест отмены ответа пользователю"""
        message.text = "Отмена"
        with patch('utils.cancel_request', return_value=True), \
             patch('handlers.admin.clear_user_state') as mock_clear:
            handler.process_reply_message(message)
            mock_clear.assert_called()
            handler.bot.send_message.assert_called()
            assert "Отменено" in handler.bot.send_message.call_args[0][1]

    def test_handle_complaints_migration_error(self, handler, message):
        """Тест ошибки миграции таблицы жалоб"""
        with patch('handlers.admin.execute_query', side_effect=[Exception("Migration Error"), []]), \
             patch('logging.error') as mock_log:
            handler.handle_complaints(message)
            mock_log.assert_called()
            handler.bot.send_message.assert_called_with(message.chat.id, "📭 Список жалоб пуст.")

    def test_handle_complaints_photo_error(self, handler, message):
        """Тест ошибки отправки фото жалобы"""
        complaints = [{
            'id': 1, 'user_id': 10, 'user_name': 'User', 'type': 'Bug',
            'message': 'Msg', 'photo_id': 'photo_123', 'status': 'new',
            'created_at': '2023-01-01', 'is_replied': 0
        }]
        user_info = {'phone': '123', 'email': 'e', 'full_name': 'U'}

        # Mock PRAGMA, then complaints query
        pragma_result = [{'name': 'photo_id'}, {'name': 'status'}, {'name': 'is_replied'}]

        with patch('handlers.admin.execute_query', side_effect=[pragma_result, complaints]), \
             patch('handlers.admin.get_user_by_id', return_value=user_info), \
             patch.object(handler.bot, 'send_photo', side_effect=Exception("Photo Error")), \
             patch('logging.error') as mock_log:

            handler.handle_complaints(message)

            mock_log.assert_called()
            # Should fallback to text message
            handler.bot.send_message.assert_called()
            assert "Не удалось загрузить скриншот" in handler.bot.send_message.call_args_list[-1][0][1]

    def test_process_reply_message_send_fail(self, handler, message):
        """Тест ошибки отправки ответа пользователю"""
        message.text = "Reply"
        state = {'target_user_id': 123}
        with patch('handlers.admin.get_user_state', return_value=state), \
             patch('handlers.admin.clear_user_state'):

            # First call fails (to user), second succeeds (error to admin)
            handler.bot.send_message.side_effect = [Exception("Send Error"), None]

            handler.process_reply_message(message)
            # Должен попытаться отправить сообщение об ошибке админу
            assert handler.bot.send_message.call_count >= 1
