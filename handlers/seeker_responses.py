import logging
from typing import Any

import database
import keyboards
import utils
from localization import get_text_by_lang, get_user_language
from pdf_generator import generate_resume_pdf


class SeekerResponseMixin:
    bot: Any

    def handle_application_callback(self, call):
        """Обработка нажатия кнопки 'Откликнуться'"""
        try:
            user_id = call.from_user.id
            lang = get_user_language(user_id)
            vacancy_id = int(call.data.split("_")[1])

            user_data = database.get_user_by_id(user_id)
            if not user_data or "full_name" not in user_data:
                self.bot.answer_callback_query(
                    call.id,
                    get_text_by_lang("auth_required_seeker", lang).replace("*", ""),
                )
                return

            # Проверяем, не откликался ли уже
            if database.check_application_exists(vacancy_id, user_data["id"]):
                self.bot.answer_callback_query(
                    call.id, "⚠️ Вы уже откликнулись на эту вакансию!"
                )
                return

            # Создаем отклик
            if database.create_application(vacancy_id, user_data["id"]):
                self.bot.answer_callback_query(call.id, "✅ Отклик отправлен!")
                self.bot.send_message(
                    call.message.chat.id, "✅ Вы успешно откликнулись на вакансию!"
                )
                # Уведомляем работодателя и отправляем PDF
                self._notify_employer_with_pdf(vacancy_id, user_data)
            else:
                self.bot.answer_callback_query(
                    call.id, "❌ Ошибка при отправке отклика."
                )
        except Exception as e:
            logging.error(
                f"❌ Ошибка в handle_application_callback: {e}", exc_info=True
            )
            self.bot.answer_callback_query(call.id, "❌ Произошла ошибка.")

    def _notify_employer_with_pdf(self, vacancy_id, seeker_data):
        """Отправка уведомления и PDF резюме работодателю"""
        try:
            # Получаем данные работодателя и вакансии
            query = """
                SELECT v.title, e.telegram_id, e.language_code 
                FROM vacancies v
                JOIN employers e ON v.employer_id = e.id
                WHERE v.id = ?
            """
            res = database.execute_query(query, (vacancy_id,), fetchone=True)

            if not res:
                return

            emp_id = res["telegram_id"]
            lang = res.get("language_code", "ru")
            title = res["title"]

            # Перевод названия вакансии, если это ключ
            if title.startswith("prof_"):
                title = get_text_by_lang(title, lang)

            # Генерируем PDF
            pdf = generate_resume_pdf(seeker_data, lang)
            pdf.name = f"Resume_{seeker_data.get('full_name', 'Candidate')}.pdf"

            caption = f"{get_text_by_lang('new_application_notify', lang)}\n\n💼 Вакансия: *{utils.escape_markdown(title)}*\n👤 Кандидат: *{utils.escape_markdown(seeker_data.get('full_name'))}*"

            # Отправляем PDF работодателю
            self.bot.send_document(emp_id, pdf, caption=caption, parse_mode="Markdown")

        except Exception as e:
            logging.error(f"Error notifying employer: {e}")

    def handle_seeker_chats(self, message):
        """Меню чатов соискателя (список приглашений)"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)
        if not user_data or "full_name" not in user_data:
            self.bot.send_message(message.chat.id, "❌ Ошибка авторизации.")
            return

        # Получаем список приглашений (отклики со статусом accepted)
        query = """
            SELECT v.title, e.company_name, e.telegram_id
            FROM applications a
            JOIN vacancies v ON a.vacancy_id = v.id
            JOIN employers e ON v.employer_id = e.id
            WHERE a.seeker_id = ? AND a.status = 'accepted'
        """
        invitations = database.execute_query(query, (user_data["id"],), fetchall=True)

        if not invitations:
            self.bot.send_message(
                message.chat.id, get_text_by_lang("no_active_chats_seeker", lang)
            )
            return

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang("your_chats_header", lang).format(count=len(invitations)),
            parse_mode="Markdown",
        )

        for inv in invitations:
            # Перевод названия вакансии
            title_raw = inv["title"]
            title_display = (
                get_text_by_lang(title_raw, lang)
                if title_raw and title_raw.startswith("prof_")
                else title_raw
            )

            text = (
                f"{get_text_by_lang('chat_company_label', lang)} *{utils.escape_markdown(inv['company_name'])}*\n"  # noqa
                f"{get_text_by_lang('chat_vacancy_label', lang)} *{utils.escape_markdown(title_display)}*\n"  # noqa
                f"{get_text_by_lang('chat_invitation_label', lang)}"
            )
            self.bot.send_message(
                message.chat.id,
                text,
                parse_mode="Markdown",
                reply_markup=keyboards.contact_employer_keyboard(inv["telegram_id"]),
            )
