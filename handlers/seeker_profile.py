import json
from datetime import datetime
from typing import Any

from telebot import types

import database
import keyboards
import utils
from localization import get_text_by_lang, get_user_language
from models import dict_to_job_seeker
from pdf_generator import generate_resume_pdf


class SeekerProfileMixin:
    bot: Any

    def handle_my_resume(self, message):
        """Просмотр резюме"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)
        if not user_data or "full_name" not in user_data:
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("auth_required_seeker", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.main_menu(lang=lang),
            )
            return

        # Преобразуем в модель
        seeker = dict_to_job_seeker(user_data)

        # Перевод профессии, если это ключ
        profession_display = seeker.profession
        if profession_display and profession_display.startswith("prof_"):
            profession_display = get_text_by_lang(profession_display, lang)

        # Обработка языков (JSON или текст)
        langs_val = seeker.languages
        langs_display = get_text_by_lang("languages_not_specified", lang)
        if langs_val and langs_val != "Не указаны":
            try:
                l_list = json.loads(langs_val)
                parts = []
                for lang_item in l_list:
                    l_name = (
                        get_text_by_lang(lang_item.get("lang_key"), lang)
                        if lang_item.get("lang_key")
                        else lang_item.get("lang_name", "?")
                    )
                    l_lvl = get_text_by_lang(lang_item.get("level_key"), lang)
                    parts.append(f"{l_name} ({l_lvl})")
                langs_display = ", ".join(parts)
            except Exception:
                langs_display = langs_val  # Fallback для старых данных

        # Обработка пола
        if seeker.gender == "male":
            gender_text = get_text_by_lang("gender_male", lang)
        elif seeker.gender == "female":
            gender_text = get_text_by_lang("gender_female", lang)
        else:
            gender_text = get_text_by_lang("age_not_specified", lang)
        gender_line = f"{get_text_by_lang('gender_label', lang)} {utils.escape_markdown(gender_text)}\n"

        age_text = (
            f"{seeker.age} {get_text_by_lang('age_years', lang)}"
            if seeker.age is not None and seeker.age > 0
            else get_text_by_lang("age_not_specified", lang)
        )
        status_text = (
            get_text_by_lang("status_active", lang)
            if seeker.status == "active"
            else get_text_by_lang("status_inactive", lang)
        )

        resume_text = (
            f"{get_text_by_lang('your_resume_header', lang)}\n"
            f"═══════════════════════════\n\n"
            f"{get_text_by_lang('full_name_label', lang)} "
            f"{utils.escape_markdown(seeker.full_name)}\n"
            f"{gender_line}"
            f"{get_text_by_lang('city_label', lang)} {utils.escape_markdown(seeker.city)}\n"
            f"{get_text_by_lang('age_label', lang)} {age_text}\n"
            f"{get_text_by_lang('phone_label', lang)} {utils.escape_markdown(seeker.phone)}\n"
            f"{get_text_by_lang('email_label', lang)} "
            f"{utils.escape_markdown(seeker.email)}\n"
            f"{get_text_by_lang('profession_label', lang)} {utils.escape_markdown(profession_display)}\n\n"
            f"{get_text_by_lang('education_label', lang).upper()}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{utils.escape_markdown(seeker.education)}\n\n"
            f"{get_text_by_lang('languages_label', lang).upper()}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{utils.escape_markdown(langs_display)}\n\n"
            f"{get_text_by_lang('skills_label', lang).upper()}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{utils.escape_markdown(seeker.skills)}\n\n"
            f"{get_text_by_lang('experience_label', lang).upper()}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{utils.escape_markdown(seeker.experience)}\n\n"
            f"═══════════════════════════\n"
            f"{get_text_by_lang('status_label', lang)} {status_text}"
        )

        # Добавляем кнопку скачивания PDF
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "📥 Скачать PDF", callback_data="download_resume"
            )
        )

        self.bot.send_message(
            message.chat.id, resume_text, parse_mode="Markdown", reply_markup=markup
        )
        # Меню отправляем отдельным сообщением, чтобы оно не пропало
        self.bot.send_message(
            message.chat.id,
            get_text_by_lang("main_menu", lang),
            reply_markup=keyboards.seeker_main_menu(lang=lang),
        )

    def handle_my_responses(self, message):
        """Мои отклики"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)
        if not user_data or "full_name" not in user_data:
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang("auth_required_seeker", lang),
                parse_mode="Markdown",
                reply_markup=keyboards.main_menu(lang=lang),
            )
            return

        # Получаем список откликов
        applications = database.get_seeker_applications(user_data["id"])

        if not applications:
            self.bot.send_message(
                message.chat.id,
                f"{get_text_by_lang('my_responses_header', lang)}\n\n"
                f"{get_text_by_lang('no_active_responses', lang)}",
                parse_mode="Markdown",
                reply_markup=keyboards.seeker_main_menu(lang=lang),
            )
            return

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang("your_responses_count", lang).format(
                count=len(applications)
            ),
            parse_mode="Markdown",
            reply_markup=keyboards.seeker_main_menu(lang=lang),
        )

        for app in applications:
            self._send_response_card(message.chat.id, app, lang)

    def _send_response_card(self, chat_id, app, lang):
        status_map = {
            "pending": get_text_by_lang("response_status_pending", lang),
            "accepted": get_text_by_lang("response_status_accepted", lang),
            "rejected": get_text_by_lang("response_status_rejected", lang),
        }
        status_text = status_map.get(
            app.get("status"), get_text_by_lang("response_status_unknown", lang)
        )

        created_at_raw = app.get("created_at")
        created_at_text = created_at_raw
        if created_at_raw:
            try:
                # Преобразуем дату в более читаемый формат
                dt_obj = datetime.strptime(
                    str(created_at_raw).split(".")[0], "%Y-%m-%d %H:%M:%S"
                )
                created_at_text = dt_obj.strftime("%d.%m.%Y")
            except (ValueError, AttributeError):
                pass  # Если формат другой, оставляем как есть

        card = (
            f"💼 *{utils.escape_markdown(app.get('title', 'Без названия'))}*\n"
            f"🏢 {utils.escape_markdown(app.get('company_name', 'Компания не указана'))}\n"
            f"💰 {utils.escape_markdown(app.get('salary', 'Не указана'))}\n"
            f"{get_text_by_lang('response_date_label', lang)} {created_at_text}\n"
            f"{get_text_by_lang('response_status_label', lang)} {status_text}"
        )

        self.bot.send_message(chat_id, card, parse_mode="Markdown")

    def handle_download_resume(self, call):
        """Генерация и отправка PDF резюме"""
        user_id = call.from_user.id
        lang = get_user_language(user_id)

        self.bot.answer_callback_query(call.id, "⏳ Генерирую PDF...")

        user_data = database.get_user_by_id(user_id)
        if not user_data:
            return

        try:
            pdf_file = generate_resume_pdf(user_data, lang)
            pdf_file.name = f"Resume_{user_data.get('full_name', 'user')}.pdf"

            self.bot.send_document(
                call.message.chat.id, pdf_file, caption="📄 Ваше резюме готово!"
            )
        except Exception as e:
            import logging

            logging.error(f"Error generating PDF: {e}")
            self.bot.send_message(call.message.chat.id, "❌ Ошибка при создании PDF.")
