import logging
from typing import Any

import database
import keyboards
from localization import get_text_by_lang, get_user_language
from utils import misc, security


class SupportMixin:
    bot: Any

    def handle_support(self, message):
        """Поддержка"""
        lang = get_user_language(message.from_user.id)
        self.bot.send_message(
            message.chat.id,
            f"{get_text_by_lang('support_header', lang)}\n\n"
            f"{get_text_by_lang('support_select_topic', lang)}",
            parse_mode="Markdown",
            reply_markup=keyboards.support_menu(lang=lang),
        )

    def handle_report_bug(self, message):
        """Обработка нажатия 'Ошибка'"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        database.set_user_state(user_id, {"step": "support_bug_report"})
        self.bot.send_message(
            message.chat.id,
            f"{get_text_by_lang('report_bug_header', lang)}\n\n"
            f"{get_text_by_lang('report_bug_prompt', lang)}",
            parse_mode="Markdown",
            reply_markup=keyboards.cancel_keyboard(lang=lang),
        )

    def handle_complaint(self, message):
        """Обработка нажатия 'Жалоба'"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        database.set_user_state(user_id, {"step": "support_complaint"})
        self.bot.send_message(
            message.chat.id,
            f"{get_text_by_lang('complaint_header', lang)}\n\n"
            f"{get_text_by_lang('complaint_prompt', lang)}",
            parse_mode="Markdown",
            reply_markup=keyboards.cancel_keyboard(lang=lang),
        )

    def _ensure_complaints_table(self):
        """Создание и миграция таблицы жалоб"""
        database.execute_query(
            """
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                type TEXT,
                message TEXT,
                photo_id TEXT,
                status TEXT DEFAULT 'new',
                is_replied INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
            commit=True,
        )

        try:
            columns = database.execute_query(
                "PRAGMA table_info(complaints)", (), fetchall=True
            )
            if columns:
                col_names = [col["name"] for col in columns]
                if "photo_id" not in col_names:
                    database.execute_query(
                        "ALTER TABLE complaints ADD COLUMN photo_id TEXT", commit=True
                    )
                if "status" not in col_names:
                    database.execute_query(
                        "ALTER TABLE complaints ADD COLUMN status TEXT DEFAULT 'new'",
                        commit=True,
                    )
                if "is_replied" not in col_names:
                    database.execute_query(
                        "ALTER TABLE complaints ADD COLUMN is_replied INTEGER DEFAULT 0",
                        commit=True,
                    )
        except Exception as e:
            logging.error(f"Ошибка миграции таблицы complaints: {e}")

    def process_support_message(self, message):
        """Обработка текста или фото обращения в поддержку"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        support_text = message.caption or message.text

        if misc.cancel_request(support_text):
            self._cancel_support(user_id, message.chat.id)
            return

        if not self._validate_support_message(message, support_text):
            return

        if not support_text and message.photo:  # noqa
            support_text = get_text_by_lang("support_no_description_photo", lang)

        user_state = database.get_user_state(user_id)
        topic = "Ошибка" if user_state.get("step") == "support_bug_report" else "Жалоба"
        photo_file_id = message.photo[-1].file_id if message.photo else None

        self._ensure_complaints_table()

        # Сохраняем обращение в базу данных
        database.execute_query(
            "INSERT INTO complaints (user_id, user_name, type, message, photo_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, message.from_user.first_name, topic, support_text, photo_file_id),
            commit=True,
        )

        database.clear_user_state(user_id)

        # Определяем, в какое меню вернуть пользователя
        user_data = database.get_user_by_id(user_id)
        markup = keyboards.main_menu()
        if user_data:
            if "full_name" in user_data:
                markup = keyboards.seeker_main_menu()
            elif "company_name" in user_data:
                markup = keyboards.employer_main_menu()

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang("support_message_accepted", lang),
            parse_mode="Markdown",
            reply_markup=markup,
        )

    def _cancel_support(self, user_id, chat_id):
        lang = get_user_language(user_id)
        database.clear_user_state(user_id)
        user_data = database.get_user_by_id(user_id)
        markup = keyboards.main_menu(lang=lang)
        if user_data:
            if "full_name" in user_data:
                markup = keyboards.seeker_main_menu(lang=lang)
            elif "company_name" in user_data:
                markup = keyboards.employer_main_menu(lang=lang)
        self.bot.send_message(
            chat_id, get_text_by_lang("support_cancelled", lang), reply_markup=markup
        )

    def _validate_support_message(self, message, support_text):
        lang = get_user_language(message.from_user.id)
        if not support_text and not message.photo:
            self.bot.send_message(
                message.chat.id, get_text_by_lang("support_no_text_no_photo", lang)
            )
            return False

        if security.contains_profanity(support_text):
            self.bot.send_message(
                message.chat.id, get_text_by_lang("support_profanity_error", lang)
            )
            return False
        return True
