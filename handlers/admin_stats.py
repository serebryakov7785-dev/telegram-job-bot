import logging
import os
from typing import Any

from telebot import types

import keyboards
from database.backup import create_backup
from database.core import execute_query


class AdminStatsMixin:
    bot: Any

    def handle_statistics(self, message):
        """Показывает статистику"""
        seekers_res = execute_query(
            "SELECT COUNT(*) as cnt FROM job_seekers", (), fetchone=True
        )
        employers_res = execute_query(
            "SELECT COUNT(*) as cnt FROM employers", (), fetchone=True
        )

        seekers_count = seekers_res["cnt"] if seekers_res else 0
        employers_count = employers_res["cnt"] if employers_res else 0
        total_count = seekers_count + employers_count

        self.bot.send_message(
            message.chat.id,
            f"📊 *Статистика бота*\n\n"
            f"• 👤 Соискатели: {seekers_count}\n"
            f"• 🏢 Работодатели: {employers_count}\n"
            f"• 👥 Всего пользователей: {total_count}\n"
            f"\nДля возврата в админ-меню нажмите /admin",
            parse_mode="Markdown",
            reply_markup=keyboards.admin_menu(),
        )

    def handle_admin_settings(self, message):
        """Обработка настроек админ-панели"""
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(
                "🔄 Очистить кэш", callback_data="admin_clear_cache"
            ),
            types.InlineKeyboardButton(
                "🛠 Режим обслуживания", callback_data="admin_maintenance"
            ),
        )
        self.bot.send_message(
            message.chat.id,
            "⚙️ *Настройки бота*\n\nВыберите действие:",
            parse_mode="Markdown",
            reply_markup=markup,
        )

    def handle_create_backup(self, message):
        """Создание резервной копии БД"""
        self.bot.send_message(
            message.chat.id, "⏳ *Создание резервной копии...*", parse_mode="Markdown"
        )
        success, result = create_backup()
        if success:
            try:
                with open(result, "rb") as f:
                    self.bot.send_document(
                        message.chat.id,
                        f,
                        caption=f"✅ *Бэкап успешно создан*\n📁 Файл: `{os.path.basename(result)}`",
                        parse_mode="Markdown",  # noqa
                    )
            except Exception as e:
                logging.error(f"Failed to send backup file: {e}")
            self.bot.send_message(
                message.chat.id,
                f"✅ *Бэкап создан*, но не удалось отправить файл.\nПуть: `{result}`",
                parse_mode="Markdown",
            )
        else:
            self.bot.send_message(
                message.chat.id,
                f"❌ *Ошибка при создании бэкапа:*\n{result}",
                parse_mode="Markdown",
            )
