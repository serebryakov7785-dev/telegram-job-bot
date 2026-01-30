import pytest
from unittest.mock import MagicMock, patch, mock_open
from handlers.admin import AdminHandlers

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
        with patch('database.execute_query') as mock_query:
            # Mock return values for seekers and employers counts
            mock_query.side_effect = [{'cnt': 10}, {'cnt': 5}]
            
            handler.handle_statistics(message)
            
            assert mock_query.call_count == 2
            handler.bot.send_message.assert_called()
            args = handler.bot.send_message.call_args[0]
            assert "10" in args[1] # seekers
            assert "5" in args[1] # employers
            assert "15" in args[1] # total

    def test_handle_statistics_empty(self, handler, message):
        """Тест статистики при пустой БД"""
        with patch('database.execute_query') as mock_query:
            # Mock return values None
            mock_query.side_effect = [None, None]
            
            handler.handle_statistics(message)
            
            handler.bot.send_message.assert_called()
            args = handler.bot.send_message.call_args[0]
            assert "0" in args[1]

    def test_handle_broadcast_start(self, handler, message):
        """Тест начала рассылки"""
        with patch('database.set_user_state') as mock_set:
            handler.handle_broadcast_start(message)
            mock_set.assert_called_with(456, {'step': 'admin_broadcast_message'})
            handler.bot.send_message.assert_called()

    def test_process_broadcast_message_cancel(self, handler, message):
        """Тест отмены ввода сообщения рассылки"""
        message.text = "Отмена"
        with patch('utils.cancel_request', return_value=True), \
             patch('database.clear_user_state') as mock_clear:
            
            handler.process_broadcast_message(message)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "отменена" in handler.bot.send_message.call_args[0][1]

    def test_process_broadcast_message_success(self, handler, message):
        """Тест успешного ввода сообщения рассылки"""
        message.text = "Broadcast Text"
        with patch('utils.cancel_request', return_value=False), \
             patch('database.get_user_state', return_value={}), \
             patch('database.set_user_state') as mock_set:
            
            handler.process_broadcast_message(message)
            
            mock_set.assert_called()
            state = mock_set.call_args[0][1]
            assert state['broadcast_message'] == "Broadcast Text"
            assert state['step'] == 'admin_broadcast_confirm'
            handler.bot.send_message.assert_called()

    def test_process_broadcast_confirm_cancel(self, handler, message):
        """Тест отмены на этапе подтверждения рассылки"""
        message.text = '❌ Нет, отменить'
        with patch('database.get_user_state', return_value={}), \
             patch('database.clear_user_state') as mock_clear:
            
            handler.process_broadcast_confirm(message)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "отменена" in handler.bot.send_message.call_args[0][1]

    def test_process_broadcast_confirm_invalid_input(self, handler, message):
        """Тест неверного ввода на этапе подтверждения"""
        message.text = 'Invalid'
        with patch('database.get_user_state', return_value={}):
            handler.process_broadcast_confirm(message)
            handler.bot.send_message.assert_called()
            assert "выберите один из вариантов" in handler.bot.send_message.call_args[0][1]

    def test_process_broadcast_confirm_no_message_in_state(self, handler, message):
        """Тест ошибки: сообщение не найдено в состоянии"""
        message.text = '✅ Да, отправить'
        with patch('database.get_user_state', return_value={}), \
             patch('database.clear_user_state') as mock_clear:
            
            handler.process_broadcast_confirm(message)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "не найдено" in handler.bot.send_message.call_args[0][1]

    def test_process_broadcast_confirm_success_with_errors(self, handler, message):
        """Тест рассылки с симуляцией ошибок отправки отдельным пользователям"""
        message.text = '✅ Да, отправить'
        user_state = {'broadcast_message': 'Hello'}
        
        seekers = [{'telegram_id': 100}]
        employers = [{'telegram_id': 200}]
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.clear_user_state') as mock_clear, \
             patch('database.execute_query') as mock_query, \
             patch('time.sleep'):
            
            # Mock seekers and employers
            mock_query.side_effect = [seekers, employers]
            
            # Mock send_message to fail for one user
            # Sequence: "Starting...", User 100 (OK), User 200 (Fail), "Finished"
            handler.bot.send_message.side_effect = [
                None, # Starting
                None, # User 100
                Exception("Telegram Error"), # User 200
                None  # Finished
            ]
            
            handler.process_broadcast_confirm(message)
            
            mock_clear.assert_called_with(456)
            
            # Verify final message contains stats
            final_call = handler.bot.send_message.call_args_list[-1]
            text = final_call[0][1]
            assert "Отправлено: 1" in text
            assert "Ошибок: 1" in text

    def test_handle_users(self, handler, message):
        handler.handle_users(message)
        handler.bot.send_message.assert_called()
        assert "Управление пользователями" in handler.bot.send_message.call_args[0][1]

    def test_handle_list_seekers_empty(self, handler, message):
        with patch('database.execute_query', return_value=[]):
            handler.handle_list_seekers(message)
            handler.bot.send_message.assert_called()
            assert "Список пуст" in handler.bot.send_message.call_args[0][1]

    def test_handle_list_seekers_success(self, handler, message):
        users = [{'telegram_id': 1, 'full_name': 'John', 'phone': '123', 'created_at': '2023'}]
        with patch('database.execute_query', return_value=users):
            handler.handle_list_seekers(message)
            handler.bot.send_message.assert_called()
            assert "John" in handler.bot.send_message.call_args[0][1]

    def test_handle_list_employers_empty(self, handler, message):
        with patch('database.execute_query', return_value=[]):
            handler.handle_list_employers(message)
            handler.bot.send_message.assert_called()
            assert "Список пуст" in handler.bot.send_message.call_args[0][1]

    def test_handle_list_employers_success(self, handler, message):
        users = [{'telegram_id': 1, 'company_name': 'Corp', 'phone': '123', 'created_at': '2023'}]
        with patch('database.execute_query', return_value=users):
            handler.handle_list_employers(message)
            handler.bot.send_message.assert_called()
            assert "Corp" in handler.bot.send_message.call_args[0][1]

    def test_handle_search_user_prompt(self, handler, message):
        with patch('database.set_user_state') as mock_set:
            handler.handle_search_user_prompt(message)
            mock_set.assert_called_with(456, {'step': 'admin_search_user'})
            handler.bot.send_message.assert_called()

    def test_process_search_user_cancel(self, handler, message):
        message.text = "Cancel"
        with patch('utils.cancel_request', return_value=True), \
             patch('database.clear_user_state') as mock_clear:
            
            handler.process_search_user(message)
            
            mock_clear.assert_called_with(456)
            # Should call handle_users
            assert "Управление пользователями" in handler.bot.send_message.call_args[0][1]

    def test_process_search_user_no_results(self, handler, message):
        message.text = "Query"
        with patch('utils.cancel_request', return_value=False), \
             patch('database.execute_query', return_value=[]), \
             patch('database.clear_user_state') as mock_clear:
            
            handler.process_search_user(message)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "не найдены" in handler.bot.send_message.call_args[0][1]

    def test_process_search_user_success(self, handler, message):
        message.text = "Query"
        seekers = [{'type': 'seeker', 'telegram_id': 1, 'name': 'John', 'phone': '123'}]
        employers = [{'type': 'employer', 'telegram_id': 2, 'name': 'Corp', 'phone': '456'}]
        
        with patch('utils.cancel_request', return_value=False), \
             patch('database.execute_query') as mock_query, \
             patch('database.clear_user_state') as mock_clear:
            
            mock_query.side_effect = [seekers, employers]
            
            handler.process_search_user(message)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            text = handler.bot.send_message.call_args[0][1]
            assert "John" in text
            assert "Corp" in text

    def test_handle_admin_settings(self, handler, message):
        handler.handle_admin_settings(message)
        handler.bot.send_message.assert_called()
        assert "в разработке" in handler.bot.send_message.call_args[0][1]

    def test_handle_create_backup_success(self, handler, message):
        with patch('database.create_backup', return_value=(True, '/path/to/backup.db')), \
             patch('builtins.open', mock_open(read_data=b'data')), \
             patch('os.path.basename', return_value='backup.db'):
            
            handler.handle_create_backup(message)
            
            handler.bot.send_document.assert_called()

    def test_handle_create_backup_send_fail(self, handler, message):
        """Тест создания бэкапа, но ошибки при отправке файла"""
        with patch('database.create_backup', return_value=(True, '/path/to/backup.db')), \
             patch('builtins.open', mock_open(read_data=b'data')), \
             patch('os.path.basename', return_value='backup.db'):
            
            handler.bot.send_document.side_effect = Exception("Send Error")
            
            handler.handle_create_backup(message)
            
            handler.bot.send_message.assert_called()
            assert "не удалось отправить" in handler.bot.send_message.call_args_list[-1][0][1]

    def test_handle_create_backup_create_fail(self, handler, message):
        """Тест ошибки при создании бэкапа"""
        with patch('database.create_backup', return_value=(False, 'Error message')):
            handler.handle_create_backup(message)
            
            handler.bot.send_message.assert_called()
            assert "Ошибка при создании" in handler.bot.send_message.call_args_list[-1][0][1]