from typing import Any

from telebot import types

import database
import keyboards
import utils
from localization import (
    LANGUAGES_I18N,
    PROFESSION_SPHERES_KEYS,
    TRANSLATIONS,
    get_text_by_lang,
    get_user_language,
)


class SeekerSettingsMixin:
    bot: Any
    handle_settings_menu: Any

    def handle_seeker_setting(self, message: types.Message, field: str) -> None:
        """Обработка нажатия на кнопку настройки соискателя"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)

        if not user_data or 'full_name' not in user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала войдите как соискатель!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        # Определяем ключ перевода для названия поля
        field_to_translation_key = {
            'profession': 'btn_profession',
            'education': 'btn_education',
            'experience': 'btn_experience',
            'skills': 'btn_skills',
            'languages': 'btn_languages',
            'gender': 'btn_gender'
        }
        translation_key = field_to_translation_key.get(field, field)
        field_display = get_text_by_lang(translation_key, lang)

        current_value = user_data.get(field, 'Не указано')

        # Сохраняем состояние для следующего шага
        database.set_user_state(user_id, {
            'action': 'edit_seeker_field',
            'field': field,
            'field_display': field_display,
            'current_value': current_value
        })

        # Показываем подменю
        # Проверяем, что значение не является одним из "пустых" значений по умолчанию
        empty_values = ['Не указана', 'Не указано', 'Не указаны', 'Нет опыта', None, '']

        if current_value and current_value not in empty_values:
            message_text = f"{field_display}\n\n*{get_text_by_lang('current_value', lang)}*\n" \
                           f"{current_value}\n\n{get_text_by_lang('choose_action', lang)}"
        else:
            message_text = f"{field_display}\n\n{get_text_by_lang('field_not_set', lang)}\n\n" \
                           f"{get_text_by_lang('choose_action', lang)}"

        self.bot.send_message(
            message.chat.id,
            message_text,
            parse_mode='Markdown',
            reply_markup=keyboards.seeker_submenu(field, current_value, lang=lang)
        )

    def handle_seeker_submenu_action(self, message):
        """Обработка действий в подменю соискателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        if not user_state or user_state.get('action') != 'edit_seeker_field':
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла!",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        field = user_state['field']
        field_display = user_state['field_display']
        current_value = user_state['current_value']

        # Проверяем кнопки на всех языках
        all_back_btns = [d.get('btn_back_settings', '') for d in TRANSLATIONS.values()]
        all_edit_btns = [d.get('edit_button', '') for d in TRANSLATIONS.values()]
        all_add_btns = [d.get('add_button', '') for d in TRANSLATIONS.values()]

        if message.text in all_back_btns:
            database.clear_user_state(user_id)
            self.handle_settings_menu(message)
            return

        elif message.text in all_edit_btns or message.text in all_add_btns:
            # Если это профессия, запускаем выбор сферы
            if field == 'profession':
                lang = get_user_language(user_id)
                user_state['step'] = 'edit_seeker_profession_sphere'
                database.set_user_state(user_id, user_state)

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                for sphere_key in PROFESSION_SPHERES_KEYS.keys():
                    markup.add(types.KeyboardButton(get_text_by_lang(sphere_key, lang)))
                markup.add(types.KeyboardButton("Другое"))
                markup.add(types.KeyboardButton("❌ Отмена"))

                self.bot.send_message(
                    message.chat.id,
                    "📂 *Выберите сферу деятельности:*",
                    parse_mode='Markdown',
                    reply_markup=markup
                )
                return

            # Если это языки, запускаем интерактивный выбор
            if field == 'languages':
                user_state['step'] = 'language_selection'
                user_state['source'] = 'settings'
                user_state['temp_languages'] = []
                lang = get_user_language(user_id)
                database.set_user_state(user_id, user_state)

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                for btn_text in LANGUAGES_I18N[lang].keys():
                    markup.add(types.KeyboardButton(btn_text))
                markup.add(types.KeyboardButton("🌐 Другой"))
                markup.add(types.KeyboardButton("Пропустить"))
                markup.add(types.KeyboardButton("❌ Отмена"))

                self.bot.send_message(message.chat.id,
                                      "🗣 *Какими языками вы владеете?*\n\nВыберите язык из списка.",
                                      parse_mode='Markdown', reply_markup=markup)
                return

            # Если это пол, запускаем выбор
            if field == 'gender':
                user_state['step'] = 'edit_seeker_gender'
                database.set_user_state(user_id, user_state)

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                markup.add(
                    types.KeyboardButton(get_text_by_lang('gender_male', lang)),
                    types.KeyboardButton(get_text_by_lang('gender_female', lang))
                )
                markup.row(types.KeyboardButton(get_text_by_lang('cancel_button', lang)))
                self.bot.send_message(message.chat.id, get_text_by_lang('prompt_gender', lang), reply_markup=markup)
                return

            # Устанавливаем состояние для ввода нового значения
            user_state['step'] = 'enter_new_value'
            database.set_user_state(user_id, user_state)

            if message.text in all_edit_btns:
                prompt = f"{get_text_by_lang('enter_new_value', lang)} {field_display}:\n\n" \
                         f"{get_text_by_lang('current_value', lang)} *{current_value}*"
            else:
                prompt = f"{get_text_by_lang('enter_new_value', lang)} {field_display}:"

            if field == 'phone':
                markup = keyboards.contact_request_keyboard(lang=lang)
            else:
                markup = keyboards.cancel_keyboard(lang=lang)

            self.bot.send_message(
                message.chat.id,
                f"✏️ *{field_display}*\n\n"
                f"{prompt}\n\n"
                f"Используйте /cancel или кнопку '❌ Отмена' для отмены.",
                parse_mode='Markdown',
                reply_markup=markup
            )
            return

        else:
            # Неизвестное действие, возвращаем в подменю
            self.bot.send_message(
                message.chat.id,
                f"❌ Неизвестное действие!\n\n"
                f"Возврат в {field_display}...",
                parse_mode='Markdown',
                reply_markup=keyboards.seeker_submenu(field, current_value, lang=lang)
            )

    def process_seeker_profession_sphere(self, message):
        """Обработка выбора сферы деятельности в настройках"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        if utils.cancel_request(message.text):
            database.clear_user_state(user_id)
            self.bot.send_message(message.chat.id, "❌ Изменение отменено", reply_markup=keyboards.seeker_main_menu())
            return

        sphere = message.text.strip()

        selected_sphere_key = None
        for key in PROFESSION_SPHERES_KEYS.keys():
            if get_text_by_lang(key, lang) == sphere:
                selected_sphere_key = key
                break

        # Если выбрано "Другое" или сфера не из списка (ручной ввод)
        if sphere == "Другое" or not selected_sphere_key:
            user_state['step'] = 'enter_new_value'
            database.set_user_state(user_id, user_state)

            self.bot.send_message(
                message.chat.id,
                "🎯 *Введите название вашей профессии:*",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        # Показываем профессии
        user_state['step'] = 'edit_seeker_profession_specific'
        database.set_user_state(user_id, user_state)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for prof_key in PROFESSION_SPHERES_KEYS[selected_sphere_key]:
            markup.add(types.KeyboardButton(get_text_by_lang(prof_key, lang)))
        markup.add(types.KeyboardButton("Другое"))
        markup.add(types.KeyboardButton("⬅️ Назад"))

        self.bot.send_message(
            message.chat.id,
            f"🎯 *Выберите профессию в сфере {sphere}:*\n"
            "Или введите свое название, если его нет в списке.",
            parse_mode='Markdown',
            reply_markup=markup
        )

    def process_seeker_profession_specific(self, message):
        """Обработка выбора конкретной профессии в настройках"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        if message.text == "⬅️ Назад":
            user_state['step'] = 'edit_seeker_profession_sphere'
            database.set_user_state(user_id, user_state)

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for sphere_key in PROFESSION_SPHERES_KEYS.keys():
                markup.add(types.KeyboardButton(get_text_by_lang(sphere_key, lang)))
            markup.add(types.KeyboardButton("Другое"))
            markup.add(types.KeyboardButton("❌ Отмена"))

            self.bot.send_message(message.chat.id, "📂 *Выберите сферу деятельности:*", parse_mode='Markdown',
                                  reply_markup=markup)
            return

        if utils.cancel_request(message.text):
            database.clear_user_state(user_id)
            self.bot.send_message(message.chat.id, "❌ Изменение отменено", reply_markup=keyboards.seeker_main_menu())
            return

        profession = message.text.strip()

        if profession == "Другое":
            user_state['step'] = 'enter_new_value'
            database.set_user_state(user_id, user_state)
            self.bot.send_message(
                message.chat.id,
                "✍️ *Введите название вашей профессии вручную:*",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        if utils.contains_profanity(profession):
            self.bot.send_message(message.chat.id, "❌ Название содержит недопустимые слова.")
            return

        # Try to find profession key
        selected_prof_key = None
        for sphere_key, prof_keys in PROFESSION_SPHERES_KEYS.items():
            for key in prof_keys:
                if get_text_by_lang(key, lang) == profession:
                    selected_prof_key = key
                    break
            if selected_prof_key: break

        # Сохраняем
        if database.update_seeker_profile(telegram_id=user_id,
                                          profession=selected_prof_key if selected_prof_key else profession):
            database.clear_user_state(
                user_id
            )

            self.bot.send_message(
                message.chat.id,
                f"✅ Профессия успешно обновлена!\n\nНовое значение: *{profession}*",
                parse_mode='Markdown',
                reply_markup=keyboards.seeker_main_menu()
            )
        else:
            self.bot.send_message(message.chat.id, "❌ Ошибка при обновлении.")

    def process_seeker_gender_update(self, message):
        """Обработка выбора пола в настройках"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)

        if utils.cancel_request(message.text):
            database.clear_user_state(user_id)
            self.bot.send_message(message.chat.id, "❌ Изменение отменено", reply_markup=keyboards.seeker_main_menu(lang))
            return

        gender_text = message.text.strip()
        gender = None
        if gender_text == get_text_by_lang('gender_male', lang):
            gender = 'male'
        elif gender_text == get_text_by_lang('gender_female', lang):
            gender = 'female'
        else:
            self.bot.send_message(message.chat.id, get_text_by_lang('select_from_list', lang))
            return

        if database.update_seeker_profile(
                telegram_id=user_id, gender=gender
        ):
            database.clear_user_state(user_id)
            self.bot.send_message(
                message.chat.id,
                f"✅ {get_text_by_lang('btn_gender', lang)} {get_text_by_lang('languages_updated', lang).split(' ')[1]}!\n\n{get_text_by_lang('current_value', lang)} *{gender_text}*",
                parse_mode='Markdown',
                reply_markup=keyboards.seeker_main_menu(lang)
            )
        else:
            self.bot.send_message(message.chat.id, "❌ Ошибка при обновлении.")

    def process_seeker_field_update(self, message):
        """Обработка ввода нового значения для поля соискателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            database.clear_user_state(user_id)
            self.bot.send_message(  # noqa
                message.chat.id,
                "❌ Изменение отменено",
                parse_mode='Markdown',
                reply_markup=keyboards.seeker_main_menu()
            )
            return

        if not user_state or user_state.get('step') != 'enter_new_value':
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла!",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        if message.contact:
            new_value = message.contact.phone_number
        else:
            new_value = message.text.strip()

        return self._save_seeker_field(message, user_id, user_state, new_value)

    def _save_seeker_field(self, message, user_id, user_state, new_value):
        field = user_state['field']
        field_display = user_state['field_display']

        # Валидация специфичных полей
        if field == 'phone':
            if not utils.is_valid_uzbek_phone(new_value):
                self.bot.send_message(
                    message.chat.id,
                    "❌ Неверный формат номера!\n\n" + utils.show_phone_format_example(),
                    parse_mode='Markdown',
                    reply_markup=keyboards.cancel_keyboard()
                )
                return
            new_value = utils.format_phone(new_value)
        elif field == 'email':
            if not utils.is_valid_email(new_value):
                self.bot.send_message(message.chat.id, "❌ Неверный формат email!\n\nПопробуйте еще раз:",
                                      reply_markup=keyboards.cancel_keyboard())
                return

        if not new_value or len(new_value) < 2:
            self.bot.send_message(
                message.chat.id,
                f"❌ Значение слишком короткое!\n\n"
                f"Введите новое значение для {field_display.lower()}:",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        if len(new_value) > 500:
            self.bot.send_message(
                message.chat.id,
                f"❌ Значение слишком длинное! Максимум 500 символов.\n\n"
                f"Введите новое значение для {field_display.lower()}:",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        if utils.contains_profanity(new_value):
            self.bot.send_message(message.chat.id, "❌ Значение содержит недопустимые слова.")
            return

        # Обновляем поле в базе данных
        success = database.update_seeker_profile(
            telegram_id=user_id,
            **{field: new_value}
        )

        if success:
            database.clear_user_state(user_id)
            self.bot.send_message(
                message.chat.id,  # noqa
                f"✅ {field_display} успешно обновлено!\n\n"
                f"Новое значение: *{new_value}*",
                parse_mode='Markdown',
                reply_markup=keyboards.seeker_main_menu()
            )
        else:
            self.bot.send_message(
                message.chat.id,
                f"❌ Ошибка при обновлении {field_display}!\n\n"
                f"Попробуйте еще раз:",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )

    def handle_status_settings(self, message):
        """Меню настройки статуса"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)

        if not user_data or 'full_name' not in user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала войдите как соискатель!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        status = user_data.get('status', 'active')
        status_text = get_text_by_lang('status_active', lang) if status == 'active' else \
            get_text_by_lang('status_inactive', lang)

        self.bot.send_message(
            message.chat.id,
            f"{get_text_by_lang('btn_status', lang)}\n\n"
            f"{get_text_by_lang('current_value', lang)} *{status_text}*\n\n"
            f"{get_text_by_lang('choose_action', lang)}",
            parse_mode='Markdown',
            reply_markup=keyboards.seeker_status_menu(lang=lang)
        )

    def set_seeker_status(self, message, status_code):
        """Установка статуса соискателя"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)

        success = database.update_seeker_profile(
            telegram_id=user_id,
            status=status_code
        )

        status_text = get_text_by_lang('status_active', lang) if status_code == 'active' else \
            get_text_by_lang('status_inactive', lang)

        if success:
            self.bot.send_message(
                message.chat.id,
                f"✅ Статус успешно изменен!\n\n"
                f"Новый статус: *{status_text}*",  # noqa
                parse_mode='Markdown',
                reply_markup=keyboards.settings_menu('seeker', lang=lang)
            )
        else:
            self.bot.send_message(
                message.chat.id,
                "❌ Ошибка обновления статуса.",
                reply_markup=keyboards.settings_menu('seeker', lang=lang)
            )