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
        with patch('database.set_user_state') as mock_set_state:
            handler.handle_broadcast_start(message)
            
            mock_set_state.assert_called_with(456, {'step': 'admin_broadcast_message'})
            handler.bot.send_message.assert_called()
            assert "Создание рассылки" in handler.bot.send_message.call_args[0][1]

    def test_process_broadcast_message_cancel(self, handler, message):
        """Отмена рассылки"""
        message.text = "Отмена"
        with patch('utils.cancel_request', return_value=True), \
             patch('database.clear_user_state') as mock_clear:
            
            handler.process_broadcast_message(message)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Рассылка отменена" in handler.bot.send_message.call_args[0][1]

    def test_process_broadcast_confirm_send(self, handler, message):
        """Подтверждение и отправка рассылки"""
        message.text = "✅ Да, отправить"
        user_state = {'broadcast_message': 'Hello World'}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.clear_user_state') as mock_clear, \
             patch('database.execute_query') as mock_query:
            
            # Мокаем получение пользователей (соискатели, затем работодатели)
            mock_query.side_effect = [
                [{'telegram_id': 111}], # seekers
                [{'telegram_id': 222}]  # employers
            ]
            
            handler.process_broadcast_confirm(message)
            
            mock_clear.assert_called_with(456)
            
            # Проверяем, что сообщения отправлялись
            # bot.send_message вызывается для админа (статус) и для пользователей
            calls = handler.bot.send_message.call_args_list
            recipients = [call[0][0] for call in calls]
            
            assert 111 in recipients
            assert 222 in recipients
            assert 456 in recipients # Админ

    def test_handle_list_seekers(self, handler, message):
        """Тест списка соискателей"""
        users = [
            {'telegram_id': 1, 'full_name': 'John Doe', 'phone': '123', 'created_at': '2023-01-01'}
        ]
        with patch('database.execute_query', return_value=users):
            handler.handle_list_seekers(message)
            handler.bot.send_message.assert_called()
            assert "John Doe" in handler.bot.send_message.call_args[0][1]

    def test_process_search_user(self, handler, message):
        """Тест поиска пользователя"""
        message.text = "John"
        with patch('utils.cancel_request', return_value=False), \
             patch('database.execute_query') as mock_query:
            
            # Мокаем поиск: сначала по соискателям, потом по работодателям
            mock_query.side_effect = [
                [{'type': 'seeker', 'telegram_id': 1, 'name': 'John Doe', 'phone': '123'}], # seekers result
                [] # employers result
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
             patch('database.execute_query', return_value=[]): # Ничего не найдено
            
            handler.process_search_user(message)
            
            handler.bot.send_message.assert_called()
            assert "Пользователи не найдены" in handler.bot.send_message.call_args[0][1]

    def test_process_search_user_cancel(self, handler, message):
        """Тест отмены поиска пользователя"""
        message.text = "Отмена"
        with patch('utils.cancel_request', return_value=True), \
             patch('database.clear_user_state') as mock_clear:
            handler.process_search_user(message)
            mock_clear.assert_called_with(456)
            assert "Управление пользователями" in handler.bot.send_message.call_args[0][1]

    def test_handle_create_backup_success(self, handler, message):
        """Тест успешного создания бэкапа"""
        with patch('database.create_backup', return_value=(True, 'backups/test.db')), \
             patch('builtins.open', mock_open(read_data=b'data')), \
             patch('os.path.basename', return_value='test.db'):
            
            handler.handle_create_backup(message)
            
            handler.bot.send_document.assert_called()
            args = handler.bot.send_document.call_args
            assert args[0][0] == 123 # chat_id
            assert "Бэкап успешно создан" in args[1]['caption']

    def test_process_broadcast_confirm_invalid_choice(self, handler, message):
        """Test invalid choice during broadcast confirmation."""
        message.text = "Maybe"
        user_state = {'broadcast_message': 'Hello'}
        with patch('database.get_user_state', return_value=user_state):
            handler.process_broadcast_confirm(message)
            handler.bot.send_message.assert_called_with(message.chat.id, "Пожалуйста, выберите один из вариантов.")

    def test_process_broadcast_confirm_no_message(self, handler, message):
        """Test broadcast confirmation when message is missing from state."""
        message.text = "✅ Да, отправить"
        user_state = {} # No broadcast_message
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.clear_user_state') as mock_clear:
            handler.process_broadcast_confirm(message)
            mock_clear.assert_called_with(message.from_user.id)
            handler.bot.send_message.assert_called()
            assert "Ошибка: сообщение для рассылки не найдено" in handler.bot.send_message.call_args[0][1]

    def test_broadcast_send_failure(self, handler, message):
        """Test broadcast when sending to a user fails."""
        message.text = "✅ Да, отправить"
        user_state = {'broadcast_message': 'Hello'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.execute_query', side_effect=[[{'telegram_id': 111}], [{'telegram_id': 222}]]), \
             patch('database.clear_user_state'):
            
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
        with patch('database.execute_query', return_value=[]):
            handler.handle_list_seekers(message)
            handler.bot.send_message.assert_called_with(message.chat.id, "Список пуст.")

    def test_handle_list_employers_empty(self, handler, message):
        """Test listing employers when the list is empty."""
        with patch('database.execute_query', return_value=[]):
            handler.handle_list_employers(message)
            handler.bot.send_message.assert_called_with(message.chat.id, "Список пуст.")

    def test_handle_list_employers_with_data(self, handler, message):
        """Тест списка работодателей с данными"""
        users = [
            {'telegram_id': 1, 'company_name': 'Test Corp', 'phone': '123', 'created_at': '2023-01-01'}
        ]
        with patch('database.execute_query', return_value=users):
            handler.handle_list_employers(message)
            handler.bot.send_message.assert_called()
            assert "Test Corp" in handler.bot.send_message.call_args[0][1]

    def test_handle_create_backup_send_fail(self, handler, message):
        """Test backup creation when sending the file fails."""
        with patch('database.create_backup', return_value=(True, 'backups/test.db')), \
             patch('builtins.open', mock_open(read_data=b'data')):
            
            handler.bot.send_document.side_effect = Exception("Telegram API error")
            
            handler.handle_create_backup(message)
            
            # Should send a text message instead of a document
            handler.bot.send_message.assert_called()
            assert "Бэкап создан" in handler.bot.send_message.call_args[0][1]
            assert "не удалось отправить файл" in handler.bot.send_message.call_args[0][1]

    def test_handle_create_backup_fail(self, handler, message):
        """Тест ошибки создания бэкапа"""
        with patch('database.create_backup', return_value=(False, 'Disk error')):
            handler.handle_create_backup(message)
            handler.bot.send_message.assert_called()
            assert "Ошибка при создании бэкапа" in handler.bot.send_message.call_args[0][1]

    def test_handle_create_backup_fail(self, handler, message):
        """Тест ошибки создания бэкапа"""
        with patch('database.create_backup', return_value=(False, 'Disk error')):
            handler.handle_create_backup(message)
            handler.bot.send_message.assert_called()
            assert "Ошибка при создании бэкапа" in handler.bot.send_message.call_args[0][1]

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
        with patch('database.set_user_state') as mock_set:
            handler.handle_search_user_prompt(message)
            mock_set.assert_called()
            assert mock_set.call_args[0][1]['step'] == 'admin_search_user'
            handler.bot.send_message.assert_called()
            assert "Введите Telegram ID" in handler.bot.send_message.call_args[0][1]

    def test_process_broadcast_message_success(self, handler, message):
        """Тест ввода сообщения для рассылки"""
        message.text = "Broadcast Text"
        with patch('database.set_user_state') as mock_set:
            handler.process_broadcast_message(message)
            mock_set.assert_called()
            assert mock_set.call_args[0][1]['step'] == 'admin_broadcast_confirm'
            assert mock_set.call_args[0][1]['broadcast_message'] == "Broadcast Text"
            handler.bot.send_message.assert_called()
            assert "Подтверждение рассылки" in handler.bot.send_message.call_args[0][1]