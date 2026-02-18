import json
import logging
import os

import utils
from config import Config
from handlers.admin_broadcast import AdminBroadcastMixin
from handlers.admin_complaints import AdminComplaintsMixin
from handlers.admin_stats import AdminStatsMixin
from handlers.admin_users import AdminUsersMixin


class AdminHandlers(
    AdminStatsMixin, AdminBroadcastMixin, AdminUsersMixin, AdminComplaintsMixin
):
    def __init__(self, bot):
        self.bot = bot

    def register(self, bot):
        """Регистрация обработчиков администратора"""
        bot.register_message_handler(self.handle_backup_command, commands=["backup"])
        bot.register_message_handler(self.handle_logs, commands=["logs"])

        # Меню
        bot.register_message_handler(
            self.handle_statistics,
            func=lambda m: m.text == "📊 Статистика"
            and m.from_user.id in Config.ADMIN_IDS,
        )
        bot.register_message_handler(
            self.handle_broadcast_start,
            func=lambda m: m.text == "📢 Рассылка"
            and m.from_user.id in Config.ADMIN_IDS,
        )
        bot.register_message_handler(
            self.handle_users,
            func=lambda m: m.text == "👥 Пользователи"
            and m.from_user.id in Config.ADMIN_IDS,
        )
        bot.register_message_handler(
            self.handle_list_seekers,
            func=lambda m: m.text == "📋 Список соискателей"
            and m.from_user.id in Config.ADMIN_IDS,
        )
        bot.register_message_handler(
            self.handle_list_employers,
            func=lambda m: m.text == "📋 Список работодателей"
            and m.from_user.id in Config.ADMIN_IDS,
        )
        bot.register_message_handler(
            self.handle_complaints,
            func=lambda m: m.text == "⚠️ Жалобы" and m.from_user.id in Config.ADMIN_IDS,
        )
        bot.register_message_handler(
            self.handle_search_user_prompt,
            func=lambda m: m.text == "🔎 Поиск пользователя"
            and m.from_user.id in Config.ADMIN_IDS,
        )
        bot.register_message_handler(
            self.handle_admin_settings,
            func=lambda m: m.text == "⚙️ Настройки бота"
            and m.from_user.id in Config.ADMIN_IDS,
        )
        bot.register_message_handler(
            self.handle_create_backup,
            func=lambda m: m.text == "💾 Бэкап" and m.from_user.id in Config.ADMIN_IDS,
        )

        # Callbacks
        bot.register_callback_query_handler(
            self.handle_admin_callbacks, func=lambda c: c.data.startswith("admin_")
        )

    def handle_admin_callbacks(self, call):
        """Центральный обработчик для всех admin-колбэков."""
        try:
            if call.data.startswith("admin_resolve_complaint_"):
                return self.handle_resolve_complaint(call)
            if call.data.startswith("admin_reply_"):
                return self.handle_reply_prompt(call)
            if call.data.startswith("admin_block_menu_"):
                return self.handle_block_menu(call)
            if call.data.startswith("admin_block_"):
                return self.handle_block_confirm(call)
            if call.data.startswith("admin_unblock_"):
                return self.handle_unblock_user(call)
            if call.data.startswith("admin_write_"):
                return self.handle_write_prompt(call)
            # Другие admin колбэки можно добавить здесь
        except Exception as e:
            logging.error(f"Error in handle_admin_callbacks: {e}", exc_info=True)
            self.bot.answer_callback_query(call.id, "❌ Произошла ошибка")

    def handle_backup_command(self, message):
        if message.from_user.id not in Config.ADMIN_IDS:
            self.bot.send_message(message.chat.id, "❌ У вас нет прав доступа.")
            return
        self.handle_create_backup(message)

    def handle_logs(self, message):
        if message.from_user.id not in Config.ADMIN_IDS:
            return

        try:
            log_file = os.getenv("LOG_FILE", "bot.json.log")
            if not os.path.exists(log_file):
                self.bot.reply_to(message, "❌ Лог-файл не найден.")
                return

            # Читаем последние 15 строк
            lines = []
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    from collections import deque

                    lines = list(deque(f, 15))
            except Exception as e:
                logging.error(f"Error reading log file: {e}")
                self.bot.reply_to(message, "❌ Ошибка доступа к файлу логов.")
                return

            if not lines:
                self.bot.reply_to(message, "📭 Лог пуст.")
                return

            formatted_logs = ""
            for line in lines:
                try:
                    entry = json.loads(line)
                    dt = (
                        entry.get("time", "").split(" ")[1].split(",")[0]
                        if " " in entry.get("time", "")
                        else entry.get("time", "")
                    )
                    level = entry.get("level", "INFO")
                    msg = entry.get("message", "")
                    icon = (
                        "🔴"
                        if level in ["ERROR", "CRITICAL"]
                        else "⚠️" if level == "WARNING" else "ℹ️"
                    )
                    formatted_logs += (
                        f"{icon} `{dt}` *{level}*: {utils.escape_markdown(msg)}\n"
                    )
                except json.JSONDecodeError:
                    formatted_logs += f"`{utils.escape_markdown(line.strip())}`\n"

            if len(formatted_logs) > 4000:
                formatted_logs = formatted_logs[-4000:]

            self.bot.reply_to(
                message,
                f"📋 *Последние логи:*\n\n{formatted_logs}",
                parse_mode="Markdown",
            )

        except Exception as e:
            logging.error(f"Error in logs command: {e}", exc_info=True)
            self.bot.reply_to(message, "❌ Произошла ошибка при получении логов.")
