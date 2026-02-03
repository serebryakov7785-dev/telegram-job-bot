import pytest
from unittest.mock import MagicMock, patch
from handlers.settings import SettingsHandlers


class TestSettingsCoverage:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return SettingsHandlers(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        return msg

    def test_handle_settings_menu_no_user(self, handler, message):
        """Test settings menu when user is not found in DB"""
        with patch('database.get_user_by_id', return_value=None):
            handler.handle_settings_menu(message)
            handler.bot.send_message.assert_called()
            assert "Сначала зарегистрируйтесь" in handler.bot.send_message.call_args[0][1]

    def test_handle_seeker_setting_no_user(self, handler, message):
        """Test seeker setting when user is not found"""
        with patch('database.get_user_by_id', return_value=None):
            handler.handle_seeker_setting(message, 'profession')
            handler.bot.send_message.assert_called()
            assert "Сначала войдите" in handler.bot.send_message.call_args[0][1]

    def test_handle_seeker_submenu_action_expired(self, handler, message):
        """Test submenu action with expired session"""
        with patch('database.get_user_state', return_value=None):
            handler.handle_seeker_submenu_action(message)
            handler.bot.send_message.assert_called()
            assert "Сессия истекла" in handler.bot.send_message.call_args[0][1]

    def test_handle_seeker_submenu_action_unknown(self, handler, message):
        """Test unknown action in submenu"""
        message.text = "Unknown Action"
        user_state = {'action': 'edit_seeker_field', 'field': 'f', 'field_display': 'D', 'current_value': 'V'}
        with patch('database.get_user_state', return_value=user_state):
            handler.handle_seeker_submenu_action(message)
            handler.bot.send_message.assert_called()
            assert "Неизвестное действие" in handler.bot.send_message.call_args[0][1]

    def test_process_seeker_field_update_expired(self, handler, message):
        """Test field update with expired session"""
        with patch('database.get_user_state', return_value=None):
            handler.process_seeker_field_update(message)
            handler.bot.send_message.assert_called()
            assert "Сессия истекла" in handler.bot.send_message.call_args[0][1]

    def test_handle_status_settings_no_user(self, handler, message):
        """Test status settings when user is not found"""
        with patch('database.get_user_by_id', return_value=None):
            handler.handle_status_settings(message)
            handler.bot.send_message.assert_called()
            assert "Сначала войдите" in handler.bot.send_message.call_args[0][1]

    def test_handle_employer_action_no_user(self, handler, message):
        """Test employer action when user is not found"""
        with patch('database.get_user_by_id', return_value=None):
            handler.handle_employer_action(message)
            handler.bot.send_message.assert_called()
            assert "Сначала войдите" in handler.bot.send_message.call_args[0][1]

    def test_handle_employer_setting_no_user(self, handler, message):
        """Test employer setting when user is not found"""
        with patch('database.get_user_by_id', return_value=None):
            handler.handle_employer_setting(message, 'company_name')
            handler.bot.send_message.assert_called()
            assert "Сначала войдите" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_field_update_expired(self, handler, message):
        """Test employer field update with expired session"""
        with patch('database.get_user_state', return_value=None):
            handler.process_employer_field_update(message)
            handler.bot.send_message.assert_called()
            assert "Сессия истекла" in handler.bot.send_message.call_args[0][1]

    def test_handle_delete_account_no_user(self, handler, message):
        """Test delete account when user is not found"""
        with patch('database.get_user_by_id', return_value=None):
            handler.handle_delete_account(message)
            handler.bot.send_message.assert_called()
            assert "Сначала зарегистрируйтесь" in handler.bot.send_message.call_args[0][1]

    def test_confirm_delete_account_expired(self, handler, message):
        """Test confirm delete with expired session"""
        with patch('database.get_user_state', return_value=None):
            handler.confirm_delete_account(message)
            handler.bot.send_message.assert_called()
            assert "Сессия истекла" in handler.bot.send_message.call_args[0][1]

    def test_handle_employer_action_back(self, handler, message):
        """Test employer action: back to menu"""
        message.text = '↩️ Назад в меню'
        user_data = {'company_name': 'Corp'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_employer_action(message)
            handler.bot.send_message.assert_called()
            assert "Панель работодателя" in handler.bot.send_message.call_args[0][1]

    def test_handle_employer_action_invalid(self, handler, message):
        """Test employer action: unknown action"""
        message.text = 'Unknown Action'
        user_data = {'company_name': 'Corp'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_employer_action(message)
            handler.bot.send_message.assert_called()
            assert "Неизвестное действие" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_field_update_invalid_phone(self, handler, message):
        """Test employer field update with invalid phone"""
        message.text = "123"
        user_state = {'step': 'enter_new_value', 'action': 'edit_employer_field', 'field': 'phone'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('utils.is_valid_uzbek_phone', return_value=False):
            handler.process_employer_field_update(message)
            handler.bot.send_message.assert_called()
            assert "Неверный формат номера" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_field_update_invalid_email(self, handler, message):
        """Test employer field update with invalid email"""
        message.text = "bad-email"
        user_state = {'step': 'enter_new_value', 'action': 'edit_employer_field', 'field': 'email'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('handlers.settings.utils.is_valid_email', return_value=False):
            handler.process_employer_field_update(message)
            handler.bot.send_message.assert_called()
            assert "Неверный формат email" in handler.bot.send_message.call_args[0][1]

    def test_handle_seeker_submenu_action_languages(self, handler, message):
        """Test submenu action for languages (special flow)"""
        message.text = '✏️ Изменить'
        user_state = {'action': 'edit_seeker_field', 'field': 'languages', 'field_display': 'Языки', 'current_value': 'En'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            handler.handle_seeker_submenu_action(message)
            assert mock_set.call_args[0][1]['step'] == 'language_selection'
            assert mock_set.call_args[0][1]['source'] == 'settings'
            handler.bot.send_message.assert_called()

    def test_process_seeker_field_update_profanity(self, handler, message):
        message.text = "badword"
        user_state = {'step': 'enter_new_value', 'field': 'profession', 'field_display': 'Prof'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('utils.contains_profanity', return_value=True):
            handler.process_seeker_field_update(message)
            handler.bot.send_message.assert_called()
            assert "недопустимые слова" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_field_update_profanity(self, handler, message):
        message.text = "badword"
        user_state = {'step': 'enter_new_value', 'action': 'edit_employer_field', 'field': 'company_name'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('utils.contains_profanity', return_value=True):
            handler.process_employer_field_update(message)
            handler.bot.send_message.assert_called()
            assert "недопустимые слова" in handler.bot.send_message.call_args[0][1]

    def test_process_seeker_profession_sphere_other(self, handler, message):
        message.text = "Другое"
        user_state = {'step': 'edit_seeker_profession_sphere'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            handler.process_seeker_profession_sphere(message)
            assert mock_set.call_args[0][1]['step'] == 'enter_new_value'

    def test_process_seeker_profession_specific_other(self, handler, message):
        message.text = "Другое"
        user_state = {'step': 'edit_seeker_profession_specific'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            handler.process_seeker_profession_specific(message)
            assert mock_set.call_args[0][1]['step'] == 'enter_new_value'

    def test_process_seeker_profession_sphere_other_manual(self, handler, message):
        """Test 'Other' option in profession sphere settings"""
        message.text = "Другое"
        user_state = {'step': 'edit_seeker_profession_sphere'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            handler.process_seeker_profession_sphere(message)
            assert mock_set.call_args[0][1]['step'] == 'enter_new_value'
            handler.bot.send_message.assert_called()
            assert "Введите название" in handler.bot.send_message.call_args[0][1]
