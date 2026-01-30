import pytest
from unittest.mock import MagicMock, patch
from handlers.common import CommonHandlers

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
        return msg

    def test_handle_start_new_user(self, handler, message):
        """Тест /start для нового пользователя"""
        with patch('database.clear_user_state') as mock_clear, \
             patch('database.get_user_by_id', return_value=None):
            
            handler.handle_start(message)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            # Проверяем, что отправлено приветствие
            args = handler.bot.send_message.call_args
            assert "Добро пожаловать" in args[0][1]

    def test_handle_start_existing_seeker(self, handler, message):
        """Тест /start для существующего соискателя"""
        user_data = {'full_name': 'John Doe', 'id': 1}
        with patch('database.clear_user_state'), \
             patch('database.get_user_by_id', return_value=user_data):
            
            handler.handle_start(message)
            
            handler.bot.send_message.assert_called()
            args = handler.bot.send_message.call_args
            assert "Здравствуйте, John Doe" in args[0][1]

    def test_handle_start_existing_employer(self, handler, message):
        """Тест /start для существующего работодателя"""
        user_data = {'company_name': 'Tech Corp', 'id': 2}
        with patch('database.clear_user_state'), \
             patch('database.get_user_by_id', return_value=user_data):
            
            handler.handle_start(message)
            
            handler.bot.send_message.assert_called()
            args = handler.bot.send_message.call_args
            assert "Здравствуйте, Tech Corp" in args[0][1]

    def test_handle_help(self, handler, message):
        """Тест команды /help"""
        handler.handle_help(message)
        handler.bot.send_message.assert_called()
        assert "Помощь" in handler.bot.send_message.call_args[0][1]

    def test_handle_unknown_command(self, handler, message):
        """Тест неизвестной команды"""
        message.text = "/unknown"
        handler.handle_unknown(message)
        handler.bot.send_message.assert_called()
        assert "Неизвестная команда" in handler.bot.send_message.call_args[0][1]

    def test_handle_unknown_text_not_logged_in(self, handler, message):
        """Тест неизвестного текста (не залогинен)"""
        message.text = "Just text"
        with patch('database.get_user_by_id', return_value=None):
            handler.handle_unknown(message)
            handler.bot.send_message.assert_called()
            assert "Не понимаю ваше сообщение" in handler.bot.send_message.call_args[0][1]

    def test_handle_back_to_main(self, handler, message):
        """Тест возврата в главное меню"""
        with patch('database.clear_user_state') as mock_clear:
            handler.handle_back_to_main(message)
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Главное меню" in handler.bot.send_message.call_args[0][1]

    def test_handle_back_to_profile_seeker(self, handler, message):
        """Тест возврата в профиль соискателя"""
        user_data = {'full_name': 'John'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_back_to_profile(message)
            handler.bot.send_message.assert_called()
            assert "Панель соискателя" in handler.bot.send_message.call_args[0][1]

    def test_handle_back_to_profile_employer(self, handler, message):
        """Тест возврата в профиль работодателя"""
        user_data = {'company_name': 'Corp'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_back_to_profile(message)
            handler.bot.send_message.assert_called()
            assert "Панель работодателя" in handler.bot.send_message.call_args[0][1]

    def test_handle_about(self, handler, message):
        """Тест команды /about"""
        handler.handle_about(message)
        handler.bot.send_message.assert_called()
        assert "О боте" in handler.bot.send_message.call_args[0][1]

    def test_handle_support(self, handler, message):
        """Тест команды /support"""
        handler.handle_support(message)
        handler.bot.send_message.assert_called()
        assert "Поддержка" in handler.bot.send_message.call_args[0][1]

    def test_handle_admin(self, handler, message):
        """Тест админ-панели"""
        with patch('database.execute_query') as mock_query:
            mock_query.side_effect = [{'cnt': 10}, {'cnt': 5}]
            handler.handle_admin(message)
            handler.bot.send_message.assert_called()
            text = handler.bot.send_message.call_args[0][1]
            assert "Панель администратора" in text
            assert "Соискатели: 10" in text
            assert "Работодатели: 5" in text

    def test_handle_unknown_text_logged_in_seeker(self, handler, message):
        """Тест неизвестного текста (залогинен соискатель)"""
        message.text = "Just text"
        user_data = {'full_name': 'John'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_unknown(message)
            handler.bot.send_message.assert_called()
            assert "Не понимаю ваше сообщение" in handler.bot.send_message.call_args[0][1]
            # Check for correct keyboard
            assert handler.bot.send_message.call_args[1]['reply_markup'] is not None

    def test_handle_start_chat_success(self, handler):
        """Тест начала чата"""
        call = MagicMock()
        call.data = "start_chat_789"
        call.from_user.id = 456
        
        target_user = {'company_name': 'Target Corp'}
        with patch('database.get_user_by_id', return_value=target_user), \
             patch('database.set_user_state') as mock_set:
            
            handler.handle_start_chat(call)
            
            mock_set.assert_called()
            state = mock_set.call_args[0][1]
            assert state['step'] == 'active_chat'
            assert state['target_id'] == 789
            assert state['target_name'] == 'Target Corp'
            
            handler.bot.send_message.assert_called()
            assert "Чат с Target Corp" in handler.bot.send_message.call_args[0][1]

    def test_handle_chat_message_success(self, handler, message):
        """Тест отправки сообщения в чате"""
        user_state = {'step': 'active_chat', 'target_id': 789}
        sender_data = {'full_name': 'Sender'}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.get_user_by_id', return_value=sender_data):
            
            handler.handle_chat_message(message)
            
            # Проверяем отправку получателю
            recipient_call = handler.bot.send_message.call_args_list[0]
            assert recipient_call[0][0] == 789 # target_id
            assert "Сообщение от Sender" in recipient_call[0][1]
            
            # Проверяем подтверждение отправителю
            sender_call = handler.bot.send_message.call_args_list[1]
            assert sender_call[0][0] == 456 # user_id
            assert "Сообщение отправлено" in sender_call[0][1]

    def test_handle_stop_chat(self, handler, message):
        """Тест завершения чата"""
        user_data = {'full_name': 'John'}
        with patch('database.clear_user_state') as mock_clear, \
             patch('database.get_user_by_id', return_value=user_data):
            
            handler.handle_stop_chat(message)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Чат завершен" in handler.bot.send_message.call_args[0][1]

    def test_handle_start_chat_user_not_found(self, handler):
        """Тест начала чата с несуществующим пользователем"""
        call = MagicMock()
        call.data = "start_chat_999" # non-existent user
        call.from_user.id = 456
        call.id = "call_id_1"
        
        with patch('database.get_user_by_id', return_value=None):
            handler.handle_start_chat(call)
            handler.bot.answer_callback_query.assert_called_with(call.id, "❌ Пользователь не найден")

    def test_handle_chat_message_api_error(self, handler, message):
        """Тест ошибки API при отправке сообщения в чате"""
        user_state = {'step': 'active_chat', 'target_id': 789}
        sender_data = {'full_name': 'Sender'}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.get_user_by_id', return_value=sender_data):
            
            # Мокаем ошибку при отправке получателю
            handler.bot.send_message.side_effect = [Exception("API Error"), None]
            
            handler.handle_chat_message(message)
            
            # Проверяем, что было 2 вызова send_message (попытка получателю и сообщение об ошибке отправителю)
            assert handler.bot.send_message.call_count == 2
            error_call = handler.bot.send_message.call_args_list[1]
            assert error_call[0][0] == 456 # user_id
            assert "Не удалось отправить сообщение" in error_call[0][1]
