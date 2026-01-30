import pytest
from unittest.mock import MagicMock, patch
from handlers.settings import SettingsHandlers

class TestSettingsHandlers:
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

    def test_handle_settings_menu_seeker(self, handler, message):
        """Меню настроек для соискателя"""
        user_data = {'full_name': 'John'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_settings_menu(message)
            handler.bot.send_message.assert_called()
            assert "Настройки соискателя" in handler.bot.send_message.call_args[0][1]

    def test_handle_seeker_setting(self, handler, message):
        """Выбор поля для редактирования"""
        user_data = {'full_name': 'John', 'profession': 'Dev'}
        with patch('database.get_user_by_id', return_value=user_data), \
             patch('database.set_user_state') as mock_set:
            
            handler.handle_seeker_setting(message, 'profession')
            
            mock_set.assert_called()
            assert mock_set.call_args[0][1]['action'] == 'edit_seeker_field'
            handler.bot.send_message.assert_called()
            assert "Профессия" in handler.bot.send_message.call_args[0][1]

    def test_process_field_update_success(self, handler, message):
        """Успешное обновление поля"""
        message.text = "New Profession"
        user_state = {'action': 'edit_seeker_field', 'field': 'profession', 'field_display': 'Профессия', 'step': 'enter_new_value'}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.update_seeker_profile', return_value=True), \
             patch('database.clear_user_state') as mock_clear:
            
            handler.process_seeker_field_update(message)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "успешно обновлено" in handler.bot.send_message.call_args[0][1]

    def test_handle_seeker_setting_invalid_field(self, handler, message):
        """Выбор несуществующего поля для редактирования"""
        user_data = {'full_name': 'John'}
        with patch('database.get_user_by_id', return_value=user_data), \
             patch('database.set_user_state') as mock_set:
            
            handler.handle_seeker_setting(message, 'non_existent_field')
            
            mock_set.assert_called()
            assert mock_set.call_args[0][1]['field'] == 'non_existent_field'
            assert "non_existent_field" in handler.bot.send_message.call_args[0][1]

    def test_process_field_update_db_fail(self, handler, message):
        """Ошибка БД при обновлении поля"""
        message.text = "New Value"
        user_state = {'step': 'enter_new_value', 'field': 'profession', 'field_display': 'Профессия'}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.update_seeker_profile', return_value=False): # DB fails
            handler.process_seeker_field_update(message)
            handler.bot.send_message.assert_called()
            assert "Ошибка при обновлении" in handler.bot.send_message.call_args[0][1]

    def test_process_field_update_invalid_phone(self, handler, message):
        """Обновление поля: невалидный телефон"""
        message.text = "123"
        user_state = {'step': 'enter_new_value', 'field': 'phone', 'field_display': 'Телефон'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('utils.is_valid_uzbek_phone', return_value=False):
            
            handler.process_seeker_field_update(message)
            assert "Неверный формат номера" in handler.bot.send_message.call_args[0][1]

    def test_process_field_update_invalid_email(self, handler, message):
        """Обновление поля: невалидный email"""
        message.text = "bad-email"
        user_state = {'step': 'enter_new_value', 'field': 'email', 'field_display': 'Email'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('utils.is_valid_email', return_value=False):
            
            handler.process_seeker_field_update(message)
            assert "Неверный формат email" in handler.bot.send_message.call_args[0][1]

    def test_handle_settings_menu_employer(self, handler, message):
        """Меню настроек для работодателя"""
        user_data = {'company_name': 'Corp'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_settings_menu(message)
            handler.bot.send_message.assert_called()
            assert "Настройки компании" in handler.bot.send_message.call_args[0][1]

    def test_handle_seeker_submenu_action_back(self, handler, message):
        """Возврат из подменю"""
        message.text = '↩️ Назад в настройки'
        user_state = {'action': 'edit_seeker_field', 'field': 'profession', 'field_display': 'P', 'current_value': 'V'}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.clear_user_state') as mock_clear, \
             patch.object(handler, 'handle_settings_menu') as mock_menu:
            
            handler.handle_seeker_submenu_action(message)
            
            mock_clear.assert_called_with(456)
            mock_menu.assert_called_with(message)

    def test_handle_seeker_submenu_action_edit(self, handler, message):
        """Выбор действия редактирования"""
        message.text = '✏️ Изменить'
        user_state = {'action': 'edit_seeker_field', 'field': 'profession', 'field_display': 'P', 'current_value': 'V'}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            
            handler.handle_seeker_submenu_action(message)
            
            assert user_state['step'] == 'enter_new_value'
            mock_set.assert_called_with(456, user_state)
            handler.bot.send_message.assert_called()
            assert "Введите новое значение" in handler.bot.send_message.call_args[0][1]

    def test_process_field_update_cancel(self, handler, message):
        """Отмена обновления поля"""
        message.text = "❌ Отмена"
        with patch('utils.cancel_request', return_value=True), \
             patch('database.clear_user_state') as mock_clear:
            
            handler.process_seeker_field_update(message)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Изменение отменено" in handler.bot.send_message.call_args[0][1]

    def test_process_field_update_invalid_length(self, handler, message):
        """Слишком короткое значение"""
        message.text = "A"
        user_state = {'step': 'enter_new_value', 'field': 'profession', 'field_display': 'P'}
        
        with patch('database.get_user_state', return_value=user_state):
            handler.process_seeker_field_update(message)
            handler.bot.send_message.assert_called()
            assert "слишком короткое" in handler.bot.send_message.call_args[0][1]

    def test_process_field_update_too_long(self, handler, message):
        """Слишком длинное значение"""
        message.text = "A" * 501
        user_state = {'step': 'enter_new_value', 'field': 'profession', 'field_display': 'P'}
        
        with patch('database.get_user_state', return_value=user_state):
            handler.process_seeker_field_update(message)
            handler.bot.send_message.assert_called()
            assert "слишком длинное" in handler.bot.send_message.call_args[0][1]

    def test_handle_status_settings(self, handler, message):
        """Меню статуса"""
        user_data = {'full_name': 'John', 'status': 'active'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_status_settings(message)
            handler.bot.send_message.assert_called()
            assert "Статус поиска" in handler.bot.send_message.call_args[0][1]

    def test_set_seeker_status_db_fail(self, handler, message):
        """Ошибка БД при установке статуса"""
        with patch('database.update_seeker_profile', return_value=False):
            handler.set_seeker_status(message, 'inactive')
            handler.bot.send_message.assert_called()
            assert "Ошибка обновления статуса" in handler.bot.send_message.call_args[0][1]

    def test_set_seeker_status(self, handler, message):
        """Установка статуса"""
        with patch('database.update_seeker_profile', return_value=True):
            handler.set_seeker_status(message, 'inactive')
            handler.bot.send_message.assert_called()
            assert "Статус успешно изменен" in handler.bot.send_message.call_args[0][1]

    def test_handle_employer_action_delete(self, handler, message):
        """Действие работодателя: удалить"""
        message.text = '🗑️ Удалить компанию'
        user_data = {'company_name': 'Corp'}
        
        with patch('database.get_user_by_id', return_value=user_data), \
             patch.object(handler, 'handle_delete_account') as mock_delete:
            
            handler.handle_employer_action(message)
            mock_delete.assert_called_with(message)

    def test_handle_delete_account_prompt(self, handler, message):
        """Запрос на удаление аккаунта"""
        user_data = {'full_name': 'John'}
        
        with patch('database.get_user_by_id', return_value=user_data), \
             patch('database.set_user_state') as mock_set:
            
            handler.handle_delete_account(message)
            
            mock_set.assert_called()
            assert mock_set.call_args[0][1]['action'] == 'delete_account'
            handler.bot.send_message.assert_called()
            assert "ВНИМАНИЕ" in handler.bot.send_message.call_args[0][1]

    def test_confirm_delete_account_yes_seeker(self, handler, message):
        """Подтверждение удаления соискателя"""
        message.text = '✅ Да, удалить аккаунт'
        user_state = {'action': 'delete_account', 'role': 'seeker', 'name': 'John', 'account_type': 'соискателя'}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.delete_seeker_account', return_value=True), \
             patch('database.clear_user_state') as mock_clear:
            
            handler.confirm_delete_account(message)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Аккаунт удален" in handler.bot.send_message.call_args[0][1]

    def test_confirm_delete_account_yes_employer(self, handler, message):
        """Подтверждение удаления работодателя"""
        message.text = '✅ Да, удалить аккаунт'
        user_state = {'action': 'delete_account', 'role': 'employer', 'name': 'Corp', 'account_type': 'компании'}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.delete_employer_account', return_value=True), \
             patch('database.clear_user_state') as mock_clear:
            
            handler.confirm_delete_account(message)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Аккаунт удален" in handler.bot.send_message.call_args[0][1]

    def test_confirm_delete_account_db_fail(self, handler, message):
        """Подтверждение удаления: ошибка БД"""
        message.text = '✅ Да, удалить аккаунт'
        user_state = {'action': 'delete_account', 'role': 'seeker'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.delete_seeker_account', return_value=False): # Ошибка удаления
            
            handler.confirm_delete_account(message)
            assert "Ошибка при удалении" in handler.bot.send_message.call_args[0][1]

    def test_confirm_delete_account_no(self, handler, message):
        """Отмена удаления аккаунта"""
        message.text = '❌ Нет, отменить'
        user_state = {'action': 'delete_account', 'role': 'seeker'}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.clear_user_state') as mock_clear:
            
            handler.confirm_delete_account(message)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Удаление отменено" in handler.bot.send_message.call_args[0][1]

    def test_confirm_delete_account_invalid_choice(self, handler, message):
        """Неверный выбор при подтверждении удаления"""
        message.text = "может быть"
        user_state = {'action': 'delete_account', 'role': 'seeker', 'name': 'John'}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'handle_delete_account') as mock_re_prompt:
            
            handler.confirm_delete_account(message)
            
            handler.bot.send_message.assert_called_with(message.chat.id, "❌ Пожалуйста, выберите один из вариантов.", parse_mode='Markdown')
            mock_re_prompt.assert_called_with(message)

    def test_handle_seeker_submenu_action_add(self, handler, message):
        """Выбор действия добавить"""
        message.text = '➕ Добавить'
        user_state = {'action': 'edit_seeker_field', 'field': 'skills', 'field_display': 'S', 'current_value': None}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            
            handler.handle_seeker_submenu_action(message)
            
            assert user_state['step'] == 'enter_new_value'
            mock_set.assert_called_with(456, user_state)
            handler.bot.send_message.assert_called()
            assert "Введите значение" in handler.bot.send_message.call_args[0][1]

    def test_handle_employer_action_back(self, handler, message):
        """Действие работодателя: назад"""
        message.text = '↩️ Назад в меню'
        user_data = {'company_name': 'Corp'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_employer_action(message)
            handler.bot.send_message.assert_called()
            assert "Панель работодателя" in handler.bot.send_message.call_args[0][1]

    def test_handle_employer_action_invalid(self, handler, message):
        """Действие работодателя: неизвестная кнопка"""
        message.text = 'Неизвестная кнопка'
        user_data = {'company_name': 'Corp'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_employer_action(message)
            handler.bot.send_message.assert_called()
            assert "Неизвестное действие" in handler.bot.send_message.call_args[0][1]

    def test_handle_employer_setting(self, handler, message):
        """Выбор поля работодателя для редактирования"""
        user_data = {'company_name': 'Corp'}
        with patch('database.get_user_by_id', return_value=user_data), \
             patch('database.set_user_state') as mock_set:
            
            handler.handle_employer_setting(message, 'company_name')
            
            mock_set.assert_called()
            assert mock_set.call_args[0][1]['action'] == 'edit_employer_field'
            assert mock_set.call_args[0][1]['field'] == 'company_name'
            handler.bot.send_message.assert_called()
            assert "Название компании" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_field_update_success(self, handler, message):
        """Успешное обновление поля работодателя"""
        message.text = "New Corp Name"
        user_state = {
            'action': 'edit_employer_field', 
            'field': 'company_name', 
            'field_display': 'Название компании', 
            'step': 'enter_new_value'
        }
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.update_employer_profile', return_value=True), \
             patch('database.clear_user_state') as mock_clear:
            
            handler.process_employer_field_update(message)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "успешно обновлено" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_field_update_fail(self, handler, message):
        """Ошибка при обновлении поля работодателя"""
        message.text = "New Corp Name"
        user_state = {'action': 'edit_employer_field', 'field': 'company_name', 'step': 'enter_new_value'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.update_employer_profile', return_value=False):
            handler.process_employer_field_update(message)
            handler.bot.send_message.assert_called()
            assert "Ошибка при обновлении" in handler.bot.send_message.call_args[0][1]