import json
import logging
from typing import Any

from telebot import types

import database
import keyboards
import utils
from localization import get_text_by_lang, get_user_language


class EmployerResponseMixin:
    bot: Any

    def handle_invitation_callback(self, call):
        """Обработка нажатия кнопки 'Пригласить'"""
        try:
            employer_telegram_id = call.from_user.id
            parts = call.data.split("_")
            seeker_telegram_id = int(parts[1])
            vacancy_id_part = parts[2] if len(parts) > 2 else None

            vacancy_id = None
            should_select_vacancy = False

            if vacancy_id_part is None:
                should_select_vacancy = True
            elif vacancy_id_part.isdigit():
                vacancy_id = int(vacancy_id_part)
            elif vacancy_id_part == "general":
                vacancy_id = None
                should_select_vacancy = False

            # 1. Получаем данные работодателя
            employer_data = database.get_user_by_id(employer_telegram_id)
            if not employer_data or "company_name" not in employer_data:
                self.bot.answer_callback_query(
                    call.id, "❌ Ошибка: не найден профиль работодателя."
                )
                return

            # Если вакансия не выбрана (и не указано "general"), предлагаем выбрать из списка
            if should_select_vacancy:
                vacancies = database.get_employer_vacancies(employer_data["id"])
                active_vacancies = [
                    v for v in vacancies if v.get("status", "active") == "active"
                ]

                if active_vacancies:
                    markup = types.InlineKeyboardMarkup(row_width=1)
                    for vac in active_vacancies:
                        markup.add(
                            types.InlineKeyboardButton(
                                f"💼 {vac.get('title', 'Вакансия')}",
                                callback_data=f"invite_{seeker_telegram_id}_{vac['id']}",
                            )
                        )
                    markup.add(
                        types.InlineKeyboardButton(
                            "Просто пригласить (без вакансии)",
                            callback_data=f"invite_{seeker_telegram_id}_general",
                        )
                    )

                    self.bot.send_message(
                        call.message.chat.id,
                        "Выберите вакансию для приглашения:",
                        reply_markup=markup,
                    )
                    self.bot.answer_callback_query(call.id)
                    return

            # 2. Получаем данные соискателя
            seeker_data = database.get_user_by_id(seeker_telegram_id)
            if not seeker_data or "full_name" not in seeker_data:
                self.bot.answer_callback_query(
                    call.id, "❌ Ошибка: не найден профиль соискателя."
                )
                return

            # 3. Отправляем уведомление соискателю
            company_name = employer_data["company_name"]
            seeker_name = seeker_data["full_name"]

            seeker_lang = get_user_language(seeker_telegram_id)
            # Получаем данные вакансии
            vacancy_title = "Не указана"
            vacancy_salary = "Не указана"
            vacancy_type = "Не указан"
            vacancy_desc = "Нет описания"
            vacancy_languages = "Не указаны"
            vacancy_gender = get_text_by_lang("gender_any", seeker_lang)

            if vacancy_id:
                vac_data = database.execute_query(
                    "SELECT title, salary, job_type, description, languages, gender FROM vacancies WHERE id = ?",
                    (vacancy_id,),
                    fetchone=True,
                )
                if vac_data:
                    raw_title = vac_data.get("title", "Не указана")
                    vacancy_title = (
                        get_text_by_lang(raw_title, seeker_lang)
                        if raw_title.startswith("prof_")
                        else raw_title
                    )
                    vacancy_salary = vac_data.get("salary", "Не указана")

                    # Перевод типа занятости для соискателя
                    raw_type = vac_data.get("job_type", "Не указан")
                    if raw_type and not raw_type.startswith("job_type_"):
                        job_type_keys = [
                            "job_type_full_time",
                            "job_type_part_time",
                            "job_type_remote",
                            "job_type_internship",
                        ]
                        for key in job_type_keys:
                            if any(
                                get_text_by_lang(key, lang_code) == raw_type
                                for lang_code in ["ru", "uz", "en"]
                            ):  # noqa
                                raw_type = key
                                break

                    vacancy_type = get_text_by_lang(raw_type, seeker_lang)

                    vacancy_desc = vac_data.get("description", "Нет описания")

                    # Обработка пола
                    gender_val = vac_data.get("gender", "any")
                    if gender_val == "male":
                        vacancy_gender = get_text_by_lang("gender_male", seeker_lang)
                    elif gender_val == "female":
                        vacancy_gender = get_text_by_lang("gender_female", seeker_lang)
                    else:
                        vacancy_gender = get_text_by_lang("gender_any", seeker_lang)

                    # Перевод языков
                    langs_json = vac_data.get("languages")
                    if langs_json:
                        try:
                            l_list = json.loads(langs_json)
                            parts = []
                            for lang_item_data in l_list:
                                l_name = (
                                    get_text_by_lang(
                                        lang_item_data.get("lang_key"), seeker_lang
                                    )
                                    if lang_item_data.get("lang_key")
                                    else lang_item_data.get("lang_name")
                                )
                                l_level = get_text_by_lang(
                                    lang_item_data.get("level_key"), seeker_lang
                                )
                                parts.append(f"{l_name} ({l_level})")
                            vacancy_languages = ", ".join(parts)
                        except Exception:
                            vacancy_languages = langs_json

            invitation_text = (
                f"🎉 *Вас пригласили на собеседование!*\n\n"
                f"🏢 Компания: *{utils.escape_markdown(company_name)}*\n"
                f"💼 Вакансия: *{utils.escape_markdown(vacancy_title)}*\n"
                f"💰 Зарплата: {utils.escape_markdown(vacancy_salary)}\n"
                f"⏱ Тип: {utils.escape_markdown(vacancy_type)}\n"
                f"{get_text_by_lang('gender_label', seeker_lang)} {utils.escape_markdown(vacancy_gender)}\n"
                f"🗣 Языки: {utils.escape_markdown(vacancy_languages)}\n"
                f"📝 Описание: {utils.escape_markdown(vacancy_desc)}\n\n"
                f"Нажмите на кнопку ниже, чтобы написать сообщение работодателю."
            )

            # Попытка отправить сообщение
            try:
                self.bot.send_message(
                    seeker_telegram_id,
                    invitation_text,
                    parse_mode="Markdown",
                    reply_markup=keyboards.contact_employer_keyboard(
                        employer_telegram_id
                    ),
                )
            except Exception as e:
                logging.error(
                    f"Не удалось отправить приглашение соискателю {seeker_telegram_id}: {e}",
                    exc_info=True,
                )
                self.bot.answer_callback_query(
                    call.id,
                    "❌ Не удалось отправить приглашение. Возможно, соискатель заблокировал бота.",
                )
                return

            # Если отправка успешна, выполняем остальные действия
            # Если приглашение по вакансии, обновляем статус отклика
            if vacancy_id:
                database.execute_query(
                    "UPDATE applications SET status = 'accepted' "
                    "WHERE vacancy_id = ? AND seeker_id = ?",
                    (vacancy_id, seeker_data["id"]),
                    commit=True,
                )

            # 4. Отправляем подтверждение работодателю
            self.bot.answer_callback_query(
                call.id, f"✅ Приглашение для {seeker_name} отправлено!"
            )

            # Обновляем сообщение, добавляя статус
            new_text = call.message.text + "\n\n*✅ Приглашение отправлено!*"
            self.bot.edit_message_text(
                text=new_text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown",
                reply_markup=None,
            )
        except Exception as e:
            logging.error(f"❌ Ошибка в handle_invitation_callback: {e}", exc_info=True)
            self.bot.answer_callback_query(call.id, "❌ Произошла системная ошибка.")

    def handle_vacancy_responses(self, call, vacancy_id):
        """Показать отклики на вакансию"""
        self.bot.answer_callback_query(call.id)

        # Получаем данные откликнувшихся соискателей
        query = """
            SELECT js.full_name, js.gender, js.age, js.city, js.profession, js.education, js.experience, js.skills, js.languages,
                   js.phone,
                   js.email,
                   js.telegram_id
            FROM applications a
            JOIN job_seekers js ON a.seeker_id = js.id
            WHERE a.vacancy_id = ?
              AND js.status = 'active'
        """
        applicants = database.execute_query(query, (vacancy_id,), fetchall=True)

        if not applicants:
            self.bot.send_message(
                call.message.chat.id, "📭 На эту вакансию пока нет откликов."
            )
            return

        self.bot.send_message(
            call.message.chat.id,
            f"📋 *Отклики на вакансию ({len(applicants)}):*",
            parse_mode="Markdown",
        )

        for app in applicants:
            try:
                # app - это словарь (Row), используем ключи
                age_val = app.get("age")
                # Проверяем, что возраст есть и он больше 0
                age_text = (
                    f"({age_val} лет)"
                    if age_val and age_val > 0
                    else "(возраст не указан)"
                )
                city_text = app.get("city", "Не указан")

                # Обработка пола
                gender_val = app.get("gender")
                lang_code = get_user_language(call.from_user.id)
                if gender_val == "male":
                    gender_text = get_text_by_lang("gender_male", lang_code)
                elif gender_val == "female":
                    gender_text = get_text_by_lang("gender_female", lang_code)
                else:
                    gender_text = get_text_by_lang("age_not_specified", lang_code)
                gender_line = f"{get_text_by_lang('gender_label', lang_code)} {utils.escape_markdown(gender_text)}\n"

                # Перевод языков
                langs_raw = app.get("languages")
                langs_display = "Не указаны"
                if langs_raw:
                    try:
                        l_list = json.loads(langs_raw)
                        parts = []
                        for lang_item_data in l_list:
                            l_name = (
                                get_text_by_lang(
                                    lang_item_data.get("lang_key"),
                                    get_user_language(call.from_user.id),
                                )
                                if lang_item_data.get("lang_key")
                                else lang_item_data.get("lang_name", "?")
                            )
                            l_lvl = get_text_by_lang(
                                lang_item_data.get("level_key"),
                                get_user_language(call.from_user.id),
                            )
                            parts.append(f"{l_name} ({l_lvl})")
                        langs_display = ", ".join(parts)
                    except Exception:
                        langs_display = langs_raw

                # Перевод профессии
                prof_raw = str(app.get("profession", ""))
                prof_display = (
                    get_text_by_lang(prof_raw, get_user_language(call.from_user.id))
                    if prof_raw.startswith("prof_")
                    else prof_raw
                )

                txt = (
                    f"👤 *{utils.escape_markdown(str(app.get('full_name', '')))}* {age_text}\n"
                    f"{gender_line}"
                    f"🏙️ Город: {utils.escape_markdown(city_text)}\n"
                    f"🎯 {utils.escape_markdown(prof_display)}\n"
                    f"🎓 {utils.escape_markdown(str(app.get('education', '')))}\n"
                    f"🗣 Языки: {utils.escape_markdown(langs_display)}\n"
                    f"💼 {utils.escape_markdown(str(app.get('experience', '')))}\n"
                    f"🎨 {utils.escape_markdown(str(app.get('skills', '')))}"
                )

                self.bot.send_message(
                    call.message.chat.id,
                    txt,
                    parse_mode="Markdown",
                    reply_markup=keyboards.employer_invite_keyboard(
                        app.get("telegram_id"), vacancy_id
                    ),
                )
            except Exception as e:
                logging.error(
                    f"❌ Ошибка при отправке карточки отклика для вакансии {vacancy_id}: "
                    f"{e}",
                    exc_info=True,  # noqa
                )
                self.bot.send_message(
                    call.message.chat.id,
                    "⚠️ Не удалось загрузить карточку одного из кандидатов из-за ошибки.",
                )

    def handle_employer_chats(self, message):
        """Меню чатов работодателя (список соискателей с которыми есть связь)"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)

        if not user_data or "company_name" not in user_data:
            self.bot.send_message(message.chat.id, "❌ Ошибка авторизации.")
            return

        # Получаем список соискателей, которым отправлено приглашение (status='accepted')
        query = """
            SELECT js.full_name, v.title, js.telegram_id
            FROM applications a
            JOIN vacancies v ON a.vacancy_id = v.id
            JOIN job_seekers js ON a.seeker_id = js.id
            WHERE v.employer_id = ? AND a.status = 'accepted'
        """
        chats = database.execute_query(query, (user_data["id"],), fetchall=True)

        if not chats:
            self.bot.send_message(
                message.chat.id, get_text_by_lang("no_active_chats_employer", lang)
            )
            return

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang("employer_chats_header", lang).format(count=len(chats)),
            parse_mode="Markdown",
        )

        for chat in chats:
            try:
                text = (
                    f"{get_text_by_lang('chat_candidate_label', lang)} "
                    f"*{utils.escape_markdown(chat['full_name'])}*\n"
                    f"{get_text_by_lang('chat_vacancy_label', lang)} "
                    f"*{utils.escape_markdown(chat['title'])}*"
                )
                self.bot.send_message(
                    message.chat.id,
                    text,
                    parse_mode="Markdown",
                    reply_markup=keyboards.contact_seeker_keyboard(chat["telegram_id"]),
                )
            except Exception as e:
                logging.error(
                    f"❌ Ошибка при отправке чата работодателя: {e}", exc_info=True
                )
