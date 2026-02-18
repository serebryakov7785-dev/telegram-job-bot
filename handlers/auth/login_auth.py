# handlers/auth/login_auth.py
import database
import keyboards

from .login_flow import LoginFlowMixin
from .recovery_flow import RecoveryFlowMixin


class LoginAuth(LoginFlowMixin, RecoveryFlowMixin):
    def __init__(self, bot):
        self.bot = bot

    def cancel_login(self, chat_id, user_id, message_text):
        """Отмена входа"""
        database.clear_user_state(user_id)
        self.bot.send_message(
            chat_id,
            f"❌ *{message_text}*",
            parse_mode="Markdown",
            reply_markup=keyboards.main_menu(),
        )
