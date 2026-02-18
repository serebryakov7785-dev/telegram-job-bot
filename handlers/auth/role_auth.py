# handlers/auth/role_auth.py
import database
import keyboards
import utils
from localization import TRANSLATIONS, get_text_by_lang, get_user_language


class RoleAuth:
    def __init__(self, bot):
        self.bot = bot
        self.seeker_auth = None
        self.employer_auth = None

    def set_handlers(self, seeker_auth, employer_auth):
        self.seeker_auth = seeker_auth
        self.employer_auth = employer_auth

    def handle_role_selection(self, message):
        user_id = message.from_user.id
        lang = get_user_language(user_id)

        # Пытаемся определить язык по тексту кнопки, если состояние было утеряно
        for code, trans in TRANSLATIONS.items():
            if message.text == trans.get("role_seeker") or message.text == trans.get(
                "role_employer"
            ):
                lang = code
                break

        all_seeker_roles = [d.get("role_seeker", "") for d in TRANSLATIONS.values()]
        all_employer_roles = [d.get("role_employer", "") for d in TRANSLATIONS.values()]

        existing_user = database.get_user_by_id(user_id)
        if existing_user:
            # Обновляем язык пользователя в БД, если он отличается
            if lang:
                table = "job_seekers" if "full_name" in existing_user else "employers"
                database.execute_query(
                    f"UPDATE {table} SET language_code = ? WHERE telegram_id = ?",  # nosec
                    (lang, user_id),
                    commit=True,
                )

            if "full_name" in existing_user:
                self.bot.send_message(
                    message.chat.id,
                    f"👋 {get_text_by_lang('welcome_back', lang)}, {existing_user['full_name']}!",
                    parse_mode="Markdown",
                    reply_markup=keyboards.seeker_main_menu(lang=lang),
                )
                if message.text in all_employer_roles:
                    self.bot.send_message(
                        message.chat.id,
                        get_text_by_lang("already_registered_seeker", lang),
                        parse_mode="Markdown",
                        reply_markup=keyboards.seeker_main_menu(lang=lang),
                    )

            else:
                self.bot.send_message(
                    message.chat.id,
                    f"👋 {get_text_by_lang('welcome_back', lang)}, {existing_user['company_name']}!",
                    parse_mode="Markdown",
                    reply_markup=keyboards.employer_main_menu(lang=lang),
                )
                if message.text in all_seeker_roles:
                    self.bot.send_message(
                        message.chat.id,
                        get_text_by_lang("already_registered_employer", lang),
                        parse_mode="Markdown",
                        reply_markup=keyboards.employer_main_menu(lang=lang),
                    )
            return
        if message.text in all_seeker_roles:
            database.set_user_state(user_id, {"role": "seeker", "language_code": lang})
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("seeker_panel_intro", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.seeker_menu(is_registered=False, lang=lang),
            )
        elif message.text in all_employer_roles:
            database.set_user_state(
                user_id, {"role": "employer", "language_code": lang}
            )
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("employer_panel_intro", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.employer_menu(is_registered=False, lang=lang),
            )

    def handle_registration_start(self, message):
        user_id = message.from_user.id
        existing_user = database.get_user_by_id(user_id)
        if existing_user:
            if "full_name" in existing_user:
                self.bot.send_message(
                    message.chat.id,
                    f"👋 Здравствуйте, {existing_user['full_name']}!",
                    parse_mode="Markdown",
                    reply_markup=keyboards.seeker_main_menu(),
                )
            else:
                self.bot.send_message(
                    message.chat.id,
                    f"👋 Здравствуйте, {existing_user['company_name']}!",
                    parse_mode="Markdown",
                    reply_markup=keyboards.employer_main_menu(),
                )
            return

        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)
        if not user_state or "role" not in user_state:
            self.bot.send_message(
                message.chat.id,
                "❌ Сначала выберите роль в главном меню!",
                parse_mode="Markdown",
                reply_markup=keyboards.main_menu(),
            )
            return

        captcha_question, captcha_answer = utils.generate_captcha()
        user_state["captcha_answer"] = captcha_answer
        user_state["step"] = "captcha"
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            f"{get_text_by_lang('security_check_intro', lang)}\n\n"
            f"{get_text_by_lang('security_check_prompt', lang).format(captcha_question=captcha_question)}",
            parse_mode="Markdown",
            reply_markup=keyboards.cancel_keyboard(lang=lang),
        )

    def process_captcha(self, message):
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        if utils.cancel_request(message.text):
            self.cancel_registration(
                message.chat.id,
                user_id,
                get_text_by_lang("registration_cancelled", lang),
            )
            return

        if not user_state:
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла!",
                reply_markup=keyboards.main_menu(),
            )
            return

        user_answer = message.text.strip()
        correct_answer = user_state.get("captcha_answer")

        if not utils.validate_captcha(user_answer, correct_answer):
            captcha_question, captcha_answer = utils.generate_captcha()
            user_state["captcha_answer"] = captcha_answer
            database.set_user_state(user_id, user_state)

            self.bot.send_message(
                message.chat.id,
                f"{get_text_by_lang('security_check_fail', lang)}\n\n"
                f"{get_text_by_lang('security_check_prompt', lang).format(captcha_question=captcha_question)}",
                parse_mode="Markdown",
                reply_markup=keyboards.cancel_keyboard(lang=lang),
            )
            return

        if "captcha_answer" in user_state:
            del user_state["captcha_answer"]

        role = user_state.get("role")
        if role == "seeker":
            self.start_seeker_registration_after_captcha(message, user_state)
        elif role == "employer":
            self.start_employer_registration_after_captcha(message, user_state)

    def start_seeker_registration_after_captcha(self, message, user_state):
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        existing_user = database.get_user_by_id(user_id)
        if existing_user:
            self.bot.send_message(
                message.chat.id,
                f"👋 Здравствуйте, {existing_user['full_name']}!",
                parse_mode="Markdown",
                reply_markup=keyboards.seeker_main_menu(),
            )
            database.clear_user_state(user_id)
            return

        user_state["step"] = "phone"
        user_state["registration_data"] = {}
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            f"{get_text_by_lang('check_passed', lang)}\n\n"
            f"{get_text_by_lang('registration_seeker_header', lang)}\n\n"
            f"{get_text_by_lang('prompt_phone', lang)}\n\n"
            + utils.show_phone_format_example(lang=lang),
            parse_mode="Markdown",
            reply_markup=keyboards.cancel_keyboard(lang=lang),
        )

    def start_employer_registration_after_captcha(self, message, user_state):
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        existing_user = database.get_user_by_id(user_id)
        if existing_user:
            self.bot.send_message(
                message.chat.id,
                f"👋 Здравствуйте, {existing_user['company_name']}!",
                parse_mode="Markdown",
                reply_markup=keyboards.employer_main_menu(),
            )
            database.clear_user_state(user_id)
            return

        user_state["step"] = "company_name"
        user_state["registration_data"] = {}
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            f"{get_text_by_lang('check_passed', lang)}\n\n"
            f"{get_text_by_lang('registration_employer_header', lang)}\n\n"
            f"{get_text_by_lang('prompt_company_name', lang)}",
            parse_mode="Markdown",
            reply_markup=keyboards.cancel_keyboard(lang=lang),
        )

    def cancel_registration(self, chat_id, user_id, message_text):
        lang = get_user_language(user_id)
        database.clear_user_state(user_id)
        self.bot.send_message(
            chat_id,
            f"❌ *{message_text}*",
            parse_mode="Markdown",
            reply_markup=keyboards.main_menu(lang=lang),
        )
