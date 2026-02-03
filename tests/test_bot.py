import pytest
import sys
import os
import logging
import time
from unittest.mock import MagicMock, patch

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Now import the bot module
import bot  # noqa: E402


# To prevent the bot from actually starting polling
@pytest.fixture(autouse=True)
def stop_polling(monkeypatch):
    monkeypatch.setattr(bot.bot, "polling", lambda *args, **kwargs: None)
    monkeypatch.setattr(bot, "MONITORING_AVAILABLE", False)  # Disable monitoring in tests


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
    message.from_user.id = bot.ADMIN_IDS[0]  # Use an actual admin ID
    with patch.object(bot, 'common_handlers') as mock_handlers:
        bot.admin_command(message)
        mock_handlers.handle_admin.assert_called_once_with(message)


def test_admin_command_denied(message):
    message.from_user.id = 999  # Non-admin ID
    with patch.object(bot.bot, 'send_message') as mock_send:
        bot.admin_command(message)
        mock_send.assert_called_once()
        assert "У вас нет прав" in mock_send.call_args[0][1]


def test_cancel_command(message):
    with patch('bot.clear_user_state') as mock_clear, patch.object(bot.bot, 'send_message') as mock_send:
        bot.cancel_command(message)
        mock_clear.assert_called_once_with(message.from_user.id)
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
    with patch('bot.get_user_by_id', return_value=None), \
         patch('bot.get_user_state', return_value=None), \
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
    ('📋 Мои отклики', 'seeker_handlers', 'handle_my_responses'),
    ('📋 Мои вакансии', 'employer_handlers', 'handle_my_vacancies'),
])
def test_text_handlers(message, text, handler_mock, method_name):
    message.text = text

    # Find the corresponding handler function in the bot module's namespace
    func_name_map = {
        'handle_find_vacancies': 'find_vacancies_handler',
        'handle_my_resume': 'my_resume_handler',
        'handle_create_vacancy': 'create_vacancy_handler',
        'handle_my_responses': 'my_responses_handler',
        'handle_my_vacancies': 'my_vacancies_handler',
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
    with patch('bot.get_user_by_id', return_value=user_data), \
         patch('bot.get_user_state', return_value={'step': 'test'}), \
         patch.object(bot.bot, 'send_message') as mock_send:

        bot.debug_command(message)

        assert mock_send.call_count == 2
        assert "Тип:* Соискатель" in mock_send.call_args_list[0][0][1]
        assert "step: test" in mock_send.call_args_list[0][0][1]


def test_chat_menu_seeker(message):
    user_data = {'full_name': 'John'}
    with patch('bot.get_user_by_id', return_value=user_data), \
         patch.object(bot, 'seeker_handlers') as mock_handler:

        bot.chat_menu_handler(message)
        mock_handler.handle_seeker_chats.assert_called_once_with(message)


def test_chat_menu_employer(message):
    user_data = {'company_name': 'Corp'}
    with patch('bot.get_user_by_id', return_value=user_data), \
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
    with patch('bot.get_user_state', return_value={'step': 'some_step'}), \
         patch('bot.step_handlers') as mock_steps:
        bot.cancel_button_handler(message)
        mock_steps.cancel_current_step.assert_called_once_with(message.from_user.id, message.chat.id)


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
         patch('logging.critical'):

        with pytest.raises(Exception):
            bot.custom_process_new_messages([message])


def test_custom_process_new_callback_query():
    """Тест обертки для rate limiting коллбеков"""
    calls = [MagicMock(), MagicMock()]

    with patch('bot.check_rate_limit', side_effect=[True, False]) as _, \
         patch('bot.original_process_new_callback_query') as mock_original, \
         patch.object(bot.bot, 'answer_callback_query') as mock_answer:

        bot.custom_process_new_callback_query(calls)

        mock_original.assert_called_once_with([calls[0]])
        mock_answer.assert_called_once()  # Для второго вызова, который вернул False

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

    if data.startswith('apply'):
        func = bot.application_callback
    elif data.startswith('invite'):
        func = bot.invitation_callback
    elif data.startswith(('edit_vac', 'delete_vac', 'responses_vac')):
        func = bot.my_vacancy_actions_callback
    elif data.startswith('confirm_del'):
        func = bot.confirm_delete_callback
    elif data.startswith('start_chat'):
        func = bot.start_chat_callback
    else:
        pytest.fail("No handler found for this test case")

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


def test_admin_action_callback_clear_cache(call):
    """Тест коллбека очистки кэша админом"""
    call.data = "admin_clear_cache"
    call.from_user.id = bot.ADMIN_IDS[0]
    with patch('bot.invalidate_vacancies_cache') as mock_invalidate, \
         patch.object(bot.bot, 'answer_callback_query') as mock_answer:
        bot.admin_action_callback(call)
        mock_invalidate.assert_called_once()
        mock_answer.assert_called_with(call.id, "✅ Кэш вакансий очищен")


def test_admin_action_callback_denied(call):
    """Тест доступа к админским коллбекам"""
    call.data = "admin_clear_cache"
    call.from_user.id = 999  # Not an admin
    with patch.object(bot.bot, 'answer_callback_query') as mock_answer:
        bot.admin_action_callback(call)
        mock_answer.assert_called_with(call.id, "❌ Доступ запрещен")

# === Test process_all_messages dispatcher ===


class TestProcessAllMessages:

    def test_routes_to_admin_handler(self, message):
        message.from_user.id = bot.ADMIN_IDS[0]
        with patch('bot.get_user_state', return_value={'step': 'admin_broadcast_message'}), \
             patch.object(bot, 'admin_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.process_broadcast_message.assert_called_once_with(message)

    def test_routes_to_admin_confirm(self, message):
        message.from_user.id = bot.ADMIN_IDS[0]
        with patch('bot.get_user_state', return_value={'step': 'admin_broadcast_confirm'}), \
             patch.object(bot, 'admin_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.process_broadcast_confirm.assert_called_once_with(message)

    def test_routes_to_admin_search(self, message):
        message.from_user.id = bot.ADMIN_IDS[0]
        with patch('bot.get_user_state', return_value={'step': 'admin_search_user'}), \
             patch.object(bot, 'admin_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.process_search_user.assert_called_once_with(message)

    def test_routes_to_chat_handler(self, message):
        with patch('bot.get_user_state', return_value={'step': 'active_chat'}), \
             patch.object(bot, 'common_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.handle_chat_message.assert_called_once_with(message)

    def test_routes_to_profile_handler(self, message):
        with patch('bot.get_user_state', return_value={'step': 'profession'}), \
             patch.object(bot, 'profile_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.process_profession_specific.assert_called_once_with(message)

    def test_routes_to_profile_handler_steps(self, message):
        steps = [
            ('education', 'process_education'),
            ('languages', 'show_language_selection'),
            ('experience', 'process_experience'),
            ('skills', 'process_skills')
        ]
        for step, method in steps:
            with patch('bot.get_user_state', return_value={'step': step, 'temp_languages': []}), \
                 patch.object(bot, 'profile_handlers') as mock_handler:
                bot.process_all_messages(message)
                if step == 'languages':
                    # Special case for languages which takes more args
                    getattr(mock_handler, method).assert_called_once()
                else:
                    getattr(mock_handler, method).assert_called_once_with(message)

    def test_routes_to_settings_handler(self, message):
        with patch('bot.get_user_state', return_value={'step': 'enter_new_value', 'action': 'edit_seeker_field'}), \
             patch.object(bot, 'settings_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.process_seeker_field_update.assert_called_once_with(message)

    def test_catches_critical_exception(self, message):
        with patch('bot.get_user_state', side_effect=Exception("Critical DB Error")), \
             patch.object(bot.bot, 'send_message') as mock_send:
            bot.process_all_messages(message)
            mock_send.assert_called_once()
            assert "Произошла системная ошибка" in mock_send.call_args[0][1]

    def test_process_all_messages_no_state(self, message):
        """Тест обработки сообщения без состояния"""
        with patch('bot.get_user_state', return_value=None), \
             patch.object(bot, 'common_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.handle_unknown.assert_called_once_with(message)

    def test_process_all_messages_unknown_step(self, message):
        """Тест обработки сообщения с неизвестным шагом"""
        with patch('bot.get_user_state', return_value={'step': 'unknown_step'}), \
             patch.object(bot, 'common_handlers') as mock_handler:
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
         patch('time.sleep'), \
         patch('bot.bot.remove_webhook'), \
         patch('bot.setup_logging'), \
         patch('bot.init_config'), \
         patch('bot.init_database'):
        bot.run_bot()


def test_run_bot_polling_exception():
    """Тест перезапуска polling при ошибке"""
    with patch.object(bot.bot, 'polling', side_effect=[Exception("Polling error"), KeyboardInterrupt]), \
         patch.object(bot.bot, 'stop_bot'), \
         patch('bot.close_all_connections'), \
         patch('time.sleep') as mock_sleep, \
         patch('bot.bot.remove_webhook'), \
         patch('bot.setup_logging'), \
         patch('bot.init_config'), \
         patch('bot.init_database'):
        bot.run_bot()
        assert mock_sleep.call_count >= 1


def test_main_block_success():
    """Тест успешного запуска из __main__"""
    import runpy
    with patch('config.init_config', return_value=True), \
         patch('bot.setup_logging'), \
         patch('database.schema.init_database'), \
         patch('telebot.TeleBot') as MockTeleBot, \
         patch.dict('sys.modules', {'prometheus_client': None, 'sentry_sdk': None}):

        # Configure the mock instance to raise KeyboardInterrupt on polling
        mock_instance = MockTeleBot.return_value
        mock_instance.polling.side_effect = KeyboardInterrupt

        # Запускаем bot.py как главный модуль
        runpy.run_module('bot', run_name='__main__')

        mock_instance.polling.assert_called()


def test_run_bot_polling_critical_error():
    """Тест критической ошибки в polling"""
    with patch.object(bot.bot, 'polling', side_effect=[Exception("Critical"), KeyboardInterrupt]), \
         patch('time.sleep') as _, \
         patch('logging.critical') as mock_log, \
         patch('bot.close_all_connections'), \
         patch('bot.bot.remove_webhook'), \
         patch('bot.setup_logging'), \
         patch('bot.init_config'), \
         patch('bot.init_database'):

        bot.run_bot()
        mock_log.assert_called()


def test_main_block_fail_config():
    """Тест неудачного запуска из __main__ при ошибке конфигурации"""
    import runpy
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

    with patch.object(bot.bot, 'send_message', side_effect=Exception("Send Error")), \
         patch('logging.error') as mock_log:

        assert bot.check_rate_limit(message) is False
        mock_log.assert_called()
        assert "Could not send rate limit warning" in mock_log.call_args[0][0]


def test_process_all_messages_critical_send_error(message):
    """Тест двойной ошибки в process_all_messages"""
    with patch('bot.get_user_state', side_effect=Exception("DB Error")), \
         patch.object(bot.bot, 'send_message', side_effect=Exception("Send Error")), \
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
         patch('bot.bot.remove_webhook'), \
         patch('bot.setup_logging'), \
         patch('bot.init_config'), \
         patch('bot.init_database'):

        bot.run_bot()

        # Should sleep after normal exit
        assert mock_sleep.call_count >= 1


def test_debug_command_employer(message):
    user_data = {'company_name': 'Corp', 'id': 2, 'contact_person': 'Boss', 'phone': '123', 'email': 'e@mail'}
    with patch('bot.get_user_by_id', return_value=user_data), \
         patch('bot.get_user_state', return_value=None), \
         patch.object(bot.bot, 'send_message') as mock_send:

        bot.debug_command(message)

        assert mock_send.call_count == 2
        assert "Тип:* Работодатель" in mock_send.call_args_list[0][0][1]
        assert "Corp" in mock_send.call_args_list[0][0][1]


def test_chat_menu_unregistered(message):
    with patch('bot.get_user_by_id', return_value=None), \
         patch.object(bot.bot, 'send_message') as mock_send:

        bot.chat_menu_handler(message)

        mock_send.assert_called_once()
        assert "Чтобы начать диалог" in mock_send.call_args[0][1]


def test_check_rate_limit_muted(message):
    user_id = message.from_user.id
    # Set user as muted in the future
    bot.muted_users[user_id] = time.time() + 100

    assert bot.check_rate_limit(message) is False
    del bot.muted_users[user_id]


def test_check_rate_limit_unmute(message):
    user_id = message.from_user.id
    # Set user as muted in the past
    bot.muted_users[user_id] = time.time() - 100
    bot.user_requests[user_id] = []

    assert bot.check_rate_limit(message) is True
    assert user_id not in bot.muted_users


def test_custom_process_new_messages_with_monitoring(message):
    with patch('bot.MONITORING_AVAILABLE', True), \
         patch('bot.METRIC_MESSAGES') as mock_metric, \
         patch('bot.METRIC_LATENCY') as mock_latency, \
         patch('bot.check_rate_limit', return_value=True), \
         patch('bot.original_process_new_messages'):

        mock_latency.time.return_value.__enter__.return_value = None

        bot.custom_process_new_messages([message])

        mock_metric.labels.assert_called_with(type='incoming_message')
        mock_metric.labels.return_value.inc.assert_called()
        mock_latency.time.assert_called()


def test_custom_process_new_callback_query_rate_limit(call):
    """Test rate limiting for callback queries"""
    calls = [call]
    with patch('bot.check_rate_limit', return_value=False), \
         patch.object(bot.bot, 'answer_callback_query') as mock_answer, \
         patch('bot.original_process_new_callback_query') as mock_original:

        bot.custom_process_new_callback_query(calls)

        mock_answer.assert_called_with(call.id, "⏳ Слишком много запросов. Подождите.", show_alert=True)
        mock_original.assert_not_called()


def test_custom_process_new_callback_query_answer_error(call):
    """Test error handling when answering callback query in rate limit"""
    calls = [call]
    with patch('bot.check_rate_limit', return_value=False), \
         patch.object(bot.bot, 'answer_callback_query', side_effect=Exception("API Error")), \
         patch('bot.original_process_new_callback_query') as mock_original:

        # Should not raise exception
        bot.custom_process_new_callback_query(calls)

        mock_original.assert_not_called()


def test_process_all_messages_critical_error_send_fail(message):
    """Test failure to send error message to user after critical error"""
    with patch('bot.get_user_state', side_effect=Exception("Critical")), \
         patch.object(bot.bot, 'send_message', side_effect=Exception("Send Fail")), \
         patch('logging.critical') as mock_log_crit, \
         patch('logging.error') as mock_log_err:

        bot.process_all_messages(message)

        mock_log_crit.assert_called()
        mock_log_err.assert_called()  # Should log the inner exception


@pytest.mark.parametrize("text, handler_mock, method_name", [
    ('🏠 На главную', 'common_handlers', 'handle_back_to_main'),
    ('🏠 Главное меню', 'common_handlers', 'handle_back_to_main'),
    ('↩️ Назад в меню', 'common_handlers', 'handle_back_to_profile'),
    ('🔑 Забыли пароль?', 'auth_handlers', 'handle_password_recovery'),
    ('🚪 Выйти', 'auth_handlers', 'handle_logout'),
    ('🐛 Ошибка', 'common_handlers', 'handle_report_bug'),
    ('⚠️ Жалоба', 'common_handlers', 'handle_complaint'),
])
def test_more_text_handlers(message, text, handler_mock, method_name):
    message.text = text

    # Map text to function name in bot.py
    func_map = {
        '🏠 На главную': 'back_to_main',
        '🏠 Главное меню': 'back_to_main',
        '↩️ Назад в меню': 'back_to_profile',
        '🔑 Забыли пароль?': 'recovery_handler',
        '🚪 Выйти': 'logout_handler',
        '🐛 Ошибка': 'bug_report_handler',
        '⚠️ Жалоба': 'complaint_handler'
    }

    target_func = bot.__dict__[func_map[text]]

    with patch.object(bot, handler_mock) as mock_handler:
        target_func(message)
        getattr(mock_handler, method_name).assert_called_once_with(message)


def test_admin_text_handlers(message):
    """Test admin text commands"""
    message.from_user.id = bot.ADMIN_IDS[0]

    admin_commands = [
        ('📊 Статистика', 'handle_statistics'),
        ('📢 Рассылка', 'handle_broadcast_start'),
        ('👥 Пользователи', 'handle_users'),
        ('📋 Список соискателей', 'handle_list_seekers'),
        ('⚠️ Жалобы', 'handle_complaints'),
        ('🔎 Поиск пользователя', 'handle_search_user_prompt'),
        ('↩️ Назад в админку', 'handle_admin'),  # common_handlers
        ('⚙️ Настройки бота', 'handle_admin_settings'),
        ('💾 Бэкап', 'handle_create_backup'),
    ]

    func_map = {
        '📊 Статистика': 'admin_stats_handler',
        '📢 Рассылка': 'admin_broadcast_handler',
        '👥 Пользователи': 'admin_users_handler',
        '📋 Список соискателей': 'admin_list_seekers',
        '⚠️ Жалобы': 'admin_complaints_handler',
        '🔎 Поиск пользователя': 'admin_search_user',
        '⚙️ Настройки бота': 'admin_settings_handler',
        '💾 Бэкап': 'admin_backup_handler'
    }

    for text, method in admin_commands:
        message.text = text
        handler_obj = 'admin_handlers'
        func_name = ''

        # Determine handler object
        if text == '↩️ Назад в админку':
            handler_obj = 'common_handlers'
            func_name = 'admin_back_to_menu'
        else:
            func_name = func_map.get(text)

        target_func = bot.__dict__[func_name]

        with patch.object(bot, handler_obj) as mock_handler:
            target_func(message)
            getattr(mock_handler, method).assert_called_once_with(message)

    # Separate test for list employers to reduce complexity
    message.text = '📋 Список работодателей'
    with patch.object(bot, 'admin_handlers') as mock_handler:
        bot.admin_list_employers(message)
        mock_handler.handle_list_employers.assert_called_once_with(message)


def test_process_all_messages_support(message):
    """Test routing for support messages"""
    steps = ['support_bug_report', 'support_complaint']

    for step in steps:
        with patch('bot.get_user_state', return_value={'step': step}), \
             patch.object(bot, 'common_handlers') as mock_handler:
            bot.process_all_messages(message)
            mock_handler.process_support_message.assert_called_once_with(message)
