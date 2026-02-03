import pytest
from unittest.mock import MagicMock, patch
from handlers.auth.role_auth import RoleAuth


class TestRoleAuth:
    @pytest.fixture
    def bot(self):
        mock_bot = MagicMock()
        return mock_bot

    @pytest.fixture
    def handler(self, bot):
        return RoleAuth(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        return msg

    def test_handle_role_selection_seeker(self, handler, message):
        """Выбор роли соискателя"""
        message.text = '👤 Я ищу работу'
        with patch('database.get_user_by_id', return_value=None), \
             patch('database.set_user_state') as mock_set:

            handler.handle_role_selection(message)

            mock_set.assert_called_with(456, {'role': 'seeker'})
            handler.bot.send_message.assert_called()
            assert "Панель соискателя" in handler.bot.send_message.call_args[0][1]

    def test_handle_role_selection_employer(self, handler, message):
        """Выбор роли работодателя"""
        message.text = '🏢 Я работодатель'
        with patch('database.get_user_by_id', return_value=None), \
             patch('database.set_user_state') as mock_set:

            handler.handle_role_selection(message)

            mock_set.assert_called_with(456, {'role': 'employer'})
            handler.bot.send_message.assert_called()
            assert "Панель работодателя" in handler.bot.send_message.call_args[0][1]

    def test_handle_role_selection_existing_seeker(self, handler, message):
        """Выбор роли уже зарегистрированным соискателем"""
        user_data = {'full_name': 'John'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_role_selection(message)
            handler.bot.send_message.assert_called()
            assert "Здравствуйте, John" in handler.bot.send_message.call_args[0][1]

    def test_handle_role_selection_existing_seeker_tries_employer(self, handler, message):
        """Выбор роли 'работодатель' уже зарегистрированным соискателем"""
        message.text = '🏢 Я работодатель'
        user_data = {'full_name': 'John'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_role_selection(message)
            # Должно быть вызвано дважды: приветствие и предупреждение
            assert handler.bot.send_message.call_count == 2
            warning_call = handler.bot.send_message.call_args_list[1]
            assert "Вы уже зарегистрированы как соискатель" in warning_call[0][1]

    def test_handle_role_selection_existing_employer_tries_seeker(self, handler, message):
        """Выбор роли 'соискатель' уже зарегистрированным работодателем"""
        message.text = '👤 Я ищу работу'
        user_data = {'company_name': 'Corp'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_role_selection(message)
            assert handler.bot.send_message.call_count == 2
            warning_call = handler.bot.send_message.call_args_list[1]
            assert "Вы уже зарегистрированы как работодатель" in warning_call[0][1]

    def test_handle_registration_start_no_role(self, handler, message):
        """Попытка регистрации без выбора роли"""
        with patch('database.get_user_by_id', return_value=None), \
             patch('database.get_user_state', return_value={}):

            handler.handle_registration_start(message)

            handler.bot.send_message.assert_called()
            assert "Сначала выберите роль" in handler.bot.send_message.call_args[0][1]

    def test_handle_registration_start_existing_seeker(self, handler, message):
        """Попытка регистрации уже существующим соискателем"""
        user_data = {'full_name': 'John'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_registration_start(message)
            handler.bot.send_message.assert_called_once()
            assert "Здравствуйте, John" in handler.bot.send_message.call_args[0][1]

    def test_handle_registration_start_existing_employer(self, handler, message):
        """Попытка регистрации уже существующим работодателем"""
        user_data = {'company_name': 'Corp'}
        with patch('database.get_user_by_id', return_value=user_data):
            handler.handle_registration_start(message)
            handler.bot.send_message.assert_called_once()
            assert "Здравствуйте, Corp" in handler.bot.send_message.call_args[0][1]

    def test_handle_registration_start_success(self, handler, message):
        """Начало регистрации (капча)"""
        with patch('database.get_user_by_id', return_value=None), \
             patch('database.get_user_state', return_value={'role': 'seeker'}), \
             patch('utils.generate_captcha', return_value=("2 + 2", 4)), \
             patch('database.set_user_state') as mock_set:

            handler.handle_registration_start(message)

            mock_set.assert_called()
            assert mock_set.call_args[0][1]['step'] == 'captcha'
            assert mock_set.call_args[0][1]['captcha_answer'] == 4
            handler.bot.send_message.assert_called()
            assert "2 + 2" in handler.bot.send_message.call_args[0][1]

    def test_process_captcha_correct_seeker(self, handler, message):
        """Правильный ответ на капчу (соискатель)"""
        message.text = "4"
        user_state = {'role': 'seeker', 'captcha_answer': 4, 'step': 'captcha'}

        with patch('database.get_user_state', return_value=user_state), \
             patch('utils.validate_captcha', return_value=True), \
             patch('database.set_user_state') as mock_set:

            handler.process_captcha(message)

            # Должен перейти к вводу телефона
            mock_set.assert_called()
            assert mock_set.call_args[0][1]['step'] == 'phone'
            handler.bot.send_message.assert_called()
            assert "Регистрация соискателя" in handler.bot.send_message.call_args[0][1]

    def test_process_captcha_incorrect(self, handler, message):
        """Неправильный ответ на капчу"""
        message.text = "5"
        user_state = {'role': 'seeker', 'captcha_answer': 4, 'step': 'captcha'}

        with patch('database.get_user_state', return_value=user_state), \
             patch('utils.validate_captcha', return_value=False), \
             patch('utils.generate_captcha', return_value=("3 + 3", 6)), \
             patch('database.set_user_state') as mock_set:

            handler.process_captcha(message)

            # Должна сгенерироваться новая капча
            mock_set.assert_called()
            assert mock_set.call_args[0][1]['captcha_answer'] == 6
            handler.bot.send_message.assert_called()
            assert "Неправильный ответ" in handler.bot.send_message.call_args[0][1]

    def test_process_captcha_cancel(self, handler, message):
        """Отмена на шаге капчи"""
        message.text = "отмена"
        with patch('utils.cancel_request', return_value=True), \
             patch.object(handler, 'cancel_registration') as mock_cancel:
            handler.process_captcha(message)
            mock_cancel.assert_called_once_with(message.chat.id, message.from_user.id, "Регистрация отменена")

    def test_process_captcha_no_state(self, handler, message):
        """Обработка капчи без состояния"""
        with patch('database.get_user_state', return_value=None):
            handler.process_captcha(message)
            handler.bot.send_message.assert_called_once()
            assert "Сессия истекла" in handler.bot.send_message.call_args[0][1]

    def test_start_seeker_reg_after_captcha_existing_user(self, handler, message):
        """Начало регистрации соискателя после капчи, но пользователь уже есть"""
        user_state = {}
        existing_user = {'full_name': 'Already Exists'}
        with patch('database.get_user_by_id', return_value=existing_user), \
             patch('database.clear_user_state') as mock_clear, \
             patch('keyboards.seeker_main_menu', return_value=MagicMock()) as mock_keyboard:

            handler.start_seeker_registration_after_captcha(message, user_state)

            mock_clear.assert_called_with(message.from_user.id)
            handler.bot.send_message.assert_called_with(message.chat.id, f"👋 Здравствуйте, {existing_user['full_name']}!",
                                                        parse_mode='Markdown', reply_markup=mock_keyboard())

    def test_start_employer_reg_after_captcha_existing_user(self, handler, message):
        """Начало регистрации работодателя после капчи, но пользователь уже есть"""
        user_state = {}
        existing_user = {'company_name': 'Existing Corp'}
        with patch('database.get_user_by_id', return_value=existing_user), \
             patch('database.clear_user_state') as mock_clear, \
             patch('keyboards.employer_main_menu', return_value=MagicMock()) as mock_keyboard:
            handler.start_employer_registration_after_captcha(message, user_state)
            mock_clear.assert_called_with(message.from_user.id)
            handler.bot.send_message.assert_called_with(message.chat.id, f"👋 Здравствуйте, {existing_user['company_name']}!",
                                                        parse_mode='Markdown', reply_markup=mock_keyboard())
