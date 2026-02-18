# handlers/auth/base_auth.py
import database
import keyboards


class AuthHandlers:
    def __init__(self, bot):
        self.bot = bot
        # Создаем обработчики
        from .employer_auth import EmployerAuth
        from .login_auth import LoginAuth
        from .role_auth import RoleAuth
        from .seeker_auth import SeekerAuth

        self.role = RoleAuth(bot)
        self.seeker = SeekerAuth(bot)
        self.employer = EmployerAuth(bot)
        self.login = LoginAuth(bot)

        # Устанавливаем обработчики в role_auth
        self.role.set_handlers(self.seeker, self.employer)

    def handle_role_selection(self, message):
        """Обработка выбора роли"""
        self.role.handle_role_selection(message)

    def handle_registration_start(self, message):
        """Начало регистрации с капчей"""
        self.role.handle_registration_start(message)

    # ================= РЕГИСТРАЦИЯ СОИСКАТЕЛЯ =================
    def process_seeker_phone(self, message):
        self.seeker.process_seeker_phone(message)

    def process_seeker_email(self, message):
        self.seeker.process_seeker_email(message)

    def process_seeker_name(self, message):
        self.seeker.process_seeker_name(message)

    def process_seeker_gender(self, message):
        self.seeker.process_seeker_gender(message)

    def process_seeker_region(self, message):
        self.seeker.process_seeker_region(message)

    def process_seeker_city_selection(self, message):
        self.seeker.process_seeker_city_selection(message)

    def finish_seeker_registration(self, message):
        self.seeker.finish_seeker_registration(message)

    # ================= РЕГИСТРАЦИЯ РАБОТОДАТЕЛЯ =================
    def process_employer_name(self, message):
        self.employer.process_employer_name(message)

    def process_employer_phone(self, message):
        self.employer.process_employer_phone(message)

    def process_employer_email(self, message):
        self.employer.process_employer_email(message)

    def process_employer_contact(self, message):
        self.employer.process_employer_contact(message)

    def process_employer_region(self, message):
        self.employer.process_employer_region(message)

    def process_employer_city_selection(self, message):
        self.employer.process_employer_city_selection(message)

    def process_business_activity(self, message):
        self.employer.process_business_activity(message)

    def handle_password_recovery(self, message):
        self.login.handle_password_recovery(message)

    def process_recovery(self, message):
        self.login.process_recovery(message)

    def handle_logout(self, message):
        self.login.handle_logout(message)

    def cancel_registration(self, chat_id, user_id, message_text):
        """Отмена регистрации"""
        database.clear_user_state(user_id)
        self.bot.send_message(
            chat_id,
            f"❌ *{message_text}*",
            parse_mode="Markdown",
            reply_markup=keyboards.main_menu(),
        )
