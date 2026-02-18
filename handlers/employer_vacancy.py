import json
import logging
from typing import Any, Dict

from telebot import types

import database
import keyboards
import utils
from localization import (
    LANGUAGES_I18N,
    LEVELS_I18N,
    PROFESSION_SPHERES_KEYS,
    TRANSLATIONS,
    get_text_by_lang,
    get_user_language,
)
from models import dict_to_employer


class EmployerVacancyMixin:
    bot: Any
    handle_vacancy_responses: Any

    def handle_create_vacancy(self, message):
        """Создание вакансии"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)

        if not user_data or "company_name" not in user_data:
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("auth_required_employer", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.main_menu(lang=lang),
            )
            return

        employer = dict_to_employer(user_data)

        # Начинаем процесс создания вакансии
        database.set_user_state(
            user_id,
            {
                "step": "vacancy_sphere",  # noqa
                "vacancy_data": {"employer_id": user_data["id"]},
            },
        )

        lang = get_user_language(user_id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for sphere_key in PROFESSION_SPHERES_KEYS.keys():
            markup.add(types.KeyboardButton(get_text_by_lang(sphere_key, lang)))
        markup.add(types.KeyboardButton(get_text_by_lang("other_button", lang)))
        markup.add(types.KeyboardButton(get_text_by_lang("cancel_button", lang)))

        self.bot.send_message(
            message.chat.id,
            f"{get_text_by_lang('vacancy_creation_title', lang)}\n\n"
            f"{get_text_by_lang('vacancy_creation_company', lang)} *{employer.company_name}*\n\n"
            f"{get_text_by_lang('vacancy_creation_choose_sphere', lang)}",
            parse_mode="Markdown",
            reply_markup=markup,
        )

    def process_vacancy_sphere(self, message):
        """Обработка выбора сферы вакансии"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)
        text = message.text.strip()

        if text == get_text_by_lang("other_button", lang):  # noqa
            user_state["step"] = "vacancy_title"
            database.set_user_state(user_id, user_state)
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("enter_vacancy_title_example", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.cancel_keyboard(lang=lang),
            )
            return

        # Find sphere key by text
        selected_sphere_key = None
        for key in PROFESSION_SPHERES_KEYS.keys():
            if get_text_by_lang(key, lang) == text:
                selected_sphere_key = key
                break

        if selected_sphere_key:
            user_state["step"] = "vacancy_profession"
            database.set_user_state(user_id, user_state)

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for prof_key in PROFESSION_SPHERES_KEYS[selected_sphere_key]:
                markup.add(types.KeyboardButton(get_text_by_lang(prof_key, lang)))
            markup.add(types.KeyboardButton(get_text_by_lang("other_button", lang)))
            markup.add(types.KeyboardButton(get_text_by_lang("back_button", lang)))
            markup.add(types.KeyboardButton(get_text_by_lang("cancel_button", lang)))

            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("choose_profession_in_sphere", lang).format(
                    sphere=text
                ),
                reply_markup=markup,
            )
            return

        self.bot.send_message(
            message.chat.id, get_text_by_lang("select_from_list", lang)
        )

    def process_vacancy_profession(self, message):
        """Обработка выбора профессии"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)
        text = message.text.strip()

        if text == get_text_by_lang("back_button", lang):
            self.handle_create_vacancy(message)
            return

        if text == get_text_by_lang("other_button", lang):  # noqa
            user_state["step"] = "vacancy_title"
            database.set_user_state(user_id, user_state)
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("enter_vacancy_title", lang),
                reply_markup=keyboards.cancel_keyboard(lang=lang),
            )
            return

        # Try to find profession key
        selected_prof_key = None
        for sphere_key, prof_keys in PROFESSION_SPHERES_KEYS.items():
            for key in prof_keys:
                if get_text_by_lang(key, lang) == text:
                    selected_prof_key = key
                    break  # noqa
            if selected_prof_key:
                break

        user_state["vacancy_data"]["title"] = (
            selected_prof_key if selected_prof_key else text
        )
        user_state["step"] = "vacancy_description"
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang("enter_vacancy_description", lang),
            reply_markup=keyboards.cancel_keyboard(lang=lang),
        )

    def process_vacancy_title(self, message):
        """Обработка названия вакансии"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        title = message.text.strip()
        if len(title) < 3:
            self.bot.send_message(
                message.chat.id, get_text_by_lang("vacancy_title_too_short", lang)
            )
            return

        if utils.contains_profanity(title):
            self.bot.send_message(
                message.chat.id, get_text_by_lang("vacancy_title_profanity", lang)
            )
            return

        user_state["vacancy_data"]["title"] = title
        user_state["step"] = "vacancy_description"
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang("enter_vacancy_description", lang),
            reply_markup=keyboards.cancel_keyboard(lang=lang),
        )

    def process_vacancy_description(self, message):
        """Обработка описания вакансии"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        description = message.text.strip()
        if len(description) < 10:
            self.bot.send_message(
                message.chat.id, get_text_by_lang("vacancy_desc_too_short", lang)
            )
            return

        if utils.contains_profanity(description):
            self.bot.send_message(
                message.chat.id, get_text_by_lang("vacancy_desc_profanity", lang)
            )
            return

        user_state["vacancy_data"]["description"] = description

        # Инициализируем временный список полов и переходим к их выбору
        user_state["temp_genders"] = []
        self.show_vacancy_gender_selection(message.chat.id, user_id, user_state)

    def show_vacancy_gender_selection(self, chat_id, user_id, user_state):
        """Показ меню выбора пола для вакансии"""
        user_state["step"] = "vacancy_gender"
        database.set_user_state(user_id, user_state)
        lang = get_user_language(user_id)

        selected_genders = user_state.get("temp_genders", [])

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

        btns = []
        if "male" not in selected_genders:
            btns.append(types.KeyboardButton(get_text_by_lang("gender_male", lang)))
        if "female" not in selected_genders:
            btns.append(types.KeyboardButton(get_text_by_lang("gender_female", lang)))

        markup.add(*btns)
        markup.add(types.KeyboardButton(get_text_by_lang("next_button", lang)))
        markup.add(types.KeyboardButton(get_text_by_lang("cancel_button", lang)))

        msg_text = get_text_by_lang("vacancy_gender_prompt", lang)  # noqa

        if selected_genders:
            selected_text = ", ".join(
                [get_text_by_lang(f"gender_{g}", lang) for g in selected_genders]
            )
            msg_text += f"\n\n✅ {get_text_by_lang('selected', lang)}: {selected_text}"

        self.bot.send_message(
            chat_id, msg_text, parse_mode="Markdown", reply_markup=markup
        )

    def process_vacancy_gender(self, message):
        """Обработка выбора пола для вакансии"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)
        text = message.text.strip()

        if text == get_text_by_lang("next_button", lang):
            selected = user_state.get("temp_genders", [])
            if not selected or ("male" in selected and "female" in selected):
                user_state["vacancy_data"]["gender"] = "any"
            elif "male" in selected:
                user_state["vacancy_data"]["gender"] = "male"
            elif "female" in selected:
                user_state["vacancy_data"]["gender"] = "female"

            if "temp_genders" in user_state:
                del user_state["temp_genders"]

            user_state["temp_languages"] = []
            self.show_vacancy_language_selection(message.chat.id, user_id, user_state)
            return

        if text == get_text_by_lang("gender_male", lang) or text == get_text_by_lang(
            "gender_female", lang
        ):  # noqa
            gender_key = (
                "male" if text == get_text_by_lang("gender_male", lang) else "female"
            )
            if "temp_genders" not in user_state:
                user_state["temp_genders"] = []
            if gender_key not in user_state["temp_genders"]:
                user_state["temp_genders"].append(gender_key)
            self.show_vacancy_gender_selection(message.chat.id, user_id, user_state)
            return

        self.bot.send_message(
            message.chat.id, get_text_by_lang("use_menu_buttons", lang)
        )

    def show_vacancy_language_selection(self, chat_id, user_id, user_state):
        """Показ меню выбора языка для вакансии"""
        user_state["step"] = "vacancy_language_selection"
        database.set_user_state(user_id, user_state)
        lang = get_user_language(user_id)

        selected_lang_keys = [
            l.get("lang_key") for l in user_state.get("temp_languages", [])
        ]

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

        # Добавляем доступные языки, исключая уже выбранные
        for btn_text, lang_key in LANGUAGES_I18N[lang].items():
            if lang_key not in selected_lang_keys:
                markup.add(types.KeyboardButton(btn_text))

        markup.add(types.KeyboardButton(get_text_by_lang("language_other", lang)))

        msg_text = get_text_by_lang("vacancy_languages_prompt", lang)

        if user_state.get("temp_languages"):
            markup.add(types.KeyboardButton(get_text_by_lang("next_button", lang)))
            langs_list = "\n".join(
                [
                    f"• {get_text_by_lang(l['lang_key'], lang) if 'lang_key' in l else l.get('lang_name', '?')} - "
                    f"{get_text_by_lang(l['level_key'], lang)}"
                    for l in user_state["temp_languages"]
                ]
            )
            msg_text += f"\n\n{get_text_by_lang('vacancy_languages_added', lang)}\n{langs_list}\n\n{get_text_by_lang('vacancy_languages_add_more', lang)}"
        else:
            markup.add(types.KeyboardButton(get_text_by_lang("skip_button_text", lang)))
            msg_text += f"\n\n{get_text_by_lang('vacancy_languages_select_list', lang)}"

        markup.add(types.KeyboardButton(get_text_by_lang("cancel_button", lang)))

        self.bot.send_message(
            chat_id, msg_text, parse_mode="Markdown", reply_markup=markup
        )

    def process_vacancy_language_selection(self, message):
        """Обработка выбора языка для вакансии"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)
        text = message.text.strip()

        if text == get_text_by_lang("next_button", lang):
            if user_state.get("temp_languages"):
                langs_json_str = json.dumps(user_state["temp_languages"])

                if user_state.get("is_editing_vacancy"):
                    user_state["edit_data"]["languages"] = langs_json_str
                    self.ask_edit_salary(message.chat.id, user_id, user_state)
                else:
                    user_state["vacancy_data"]["languages"] = langs_json_str
                    self.ask_vacancy_salary(message.chat.id, user_id, user_state)
            else:
                self.bot.send_message(
                    message.chat.id, get_text_by_lang("at_least_one_language", lang)
                )
            return

        if text == get_text_by_lang("skip_button_text", lang):
            langs_str = "Не имеет значения"  # noqa
            if user_state.get("is_editing_vacancy"):
                user_state["edit_data"]["languages"] = langs_str
                self.ask_edit_salary(message.chat.id, user_id, user_state)
            else:
                user_state["vacancy_data"]["languages"] = langs_str
                self.ask_vacancy_salary(message.chat.id, user_id, user_state)
            return

        if text == get_text_by_lang("language_other", lang):
            user_state["step"] = "vacancy_language_custom_name"
            database.set_user_state(user_id, user_state)
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("prompt_language_custom", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.cancel_keyboard(lang=lang),
            )
            return

        lang_key = LANGUAGES_I18N[lang].get(text)
        if lang_key:
            user_state["current_lang_key_editing"] = lang_key
            self.show_vacancy_language_level(message.chat.id, user_id, user_state)
            return

        self.bot.send_message(
            message.chat.id, get_text_by_lang("use_menu_buttons", lang)
        )

    def process_vacancy_language_custom_name(self, message):
        """Обработка ввода названия другого языка"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        lang_name = message.text.strip()
        if len(lang_name) < 2:
            self.bot.send_message(
                message.chat.id, get_text_by_lang("language_name_too_short", lang)
            )
            return

        # Проверка дубликатов
        selected_names = [
            lang_item.get("lang_name", "").lower()
            for lang_item in user_state.get("temp_languages", [])
        ]
        if lang_name.lower() in selected_names:
            self.bot.send_message(
                message.chat.id, get_text_by_lang("language_already_added", lang)
            )
            self.show_vacancy_language_selection(message.chat.id, user_id, user_state)
            return

        user_state["current_lang_name_editing"] = lang_name
        self.show_vacancy_language_level(message.chat.id, user_id, user_state)

    def show_vacancy_language_level(self, chat_id, user_id, user_state):
        """Показ меню выбора уровня языка"""
        user_state["step"] = "vacancy_language_level"
        lang = get_user_language(user_id)
        database.set_user_state(user_id, user_state)

        lang_name_key = user_state.get("current_lang_key_editing")
        lang_name_custom = user_state.get("current_lang_name_editing")
        if lang_name_key:
            lang_name = get_text_by_lang(lang_name_key, lang)
        elif lang_name_custom:
            lang_name = lang_name_custom
        else:
            lang_name = get_text_by_lang("this_language", lang)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for level_text in LEVELS_I18N[lang].keys():
            markup.add(types.KeyboardButton(level_text))
        markup.add(types.KeyboardButton(get_text_by_lang("back_button", lang)))

        self.bot.send_message(
            chat_id,
            get_text_by_lang("prompt_language_level", lang).format(lang_name=lang_name),
            parse_mode="Markdown",
            reply_markup=markup,
        )

    def ask_vacancy_salary(self, chat_id, user_id, user_state):
        """Переход к вопросу о зарплате"""
        user_state["step"] = "vacancy_salary"
        if "temp_languages" in user_state:
            del user_state["temp_languages"]

        lang = get_user_language(user_id)
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            chat_id,
            get_text_by_lang("vacancy_salary_prompt", lang),
            parse_mode="Markdown",
            reply_markup=keyboards.cancel_keyboard(lang=lang),
        )

    def process_vacancy_language_level(self, message):
        """Обработка выбора уровня языка"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)
        text = message.text.strip()

        if text == get_text_by_lang("back_button", lang):
            self.show_vacancy_language_selection(message.chat.id, user_id, user_state)
            return

        if text not in LEVELS_I18N[lang].keys():
            self.bot.send_message(
                message.chat.id, get_text_by_lang("select_level_from_menu", lang)
            )
            return

        level_key = LEVELS_I18N[lang].get(text)
        lang_key = user_state.get("current_lang_key_editing")
        lang_name = user_state.get("current_lang_name_editing")

        if not lang_key and not lang_name:
            self.show_vacancy_language_selection(message.chat.id, user_id, user_state)
            return

        if "temp_languages" not in user_state:
            user_state["temp_languages"] = []

        if lang_key:
            user_state["temp_languages"].append(
                {"lang_key": lang_key, "level_key": level_key}
            )
            del user_state["current_lang_key_editing"]
        elif lang_name:
            user_state["temp_languages"].append(
                {"lang_name": lang_name, "level_key": level_key}
            )
            del user_state["current_lang_name_editing"]

        self.show_vacancy_language_selection(message.chat.id, user_id, user_state)

    def process_vacancy_salary(self, message):
        """Обработка зарплаты"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        user_state["vacancy_data"]["salary"] = message.text.strip()
        user_state["step"] = "vacancy_type"
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang("vacancy_type_prompt", lang),
            reply_markup=keyboards.job_type_menu(lang=lang),
        )

    def process_vacancy_type(self, message):
        """Обработка типа занятости и сохранение"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        job_type_text = message.text.strip()
        job_type_key = None

        # Проверяем валидность типа занятости на всех языках
        job_type_keys = [
            "job_type_full_time",
            "job_type_part_time",
            "job_type_remote",
            "job_type_internship",
        ]
        for key in job_type_keys:  # noqa
            for lang_code in TRANSLATIONS.keys():
                if get_text_by_lang(key, lang_code) == job_type_text:
                    job_type_key = key
                    break  # noqa
            if job_type_key:
                break

        if not job_type_key:
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("select_from_list", lang),
                reply_markup=keyboards.job_type_menu(lang=lang),
            )
            return

        user_state["vacancy_data"]["job_type"] = job_type_key

        # Сохраняем вакансию
        if database.create_vacancy(user_state["vacancy_data"]):
            # Принудительно обновляем пол, так как create_vacancy может не сохранять его
            try:
                employer_id = user_state["vacancy_data"].get("employer_id")
                gender = user_state["vacancy_data"].get("gender")
                if employer_id and gender:
                    last_vac = database.execute_query(  # noqa
                        "SELECT id FROM vacancies WHERE employer_id = ? ORDER BY id DESC LIMIT 1",
                        (employer_id,),
                        fetchone=True,
                    )
                    if last_vac:
                        database.execute_query(
                            "UPDATE vacancies SET gender = ? WHERE id = ?",
                            (gender, last_vac["id"]),
                            commit=True,
                        )
            except Exception as e:
                logging.error(f"Error patching vacancy gender: {e}")

            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("vacancy_created_success", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.employer_main_menu(lang=lang),
            )
        else:
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("vacancy_creation_error", lang),
                reply_markup=keyboards.employer_main_menu(lang=lang),
            )

        database.clear_user_state(user_id)

    def handle_my_vacancies(self, message):
        """Мои вакансии"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)

        if not user_data or "company_name" not in user_data:
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("auth_required_employer", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.main_menu(lang=lang),
            )
            return

        vacancies = database.get_employer_vacancies(user_data["id"])

        if not vacancies:
            self.bot.send_message(
                message.chat.id,
                f"{get_text_by_lang('my_vacancies_header', lang)}\n\n"
                f"{get_text_by_lang('my_vacancies_empty', lang)}",
                parse_mode="Markdown",
                reply_markup=keyboards.employer_main_menu(lang=lang),
            )
            return

        for vac in vacancies:
            # --- Логика перевода для отображения ---
            # 1. Тип занятости
            job_type_from_db = vac["job_type"]

            # Обратная совместимость для старых вакансий (текст -> ключ)
            if job_type_from_db and not job_type_from_db.startswith("job_type_"):
                job_type_keys = [
                    "job_type_full_time",
                    "job_type_part_time",
                    "job_type_remote",
                    "job_type_internship",
                ]
                for key in job_type_keys:
                    # Проверяем совпадение с любым из языков
                    if any(
                        get_text_by_lang(key, lang_code) == job_type_from_db
                        for lang_code in ["ru", "uz", "en"]
                    ):
                        job_type_from_db = key
                        break

            # Переводим ключ в текст на нужном языке
            job_type_text = get_text_by_lang(job_type_from_db, lang)

            # 2. Профессия (Title)
            title_from_db = vac["title"]  # noqa
            title_text = (
                get_text_by_lang(title_from_db, lang)
                if title_from_db and title_from_db.startswith("prof_")
                else title_from_db
            )

            # Gender
            gender_val = vac.get("gender", "any")
            if gender_val == "male":
                gender_text = get_text_by_lang("gender_male", lang)
            elif gender_val == "female":
                gender_text = get_text_by_lang("gender_female", lang)
            else:
                gender_text = get_text_by_lang("gender_any", lang)

            # 2. Языки
            langs_json_str = vac.get("languages")
            langs_display_str = get_text_by_lang(
                "languages_not_specified_in_vacancy", lang
            )
            if langs_json_str:
                try:
                    # Try to parse as JSON
                    try:
                        langs_list = json.loads(langs_json_str)
                    except json.JSONDecodeError:
                        # If not JSON, treat as old string format
                        langs_list = []
                        langs_display_str = langs_json_str  # Fallback

                    display_parts = []
                    for lang_info in langs_list:
                        lang_name = (
                            get_text_by_lang(lang_info["lang_key"], lang)
                            if "lang_key" in lang_info
                            else lang_info.get("lang_name", "?")
                        )
                        level_name = get_text_by_lang(
                            lang_info["level_key"], lang
                        )  # noqa
                        display_parts.append(f"{lang_name} ({level_name})")
                    if display_parts:
                        langs_display_str = ", ".join(display_parts)
                except (json.JSONDecodeError, TypeError):
                    langs_display_str = langs_json_str  # Fallback для старых данных

            # Форматируем дату создания в ташкентское время
            created_at_tashkent = utils.format_db_datetime_to_tashkent(
                vac["created_at"]
            )

            self.bot.send_message(
                message.chat.id,
                f"💼 *{title_text}*\n"
                f"{get_text_by_lang('vacancy_card_salary', lang)} {vac['salary']}\n"  # noqa
                f"{get_text_by_lang('vacancy_card_type', lang)} {job_type_text}\n"  # noqa
                f"{get_text_by_lang('gender_label', lang)} {gender_text}\n"  # noqa
                f"{get_text_by_lang('vacancy_card_languages', lang)} {langs_display_str}\n"  # noqa
                f"{get_text_by_lang('vacancy_card_description', lang)} {vac['description']}\n\n"  # noqa
                f"{get_text_by_lang('vacancy_card_created_at', lang)} {created_at_tashkent}",  # noqa
                parse_mode="Markdown",
                reply_markup=keyboards.my_vacancy_actions(vac["id"], lang=lang),
            )

    def handle_my_vacancy_actions(self, call):
        """Обработка кнопок 'Изменить', 'Удалить', 'Отклики'"""
        try:
            action, _, vacancy_id_str = call.data.partition("_vac_")
            vacancy_id = int(vacancy_id_str)

            if action == "edit":
                self.handle_edit_vacancy(call, vacancy_id)
            elif action == "delete":
                self.handle_delete_vacancy(call, vacancy_id)
            elif action == "responses":
                self.handle_vacancy_responses(call, vacancy_id)
        except ValueError as e:
            logging.error(
                f"❌ Ошибка разбора callback_data в handle_my_vacancy_actions: {e}",
                exc_info=True,
            )
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки команды.")

    def handle_edit_vacancy(self, call, vacancy_id):
        """Начало редактирования вакансии"""
        self.bot.answer_callback_query(call.id)
        user_id = call.from_user.id

        # Получаем текущие данные вакансии через список вакансий работодателя
        user_data = database.get_user_by_id(user_id)
        vacancies = database.get_employer_vacancies(user_data["id"])
        target_vac = next((v for v in vacancies if v["id"] == vacancy_id), None)

        if not target_vac:
            self.bot.send_message(call.message.chat.id, "❌ Вакансия не найдена.")
            return

        # Сохраняем состояние
        database.set_user_state(
            user_id,
            {
                "step": "edit_vacancy_title",
                "vacancy_id": vacancy_id,
                "current_vac": target_vac,
                "edit_data": {},
            },
        )

        self.bot.send_message(
            call.message.chat.id,
            f"✏️ *Редактирование вакансии*\n\n"  # TODO: Localize
            # Note: Title might be a key, so we should translate it for display
            f"Текущее название: *{target_vac['title']}*\n\n"
            f"Введите новое название (или отправьте точку . чтобы оставить текущее):",
            parse_mode="Markdown",
            reply_markup=keyboards.cancel_keyboard(),
        )

    def process_edit_title(self, message):
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        val = message.text.strip()
        if val != ".":
            if len(val) < 3:
                self.bot.send_message(message.chat.id, "❌ Слишком короткое название.")
                return

            if utils.contains_profanity(val):
                self.bot.send_message(
                    message.chat.id, "❌ Название содержит недопустимые слова."
                )
                return

            # Try to find profession key if user typed it manually matching a known profession
            selected_prof_key = None
            lang = get_user_language(user_id)  # noqa
            for sphere_key, prof_keys in PROFESSION_SPHERES_KEYS.items():
                for key in prof_keys:
                    if get_text_by_lang(key, lang) == val:
                        selected_prof_key = key
                        break
                if selected_prof_key:
                    break
            user_state["edit_data"]["title"] = (
                selected_prof_key if selected_prof_key else val
            )

        user_state["step"] = "edit_vacancy_desc"
        database.set_user_state(user_id, user_state)

        current_desc = user_state["current_vac"]["description"]
        self.bot.send_message(
            message.chat.id,
            f"📝 Текущее описание: {current_desc}\n\n"
            "Введите новое описание (или . чтобы оставить):",
            reply_markup=keyboards.cancel_keyboard(),
        )

    def process_edit_desc(self, message):
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        if not user_state:
            return

        val = message.text.strip()
        if val != ".":
            if len(val) < 10:
                self.bot.send_message(message.chat.id, "❌ Описание слишком короткое.")
                return

            if utils.contains_profanity(val):
                self.bot.send_message(
                    message.chat.id, "❌ Описание содержит недопустимые слова."
                )
                return
            if not user_state:
                return
            user_state["edit_data"]["description"] = val

        # Переход к редактированию языков
        user_state["step"] = "edit_vacancy_languages_prompt"
        database.set_user_state(user_id, user_state)

        current_langs = user_state["current_vac"].get("languages", "Не указаны")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("✏️ Изменить"),
            types.KeyboardButton("➡️ Оставить текущие"),
        )
        markup.add(types.KeyboardButton("❌ Отмена"))

        self.bot.send_message(
            message.chat.id,
            f"🗣 Текущие требования к языкам: {current_langs}\n\n" "Хотите изменить?",
            reply_markup=markup,
        )

    def process_edit_languages_prompt(self, message):
        """Обработка выбора: менять языки или нет"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        text = message.text.strip()

        if text == "➡️ Оставить текущие" or text == ".":
            self.ask_edit_salary(message.chat.id, user_id, user_state)
            return

        if text == "✏️ Изменить":
            user_state["temp_languages"] = []
            user_state["is_editing_vacancy"] = True
            self.show_vacancy_language_selection(message.chat.id, user_id, user_state)
            return

        self.bot.send_message(message.chat.id, "❌ Выберите действие из меню.")

    def ask_edit_salary(self, chat_id, user_id, user_state):
        """Переход к редактированию зарплаты"""
        user_state["step"] = "edit_vacancy_salary"
        # Очистка временных флагов
        if "is_editing_vacancy" in user_state:
            del user_state["is_editing_vacancy"]
        if "temp_languages" in user_state:
            del user_state["temp_languages"]

        database.set_user_state(user_id, user_state)

        current_salary = user_state["current_vac"]["salary"]
        self.bot.send_message(
            chat_id,
            f"💰 Текущая зарплата: {current_salary}\n\n"
            "Введите новую зарплату (или . чтобы оставить):",
            reply_markup=keyboards.cancel_keyboard(),
        )

    def process_edit_salary(self, message):
        user_id = message.from_user.id
        user_state: Dict[str, Any] = database.get_user_state(user_id)
        if not user_state:
            return
        # user_state is already Dict[str, Any]

        val = message.text.strip()
        if val != ".":
            user_state["edit_data"]["salary"] = val

        user_state["step"] = "edit_vacancy_type"
        database.set_user_state(user_id, user_state)

        current_type = user_state["current_vac"]["job_type"]
        self.bot.send_message(
            message.chat.id,
            f"⏱ Текущий тип занятости: {current_type}\n\n"
            "Выберите новый тип (или . чтобы оставить):",
            reply_markup=keyboards.job_type_menu(),
        )

    def process_edit_type(self, message):
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        val = message.text.strip()
        if val != ".":
            # Определяем ключ по тексту
            job_type_key = None
            job_type_keys = [
                "job_type_full_time",
                "job_type_part_time",
                "job_type_remote",
                "job_type_internship",
            ]

            for key in job_type_keys:
                if any(
                    get_text_by_lang(key, lang_code) == val
                    for lang_code in ["ru", "uz", "en"]
                ):
                    job_type_key = key
                    break

            if not job_type_key:
                self.bot.send_message(
                    message.chat.id,
                    get_text_by_lang("select_from_list", lang),
                    reply_markup=keyboards.job_type_menu(lang=lang),
                )
                return

            user_state["edit_data"]["job_type"] = job_type_key

        # Обновляем данные в БД
        vac_id = user_state["vacancy_id"]
        edit_data = user_state["edit_data"]

        if edit_data and database.update_vacancy(vac_id, **edit_data):
            self.bot.send_message(
                message.chat.id,
                "✅ Вакансия успешно обновлена!",  # Можно добавить ключ перевода
                reply_markup=keyboards.employer_main_menu(lang=lang),
            )
        else:
            self.bot.send_message(
                message.chat.id,
                "ℹ️ Данные не были изменены.",
                reply_markup=keyboards.employer_main_menu(lang=lang),
            )

        database.clear_user_state(user_id)

    def handle_delete_vacancy(self, call, vacancy_id):
        """Запрос подтверждения удаления"""
        user_id = call.from_user.id
        lang = get_user_language(user_id)
        self.bot.edit_message_text(
            text=f"{get_text_by_lang('confirm_delete_vacancy', lang)}\n\n{call.message.text}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=keyboards.delete_confirmation_keyboard(vacancy_id, lang=lang),
        )

    def handle_confirm_delete(self, call):
        """Подтверждение удаления"""
        vacancy_id = int(call.data.split("_")[2])
        user_id = call.from_user.id
        lang = get_user_language(user_id)

        database.delete_vacancy(vacancy_id)

        self.bot.answer_callback_query(
            call.id, get_text_by_lang("vacancy_deleted_alert", lang)
        )
        self.bot.delete_message(call.message.chat.id, call.message.message_id)
        self.bot.send_message(
            call.message.chat.id,
            get_text_by_lang("vacancy_deleted_success", lang),
            reply_markup=keyboards.employer_main_menu(lang=lang),
        )
