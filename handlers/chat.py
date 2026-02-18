import logging
from typing import Any, Optional

import database
import keyboards
from utils import formatters, misc, security


class ChatMixin:
    bot: Any
    handle_back_to_profile: Any

    def handle_start_chat(self, call):
        """Начало чата"""
        try:
            target_id = int(call.data.split("_")[2])
            user_id = call.from_user.id

            target_user = database.get_user_by_id(target_id)
            if not target_user:
                self.bot.answer_callback_query(call.id, "❌ Пользователь не найден")
                return

            assert target_user is not None
            target_name = (
                target_user.get("company_name")
                or target_user.get("full_name")
                or "Пользователь"
            )

            database.set_user_state(
                user_id,
                {
                    "step": "active_chat",
                    "target_id": target_id,
                    "target_name": target_name,
                },
            )

            self.bot.send_message(
                user_id,
                f"💬 *Чат с {formatters.escape_markdown(target_name)}*\n\n"
                f"Напишите ваше сообщение. Оно будет отправлено получателю.",
                parse_mode="Markdown",
                reply_markup=keyboards.cancel_keyboard(),
            )
            self.bot.answer_callback_query(call.id)
        except Exception as e:
            logging.error(f"Error starting chat: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка")

    def handle_chat_message(self, message):
        """Обработка сообщения в чате"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if not user_state or "target_id" not in user_state:
            self.handle_stop_chat(message, custom_text="❌ Сессия чата истекла.")
            return

        target_id = user_state["target_id"]
        sender = database.get_user_by_id(user_id)
        if not sender:
            self.handle_stop_chat(message, custom_text="❌ Ошибка авторизации.")
            return

        sender_name = (
            sender.get("company_name") or sender.get("full_name") or "Пользователь"
        )

        if security.contains_profanity(message.text):
            self.bot.send_message(
                user_id, "❌ Сообщение не отправлено: обнаружена нецензурная лексика."
            )
            return

        try:
            # Отправляем получателю
            self.bot.send_message(
                target_id,
                f"📩 *Сообщение от {formatters.escape_markdown(sender_name)}:*\n\n"
                f"{formatters.escape_markdown(message.text)}",
                parse_mode="Markdown",
                reply_markup=keyboards.reply_keyboard(user_id),
            )
            # Подтверждаем отправителю и автоматически завершаем чат
            self.handle_stop_chat(message, "✅ Сообщение отправлено.")
        except Exception as e:
            print(f"Failed to send chat message: {e}")
            # Завершаем чат при ошибке
            self.handle_stop_chat(
                message,
                "❌ Не удалось отправить сообщение. Возможно, пользователь заблокировал бота.",
            )

    def handle_stop_chat(self, message: Any, custom_text: Optional[str] = None) -> None:
        """Завершение чата"""
        user_id = message.from_user.id
        database.clear_user_state(user_id)

        user_data = database.get_user_by_id(user_id)
        if user_data:
            if "full_name" in user_data:
                markup = keyboards.seeker_main_menu()
            else:
                markup = keyboards.employer_main_menu()
        else:
            markup = keyboards.main_menu()

        text_to_send = custom_text if custom_text is not None else "❌ Чат завершен."

        self.bot.send_message(message.chat.id, text_to_send, reply_markup=markup)

    def handle_reply_admin_prompt(self, call):
        """Запрос ответа админу"""
        admin_id = int(call.data.split("_")[-1])
        database.set_user_state(
            call.from_user.id, {"step": "reply_to_admin", "target_admin_id": admin_id}
        )
        self.bot.send_message(
            call.message.chat.id,
            "✍️ Введите ваш ответ:",
            reply_markup=keyboards.cancel_keyboard(),
        )
        self.bot.answer_callback_query(call.id)

    def process_reply_to_admin(self, message):
        """Отправка ответа админу"""
        user_id = message.from_user.id
        state = database.get_user_state(user_id)
        admin_id = state.get("target_admin_id") if state else None

        if misc.cancel_request(message.text):
            database.clear_user_state(user_id)
            self.handle_back_to_profile(message)
            return

        try:
            user_info = database.get_user_by_id(user_id)
            assert user_info is not None
            name = (
                user_info.get("full_name")
                or user_info.get("company_name")
                or "Пользователь"
            )

            self.bot.send_message(
                admin_id,
                f"📩 *Ответ от {formatters.escape_markdown(name)} (ID: `{user_id}`):*\n\n{message.text}",  # noqa
                parse_mode="Markdown",
            )
            self.bot.send_message(message.chat.id, "✅ Ответ отправлен.")
            database.clear_user_state(user_id)
            self.handle_back_to_profile(message)
        except Exception as e:
            logging.error(f"Failed to reply to admin: {e}")
            self.bot.send_message(message.chat.id, "❌ Ошибка отправки.")
