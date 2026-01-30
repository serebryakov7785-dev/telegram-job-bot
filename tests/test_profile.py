import pytest
from unittest.mock import MagicMock, patch
import keyboards
from handlers.profile import ProfileHandlers

class TestProfileHandlers:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return ProfileHandlers(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        return msg

    def test_start_profile_setup_seeker(self, handler, message):
        """Начало заполнения профиля соискателя"""
        user_data = {'full_name': 'John'}
        with patch('database.set_user_state') as mock_set:
            handler.start_profile_setup(message, user_data)
            
            mock_set.assert_called()
            assert mock_set.call_args[0][1]['step'] == 'education'
            assert mock_set.call_args[0][1]['role'] == 'seeker'
            handler.bot.send_message.assert_called()
            assert "Регистрация завершена" in handler.bot.send_message.call_args[0][1]

    def test_start_profile_setup_employer(self, handler, message):
        """Начало заполнения профиля работодателя (сразу в меню)"""
        user_data = {'company_name': 'Corp Inc.', 'telegram_id': 456}
        with patch('database.clear_user_state') as mock_clear:
            handler.start_profile_setup(message, user_data)
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Регистрация компании завершена" in handler.bot.send_message.call_args[0][1]

    def test_process_profession_success(self, handler, message):
        """Ввод профессии"""
        message.text = "Developer"
        user_state = {'step': 'profession', 'role': 'seeker', 'profile_data': {}}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            
            handler.process_profession(message)
            
            assert user_state['profile_data']['profession'] == "Developer"
            assert user_state['step'] == 'languages'
            mock_set.assert_called_with(456, user_state)

    def test_process_profession_cancel(self, handler, message):
        """Отмена на шаге ввода профессии"""
        message.text = "отмена"
        user_state = {'step': 'profession', 'role': 'seeker', 'profile_data': {}}
        with patch('utils.cancel_request', return_value=True), \
             patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'finish_profile_setup') as mock_finish:
            handler.process_profession(message)
            mock_finish.assert_called_once_with(message.chat.id, message.from_user.id, user_state, show_summary=False)

    def test_process_profession_invalid(self, handler, message):
        """Ввод невалидной профессии"""
        message.text = "A"
        user_state = {'step': 'profession'}
        with patch('database.get_user_state', return_value=user_state):
            handler.process_profession(message)
            handler.bot.send_message.assert_called()
            assert "Слишком короткое название" in handler.bot.send_message.call_args[0][1]

    def test_process_step_expired_session(self, handler, message):
        """Тест обработки шага с истекшей сессией (неверный step)"""
        message.text = "Some text"
        # Устанавливаем неверный шаг, чтобы имитировать истекшую сессию
        user_state = {'step': 'wrong_step'}
        with patch('database.get_user_state', return_value=user_state):
            handler.process_education(message) # Вызываем любой обработчик шага
            
            # Проверяем, что send_message был вызван
            handler.bot.send_message.assert_called_once()
            
            # Получаем аргументы вызова
            args, kwargs = handler.bot.send_message.call_args
            
            # Проверяем текст и chat_id
            assert args == (message.chat.id, "❌ Сессия истекла!")
            # Проверяем, что была передана правильная клавиатура, сравнивая их JSON-представления
            assert 'reply_markup' in kwargs
            assert kwargs['reply_markup'].to_json() == keyboards.main_menu().to_json()

    def test_process_education_success(self, handler, message):
        """Ввод образования"""
        message.text = "Higher"
        user_state = {'step': 'education', 'role': 'seeker', 'profile_data': {}}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            
            handler.process_education(message)
            
            assert user_state['profile_data']['education'] == "Higher"
            assert user_state['step'] == 'profession'
            mock_set.assert_called_with(456, user_state)

    def test_process_education_cancel(self, handler, message):
        """Отмена на шаге ввода образования"""
        message.text = "отмена"
        user_state = {'step': 'education', 'role': 'seeker', 'profile_data': {}}
        with patch('utils.cancel_request', return_value=True), \
             patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'finish_profile_setup') as mock_finish:
            handler.process_education(message)
            mock_finish.assert_called_once_with(message.chat.id, message.from_user.id, user_state, show_summary=False)

    def test_process_education_invalid(self, handler, message):
        """Ввод невалидного образования"""
        message.text = "A"
        user_state = {'step': 'education'}
        with patch('database.get_user_state', return_value=user_state):
            handler.process_education(message)
            assert "Слишком короткое описание" in handler.bot.send_message.call_args[0][1]

    def test_process_languages_success(self, handler, message):
        """Ввод языков"""
        message.text = "Uzbek, Russian"
        user_state = {'step': 'languages', 'role': 'seeker', 'profile_data': {}}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            handler.process_languages(message)
            assert user_state['profile_data']['languages'] == "Uzbek, Russian"
            assert user_state['step'] == 'experience'
            mock_set.assert_called_with(456, user_state)

    def test_process_languages_invalid(self, handler, message):
        """Ввод невалидных языков"""
        message.text = "A"
        user_state = {'step': 'languages'}
        with patch('database.get_user_state', return_value=user_state):
            handler.process_languages(message)
            assert "Слишком короткое описание" in handler.bot.send_message.call_args[0][1]

    def test_process_experience_success(self, handler, message):
        """Ввод опыта"""
        message.text = "5 years"
        user_state = {'step': 'experience', 'role': 'seeker', 'profile_data': {}}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            handler.process_experience(message)
            assert user_state['profile_data']['experience'] == "5 years"
            assert user_state['step'] == 'skills'
            mock_set.assert_called_with(456, user_state)

    def test_process_experience_invalid(self, handler, message):
        """Ввод невалидного опыта"""
        message.text = "1"
        user_state = {'step': 'experience'}
        with patch('database.get_user_state', return_value=user_state):
            handler.process_experience(message)
            handler.bot.send_message.assert_called()
            assert "Слишком короткое описание" in handler.bot.send_message.call_args[0][1]

    def test_process_skills_success(self, handler, message):
        """Ввод навыков и завершение"""
        message.text = "Python, SQL"
        user_state = {'step': 'skills', 'role': 'seeker', 'profile_data': {}}
        
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.update_seeker_profile', return_value=True), \
             patch('database.clear_user_state') as mock_clear:
            
            handler.process_skills(message)
            
            assert user_state['profile_data']['skills'] == "Python, SQL"
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Профиль успешно заполнен" in handler.bot.send_message.call_args[0][1]

    def test_process_skills_cancel(self, handler, message):
        """Отмена на шаге ввода навыков"""
        message.text = "отмена"
        user_state = {'step': 'skills', 'role': 'seeker', 'profile_data': {}}
        with patch('utils.cancel_request', return_value=True), \
             patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'finish_profile_setup') as mock_finish:
            handler.process_skills(message)
            mock_finish.assert_called_once_with(message.chat.id, message.from_user.id, user_state, show_summary=False)

    def test_process_skills_invalid(self, handler, message):
        """Ввод невалидных навыков"""
        message.text = "A"
        user_state = {'step': 'skills'}
        with patch('database.get_user_state', return_value=user_state):
            handler.process_skills(message)
            handler.bot.send_message.assert_called()
            assert "Слишком короткое описание" in handler.bot.send_message.call_args[0][1]

    def test_handle_complete_profile_not_logged_in(self, handler, message):
        """Попытка заполнить профиль без входа"""
        with patch('database.get_user_by_id', return_value=None):
            handler.handle_complete_profile(message)
            handler.bot.send_message.assert_called()
            assert "Сначала зарегистрируйтесь" in handler.bot.send_message.call_args[0][1]

    def test_handle_complete_profile_already_filled(self, handler, message):
        """Попытка заполнить уже заполненный профиль"""
        user_data = {'role': 'seeker', 'profession': 'Dev', 'skills': 'Python'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_complete_profile(message)
            handler.bot.send_message.assert_called()
            assert "Ваш профиль уже заполнен" in handler.bot.send_message.call_args[0][1]

    def test_handle_complete_profile_for_employer(self, handler, message):
        """Попытка заполнить профиль для работодателя"""
        user_data = {'role': 'employer', 'company_name': 'Corp'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_complete_profile(message)
            handler.bot.send_message.assert_called()
            assert "не требует дополнительного заполнения" in handler.bot.send_message.call_args[0][1]

    def test_finish_profile_setup_on_cancel(self, handler, message):
        """Завершение настройки при отмене (show_summary=False)"""
        user_state = {'role': 'seeker', 'profile_data': {}}
        with patch('database.clear_user_state') as mock_clear:
            handler.finish_profile_setup(message.chat.id, message.from_user.id, user_state, show_summary=False)
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "заполнить профиль позже" in handler.bot.send_message.call_args[0][1]

    def test_save_profile_data_for_employer(self, handler, message):
        """Тест сохранения данных профиля для работодателя"""
        user_id = message.from_user.id
        user_state = {
            'role': 'employer',
            'profile_data': {
                'profession': 'IT',
                'education': 'Higher',
                'experience': '5 years'
            }
        }
        employer_data = {'id': 1, 'company_name': 'TestCo', 'description': 'Initial desc.'}

        with patch('database.get_user_by_id', return_value=employer_data), \
             patch('database.update_employer_profile') as mock_update:
            
            handler.save_profile_data(user_id, user_state)
            
            mock_update.assert_called_once()
            # Проверяем, что новое описание содержит данные из профиля
            updated_description = mock_update.call_args[1]['description']
            assert 'Initial desc.' in updated_description
            assert 'Сфера деятельности: IT' in updated_description
            assert 'Требования к образованию: Higher' in updated_description
            assert 'Требования к опыту: 5 years' in updated_description

    def test_save_profile_data_seeker_fails(self, handler, message):
        """Тест ошибки сохранения данных профиля соискателя"""
        user_id = message.from_user.id
        user_state = {'role': 'seeker', 'profile_data': {'profession': 'Test'}}
        
        with patch('database.update_seeker_profile', return_value=False) as mock_update:
            handler.save_profile_data(user_id, user_state)
            mock_update.assert_called_once()

    def test_process_languages_cancel(self, handler, message):
        """Отмена на шаге языков"""
        message.text = "отмена"
        user_state = {'step': 'languages', 'role': 'seeker', 'profile_data': {}}
        with patch('utils.cancel_request', return_value=True), \
             patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'finish_profile_setup') as mock_finish:
            handler.process_languages(message)
            mock_finish.assert_called_once()

    def test_process_experience_cancel(self, handler, message):
        """Отмена на шаге опыта"""
        message.text = "отмена"
        user_state = {'step': 'experience', 'role': 'seeker', 'profile_data': {}}
        with patch('utils.cancel_request', return_value=True), \
             patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'finish_profile_setup') as mock_finish:
            handler.process_experience(message)
            mock_finish.assert_called_once()

    def test_finish_profile_setup_success(self, handler, message):
        """Успешное завершение настройки профиля"""
        user_state = {
            'role': 'seeker', 
            'profile_data': {
                'profession': 'Dev', 'education': 'High', 
                'languages': 'En', 'experience': '5y', 'skills': 'Py'
            }
        }
        with patch('database.clear_user_state') as mock_clear, \
             patch.object(handler, 'save_profile_data', return_value=True):
            
            handler.finish_profile_setup(message.chat.id, message.from_user.id, user_state, show_summary=True)
            
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Профиль успешно заполнен" in handler.bot.send_message.call_args[0][1]
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Профиль успешно заполнен" in handler.bot.send_message.call_args[0][1]