from typing import Any

from telebot import types

import database
import keyboards
import utils
from localization import TRANSLATIONS, get_text_by_lang, get_user_language


class EmployerSettingsMixin:
    bot: Any
    handle_delete_account: Any
    handle_change_language: Any

    def handle_employer_action(self, message: types.Message) -> None:
        """Обработка действий работодателя"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)

        if not user_data or "company_name" not in user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала войдите как работодатель!*",
                parse_mode="Markdown",
                reply_markup=keyboards.main_menu(),
            )
            return

        all_del_company_btns = [
            d.get("btn_delete_company", "") for d in TRANSLATIONS.values()
        ]
        all_back_btns = [
            d.get("btn_back_to_panel_menu", "") for d in TRANSLATIONS.values()
        ]

        if message.text in all_del_company_btns:
            self.handle_delete_account(message)
        elif message.text == get_text_by_lang("change_language", lang):
            self.handle_change_language(message)
        elif message.text in all_back_btns:
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("main_menu", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.employer_main_menu(lang=lang),
            )
        else:
            self.bot.send_message(
                message.chat.id,
                "❌ Неизвестное действие",
                parse_mode="Markdown",
                reply_markup=keyboards.employer_main_menu(),
            )

    def handle_employer_setting(self, message: types.Message, field: str) -> None:
        """Обработка нажатия на кнопку настройки работодателя"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data or "company_name" not in user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала войдите как работодатель!*",
                parse_mode="Markdown",
                reply_markup=keyboards.main_menu(),
            )
            return

        field_names = {
            "company_name": "Название компании",
            "contact_person": "Контактное лицо",
            "description": "Описание компании",
            "business_activity": "Род деятельности",
            "phone": "Телефон",
            "email": "Email",
            "city": "Город",
        }

        field_display = field_names.get(field, field)
        current_value = user_data.get(field, "Не указано")

        database.set_user_state(
            user_id,
            {
                "action": "edit_employer_field",
                "field": field,
                "field_display": field_display,
                "current_value": current_value,
                "step": "enter_new_value",
            },
        )

        if field == "phone":
            markup = keyboards.contact_request_keyboard(lang=get_user_language(user_id))
        else:
            markup = keyboards.cancel_keyboard()

        self.bot.send_message(
            message.chat.id,
            f"✏️ *{field_display}*\n\nВведите новое значение:",
            parse_mode="Markdown",
            reply_markup=markup,
        )

    def process_employer_field_update(self, message):
        """Обработка ввода нового значения для поля работодателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if utils.cancel_request(message.text):
            database.clear_user_state(user_id)
            self.bot.send_message(
                message.chat.id,
                "❌ Изменение отменено",
                parse_mode="Markdown",
                reply_markup=keyboards.employer_main_menu(),
            )
            return

        if (
            not user_state
            or user_state.get("step") != "enter_new_value"
            or user_state.get("action") != "edit_employer_field"
        ):
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла!",
                parse_mode="Markdown",
                reply_markup=keyboards.main_menu(),
            )
            return

        field = user_state["field"]
        field_display = user_state.get("field_display", "Поле")

        if message.contact:
            new_value = message.contact.phone_number
        else:
            new_value = message.text.strip()

        # Валидация специфичных полей
        if field == "phone":
            if not utils.is_valid_uzbek_phone(new_value):
                self.bot.send_message(
                    message.chat.id,
                    "❌ Неверный формат номера!\n\n"
                    + utils.show_phone_format_example(),
                    parse_mode="Markdown",
                    reply_markup=keyboards.cancel_keyboard(),
                )
                return
            new_value = utils.format_phone(new_value)
        elif field == "email":
            if not utils.is_valid_email(new_value):
                self.bot.send_message(
                    message.chat.id,
                    "❌ Неверный формат email!\n\nПопробуйте еще раз:",
                    reply_markup=keyboards.cancel_keyboard(),
                )
                return

        if utils.contains_profanity(new_value):
            self.bot.send_message(
                message.chat.id, "❌ Значение содержит недопустимые слова."
            )
            return  # noqa

        success = database.update_employer_profile(
            telegram_id=user_id, **{field: new_value}
        )

        if success:
            database.clear_user_state(user_id)
            self.bot.send_message(
                message.chat.id,
                f"✅ {field_display} успешно обновлено!",
                parse_mode="Markdown",
                reply_markup=keyboards.employer_main_menu(),
            )
        else:
            self.bot.send_message(
                message.chat.id,
                f"❌ Ошибка при обновлении {field_display}!",
                parse_mode="Markdown",
            )
