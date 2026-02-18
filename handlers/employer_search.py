import json
import logging
from typing import Any

from telebot import types

import database
import keyboards
import utils
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


class EmployerSearchMixin:
    bot: Any

    def handle_find_candidates(self, message):
        """Поиск сотрудников"""
        user_id = message.from_user.id
        # Упрощенный поиск: показываем всех кандидатов
        self.show_candidates(message, city=None)

    def process_candidate_filter_choice(self, message):
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)

        if message.text == "⬅️ Назад":
            if user_data and "company_name" in user_data:
                markup = keyboards.employer_main_menu(lang=lang)
            else:
                markup = keyboards.employer_menu(lang=lang)
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
            self.bot.register_next_step_handler(
                msg, self.process_candidate_region_choice
            )
        else:
            # Все города
            self.show_candidates(message, city=None)

    def process_candidate_region_choice(self, message):
        if message.text == "⬅️ Назад":
            self.handle_find_candidates(message)
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
            self.bot.register_next_step_handler(msg, self.process_candidate_city_choice)
        else:
            self.bot.send_message(message.chat.id, "❌ Выберите регион из списка.")
            # Перезапускаем шаг, имитируя нажатие кнопки "Выбрать город"
            message.text = "🏙 Выбрать город"
            self.process_candidate_filter_choice(message)

    def process_candidate_city_choice(self, message):
        if message.text == "⬅️ Назад":
            # Возвращаемся к выбору региона
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for region in UZB_REGIONS.keys():
                markup.add(types.KeyboardButton(region))
            markup.add("⬅️ Назад")

            msg = self.bot.send_message(
                message.chat.id, "Выберите область/регион:", reply_markup=markup
            )
            self.bot.register_next_step_handler(
                msg, self.process_candidate_region_choice
            )
            return

        city = message.text
        self.show_candidates(message, city)

    def show_candidates(self, message, city=None):
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)

        if user_data and "company_name" in user_data:
            markup = keyboards.employer_main_menu(lang=lang)
        else:
            markup = keyboards.employer_menu(lang=lang)

        # Получаем список активных соискателей с фильтром
        seekers = database.get_all_seekers(limit=20, city=city, status="active")

        if not seekers:
            self.bot.send_message(
                message.chat.id,
                f"{get_text_by_lang('find_candidates_header', lang)}\n\n"
                f"{get_text_by_lang('no_active_seekers', lang)}",
                parse_mode="Markdown",
                reply_markup=markup,
            )
            return

        self.bot.send_message(
            message.chat.id,
            f"{get_text_by_lang('candidates_found', lang).format(count=len(seekers))}\n\n"
            f"{get_text_by_lang('candidate_list_header', lang)}",
            parse_mode="Markdown",
            reply_markup=markup,
        )

        for seeker in seekers:
            try:
                age_text = (
                    f"{seeker.get('age')} {get_text_by_lang('age_years', lang)}"
                    if seeker.get("age")
                    else get_text_by_lang("age_not_specified", lang)
                )
                city_text = seeker.get(
                    "city", get_text_by_lang("age_not_specified", lang)
                )

                # Обработка пола
                gender_val = seeker.get("gender")
                if gender_val == "male":
                    gender_text = get_text_by_lang("gender_male", lang)
                elif gender_val == "female":
                    gender_text = get_text_by_lang("gender_female", lang)
                else:
                    gender_text = get_text_by_lang("age_not_specified", lang)
                gender_line = f"{get_text_by_lang('gender_label', lang)} {utils.escape_markdown(gender_text)}\n"

                # Перевод профессии
                prof_raw = seeker.get("profession", "")
                prof_display = (
                    get_text_by_lang(prof_raw, lang)
                    if prof_raw and prof_raw.startswith("prof_")
                    else (prof_raw or get_text_by_lang("education_not_specified", lang))
                )

                # Перевод языков
                langs_raw = seeker.get("languages")
                langs_display = get_text_by_lang("languages_not_specified", lang)
                if langs_raw:
                    try:
                        if isinstance(langs_raw, str) and langs_raw.strip().startswith(
                            "["
                        ):
                            l_list = json.loads(langs_raw)
                            parts = []
                            for lang_item in l_list:
                                l_name = (
                                    get_text_by_lang(lang_item.get("lang_key"), lang)
                                    if lang_item.get("lang_key")
                                    else lang_item.get("lang_name", "?")
                                )
                                l_lvl = get_text_by_lang(
                                    lang_item.get("level_key"), lang
                                )
                                parts.append(f"{l_name} ({l_lvl})")
                            langs_display = ", ".join(parts)
                        else:
                            langs_display = langs_raw
                    except Exception:  # noqa: E722
                        langs_display = langs_raw

                card = (
                    f"👤 *{seeker['full_name']}*\n"
                    f"{gender_line}{get_text_by_lang('candidate_card_city', lang)} {city_text}\n"
                    f"{get_text_by_lang('candidate_card_age', lang)} {age_text}\n"
                    f"{get_text_by_lang('candidate_card_profession', lang)} "
                    f"{utils.escape_markdown(prof_display)}\n"
                    f"{get_text_by_lang('candidate_card_education', lang)} "
                    f"{utils.escape_markdown(seeker.get('education', get_text_by_lang('education_not_specified', lang)))}\n"
                    f"{get_text_by_lang('candidate_card_languages', lang)} {utils.escape_markdown(langs_display)}\n"
                    f"{get_text_by_lang('candidate_card_experience', lang)} "
                    f"{utils.escape_markdown(seeker.get('experience', get_text_by_lang('experience_not_specified', lang)))}\n"
                    f"{get_text_by_lang('candidate_card_skills', lang)} {utils.escape_markdown(seeker.get('skills', get_text_by_lang('skills_not_specified', lang)))}"
                )

                self.bot.send_message(
                    message.chat.id,
                    card,
                    parse_mode="Markdown",
                    # Добавляем кнопку "Пригласить"
                    reply_markup=keyboards.employer_invite_keyboard(
                        seeker["telegram_id"], lang=lang
                    ),
                )
            except Exception as e:
                logging.error(
                    f"❌ Ошибка при отправке карточки кандидата: {e}", exc_info=True
                )
