import time
from typing import Any

from telebot import types
from telebot.apihelper import ApiTelegramException

import keyboards
import utils
from database.core import (
    clear_user_state,
    execute_query,
    get_user_state,
    set_user_state,
)


class AdminBroadcastMixin:
    bot: Any

    def handle_broadcast_start(self, message):
        """Начало создания рассылки"""
        set_user_state(message.from_user.id, {'step': 'admin_broadcast_message'})
        self.bot.send_message(
            message.chat.id,
            "📢 *Создание рассылки*\n\n"
            "Введите текст сообщения для рассылки. "
            "Вы можете использовать Markdown для форматирования.\n\n"
            "Сообщение будет отправлено ВСЕМ пользователям бота (соискателям и работодателям).",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )

    def process_broadcast_message(self, message):
        """Получение текста рассылки и запрос подтверждения"""
        user_id = message.from_user.id
        if utils.cancel_request(message.text):
            clear_user_state(user_id)
            self.bot.send_message(user_id, "❌ Рассылка отменена.", reply_markup=keyboards.admin_menu())
            return

        user_state = get_user_state(user_id) or {}
        user_state['broadcast_message'] = message.text
        user_state['step'] = 'admin_broadcast_confirm'
        set_user_state(user_id, user_state)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('✅ Да, отправить', '❌ Нет, отменить')

        self.bot.send_message(
            user_id,
            f"🤔 *Подтверждение рассылки*\n\n"
            f"Вы уверены, что хотите отправить следующее сообщение?\n\n"
            f"----------\n{message.text}\n----------\n\n"
            f"Сообщение будет отправлено всем пользователям.",
            parse_mode='Markdown',
            reply_markup=markup
        )

    def process_broadcast_confirm(self, message):
        """Подтверждение и отправка рассылки"""
        user_id = message.from_user.id
        user_state = get_user_state(user_id)

        if message.text == '❌ Нет, отменить':
            clear_user_state(user_id)
            self.bot.send_message(user_id, "❌ Рассылка отменена.", reply_markup=keyboards.admin_menu())
            return

        if message.text != '✅ Да, отправить':
            self.bot.send_message(message.chat.id, "Пожалуйста, выберите один из вариантов.")
            return

        broadcast_message = user_state.get('broadcast_message')
        if not broadcast_message:
            clear_user_state(user_id)
            self.bot.send_message(
                user_id,
                "❌ Ошибка: сообщение для рассылки не найдено.",
                reply_markup=keyboards.admin_menu()
            )
            return

        clear_user_state(user_id)
        self.bot.send_message(
            user_id, "⏳ *Начинаю рассылку...*", parse_mode='Markdown', reply_markup=keyboards.admin_menu()
        )

        all_users = set()
        for table in ['job_seekers', 'employers']:
            query = f"SELECT telegram_id FROM {table}"  # nosec B608
            users = execute_query(query, (), fetchall=True)
            if users:
                for u in users:
                    all_users.add(u['telegram_id'])

        sent_count, failed_count, deactivated_count = 0, 0, 0

        for telegram_id in all_users:
            try:
                self.bot.send_message(telegram_id, broadcast_message, parse_mode='Markdown')
                sent_count += 1
                time.sleep(0.05)
            except ApiTelegramException as e:
                if e.error_code in [400, 403]:  # noqa
                    execute_query("DELETE FROM job_seekers WHERE telegram_id = ?", (telegram_id,), commit=True)
                    execute_query("DELETE FROM employers WHERE telegram_id = ?", (telegram_id,), commit=True)
                    deactivated_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1

        self.bot.send_message(
            user_id,
            f"✅ *Рассылка завершена!*\n\n• ✅ Отправлено: {sent_count}\n"
            f"• 🗑️ Удалено (неактив): {deactivated_count}\n• ❌ Ошибок: {failed_count}",
            parse_mode='Markdown'
        )