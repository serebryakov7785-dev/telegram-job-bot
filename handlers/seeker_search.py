import json
import logging
from typing import Any

from telebot import types

import database
import keyboards
import utils
from database.core import execute_query
from localization import get_text_by_lang, get_user_language

# Список регионов и городов для фильтрации
UZB_REGIONS = {
    "Ташкентская обл.": [
        "Ташкент",
        "Чирчик",
        "Ангрен",
        "Алмалык",
        "Бекабад",
        "Янгиюль",
        "Нурафшон",
        "Газалкент",
    ],
    "Самаркандская обл.": [
        "Самарканд",
        "Каттакурган",
        "Ургут",
        "Акташ",
        "Булунгур",
        "Джамбай",
    ],
    "Бухарская обл.": ["Бухара", "Каган", "Гиждуван", "Газли", "Галаасия"],
    "Ферганская обл.": ["Фергана", "Коканд", "Маргилан", "Кувасай", "Кува", "Риштан"],
    "Андижанская обл.": ["Андижан", "Асака", "Ханобад", "Шахрихан", "Карасу"],
    "Наманганская обл.": ["Наманган", "Чуст", "Касансай", "Пап", "Учкурган"],
    "Навоийская обл.": ["Навои", "Зарафшан", "Учкудук", "Нурата"],
    "Кашкадарьинская обл.": ["Карши", "Шахрисабз", "Гузар", "Камаши", "Мубарек"],
    "Сурхандарьинская обл.": ["Термез", "Денау", "Джаркурган", "Шерабад"],
    "Джизакская обл.": ["Джизак", "Гагарин", "Галляарал", "Даштабад"],
    "Сырдарьинская обл.": ["Гулистан", "Янгиер", "Ширин", "Сырдарья"],
    "Хорезмская обл.": ["Ургенч", "Хива", "Питнак", "Ханка"],
    "Респ. Каракалпакстан": ["Нукус", "Беруни", "Кунград", "Тахиаташ", "Турткуль"],
}


class SeekerSearchMixin:
    bot: Any

    def handle_find_vacancies(self, message):
        """Поиск вакансий"""
        user_id = message.from_user.id
        # Упрощенный поиск: показываем все вакансии
        self.show_vacancies(message, city=None)

    def process_vacancy_filter_choice(self, message):
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)

        if message.text == "⬅️ Назад":
            if user_data and "full_name" in user_data:
                markup = keyboards.seeker_main_menu(lang=lang)
            else:
                markup = keyboards.seeker_menu(lang=lang)
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("main_menu", lang),
                reply_markup=markup,
            )
            return

        if message.text == "🏙 Выбрать город":
            # Показываем список регионов
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for region in UZB_REGIONS.keys():
                markup.add(types.KeyboardButton(region))
            markup.add("⬅️ Назад")

            msg = self.bot.send_message(
                message.chat.id, "Выберите область/регион:", reply_markup=markup
            )
            self.bot.register_next_step_handler(msg, self.process_vacancy_region_choice)
        else:
            self.show_vacancies(message, city=None)

    def process_vacancy_region_choice(self, message):
        if message.text == "⬅️ Назад":
            self.handle_find_vacancies(message)
            return

        region = message.text
        if region in UZB_REGIONS:
            # Показываем города выбранного региона
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for city in UZB_REGIONS[region]:
                markup.add(types.KeyboardButton(city))
            markup.add("⬅️ Назад")

            msg = self.bot.send_message(
                message.chat.id,
                f"Выберите город/район в {region}:",
                reply_markup=markup,
            )
            self.bot.register_next_step_handler(msg, self.process_vacancy_city_choice)
        else:
            self.bot.send_message(message.chat.id, "❌ Выберите регион из списка.")
            # Перезапускаем шаг, имитируя нажатие кнопки "Выбрать город"
            message.text = "🏙 Выбрать город"
            self.process_vacancy_filter_choice(message)

    def process_vacancy_city_choice(self, message):
        if message.text == "⬅️ Назад":
            # Возвращаемся к выбору региона
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for region in UZB_REGIONS.keys():
                markup.add(types.KeyboardButton(region))
            markup.add("⬅️ Назад")

            msg = self.bot.send_message(
                message.chat.id, "Выберите область/регион:", reply_markup=markup
            )
            self.bot.register_next_step_handler(msg, self.process_vacancy_region_choice)
            return

        city = message.text
        self.show_vacancies(message, city)

    def show_vacancies(self, message, city=None):
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)
        # Формируем запрос с фильтром
        query = """
            SELECT v.*, e.company_name, e.city
            FROM vacancies v
            JOIN employers e ON v.employer_id = e.id
            WHERE v.status = 'active'
        """
        params = []
        if city:
            query += " AND e.city LIKE ?"
            params.append(f"%{city}%")

        query += " ORDER BY v.created_at DESC LIMIT 20"

        vacancies = execute_query(query, tuple(params), fetchall=True)

        # Определяем клавиатуру (для зарегистрированных или гостей)
        if user_data and "full_name" in user_data:
            markup = keyboards.seeker_main_menu(lang=lang)
        else:
            markup = keyboards.seeker_menu(lang=lang)

        if not vacancies:
            self.bot.send_message(
                message.chat.id,
                f"{get_text_by_lang('find_vacancies_header', lang)}\n\n"
                f"{get_text_by_lang('no_active_vacancies', lang)}",
                parse_mode="Markdown",
                reply_markup=markup,
            )
            return

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang("vacancies_found", lang).format(count=len(vacancies)),
            parse_mode="Markdown",
            reply_markup=markup,
        )

        for vac in vacancies:
            self._send_vacancy_card(message.chat.id, vac, lang)

    def _send_vacancy_card(self, chat_id, vac, lang):
        try:
            # --- Логика перевода для отображения ---
            # 1. Тип занятости
            job_type_from_db = vac["job_type"]

            # Обратная совместимость для старых вакансий
            if job_type_from_db and not job_type_from_db.startswith("job_type_"):
                job_type_keys = [
                    "job_type_full_time",
                    "job_type_part_time",
                    "job_type_remote",
                    "job_type_internship",
                ]
                for key in job_type_keys:  # noqa
                    if any(
                        get_text_by_lang(key, l) == job_type_from_db
                        for l in ["ru", "uz", "en"]
                    ):
                        job_type_from_db = key
                        break

            job_type_text = get_text_by_lang(job_type_from_db, lang)

            # 2. Профессия (Title)
            title_from_db = vac["title"]
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
                    try:
                        langs_list = json.loads(langs_json_str)
                    except json.JSONDecodeError:
                        langs_list = []
                        langs_display_str = langs_json_str  # noqa
                    display_parts = []
                    for lang_info in langs_list:  # noqa
                        lang_name = (
                            get_text_by_lang(lang_info["lang_key"], lang)
                            if "lang_key" in lang_info
                            else lang_info.get("lang_name", "?")
                        )
                        level_name = get_text_by_lang(lang_info["level_key"], lang)
                        display_parts.append(f"{lang_name} ({level_name})")
                    if display_parts:
                        langs_display_str = ", ".join(display_parts)
                except (json.JSONDecodeError, TypeError):
                    langs_display_str = langs_json_str  # Fallback для старых данных

            card = (
                f"💼 *{utils.escape_markdown(title_text)}*\n"  # noqa
                f"{get_text_by_lang('vacancy_card_company', lang)} *{utils.escape_markdown(vac['company_name'])}*\n"  # noqa
                f"{get_text_by_lang('vacancy_card_city', lang)} {utils.escape_markdown(vac['city'])}\n"  # noqa
                f"{get_text_by_lang('vacancy_card_salary', lang)} {utils.escape_markdown(vac['salary'])}\n"  # noqa
                f"{get_text_by_lang('gender_label', lang)} {utils.escape_markdown(gender_text)}\n"  # noqa
                f"{get_text_by_lang('vacancy_card_type', lang)} {utils.escape_markdown(job_type_text)}\n"  # noqa
                f"{get_text_by_lang('vacancy_card_languages', lang)} {utils.escape_markdown(langs_display_str)}\n"  # noqa
                f"{get_text_by_lang('vacancy_card_description', lang)} {utils.escape_markdown(vac['description'])}"  # noqa
            )

            self.bot.send_message(
                chat_id,
                card,
                parse_mode="Markdown",
                reply_markup=keyboards.vacancy_actions(vac["id"], lang=lang),
            )
        except Exception as e:
            logging.error(
                f"❌ Ошибка при отправке карточки вакансии: {e}", exc_info=True
            )
