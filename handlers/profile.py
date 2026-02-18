# handlers/profile.py
import json

from telebot import types

import database
import keyboards
import utils
from localization import (
    LANGUAGES_I18N,
    LEVELS_I18N,
    PROFESSION_SPHERES_KEYS,
    get_text_by_lang,
    get_user_language,
)


class ProfileHandlers:
    def __init__(self, bot):
        self.bot = bot

    def register(self, bot):
        bot.register_message_handler(self.handle_complete_profile, func=lambda m: m.text in ['📝 Заполнить профиль', '🏢 Заполнить профиль компании'])

    def start_profile_setup(self, message, user_data):
        """Начало заполнения профиля после регистрации"""
        user_id = message.from_user.id
        lang = user_data.get('language_code') or get_user_language(user_id)

        # Определяем роль пользователя
        role = 'seeker' if 'full_name' in user_data else 'employer'

        # Обновляем язык в БД, чтобы убедиться, что он сохранен
        if user_data.get('language_code'):
            table = 'job_seekers' if role == 'seeker' else 'employers'
            database.execute_query(f"UPDATE {table} SET language_code = ? WHERE telegram_id = ?",  # nosec
                                   (lang, user_id), commit=True)

        # Устанавливаем состояние для заполнения профиля
        database.set_user_state(user_id, {
            'step': 'education',
            'role': role,
            'profile_data': {},
            'language_code': lang
        })

        if role == 'seeker':  # Соискатель
            self.bot.send_message(
                message.chat.id,
                f"{get_text_by_lang('registration_complete', lang)}\n\n"
                f"{get_text_by_lang('prompt_education', lang)}",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard(lang=lang)
            )
        else:  # Работодатель - СРАЗУ В МЕНЮ, без доп вопросов
            database.clear_user_state(user_id)
            summary_text = (
                f"{get_text_by_lang('employer_registration_complete', lang)}\n\n"
                f"{get_text_by_lang('reg_summary_company', lang)} *{user_data.get('company_name', '')}*\n"
                f"{get_text_by_lang('reg_summary_city', lang)} {user_data.get('city', '')}\n"
                f"{get_text_by_lang('reg_summary_activity', lang)} {user_data.get('business_activity', '')}\n"
                f"{get_text_by_lang('reg_summary_contact', lang)} *{user_data.get('contact_person', '')}*\n"
                f"{get_text_by_lang('reg_summary_phone', lang)} {user_data.get('phone', '')}\n"
                f"{get_text_by_lang('reg_summary_email', lang)} {user_data.get('email', '')}\n\n"
                f"{get_text_by_lang('use_search_menu_employer', lang)}"
            )
            self.bot.send_message(
                message.chat.id,
                summary_text,
                parse_mode='Markdown',
                reply_markup=keyboards.employer_main_menu(lang=lang)
            )

    def process_education(self, message):
        """Обработка образования"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return

        if not user_state or user_state.get('step') != 'education':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        if message.text.strip().lower() == get_text_by_lang('skip_button_text', lang).lower():
            education = get_text_by_lang('education_not_specified', lang)
        else:
            education = message.text.strip()
            # Проверка ввода
            if len(education) < 2:
                self.bot.send_message(
                    message.chat.id,
                    get_text_by_lang('education_too_short', lang),
                    reply_markup=keyboards.cancel_keyboard(lang=lang)
                )
                return

            if utils.contains_profanity(education):
                self.bot.send_message(message.chat.id, get_text_by_lang('profanity_detected', lang))
                return

        user_state['profile_data']['education'] = education

        if user_state['role'] == 'seeker':
            user_state['step'] = 'profession_sphere'
            database.set_user_state(user_id, user_state)

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for sphere_key in PROFESSION_SPHERES_KEYS.keys():
                markup.add(types.KeyboardButton(get_text_by_lang(sphere_key, lang)))
            markup.add(types.KeyboardButton(get_text_by_lang('other_button', lang)))
            markup.add(types.KeyboardButton(get_text_by_lang('cancel_button', lang)))

            self.bot.send_message(
                message.chat.id,
                get_text_by_lang('prompt_profession_sphere', lang),
                parse_mode='Markdown',
                reply_markup=markup
            )
        else:
            # Работодателю не задаем вопросы о требованиях
            self.save_profile_data(user_id, user_state)
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=True)

    def process_profession_sphere(self, message):
        """Обработка выбора сферы деятельности"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return

        if not user_state or user_state.get('step') != 'profession_sphere':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        sphere = message.text.strip()

        selected_sphere_key = None
        for key in PROFESSION_SPHERES_KEYS.keys():
            if get_text_by_lang(key, lang) == sphere:
                selected_sphere_key = key
                break

        # Если выбрано "Другое" или сфера не из списка (ручной ввод), просим ввести профессию вручную
        if sphere == get_text_by_lang('other_button', lang) or not selected_sphere_key:
            user_state['step'] = 'profession_specific'
            database.set_user_state(user_id, user_state)

            self.bot.send_message(
                message.chat.id,
                get_text_by_lang('prompt_profession_manual', lang),
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard(lang=lang)
            )
            return

        # Если сфера выбрана из списка, показываем профессии
        user_state['step'] = 'profession_specific'
        database.set_user_state(user_id, user_state)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for prof_key in PROFESSION_SPHERES_KEYS[selected_sphere_key]:
            markup.add(types.KeyboardButton(get_text_by_lang(prof_key, lang)))
        markup.add(types.KeyboardButton(get_text_by_lang('other_button', lang)))
        markup.add(types.KeyboardButton(get_text_by_lang('back_button', lang)))

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang('prompt_profession_in_sphere', lang).format(sphere=sphere),
            parse_mode='Markdown',
            reply_markup=markup
        )

    def process_profession_specific(self, message):  # noqa: C901
        """Обработка выбора конкретной профессии"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        # Обработка кнопки Назад
        if message.text == get_text_by_lang('back_button', lang):
            user_state['step'] = 'profession_sphere'
            database.set_user_state(user_id, user_state)

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for sphere_key in PROFESSION_SPHERES_KEYS.keys():
                markup.add(types.KeyboardButton(get_text_by_lang(sphere_key, lang)))
            markup.add(types.KeyboardButton(get_text_by_lang('other_button', lang)))
            markup.add(types.KeyboardButton(get_text_by_lang('cancel_button', lang)))

            self.bot.send_message(
                message.chat.id,
                get_text_by_lang('prompt_profession_sphere', lang),
                parse_mode='Markdown',
                reply_markup=markup
            )
            return

        if utils.cancel_request(message.text):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return

        if not user_state or user_state.get('step') != 'profession_specific':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        profession = message.text.strip()

        if profession == get_text_by_lang('other_button', lang):
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang('prompt_profession_manual_edit', lang),
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard(lang=lang)
            )
            return

        # Проверка ввода
        if len(profession) < 2:
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang('profession_too_short', lang),
                reply_markup=keyboards.cancel_keyboard(lang=lang)
            )
            return

        if utils.contains_profanity(profession):
            self.bot.send_message(message.chat.id, get_text_by_lang('profanity_in_profession', lang))
            return

        # Try to find profession key
        selected_prof_key = None
        for sphere_key, prof_keys in PROFESSION_SPHERES_KEYS.items():
            for key in prof_keys:
                if get_text_by_lang(key, lang) == profession:
                    selected_prof_key = key
                    break
            if selected_prof_key:
                break

        user_state['profile_data']['profession'] = selected_prof_key if selected_prof_key else profession

        if user_state['role'] == 'seeker':
            user_state['temp_languages'] = []
            self.show_language_selection(message.chat.id, user_id, user_state)
        else:
            # Работодателю не задаем вопросы о требованиях
            self.save_profile_data(user_id, user_state)
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=True)

    def show_language_selection(self, chat_id, user_id, user_state):
        """Показ меню выбора языка"""
        user_state['step'] = 'language_selection'
        lang = get_user_language(user_id)
        database.set_user_state(user_id, user_state)

        selected_lang_keys = [item.get('lang_key') for item in user_state.get('temp_languages', [])
                              if 'lang_key' in item]

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

        # Add available languages excluding selected ones
        for btn_text, lang_key in LANGUAGES_I18N[lang].items():
            if lang_key not in selected_lang_keys:
                markup.add(types.KeyboardButton(btn_text))

        markup.add(types.KeyboardButton(get_text_by_lang('language_other', lang)))

        msg_text = get_text_by_lang('prompt_languages', lang)

        if user_state.get('temp_languages'):
            markup.add(types.KeyboardButton(get_text_by_lang('next_button', lang)))
            langs_list = "\n".join([
                f"• {get_text_by_lang(item['lang_key'], lang) if 'lang_key' in item else item.get('lang_name', '?')} - "
                f"{get_text_by_lang(item['level_key'], lang)}"
                for item in user_state['temp_languages']
            ])
            msg_text = (
                f"{get_text_by_lang('added_languages', lang)}\n{langs_list}\n\n"
                f"{get_text_by_lang('prompt_languages_again', lang)}"
            )
        else:
            markup.add(types.KeyboardButton(get_text_by_lang('skip_button_text', lang)))

        if user_state.get('source') == 'settings':
            markup.add(types.KeyboardButton(get_text_by_lang('cancel_button', lang)))

        self.bot.send_message(chat_id, msg_text, parse_mode='Markdown', reply_markup=markup)

    def process_language_selection(self, message):
        """Обработка выбора языка"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)
        text = message.text.strip()

        if utils.cancel_request(message.text):
            if user_state.get('source') == 'settings':
                database.clear_user_state(user_id)
                self.bot.send_message(message.chat.id, "❌ Изменение отменено", reply_markup=keyboards.seeker_main_menu())
                return

            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return

        if text == get_text_by_lang('next_button', lang):
            if user_state.get('temp_languages'):
                # Save and move on
                langs_json = json.dumps(user_state['temp_languages'])
                if user_state.get('source') == 'settings':
                    database.update_seeker_profile(telegram_id=user_id, languages=langs_json)
                    database.clear_user_state(user_id)
                    self.bot.send_message(message.chat.id,
                                          get_text_by_lang('languages_updated', lang).format(langs_str="..."),
                                          parse_mode='Markdown', reply_markup=keyboards.seeker_main_menu())
                    return

                user_state['profile_data']['languages'] = langs_json
                self._ask_experience(message.chat.id, user_id, user_state)
            else:
                self.bot.send_message(message.chat.id, get_text_by_lang('at_least_one_language', lang))
            return

        if text == get_text_by_lang('skip_button_text', lang):
            return self._handle_language_skip(message, user_id, user_state)

        if text == get_text_by_lang('language_other', lang):
            user_state['step'] = 'language_custom_name'
            database.set_user_state(user_id, user_state)
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang('prompt_language_custom', lang),
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard(lang=lang)
            )
            return

        # Check standard languages
        lang_key = LANGUAGES_I18N[lang].get(text)
        if lang_key:
            user_state['current_lang_key_editing'] = lang_key
            self.show_level_selection(message.chat.id, user_id, user_state)
            return

        self.bot.send_message(message.chat.id, get_text_by_lang('use_menu_buttons', lang))

    def _handle_language_skip(self, message, user_id, user_state):
        lang = get_user_language(user_id)
        if not user_state.get('temp_languages'):
            if user_state.get('source') == 'settings':
                database.update_seeker_profile(telegram_id=user_id,
                                               languages=get_text_by_lang('languages_not_specified', lang))
                database.clear_user_state(user_id)
                self.bot.send_message(message.chat.id, get_text_by_lang('languages_cleared', lang),
                                      reply_markup=keyboards.seeker_main_menu())
                return

            user_state['profile_data']['languages'] = get_text_by_lang('languages_not_specified', lang)
            self._ask_experience(message.chat.id, user_id, user_state)
        else:
            # Should not happen if logic is correct (button changes to Next)
            self.process_language_selection(message)  # Retry

    def _ask_experience(self, chat_id, user_id, user_state):
        lang = get_user_language(user_id)
        user_state['step'] = 'experience'
        if 'temp_languages' in user_state:
            del user_state['temp_languages']
        database.set_user_state(user_id, user_state)
        self.bot.send_message(
            chat_id,
            get_text_by_lang('prompt_experience', lang),
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard(lang=lang)
        )

    def process_language_custom_name(self, message):
        """Обработка ввода названия другого языка"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        if utils.cancel_request(message.text):
            if user_state.get('source') == 'settings':
                database.clear_user_state(user_id)
                self.bot.send_message(message.chat.id, "❌ Изменение отменено", reply_markup=keyboards.seeker_main_menu())
                return

            self.show_language_selection(message.chat.id, user_id, user_state)
            return

        lang_name = message.text.strip()
        if len(lang_name) < 2:
            self.bot.send_message(message.chat.id, get_text_by_lang('language_name_too_short', lang))
            return

        # Check duplicates
        existing_names = []
        for item in user_state.get('temp_languages', []):
            if 'lang_key' in item:
                existing_names.append(get_text_by_lang(item['lang_key'], lang).lower())
            elif 'lang_name' in item:
                existing_names.append(item['lang_name'].lower())

        if lang_name.lower() in existing_names:
            self.bot.send_message(message.chat.id, get_text_by_lang('language_already_added', lang))
            self.show_language_selection(message.chat.id, user_id, user_state)
            return

        user_state['current_lang_name_editing'] = lang_name
        self.show_level_selection(message.chat.id, user_id, user_state)

    def show_level_selection(self, chat_id, user_id, user_state):
        """Показ меню выбора уровня"""
        user_state['step'] = 'language_level'
        lang = get_user_language(user_id)
        database.set_user_state(user_id, user_state)

        lang_name_key = user_state.get('current_lang_key_editing')
        lang_name_custom = user_state.get('current_lang_name_editing')
        if lang_name_key:
            lang_name = get_text_by_lang(lang_name_key, lang)
        elif lang_name_custom:
            lang_name = lang_name_custom
        else:
            lang_name = get_text_by_lang('this_language', lang)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for level_text in LEVELS_I18N[lang].keys():
            markup.add(types.KeyboardButton(level_text))
        markup.add(types.KeyboardButton(get_text_by_lang('back_button', lang)))

        self.bot.send_message(
            chat_id,
            get_text_by_lang('prompt_language_level', lang).format(lang_name=lang_name),
            parse_mode='Markdown',
            reply_markup=markup
        )

    def process_language_level(self, message):
        """Обработка выбора уровня"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)
        text = message.text.strip()

        if text == get_text_by_lang('back_button', lang):
            self.show_language_selection(message.chat.id, user_id, user_state)
            return

        if text not in LEVELS_I18N[lang].keys():
            self.bot.send_message(message.chat.id, get_text_by_lang('select_level_from_menu', lang))
            return

        level_key = LEVELS_I18N[lang].get(text)
        lang_key = user_state.get('current_lang_key_editing')
        lang_name = user_state.get('current_lang_name_editing')

        if not lang_key and not lang_name:
            self.show_language_selection(message.chat.id, user_id, user_state)
            return

        # Add to list
        if 'temp_languages' not in user_state:
            user_state['temp_languages'] = []

        if lang_key:
            user_state['temp_languages'].append({'lang_key': lang_key, 'level_key': level_key})
            del user_state['current_lang_key_editing']
        elif lang_name:
            user_state['temp_languages'].append({'lang_name': lang_name, 'level_key': level_key})
            del user_state['current_lang_name_editing']

        # Back to selection
        self.show_language_selection(message.chat.id, user_id, user_state)

    def process_experience(self, message):
        """Обработка опыта работы"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        if utils.cancel_request(message.text):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return

        if not user_state or user_state.get('step') != 'experience':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        if message.text.strip().lower() == get_text_by_lang('skip_button_text', lang).lower():
            experience = get_text_by_lang('experience_not_specified', lang)
        else:
            experience = message.text.strip()
            if len(experience) < 2:
                self.bot.send_message(
                    message.chat.id,
                    get_text_by_lang('experience_too_short', lang),
                    reply_markup=keyboards.cancel_keyboard(lang=lang)
                )
                return

            if utils.contains_profanity(experience):
                self.bot.send_message(message.chat.id, "❌ Текст содержит недопустимые слова.")
                return

        user_state['profile_data']['experience'] = experience
        user_state['step'] = 'skills'
        database.set_user_state(user_id, user_state)

        if user_state['role'] == 'seeker':
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang('prompt_skills', lang),
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard(lang=lang)
            )
        else:
            # Работодателю не задаем вопросы о требованиях
            self.save_profile_data(user_id, user_state)
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=True)

    def process_skills(self, message):
        """Обработка навыков/хобби"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        if utils.cancel_request(message.text):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return

        if not user_state or user_state.get('step') != 'skills':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        if message.text.strip().lower() == get_text_by_lang('skip_button_text', lang).lower():
            skills = get_text_by_lang('skills_not_specified', lang)
        else:
            skills = message.text.strip()
            if len(skills) < 2:
                self.bot.send_message(
                    message.chat.id,
                    get_text_by_lang('skills_too_short', lang),
                    reply_markup=keyboards.cancel_keyboard(lang=lang)
                )
                return

            if len(skills) > 500:
                self.bot.send_message(
                    message.chat.id,
                    get_text_by_lang('skills_too_long', lang),
                    reply_markup=keyboards.cancel_keyboard(lang=lang)
                )
                return

            if utils.contains_profanity(skills):
                self.bot.send_message(message.chat.id, "❌ Текст содержит недопустимые слова.")
                return

        user_state['profile_data']['skills'] = skills

        # Сохраняем данные профиля в базу
        if self.save_profile_data(user_id, user_state):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=True)
        else:
            database.clear_user_state(user_id)
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang('profile_save_error', lang),
                reply_markup=keyboards.seeker_main_menu(lang=lang)
            )

    def save_profile_data(self, user_id, user_state):
        """Сохранение данных профиля в базу"""
        success = False
        profile_data = user_state['profile_data']

        if user_state['role'] == 'seeker':
            # Обновляем профиль соискателя
            success = database.update_seeker_profile(
                telegram_id=user_id,
                profession=profile_data.get('profession', 'Не указана'),
                education=profile_data.get('education', 'Не указано'),
                experience=profile_data.get('experience', 'Нет опыта'),
                skills=profile_data.get('skills', 'Не указаны'),
                languages=profile_data.get('languages', 'Не указаны')
            )

            if success:
                print(f"✅ Профиль соискателя {user_id} обновлен")
            else:
                print(f"⚠️ Не удалось обновить профиль соискателя {user_id}")

        else:
            # Для работодателя сохраняем в существующее описание
            current_user = database.get_user_by_id(user_id)
            if current_user and 'company_name' in current_user:
                current_description = current_user.get('description', '')

                # Формируем новое описание с профилем
                new_description = f"{current_description}\n\n"
                new_description += "*Дополнительная информация:*\n"
                new_description += f"• Сфера деятельности: {profile_data.get('profession', 'Не указана')}\n"
                new_description += f"• Требования к образованию: {profile_data.get('education', 'Не указано')}\n"
                new_description += f"• Требования к опыту: {profile_data.get('experience', 'Не указано')}\n"
                new_description += f"• Дополнительные пожелания: {profile_data.get('skills', 'Не указано')}"

                success = database.update_employer_profile(
                    telegram_id=user_id,
                    description=new_description
                )

                if success:
                    print(f"✅ Профиль работодателя {user_id} обновлен")
                else:
                    print(f"⚠️ Не удалось обновить профиль работодателя {user_id}")
        return success

    def finish_profile_setup(self, chat_id, user_id, user_state, show_summary=False):
        """Завершение заполнения профиля"""
        # Получаем язык перед очисткой состояния
        lang = user_state.get('language_code') or get_user_language(user_id)
        database.clear_user_state(user_id)

        if show_summary:
            profile_data = user_state['profile_data']

            if user_state['role'] == 'seeker':
                # Форматирование профессии (перевод ключа)
                prof_raw = profile_data.get('profession', 'Не указана')
                profession_display = get_text_by_lang(prof_raw, lang)

                # Форматирование языков (JSON -> текст)
                langs_raw = profile_data.get('languages', 'Не указаны')
                languages_display = langs_raw
                try:
                    if isinstance(langs_raw, str) and langs_raw.startswith('['):
                        langs_list = json.loads(langs_raw)
                        formatted_langs = []
                        for item in langs_list:
                            l_name = get_text_by_lang(item.get('lang_key'), lang) if item.get('lang_key') else item.get('lang_name')
                            l_level = get_text_by_lang(item.get('level_key'), lang)
                            formatted_langs.append(f"{l_name} ({l_level})")
                        languages_display = ", ".join(formatted_langs)
                except Exception:
                    pass

                summary = (
                    f"{get_text_by_lang('profile_completed_seeker', lang)}\n\n"
                    f"{get_text_by_lang('your_profile', lang)}\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"{get_text_by_lang('profession_label', lang)} {profession_display}\n"
                    f"{get_text_by_lang('education_label', lang)} {profile_data.get('education', 'Не указано')}\n"
                    f"{get_text_by_lang('languages_label', lang)} {languages_display}\n"
                    f"{get_text_by_lang('experience_label', lang)} {profile_data.get('experience', 'Нет опыта')}\n"
                    f"{get_text_by_lang('skills_label', lang)} {profile_data.get('skills', 'Не указаны')}\n\n"
                    f"{get_text_by_lang('now_employers_can_find', lang)}"
                )
                keyboard = keyboards.seeker_main_menu(lang=lang)
            else:
                summary = (
                    f"{get_text_by_lang('profile_completed_employer', lang)}\n\n"
                    f"{get_text_by_lang('company_profile', lang)}\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"{get_text_by_lang('sphere_label', lang)} {profile_data.get('profession', 'Не указана')}\n"
                    f"{get_text_by_lang('edu_req_label', lang)} {profile_data.get('education', 'Не указано')}\n"
                    f"{get_text_by_lang('exp_req_label', lang)} {profile_data.get('experience', 'Не указано')}\n"
                    f"{get_text_by_lang('skills_req_label', lang)} {profile_data.get('skills', 'Не указано')}\n\n"
                    f"{get_text_by_lang('now_seekers_can_find', lang)}"
                )
                keyboard = keyboards.employer_main_menu(lang=lang)

            self.bot.send_message(
                chat_id,
                summary,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        else:
            # Если пользователь отменил заполнение
            if user_state['role'] == 'seeker':
                self.bot.send_message(
                    chat_id,
                    f"{get_text_by_lang('fill_profile_later_seeker', lang)}\n\n"
                    f"{get_text_by_lang('use_search_menu_seeker', lang)}",
                    parse_mode='Markdown',
                    reply_markup=keyboards.seeker_main_menu(lang=lang)
                )
            else:
                self.bot.send_message(
                    chat_id,
                    f"{get_text_by_lang('fill_profile_later_employer', lang)}\n\n"
                    f"{get_text_by_lang('use_search_menu_employer', lang)}",
                    parse_mode='Markdown',
                    reply_markup=keyboards.employer_main_menu(lang=lang)
                )

    def handle_complete_profile(self, message):
        """Ручной запуск заполнения профиля из меню"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала зарегистрируйтесь или войдите в аккаунт!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        # Проверяем, есть ли уже профиль
        role = user_data.get('role')

        if role == 'seeker':
            # Проверяем, заполнен ли уже профиль
            if user_data.get('profession') != 'Не указана' and user_data.get(
                    'skills') != 'Не указаны':
                self.bot.send_message(
                    message.chat.id,
                    "ℹ️ *Ваш профиль уже заполнен.*\n\n"
                    "Используйте меню для поиска работы.",
                    parse_mode='Markdown',
                    reply_markup=keyboards.seeker_main_menu()
                )
                return

            # Начинаем заполнение профиля
            self.start_profile_setup(message, user_data)

        else:  # employer
            # Работодателю больше не предлагаем заполнять профиль
            self.bot.send_message(
                message.chat.id,
                "ℹ️ *Профиль компании не требует дополнительного заполнения.*\n\n"
                "Используйте меню для поиска сотрудников.",
                parse_mode='Markdown',
                reply_markup=keyboards.employer_main_menu()
            )
