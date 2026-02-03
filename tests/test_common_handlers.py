import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
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
            assert recipient_call[0][0] == 789  # target_id
            assert "Сообщение от Sender" in recipient_call[0][1]

            # Проверяем подтверждение отправителю
            sender_call = handler.bot.send_message.call_args_list[1]
            assert sender_call[0][0] == 123  # chat_id
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
        call.data = "start_chat_999"  # non-existent user
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
            assert error_call[0][0] == 123  # chat_id
            assert "Не удалось отправить сообщение" in error_call[0][1]

    def test_handle_admin_exception(self, handler, message):
        """Тест обработки ошибки в handle_admin"""
        with patch('handlers.common.database.execute_query', side_effect=Exception("DB Error")), \
             patch('logging.error') as mock_log:

            handler.handle_admin(message)

            mock_log.assert_called()
            handler.bot.send_message.assert_called()
            assert "Произошла ошибка" in handler.bot.send_message.call_args[0][1]

    def test_handle_report_bug(self, handler, message):
        """Тест начала сообщения об ошибке"""
        with patch('database.set_user_state') as mock_set:
            handler.handle_report_bug(message)
            mock_set.assert_called_with(456, {'step': 'support_bug_report'})
            handler.bot.send_message.assert_called()
            assert "Сообщить об ошибке" in handler.bot.send_message.call_args[0][1]

    def test_handle_complaint(self, handler, message):
        """Тест начала подачи жалобы"""
        with patch('database.set_user_state') as mock_set:
            handler.handle_complaint(message)
            mock_set.assert_called_with(456, {'step': 'support_complaint'})
            handler.bot.send_message.assert_called()
            assert "Подать жалобу" in handler.bot.send_message.call_args[0][1]

    def test_process_support_message_success(self, handler, message):
        """Тест успешной отправки сообщения в поддержку"""
        message.text = "Something is wrong"
        user_state = {'step': 'support_bug_report'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.execute_query') as mock_query, \
             patch('database.clear_user_state') as mock_clear, \
             patch('database.get_user_by_id', return_value={'full_name': 'test'}):
            handler.process_support_message(message)
            # Check DB insert
            mock_query.assert_any_call(
                "INSERT INTO complaints (user_id, user_name, type, message, photo_id) VALUES (?, ?, ?, ?, ?)",
                (456, 'TestUser', 'Ошибка', 'Something is wrong', None),
                commit=True
            )
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Ваше сообщение принято" in handler.bot.send_message.call_args[0][1]

    def test_handle_start_chat_exception(self, handler):
        """Тест обработки ошибки в handle_start_chat"""
        call = MagicMock()
        call.data = "start_chat_789"
        call.from_user.id = 456

        with patch('database.get_user_by_id', side_effect=Exception("DB Error")), \
             patch('logging.error') as mock_log:

            handler.handle_start_chat(call)

            mock_log.assert_called()
            handler.bot.answer_callback_query.assert_called_with(call.id, "❌ Ошибка")

    def test_process_support_message_photo_no_caption(self, handler, message):
        """Тест сообщения в поддержку: фото без подписи"""
        message.text = None
        message.caption = None
        message.photo = [MagicMock(file_id='123')]
        user_state = {'step': 'support_bug_report'}

        with patch('database.get_user_state', return_value=user_state), \
             patch('database.execute_query') as mock_query, \
             patch('database.clear_user_state'), \
             patch('database.get_user_by_id', return_value={'full_name': 'User'}):

            handler.process_support_message(message)

            # Проверяем, что использовался дефолтный текст
            args = mock_query.call_args_list[-1][0]  # Last call is INSERT
            assert "Пользователь прислал изображение без описания" in args[1][3]  # params

    def test_process_support_message_no_text_no_photo(self, handler, message):
        """Тест сообщения в поддержку: пустое сообщение"""
        message.text = None
        message.caption = None
        message.photo = None

        with patch('database.get_user_state', return_value={'step': 'support_bug_report'}):
            handler.process_support_message(message)
            handler.bot.send_message.assert_called()
            assert "опишите вашу проблему" in handler.bot.send_message.call_args[0][1]

    def test_process_support_message_profanity(self, handler, message):
        """Тест сообщения в поддержку: мат"""
        message.text = "bad word"

        with patch('database.get_user_state', return_value={'step': 'support_bug_report'}), \
             patch('utils.contains_profanity', return_value=True):

            handler.process_support_message(message)
            handler.bot.send_message.assert_called()
            assert "недопустимые слова" in handler.bot.send_message.call_args[0][1]

    def test_process_support_message_complaint_type(self, handler, message):
        """Тест сообщения в поддержку: тип Жалоба"""
        message.text = "Complaint"
        user_state = {'step': 'support_complaint'}

        with patch('database.get_user_state', return_value=user_state), \
             patch('database.execute_query') as mock_query, \
             patch('database.clear_user_state'), \
             patch('database.get_user_by_id', return_value={'full_name': 'User'}):

            handler.process_support_message(message)

            # Проверяем тип в INSERT
            args = mock_query.call_args_list[-1][0]
            # params is args[1]
            # (user_id, user_name, type, message, photo_id)
            assert args[1][2] == "Жалоба"

    def test_process_support_message_migration_error(self, handler, message):
        """Тест ошибки миграции в process_support_message"""
        message.text = "Bug"
        user_state = {'step': 'support_bug_report'}

        with patch('database.get_user_state', return_value=user_state), \
             patch('database.execute_query') as mock_query, \
             patch('database.clear_user_state'), \
             patch('database.get_user_by_id', return_value={'full_name': 'User'}), \
             patch('logging.error') as mock_log:

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
