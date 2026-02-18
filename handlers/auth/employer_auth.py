# handlers/auth/employer_auth.py
import logging

from telebot import types

import database
import keyboards
import utils
from localization import (
    PROFESSION_SPHERES_KEYS,
    REGIONS,
    get_text_by_lang,
    get_user_language,
)


class EmployerAuth:
    def __init__(self, bot):
        self.bot = bot

    def process_employer_name(self, message):
        """Обработка названия компании"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            self.cancel_employer_registration(
                message.chat.id,
                user_id,
                get_text_by_lang("registration_cancelled", lang),
            )
            return

        if not user_state or user_state.get("step") != "company_name":
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла!",
                reply_markup=keyboards.main_menu(),
            )
            return

        company_name = message.text.strip()

        if len(company_name) < 2:
            self.bot.send_message(
                message.chat.id,
                "❌ Название компании слишком короткое!\nВведите название:",
                reply_markup=keyboards.cancel_keyboard(lang=lang),
            )
            return

        logging.info(f"🔍 Проверка уникальности компании: {company_name}")

        # Проверяем уникальность названия компании (регистронезависимо)
        is_exist = database.execute_query(
            "SELECT id FROM employers WHERE LOWER(company_name) = ?",
            (company_name.lower(),),
            fetchone=True,
        )
        if is_exist:
            logging.warning(f"❌ Компания {company_name} уже зарегистрирована!")
            self.bot.send_message(
                message.chat.id,
                "❌ Компания с таким названием уже зарегистрирована! Пожалуйста, укажите другое название.",
                reply_markup=keyboards.cancel_keyboard(lang=lang),
            )
            return

        user_state["registration_data"]["company_name"] = company_name
        user_state["step"] = "phone"
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            f"{get_text_by_lang('prompt_phone_company', lang)}\n\n"
            + utils.show_phone_format_example(lang=lang),
            parse_mode="Markdown",
            reply_markup=keyboards.cancel_keyboard(lang=lang),
        )

    def process_employer_phone(self, message):
        """Обработка телефона компании"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            self.cancel_employer_registration(
                message.chat.id,
                user_id,
                get_text_by_lang("registration_cancelled", lang),
            )
            return

        if not user_state or user_state.get("step") != "phone":
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла!",
                reply_markup=keyboards.main_menu(),
            )
            return

        phone = message.text.strip()

        if not utils.is_valid_uzbek_phone(phone):
            self.bot.send_message(
                message.chat.id,
                f"{get_text_by_lang('invalid_phone_format', lang)}\n\n"
                + utils.show_phone_format_example(lang=lang)
                + f"\n\n{get_text_by_lang('prompt_enter_number', lang)}",
                parse_mode="Markdown",
                reply_markup=keyboards.cancel_keyboard(lang=lang),
            )
            return

        formatted_phone = utils.format_phone(phone)
        clean_phone = formatted_phone.lstrip("+")  # Версия без плюса

        logging.info(f"🔍 Проверка уникальности телефона: {formatted_phone}")

        # Проверяем уникальность телефона (в обеих таблицах)
        is_exist_employer = database.execute_query(
            "SELECT id FROM employers WHERE phone = ? OR phone = ?",
            (formatted_phone, clean_phone),
            fetchone=True,
        )
        is_exist_seeker = database.execute_query(
            "SELECT id FROM job_seekers WHERE phone = ? OR phone = ?",
            (formatted_phone, clean_phone),
            fetchone=True,
        )

        if is_exist_employer or is_exist_seeker:
            logging.warning(f"❌ Телефон {formatted_phone} уже занят!")
            self.bot.send_message(
                message.chat.id,
                "❌ Данный номер телефона уже зарегестрирован! Пожалуйста укажите другой номер телефона.",
                reply_markup=keyboards.cancel_keyboard(lang=lang),
            )
            return

        user_state["registration_data"]["phone"] = formatted_phone
        user_state["step"] = "email"
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            f"{get_text_by_lang('phone_accepted', lang).format(phone=formatted_phone)}\n\n"
            f"{get_text_by_lang('prompt_email_company', lang)}",
            reply_markup=keyboards.cancel_keyboard(lang=lang),
        )

    def process_employer_email(self, message):
        """Обработка email компании"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            self.cancel_employer_registration(
                message.chat.id,
                user_id,
                get_text_by_lang("registration_cancelled", lang),
            )
            return

        if not user_state or user_state.get("step") != "email":
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла!",
                reply_markup=keyboards.main_menu(),
            )
            return

        email = message.text.strip().lower()

        if not utils.is_valid_email(email):
            self.bot.send_message(
                message.chat.id,
                "❌ Неверный формат email!\nВведите email:",
                reply_markup=keyboards.cancel_keyboard(lang=lang),
            )
            return

        logging.info(f"🔍 Проверка уникальности email: {email}")

        # Проверяем уникальность email (в обеих таблицах)
        is_exist_employer = database.execute_query(
            "SELECT id FROM employers WHERE LOWER(email) = ?", (email,), fetchone=True
        )
        is_exist_seeker = database.execute_query(
            "SELECT id FROM job_seekers WHERE LOWER(email) = ?", (email,), fetchone=True
        )

        if is_exist_employer or is_exist_seeker:
            logging.warning(f"❌ Email {email} уже занят!")
            self.bot.send_message(
                message.chat.id,
                "❌ Данный email уже зарегестрирован! Пожалуйста укажите другой email.",
                reply_markup=keyboards.cancel_keyboard(lang=lang),
            )
            return

        user_state["registration_data"]["email"] = email
        # Генерируем случайный пароль, так как шаг ввода пароля убран
        user_state["registration_data"]["password"] = utils.generate_random_string(16)
        user_state["step"] = "contact_person"
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            f"{get_text_by_lang('email_accepted', lang)}\n\n"
            f"{get_text_by_lang('prompt_contact_person', lang)}",
            reply_markup=keyboards.cancel_keyboard(lang=lang),
        )

    def process_employer_contact(self, message):
        """Обработка контактного лица"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            self.cancel_employer_registration(
                message.chat.id,
                user_id,
                get_text_by_lang("registration_cancelled", lang),
            )
            return

        if not user_state or user_state.get("step") != "contact_person":
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла!",
                reply_markup=keyboards.main_menu(),
            )
            return

        contact_person = message.text.strip()
        user_state["registration_data"]["contact_person"] = contact_person
        user_state["step"] = "region"
        database.set_user_state(user_id, user_state)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(*[types.KeyboardButton(reg) for reg in REGIONS[lang].keys()])
        markup.row(types.KeyboardButton(get_text_by_lang("cancel_button", lang)))

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang("prompt_region_company", lang),
            reply_markup=markup,
        )

    def process_employer_region(self, message):
        """Обработка выбора региона работодателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        if utils.cancel_request(message.text):
            self.cancel_employer_registration(
                message.chat.id,
                user_id,
                get_text_by_lang("registration_cancelled", lang),
            )
            return

        if not user_state or user_state.get("step") != "region":
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла!",
                reply_markup=keyboards.main_menu(),
            )
            return

        region = message.text.strip()
        if region not in REGIONS[lang]:
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("select_from_list", lang),
                reply_markup=None,
            )
            return

        user_state["registration_data"]["region"] = region
        user_state["step"] = "city_selection"
        database.set_user_state(user_id, user_state)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        cities = [types.KeyboardButton(city) for city in REGIONS[lang][region]]
        markup.add(*cities)
        markup.row(
            types.KeyboardButton(get_text_by_lang("back_button", lang)),
            types.KeyboardButton(get_text_by_lang("cancel_button", lang)),
        )

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang("prompt_city_in_region", lang).format(region=region),
            reply_markup=markup,
        )

    def process_employer_city_selection(self, message):
        """Обработка выбора города работодателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        if message.text == get_text_by_lang("back_button", lang):
            user_state["step"] = "region"
            database.set_user_state(user_id, user_state)

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(*[types.KeyboardButton(reg) for reg in REGIONS[lang].keys()])
            markup.row(types.KeyboardButton(get_text_by_lang("cancel_button", lang)))

            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("prompt_region_company", lang),
                reply_markup=markup,
            )
            return

        if utils.cancel_request(message.text):
            self.cancel_employer_registration(
                message.chat.id,
                user_id,
                get_text_by_lang("registration_cancelled", lang),
            )
            return

        if not user_state or user_state.get("step") != "city_selection":
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла!",
                reply_markup=keyboards.main_menu(),
            )
            return

        city = message.text.strip()
        user_state["registration_data"]["city"] = city
        user_state["step"] = "business_activity"
        database.set_user_state(user_id, user_state)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for sphere_key in PROFESSION_SPHERES_KEYS.keys():
            markup.add(types.KeyboardButton(get_text_by_lang(sphere_key, lang)))
        markup.add(types.KeyboardButton(get_text_by_lang("other_button", lang)))
        markup.add(types.KeyboardButton(get_text_by_lang("cancel_button", lang)))

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang("prompt_business_activity", lang),
            reply_markup=markup,
        )

    def process_business_activity(self, message):
        """Обработка рода деятельности компании"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            self.cancel_employer_registration(
                message.chat.id,
                user_id,
                get_text_by_lang("registration_cancelled", lang),
            )
            return

        step = user_state.get("step")
        if not user_state or step not in [
            "business_activity",
            "business_activity_custom",
        ]:
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла!",
                reply_markup=keyboards.main_menu(),
            )
            return

        text = message.text.strip()

        if step == "business_activity":
            if text == get_text_by_lang("other_button", lang):
                user_state["step"] = "business_activity_custom"
                database.set_user_state(user_id, user_state)
                self.bot.send_message(
                    message.chat.id,
                    "✍️ Введите сферу деятельности вручную:",
                    reply_markup=keyboards.cancel_keyboard(lang=lang),
                )
                return
            business_activity = text
        else:
            business_activity = text
            if len(business_activity) < 2:
                self.bot.send_message(
                    message.chat.id,
                    "❌ Род деятельности слишком короткий!\nВведите род деятельности:",
                    reply_markup=keyboards.cancel_keyboard(lang=lang),
                )
                return

        # Финальная проверка перед регистрацией
        existing_user = database.get_user_by_id(user_id)
        if existing_user:
            self.bot.send_message(
                message.chat.id,
                "❌ *Вы уже зарегистрированы!*\n\n" "Войдите в аккаунт.",
                parse_mode="Markdown",
                reply_markup=keyboards.main_menu(),
            )
            database.clear_user_state(user_id)
            return

        # Получаем данные регистрации
        reg_data = user_state["registration_data"]
        reg_data["telegram_id"] = user_id
        reg_data["business_activity"] = business_activity
        reg_data["language_code"] = lang
        reg_data["description"] = "Описание не указано"  # Добавляем дефолтное описание

        # Сохраняем в базу данных
        success = database.create_employer(reg_data)

        if success:
            # Обновляем язык в БД явно
            database.execute_query(
                "UPDATE employers SET language_code = ? WHERE telegram_id = ?",
                (lang, user_id),
                commit=True,
            )

            # Очищаем состояние
            database.clear_user_state(user_id)

            # Итоговое сообщение
            text = (
                f"{get_text_by_lang('employer_registration_complete', lang)}\n\n"
                f"🏢 *Компания:* {utils.escape_markdown(reg_data['company_name'])}\n"
                f"🏙️ *Город:* {reg_data['city']}\n"
                f"📋 *Род деятельности:* {reg_data['business_activity']}\n"
                f"👤 *Контакт:* {utils.escape_markdown(reg_data['contact_person'])}\n"
                f"📞 *Телефон:* {utils.escape_markdown(reg_data['phone'])}\n"
                f"📧 *Email:* {utils.escape_markdown(reg_data['email'])}\n\n"
                f"Используйте меню для поиска сотрудников:"
            )
            self.bot.send_message(
                message.chat.id,
                text,
                parse_mode="Markdown",
                reply_markup=keyboards.employer_main_menu(),
            )
        else:
            self.bot.send_message(
                message.chat.id,
                "❌ Ошибка регистрации! Возможно, вы уже зарегистрированы.",
                parse_mode="Markdown",
                reply_markup=keyboards.main_menu(),
            )
            database.clear_user_state(user_id)

    def cancel_employer_registration(self, chat_id, user_id, message_text):
        """Отмена регистрации работодателя"""
        lang = get_user_language(user_id)
        database.clear_user_state(user_id)
        self.bot.send_message(
            chat_id,
            f"❌ *{message_text}*",
            parse_mode="Markdown",
            reply_markup=keyboards.main_menu(lang=lang),
        )
