import pytest
from unittest.mock import MagicMock, patch

# Now import the bot module
import bot
import logging
import time

# To prevent the bot from actually starting polling
@pytest.fixture(autouse=True)
def stop_polling(monkeypatch):
    monkeypatch.setattr(bot.bot, "polling", lambda *args, **kwargs: None)
    monkeypatch.setattr(bot, "MONITORING_AVAILABLE", False) # Disable monitoring in tests

@pytest.fixture
def message():
    msg = MagicMock()
    msg.chat.id = 123
    msg.from_user.id = 456
    msg.text = "Test"
    return msg

@pytest.fixture
def call():
    c = MagicMock()
    c.message.chat.id = 123
    c.from_user.id = 456
    c.data = "test_data"
    return c

# === Test Command Handlers ===

def test_start_command(message):
    with patch.object(bot, 'common_handlers') as mock_handlers:
        bot.start_command(message)
        mock_handlers.handle_start.assert_called_once_with(message)

def test_admin_command_allowed(message):
    message.from_user.id = bot.ADMIN_IDS[0] # Use an actual admin ID
    with patch.object(bot, 'common_handlers') as mock_handlers:
        bot.admin_command(message)
        mock_handlers.handle_admin.assert_called_once_with(message)

def test_admin_command_denied(message):
    message.from_user.id = 999 # Non-admin ID
    with patch.object(bot.bot, 'send_message') as mock_send:
        bot.admin_command(message)
        mock_send.assert_called_once()
        assert "У вас нет прав" in mock_send.call_args[0][1]

def test_cancel_command(message):
    with patch('bot.database') as mock_db, patch.object(bot.bot, 'send_message') as mock_send:
        bot.cancel_command(message)
        mock_db.clear_user_state.assert_called_once_with(message.from_user.id)
        mock_send.assert_called_once()
        assert "Действие отменено" in mock_send.call_args[0][1]

def test_help_command(message):
    with patch.object(bot, 'common_handlers') as mock_handlers:
        bot.help_command(message)
        mock_handlers.handle_help.assert_called_once_with(message)

def test_backup_command_admin(message):
    message.from_user.id = bot.ADMIN_IDS[0]
    with patch.object(bot, 'admin_handlers') as mock_handlers:
        bot.backup_command(message)
        mock_handlers.handle_create_backup.assert_called_once_with(message)

def test_backup_command_denied(message):
    message.from_user.id = 999
    with patch.object(bot.bot, 'send_message') as mock_send:
        bot.backup_command(message)
        mock_send.assert_called_once()
        assert "нет прав" in mock_send.call_args[0][1]

def test_debug_command_unregistered(message):
    with patch('bot.database.get_user_by_id', return_value=None), \
         patch('bot.database.get_user_state', return_value=None), \
         patch.object(bot.bot, 'send_message') as mock_send:
        
        bot.debug_command(message)
        
        assert mock_send.call_count == 2
        assert "Не зарегистрирован" in mock_send.call_args_list[0][0][1]

# === Test Text Handlers ===

@pytest.mark.parametrize("text, handler_mock, method_name", [
    ('🔍 Найти вакансии', 'seeker_handlers', 'handle_find_vacancies'),
    ('📄 Мое резюме', 'seeker_handlers', 'handle_my_resume'),
    ('➕ Создать вакансию', 'employer_handlers', 'handle_create_vacancy'),
    ('👥 Найти сотрудников', 'employer_handlers', 'handle_find_candidates'),
    ('⚙️ Настройки', 'settings_handlers', 'handle_settings_menu'),
    ('ℹ️ О боте', 'common_handlers', 'handle_about'),
    ('📞 Поддержка', 'common_handlers', 'handle_support'),
])
def test_text_handlers(message, text, handler_mock, method_name):
    message.text = text
    
    # Find the corresponding handler function in the bot module's namespace
    func_name_map = {
        'handle_find_vacancies': 'find_vacancies_handler',
        'handle_my_resume': 'my_resume_handler',
        'handle_create_vacancy': 'create_vacancy_handler',
        'handle_find_candidates': 'find_candidates_handler',
        'handle_settings_menu': 'settings_handler',
        'handle_about': 'about_handler',
        'handle_support': 'support_handler',
    }
    target_func = bot.__dict__[func_name_map[method_name]]

    with patch.object(bot, handler_mock) as mock_handler:
        target_func(message)
        getattr(mock_handler, method_name).assert_called_once_with(message)

def test_seeker_settings_handler(message):
    message.text = '🎯 Профессия'
    with patch.object(bot, 'settings_handlers') as mock_handler:
        bot.seeker_settings_handler(message)
        mock_handler.handle_seeker_setting.assert_called_once_with(message, 'profession')

def test_seeker_status_handler(message):
    with patch.object(bot, 'settings_handlers') as mock_handler:
        bot.seeker_status_handler(message)
        mock_handler.handle_status_settings.assert_called_once_with(message)

def test_set_status_handler(message):
    message.text = '✅ Активно ищет работу'
    with patch.object(bot, 'settings_handlers') as mock_handler:
        bot.set_status_handler(message)
        mock_handler.set_seeker_status.assert_called_once_with(message, 'active')

def test_seeker_submenu_handler(message):
    with patch.object(bot, 'settings_handlers') as mock_handler:
        bot.seeker_submenu_handler(message)
        mock_handler.handle_seeker_submenu_action.assert_called_once_with(message)

def test_delete_account_handler(message):
    with patch.object(bot, 'settings_handlers') as mock_handler:
        bot.delete_account_handler(message)
        mock_handler.handle_delete_account.assert_called_once_with(message)

def test_confirm_delete_handler(message):
    with patch.object(bot, 'settings_handlers') as mock_handler:
        bot.confirm_delete_handler(message)
        mock_handler.confirm_delete_account.assert_called_once_with(message)

def test_complete_profile_handler(message):
    with patch.object(bot, 'profile_handlers') as mock_handler:
        bot.complete_profile_handler(message)
        mock_handler.handle_complete_profile.assert_called_once_with(message)

def test_stop_chat_handler(message):
    with patch.object(bot, 'common_handlers') as mock_handler:
        bot.stop_chat_handler(message)
        mock_handler.handle_stop_chat.assert_called_once_with(message)

def test_debug_command_seeker(message):
    user_data = {'full_name': 'John', 'id': 1}
    with patch('bot.database.get_user_by_id', return_value=user_data), \
         patch('bot.database.get_user_state', return_value={'step': 'test'}), \
         patch.object(bot.bot, 'send_message') as mock_send:
        
        bot.debug_command(message)
        
        assert mock_send.call_count == 2
        assert "Тип:* Соискатель" in mock_send.call_args_list[0][0][1]
        assert "step: test" in mock_send.call_args_list[0][0][1]

def test_chat_menu_seeker(message):
    user_data = {'full_name': 'John'}
    with patch('bot.database.get_user_by_id', return_value=user_data), \
         patch.object(bot, 'seeker_handlers') as mock_handler:
        
        bot.chat_menu_handler(message)
        mock_handler.handle_seeker_chats.assert_called_once_with(message)

def test_chat_menu_employer(message):
    user_data = {'company_name': 'Corp'}
    with patch('bot.database.get_user_by_id', return_value=user_data), \
         patch.object(bot, 'employer_handlers') as mock_handler:
        
        bot.chat_menu_handler(message)
        mock_handler.handle_employer_chats.assert_called_once_with(message)

def test_role_selection(message):
    with patch.object(bot, 'auth_handlers') as mock_handler:
        bot.role_selection(message)
        mock_handler.handle_role_selection.assert_called_once_with(message)

def test_register_handler(message):
    with patch.object(bot, 'auth_handlers') as mock_handler:
        bot.register_handler(message)
        mock_handler.handle_registration_start.assert_called_once_with(message)

def test_cancel_button_handler(message):
    with patch('bot.database.clear_user_state') as mock_clear, \
         patch.object(bot.bot, 'send_message') as mock_send:
        
        bot.cancel_button_handler(message)
        
        mock_clear.assert_called_once_with(message.from_user.id)
        mock_send.assert_called_once()
        assert "Действие отменено" in mock_send.call_args[0][1]

def test_custom_process_new_messages():
    """Тест обертки для rate limiting сообщений"""
    msgs = [MagicMock(), MagicMock()]
    msgs[0].from_user.id = 123
    msgs[1].from_user.id = 123
    
    with patch('bot.check_rate_limit', return_value=True) as mock_check, \
         patch('bot.original_process_new_messages') as mock_original:
        
        bot.custom_process_new_messages(msgs)
        
        assert mock_check.call_count == 2
        mock_original.assert_called_once_with(msgs)

def test_custom_process_new_messages_exception(message):
    """Тест критической ошибки при обработке сообщений"""
    with patch('bot.check_rate_limit', return_value=True), \
         patch('bot.original_process_new_messages', side_effect=Exception("Test Crash")), \
         patch('logging.critical') as mock_log:
        
        with pytest.raises(Exception):
            bot.custom_process_new_messages([message])

def test_custom_process_new_callback_query():
    """Тест обертки для rate limiting коллбеков"""
    calls = [MagicMock(), MagicMock()]
    
    with patch('bot.check_rate_limit', side_effect=[True, False]) as mock_check, \
         patch('bot.original_process_new_callback_query') as mock_original, \
         patch.object(bot.bot, 'answer_callback_query') as mock_answer:
        
        bot.custom_process_new_callback_query(calls)
        
        mock_original.assert_called_once_with([calls[0]])
        mock_answer.assert_called_once() # Для второго вызова, который вернул False

# === Test Callback Query Handlers ===

@pytest.mark.parametrize("data, handler_mock, method_name", [
    ('apply_123', 'seeker_handlers', 'handle_application_callback'),
    ('invite_123', 'employer_handlers', 'handle_invitation_callback'),
    ('edit_vac_123', 'employer_handlers', 'handle_my_vacancy_actions'),
    ('confirm_del_123', 'employer_handlers', 'handle_confirm_delete'),
    ('start_chat_123', 'common_handlers', 'handle_start_chat'),
])
def test_callback_handlers(call, data, handler_mock, method_name):
    call.data = data
    
    # Find the correct callback handler function in bot.py
    if data.startswith('apply'): func = bot.application_callback
    elif data.startswith('invite'): func = bot.invitation_callback
    elif data.startswith(('edit_vac', 'delete_vac', 'responses_vac')): func = bot.my_vacancy_actions_callback
    elif data.startswith('confirm_del'): func = bot.confirm_delete_callback
    elif data.startswith('start_chat'): func = bot.start_chat_callback
    else: pytest.fail("No handler found for this test case")

    with patch.object(bot, handler_mock) as mock_handler:
        func(call)
        getattr(mock_handler, method_name).assert_called_once_with(call)

def test_cancel_delete_callback(call):
    call.data = 'cancel_del_123'
    with patch.object(bot.bot, 'delete_message') as mock_delete, \
         patch.object(bot.bot, 'send_message') as mock_send:
        bot.cancel_delete_callback(call)
        mock_delete.assert_called_once_with(call.message.chat.id, call.message.message_id)
        mock_send.assert_called_once()
        assert "Возврат в меню" in mock_send.call_args[0][1]

# === Test process_all_messages dispatcher ===

@patch('bot.database')
class TestProcessAllMessages:

    def test_routes_to_admin_handler(self, mock_db, message):
        message.from_user.id = bot.ADMIN_IDS[0]
        mock_db.get_user_state.return_value = {'step': 'admin_broadcast_message'}
        with patch.object(bot, 'admin_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.process_broadcast_message.assert_called_once_with(message)

    def test_routes_to_admin_confirm(self, mock_db, message):
        message.from_user.id = bot.ADMIN_IDS[0]
        mock_db.get_user_state.return_value = {'step': 'admin_broadcast_confirm'}
        with patch.object(bot, 'admin_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.process_broadcast_confirm.assert_called_once_with(message)

    def test_routes_to_admin_search(self, mock_db, message):
        message.from_user.id = bot.ADMIN_IDS[0]
        mock_db.get_user_state.return_value = {'step': 'admin_search_user'}
        with patch.object(bot, 'admin_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.process_search_user.assert_called_once_with(message)

    def test_routes_to_admin_confirm(self, mock_db, message):
        message.from_user.id = bot.ADMIN_IDS[0]
        mock_db.get_user_state.return_value = {'step': 'admin_broadcast_confirm'}
        with patch.object(bot, 'admin_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.process_broadcast_confirm.assert_called_once_with(message)

    def test_routes_to_admin_search(self, mock_db, message):
        message.from_user.id = bot.ADMIN_IDS[0]
        mock_db.get_user_state.return_value = {'step': 'admin_search_user'}
        with patch.object(bot, 'admin_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.process_search_user.assert_called_once_with(message)

    def test_routes_to_chat_handler(self, mock_db, message):
        mock_db.get_user_state.return_value = {'step': 'active_chat'}
        with patch.object(bot, 'common_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.handle_chat_message.assert_called_once_with(message)

    def test_routes_to_profile_handler(self, mock_db, message):
        mock_db.get_user_state.return_value = {'step': 'profession'}
        with patch.object(bot, 'profile_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.process_profession.assert_called_once_with(message)

    def test_routes_to_profile_handler_steps(self, mock_db, message):
        steps = [
            ('education', 'process_education'),
            ('languages', 'process_languages'),
            ('experience', 'process_experience'),
            ('skills', 'process_skills')
        ]
        for step, method in steps:
            mock_db.get_user_state.return_value = {'step': step}
            with patch.object(bot, 'profile_handlers') as mock_handler:
                bot.process_all_messages(message)
                getattr(mock_handler, method).assert_called_once_with(message)

    def test_routes_to_settings_handler(self, mock_db, message):
        mock_db.get_user_state.return_value = {'step': 'enter_new_value', 'action': 'edit_seeker_field'}
        with patch.object(bot, 'settings_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.process_seeker_field_update.assert_called_once_with(message)

    def test_catches_critical_exception(self, mock_db, message):
        mock_db.get_user_state.side_effect = Exception("Critical DB Error")
        with patch.object(bot.bot, 'send_message') as mock_send:
            bot.process_all_messages(message)
            mock_send.assert_called_once()
            assert "Произошла системная ошибка" in mock_send.call_args[0][1]

    def test_process_all_messages_no_state(self, mock_db, message):
        """Тест обработки сообщения без состояния"""
        mock_db.get_user_state.return_value = None
        with patch.object(bot, 'common_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.handle_unknown.assert_called_once_with(message)

    def test_process_all_messages_unknown_step(self, mock_db, message):
        """Тест обработки сообщения с неизвестным шагом"""
        mock_db.get_user_state.return_value = {'step': 'unknown_step'}
        with patch.object(bot, 'common_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.handle_unknown.assert_called_once_with(message)

def test_json_formatter():
    """Тест JSON форматтера логов"""
    formatter = bot.JSONFormatter()
    record = logging.LogRecord("name", logging.INFO, "pathname", 1, "message", None, None)
    json_log = formatter.format(record)
    import json
    log_dict = json.loads(json_log)
    assert log_dict["message"] == "message"
    assert log_dict["level"] == "INFO"

def test_run_bot_keyboard_interrupt():
    """Тест остановки бота по Ctrl+C"""
    with patch.object(bot.bot, 'polling', side_effect=KeyboardInterrupt), \
         patch.object(bot.bot, 'stop_bot'), \
         patch('time.sleep'):
        bot.run_bot()

def test_run_bot_polling_exception():
    """Тест перезапуска polling при ошибке"""
    with patch.object(bot.bot, 'polling', side_effect=[Exception("Polling error"), KeyboardInterrupt]), \
         patch.object(bot.bot, 'stop_bot'), \
         patch('database.close_all_connections'), \
         patch('time.sleep') as mock_sleep:
        bot.run_bot()
        assert mock_sleep.call_count >= 1

def test_main_block_success():
    """Тест успешного запуска из __main__"""
    import runpy
    with patch('config.init_config', return_value=True), \
         patch('bot.setup_logging'), \
         patch('telebot.TeleBot') as MockTeleBot, \
         patch.dict('sys.modules', {'prometheus_client': None, 'sentry_sdk': None}):
        
        # Configure the mock instance to raise KeyboardInterrupt on polling
        mock_instance = MockTeleBot.return_value
        mock_instance.polling.side_effect = KeyboardInterrupt
        
        # Запускаем bot.py как главный модуль
        runpy.run_module('bot', run_name='__main__')
        
        mock_instance.polling.assert_called()

    def test_run_bot_polling_critical_error(self):
        """Тест критической ошибки в polling"""
        with patch.object(bot.bot, 'polling', side_effect=[Exception("Critical"), KeyboardInterrupt]), \
             patch('time.sleep') as mock_sleep, \
             patch('logging.critical') as mock_log:
            
            bot.run_bot()
            mock_log.assert_called()

def test_main_block_fail_config():
    """Тест неудачного запуска из __main__ при ошибке конфигурации"""
    import runpy
    import sys
    # init_config вызывает exit(1) при ошибке
    with patch('config.init_config', side_effect=SystemExit(1)), \
         patch('bot.setup_logging'), \
         patch.dict('sys.modules', {'prometheus_client': None, 'sentry_sdk': None}):
        
        with pytest.raises(SystemExit) as excinfo:
            runpy.run_module('bot', run_name='__main__')
        assert excinfo.value.code == 1

def test_check_rate_limit_send_error(message):
    """Тест ошибки отправки сообщения о лимите"""
    message.from_user.id = 99999
    
    # Заполняем лимит
    bot.user_requests[99999] = [time.time()] * bot.RATE_LIMIT
    
    with patch.object(bot.bot, 'send_message', side_effect=Exception("Send Error")) as mock_send, \
         patch('logging.error') as mock_log:
        
        assert bot.check_rate_limit(message) is False
        mock_log.assert_called()
        assert "Could not send rate limit warning" in mock_log.call_args[0][0]

def test_process_all_messages_critical_send_error(message):
    """Тест двойной ошибки в process_all_messages"""
    with patch('bot.database.get_user_state', side_effect=Exception("DB Error")), \
         patch.object(bot.bot, 'send_message', side_effect=Exception("Send Error")) as mock_send, \
         patch('logging.error') as mock_log:
        
        bot.process_all_messages(message)
        
        # Должен залогировать ошибку отправки
        mock_log.assert_called()
        assert "Не удалось отправить сообщение об ошибке" in mock_log.call_args[0][0]

def test_run_bot_polling_normal_exit():
    """Тест нормального завершения polling (перезапуск)"""
    # side_effect: 1. Normal return (None), 2. KeyboardInterrupt to stop loop
    with patch.object(bot.bot, 'polling', side_effect=[None, KeyboardInterrupt]), \
         patch.object(bot.bot, 'stop_bot'), \
         patch('time.sleep') as mock_sleep, \
         patch('bot.bot.remove_webhook'):
        
        bot.run_bot()
        
        # Should sleep after normal exit
        assert mock_sleep.call_count >= 1