# handlers/steps.py
import logging

import database
import keyboards
import utils  # Добавлен импорт
from localization import get_text_by_lang, get_user_language


class StepHandlers:
    def __init__(self, bot, auth_handlers=None):
        self.bot = bot
        self.auth_handlers = auth_handlers
        self.employer_handlers = None
        self.admin_handlers = None
        self.profile_handlers = None

    def set_auth_handlers(self, auth_handlers):
        """Установка обработчиков авторизации"""
        self.auth_handlers = auth_handlers

    def set_employer_handlers(self, handlers):
        """Установка обработчиков работодателя"""
        self.employer_handlers = handlers

    def set_admin_handlers(self, handlers):
        """Установка обработчиков админа"""
        self.admin_handlers = handlers

    def set_profile_handlers(self, handlers):
        """Установка обработчиков профиля"""
        self.profile_handlers = handlers

    def handle_steps(self, message):
        """Обработка step-by-step сообщений"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if not user_state or "step" not in user_state:
            return False  # Не наш step, пропускаем

        step = user_state["step"]
        role = user_state.get("role")

        # ПРОВЕРКА ОТМЕНЫ для любого шага
        # Если нажата кнопка "Назад" на шаге выбора города, передаем управление обработчику
        if message.text == "⬅️ Назад" and step in [
            "city_selection",
            "vacancy_profession",
            "vacancy_language_level",
        ]:
            pass
        elif utils.cancel_request(message.text):  # Теперь работает
            self.cancel_current_step(user_id, message.chat.id)
            return True

        # Обработка админских шагов
        if self.admin_handlers:
            admin_steps_map = {
                "admin_broadcast_message": self.admin_handlers.process_broadcast_message,
                "admin_broadcast_confirm": self.admin_handlers.process_broadcast_confirm,
                "admin_search_user": self.admin_handlers.process_search_user,
            }
            if step in admin_steps_map:
                admin_steps_map[step](message)
                return True

        # Обработка капчи (особый случай)
        if step == "captcha":
            # Если есть auth_handlers, используем их
            if self.auth_handlers and self.auth_handlers.role:
                self.auth_handlers.role.process_captcha(message)
                return True
            else:
                # Fallback
                from handlers.auth.role_auth import RoleAuth

                role_auth = RoleAuth(self.bot)
                role_auth.process_captcha(message)
                return True

        # Обработка шагов вакансии
        if isinstance(step, str) and (
            step.startswith("vacancy_") or step.startswith("edit_vacancy_")
        ):
            return self.handle_vacancy_steps(message, step, user_state)

        profile_steps = [
            "profession",
            "profession_sphere",
            "profession_specific",
            "education",
            "languages",
            "experience",
            "skills",
            "language_selection",
            "language_level",
            "language_custom_name",
        ]
        if isinstance(step, str) and step in profile_steps:
            return self.handle_profile_steps(message, step, user_state)

        # Для остальных шагов используем auth_handlers
        if self.auth_handlers:
            return self.handle_steps_with_auth_handlers(message, step, role, user_state)
        else:
            # Fallback на старую логику (для совместимости)
            return self.handle_steps_fallback(message, step, role, user_state)

    def handle_vacancy_steps(self, message, step, user_state):
        """Обработка шагов создания вакансии"""
        if not self.employer_handlers:
            return False

        steps_map = {
            "vacancy_sphere": self.employer_handlers.process_vacancy_sphere,
            "vacancy_profession": self.employer_handlers.process_vacancy_profession,
            "vacancy_title": self.employer_handlers.process_vacancy_title,
            "vacancy_description": self.employer_handlers.process_vacancy_description,
            "vacancy_gender": self.employer_handlers.process_vacancy_gender,
            "vacancy_language_selection": self.employer_handlers.process_vacancy_language_selection,
            "vacancy_language_level": self.employer_handlers.process_vacancy_language_level,
            "vacancy_language_custom_name": self.employer_handlers.process_vacancy_language_custom_name,
            "vacancy_salary": self.employer_handlers.process_vacancy_salary,
            "vacancy_type": self.employer_handlers.process_vacancy_type,
            "edit_vacancy_title": self.employer_handlers.process_edit_title,
            "edit_vacancy_desc": self.employer_handlers.process_edit_desc,
            "edit_vacancy_languages_prompt": self.employer_handlers.process_edit_languages_prompt,
            "edit_vacancy_salary": self.employer_handlers.process_edit_salary,
            "edit_vacancy_type": self.employer_handlers.process_edit_type,
        }

        if step in steps_map:
            steps_map[step](message)
            return True
        return False

    def handle_profile_steps(self, message, step, user_state):
        """Обработка шагов заполнения профиля"""
        if not self.profile_handlers:
            return False

        steps_map = {
            "education": self.profile_handlers.process_education,
            "profession_sphere": self.profile_handlers.process_profession_sphere,
            "profession_specific": self.profile_handlers.process_profession_specific,
            "language_selection": self.profile_handlers.process_language_selection,
            "language_level": self.profile_handlers.process_language_level,
            "language_custom_name": self.profile_handlers.process_language_custom_name,
            "experience": self.profile_handlers.process_experience,
            "skills": self.profile_handlers.process_skills,
        }

        # Special case from bot_factory.py
        if step == "languages":
            user_state["temp_languages"] = []
            self.profile_handlers.show_language_selection(
                message.chat.id, message.from_user.id, user_state
            )
            return True

        if step in steps_map:
            try:
                steps_map[step](message)
                return True
            except Exception as e:
                logging.error(
                    f"❌ Ошибка обработки шага профиля {step}: {e}", exc_info=True
                )
                self.bot.send_message(
                    message.chat.id,
                    "❌ Произошла ошибка. Попробуйте снова.",
                    reply_markup=keyboards.main_menu(),
                )
                database.clear_user_state(message.from_user.id)
                return True
        return False

    def handle_steps_with_auth_handlers(
        self, message, step, role, user_state
    ):  # noqa: C901
        """Обработка шагов с использованием auth_handlers"""
        if not self.auth_handlers:
            return False

        # Обработка шагов входа и восстановления
        login_steps_map = {
            "login_email": "process_login_email",
            "login_password": "process_login_password",
            "recovery_code": "process_recovery_code",
        }
        if step in login_steps_map:
            # Динамический вызов метода, так как login может быть моком
            method_name = login_steps_map[step]
            if hasattr(self.auth_handlers, "login") and hasattr(
                self.auth_handlers.login, method_name
            ):
                getattr(self.auth_handlers.login, method_name)(message)
                return True

        if step == "recovery":
            self.auth_handlers.process_recovery(message)
            return True

        # Словарь соответствия шагов методам
        if role == "seeker":
            steps_map = {
                "phone": self.auth_handlers.process_seeker_phone,
                "email": self.auth_handlers.process_seeker_email,
                "full_name": self.auth_handlers.process_seeker_name,
                "gender": self.auth_handlers.process_seeker_gender,
                "region": self.auth_handlers.process_seeker_region,
                "city_selection": self.auth_handlers.process_seeker_city_selection,
                "age": self.auth_handlers.finish_seeker_registration,
            }
        elif role == "employer":
            steps_map = {
                "company_name": self.auth_handlers.process_employer_name,
                "phone": self.auth_handlers.process_employer_phone,
                "email": self.auth_handlers.process_employer_email,
                "contact_person": self.auth_handlers.process_employer_contact,
                "region": self.auth_handlers.process_employer_region,
                "city_selection": self.auth_handlers.process_employer_city_selection,
                "business_activity": self.auth_handlers.process_business_activity,
                "business_activity_custom": self.auth_handlers.process_business_activity,
            }
        elif (
            step == "enter_new_value"
            and user_state.get("action") == "edit_seeker_field"
        ):
            # Это обрабатывается в settings.py
            return False
        else:
            return False

        if step in steps_map:
            try:
                steps_map[step](message)
                return True
            except Exception as e:
                logging.error(f"❌ Ошибка обработки шага {step}: {e}", exc_info=True)
                self.bot.send_message(
                    message.chat.id,
                    "❌ Произошла ошибка. Попробуйте снова.",
                    reply_markup=keyboards.main_menu(),
                )
                database.clear_user_state(message.from_user.id)
                return True

        return False

    def handle_steps_fallback(self, message, step, role, user_state):
        """Fallback обработка шагов (старая логика)"""
        if role == "seeker":
            return self.handle_seeker_steps_fallback(message, step, user_state)
        elif role == "employer":
            return self.handle_employer_steps_fallback(message, step, user_state)
        elif step == "recovery":
            return self.handle_recovery_step_fallback(message)
        elif (
            step == "enter_new_value"
            and user_state.get("action") == "edit_seeker_field"
        ):
            # Это обрабатывается в settings.py
            return False

        return False

    def handle_seeker_steps_fallback(self, message, step, user_state):
        """Fallback обработка шагов соискателя"""
        from handlers.auth.seeker_auth import SeekerAuth

        try:
            handler = SeekerAuth(self.bot)

            steps_map = {
                "phone": handler.process_seeker_phone,
                "email": handler.process_seeker_email,
                "full_name": handler.process_seeker_name,
                "gender": handler.process_seeker_gender,
                "region": handler.process_seeker_region,
                "city_selection": handler.process_seeker_city_selection,
                "age": handler.finish_seeker_registration,
            }

            if step in steps_map:
                steps_map[step](message)
                return True
        except Exception as e:
            logging.error(
                f"❌ Fallback ошибка обработки шага соискателя {step}: {e}",
                exc_info=True,
            )

        return False

    def handle_employer_steps_fallback(self, message, step, user_state):
        """Fallback обработка шагов работодателя"""
        from handlers.auth.employer_auth import EmployerAuth

        try:
            handler = EmployerAuth(self.bot)

            steps_map = {
                "company_name": handler.process_employer_name,
                "phone": handler.process_employer_phone,
                "email": handler.process_employer_email,
                "contact_person": handler.process_employer_contact,
                "region": handler.process_employer_region,
                "city_selection": handler.process_employer_city_selection,
                "business_activity": handler.process_business_activity,
                "business_activity_custom": handler.process_business_activity,
            }

            if step in steps_map:
                steps_map[step](message)
                return True
        except Exception as e:
            logging.error(
                f"❌ Fallback ошибка обработки шага работодателя {step}: {e}",
                exc_info=True,
            )

        return False

    def handle_recovery_step_fallback(self, message):
        """Fallback обработка восстановления пароля"""
        from handlers.auth.login_auth import LoginAuth

        try:
            handler = LoginAuth(self.bot)
            handler.process_recovery(message)
            return True
        except Exception as e:
            logging.error(
                f"❌ Fallback ошибка обработки восстановления: {e}", exc_info=True
            )

        return False

    def cancel_current_step(self, user_id, chat_id):  # noqa: C901
        """Отмена текущего шага"""
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        if not user_state:
            self.bot.send_message(
                chat_id,
                get_text_by_lang("action_cancelled", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.main_menu(lang=lang),
            )
            return

        # Проверяем, какое действие отменяется
        action = user_state.get("action")
        step = user_state.get("step")

        # Определяем, куда вернуть пользователя
        if action == "edit_seeker_field" or step == "enter_new_value":
            database.clear_user_state(user_id)
            # Возвращаем в меню соискателя
            self.bot.send_message(
                chat_id,
                get_text_by_lang("edit_cancelled", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.seeker_main_menu(lang=lang),
            )
        elif isinstance(step, str) and step.startswith("vacancy_"):
            database.clear_user_state(user_id)
            # Отмена создания вакансии
            self.bot.send_message(
                chat_id,
                get_text_by_lang("vacancy_creation_cancelled", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.employer_main_menu(lang=lang),
            )
        elif step in [
            "admin_broadcast_message",
            "admin_broadcast_confirm",
            "admin_reply_message",
        ]:
            database.clear_user_state(user_id)
            self.bot.send_message(
                chat_id,
                get_text_by_lang("action_cancelled", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.admin_menu(),
            )
        elif step in ["admin_search_user", "admin_write_user"]:
            database.clear_user_state(user_id)
            self.bot.send_message(
                chat_id,
                get_text_by_lang("action_cancelled", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.admin_users_menu(),
            )
        elif step in ["support_bug_report", "support_complaint", "reply_to_admin"]:
            database.clear_user_state(user_id)
            user_data = database.get_user_by_id(user_id)
            markup = keyboards.main_menu(lang=lang)
            if user_data:
                if "full_name" in user_data:
                    markup = keyboards.seeker_main_menu(lang=lang)
                elif "company_name" in user_data:
                    markup = keyboards.employer_main_menu(lang=lang)

            self.bot.send_message(
                chat_id,
                get_text_by_lang("action_cancelled", lang),
                parse_mode="Markdown",
                reply_markup=markup,
            )
        elif step in [
            "captcha",
            "phone",
            "email",
            "full_name",
            "region",
            "city_selection",
            "age",
            "company_name",
            "contact_person",
            "business_activity",
            "gender",
        ]:
            # Регистрация - возврат в главное меню
            msg = get_text_by_lang("registration_cancelled", lang)
            if self.auth_handlers and self.auth_handlers.role:
                self.auth_handlers.role.cancel_registration(chat_id, user_id, msg)
            else:
                database.clear_user_state(user_id)
                self.bot.send_message(
                    chat_id,
                    f"❌ {msg}",
                    parse_mode="Markdown",
                    reply_markup=keyboards.main_menu(lang=lang),
                )
        else:
            database.clear_user_state(user_id)
            # По умолчанию - главное меню
            self.bot.send_message(
                chat_id,
                get_text_by_lang("action_cancelled", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.main_menu(lang=lang),
            )
