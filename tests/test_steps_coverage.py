import pytest
from unittest.mock import MagicMock, patch
from handlers.steps import StepHandlers


class TestStepHandlersCoverage:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return StepHandlers(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        return msg

    def test_handle_steps_captcha_fallback(self, handler, message):
        """Test captcha step fallback when auth_handlers is not set"""
        handler.auth_handlers = None
        with patch('database.get_user_state', return_value={'step': 'captcha'}), \
             patch('handlers.auth.role_auth.RoleAuth') as MockRoleAuth:

            mock_role = MockRoleAuth.return_value
            assert handler.handle_steps(message) is True
            mock_role.process_captcha.assert_called_with(message)

    def test_handle_seeker_steps_fallback_exception(self, handler, message):
        """Test exception in seeker steps fallback"""
        user_state = {'step': 'phone', 'role': 'seeker'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('handlers.auth.seeker_auth.SeekerAuth', side_effect=Exception("Init Error")), \
             patch('logging.error') as mock_log:

            assert handler.handle_steps(message) is False
            mock_log.assert_called()

    def test_handle_employer_steps_fallback_exception(self, handler, message):
        """Test exception in employer steps fallback"""
        user_state = {'step': 'company_name', 'role': 'employer'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('handlers.auth.employer_auth.EmployerAuth', side_effect=Exception("Init Error")), \
             patch('logging.error') as mock_log:

            assert handler.handle_steps(message) is False
            mock_log.assert_called()

    def test_handle_recovery_step_fallback_exception(self, handler, message):
        """Test exception in recovery step fallback"""
        user_state = {'step': 'recovery'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('handlers.auth.login_auth.LoginAuth', side_effect=Exception("Init Error")), \
             patch('logging.error') as mock_log:

            assert handler.handle_steps(message) is False
            mock_log.assert_called()
