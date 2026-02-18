from datetime import datetime, timedelta
from typing import Any

from telebot import types

import keyboards
import utils
from database.core import (
    clear_user_state,
    execute_query,
    get_user_state,
    set_user_state,
)


class AdminUsersMixin:
    bot: Any

    def handle_users(self, message):
        """Меню управления пользователями"""
        self.bot.send_message(
            message.chat.id,
            "👥 *Управление пользователями*\n\nВыберите действие:",
            parse_mode='Markdown', reply_markup=keyboards.admin_users_menu()
        )

    def _list_users(self, message, table, title):
        name_col = 'full_name' if table == 'job_seekers' else 'company_name'
        # fmt: off
        query = f"SELECT telegram_id, {name_col} as name, phone, email, created_at FROM {table} ORDER BY id DESC LIMIT 10"  # nosec B608
        # fmt: on
        users = execute_query(query, (), fetchall=True)
        if not users:
            self.bot.send_message(message.chat.id, "Список пуст.")
            return
        text = f"📋 *Последние 10 {title} (время по Ташкенту):*\n\n"
        for u in users:
            reg_date = utils.format_db_datetime_to_tashkent(
                u.get('created_at'), '%d.%m.%Y %H:%M'
            )
            text += f"{'👤' if table == 'job_seekers' else '🏢'} *{utils.escape_markdown(u['name'])}*\n"
            text += f"🆔 `{u['telegram_id']}` | 📞 {u['phone']}\n"
            text += f"📧 {utils.escape_markdown(u.get('email') or 'Не указан')}\n"
            text += f"📅 {reg_date}\n\n"
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown')

    def handle_list_seekers(self, message): self._list_users(message, 'job_seekers', 'соискателей')

    def handle_list_employers(self, message): self._list_users(message, 'employers', 'работодателей')

    def handle_search_user_prompt(self, message):
        set_user_state(message.from_user.id, {'step': 'admin_search_user'})
        self.bot.send_message(
            message.chat.id,
            "🔎 *Поиск пользователя*\n\nВведите Telegram ID, номер телефона или часть имени:",
            parse_mode='Markdown', reply_markup=keyboards.cancel_keyboard()
        )

    def process_search_user(self, message):
        self._ensure_blocked_table()
        user_id = message.from_user.id
        if utils.cancel_request(message.text):
            clear_user_state(user_id)
            self.handle_users(message)
            return
        search_query = message.text.strip()
        params = (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%")  # noqa

        seekers = execute_query(
            "SELECT 'seeker' as type, telegram_id, full_name as name, phone, email FROM job_seekers WHERE "
            "telegram_id LIKE ? OR phone LIKE ? OR full_name LIKE ? LIMIT 5", params, fetchall=True) or []
        employers = execute_query(
            "SELECT 'employer' as type, telegram_id, company_name as name, phone, email FROM employers WHERE "
            "telegram_id LIKE ? OR phone LIKE ? OR company_name LIKE ? LIMIT 5", params, fetchall=True) or []
        results = seekers + employers

        if not results:
            self.bot.send_message(
                message.chat.id, "❌ Пользователи не найдены.", reply_markup=keyboards.admin_users_menu()
            )
            clear_user_state(user_id)
            return

        self.bot.send_message(
            message.chat.id, f"🔎 *Результаты поиска:* \"{utils.escape_markdown(search_query)}\"", parse_mode='Markdown'
        )
        for u in results:  # noqa
            is_blocked = False
            blk = execute_query("SELECT blocked_until FROM blocked_users WHERE telegram_id = ?", (u['telegram_id'],), fetchone=True)
            if blk:
                if blk['blocked_until'] == 'forever':
                    is_blocked = True
                else:
                    try:
                        if datetime.now() < datetime.strptime(blk['blocked_until'], '%Y-%m-%d %H:%M:%S'):
                            is_blocked = True
                    except Exception:  # noqa
                        pass

            text = f"{'👤' if u['type'] == 'seeker' else '🏢'} *{utils.escape_markdown(u['name'])}*\n"
            if is_blocked:
                text += "🚫 *СТАТУС: ЗАБЛОКИРОВАН*\n"
            text += f"🆔 `{u['telegram_id']}` | 📞 {u['phone']}\n"
            text += f"📧 {utils.escape_markdown(u.get('email') or 'Не указан')}\n\n"
            self.bot.send_message(
                message.chat.id, text, parse_mode='Markdown',
                reply_markup=keyboards.admin_user_action_keyboard(u['telegram_id'], is_blocked=is_blocked)
            )

        clear_user_state(user_id)
        self.bot.send_message(message.chat.id, "✅ Поиск завершен", reply_markup=keyboards.admin_users_menu())

    def _ensure_blocked_table(self):
        execute_query(
            "CREATE TABLE IF NOT EXISTS blocked_users (telegram_id INTEGER PRIMARY KEY, blocked_until TEXT, "
            "reason TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)", commit=True
        )

    def handle_block_menu(self, call):
        self._ensure_blocked_table()
        user_id = call.data.split('_')[-1]
        self.bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=keyboards.block_duration_keyboard(user_id)
        )

    def handle_block_confirm(self, call):
        data = call.data.split('_')
        target_id, duration_str = int(data[2]), data[3]
        if duration_str == 'cancel':
            self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                               reply_markup=keyboards.admin_user_action_keyboard(target_id))
            return

        now = datetime.now()
        if duration_str == '1h':
            blocked_until = (now + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        elif duration_str == '12h':
            blocked_until = (now + timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')
        elif duration_str == '24h':
            blocked_until = (now + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        elif duration_str == 'forever':
            blocked_until = 'forever'
        else:
            return

        execute_query("INSERT OR REPLACE INTO blocked_users (telegram_id, blocked_until) VALUES (?, ?)",
                      (target_id, blocked_until), commit=True)
        try:
            msg = "🚫 *Ваш аккаунт был заблокирован администратором навсегда.*" if duration_str == 'forever' else \
                f"🚫 *Ваш аккаунт заблокирован.*\n⏳ До: {blocked_until}"
            self.bot.send_message(target_id, msg, parse_mode='Markdown', reply_markup=types.ReplyKeyboardRemove())
        except Exception:
            pass

        self.bot.answer_callback_query(call.id, "✅ Пользователь заблокирован")
        self.bot.edit_message_text(text=f"{call.message.text}\n\n🚫 *ЗАБЛОКИРОВАН* ({duration_str})",
                                   chat_id=call.message.chat.id, message_id=call.message.message_id,
                                   parse_mode='Markdown', reply_markup=None)

    def handle_unblock_user(self, call):
        user_id = int(call.data.split('_')[-1])
        execute_query("DELETE FROM blocked_users WHERE telegram_id = ?", (user_id,), commit=True)
        self.bot.answer_callback_query(call.id, "✅ Пользователь разблокирован")
        self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                           reply_markup=keyboards.admin_user_action_keyboard(user_id, is_blocked=False))
        try:
            self.bot.send_message(user_id, "✅ *Ваш аккаунт был разблокирован.*", parse_mode='Markdown')
        except Exception:
            pass

    def handle_write_prompt(self, call):
        target_id = int(call.data.split('_')[-1])
        set_user_state(call.from_user.id, {'step': 'admin_write_user', 'target_user_id': target_id})
        self.bot.send_message(call.message.chat.id, "✍️ Введите сообщение для пользователя:",
                              reply_markup=keyboards.cancel_keyboard())
        self.bot.answer_callback_query(call.id)

    def process_write_message(self, message):
        user_id = message.from_user.id
        state = get_user_state(user_id)
        target_id = state.get('target_user_id')
        if utils.cancel_request(message.text):
            clear_user_state(user_id)
            self.bot.send_message(message.chat.id, "❌ Отменено", reply_markup=keyboards.admin_users_menu())
            return
        try:
            self.bot.send_message(
                target_id, f"🔔 *Сообщение от администрации:*\n\n{message.text}",
                parse_mode='Markdown', reply_markup=keyboards.user_reply_keyboard(user_id)
            )
            self.bot.send_message(message.chat.id, "✅ Сообщение отправлено.", reply_markup=keyboards.admin_users_menu())
        except Exception:
            self.bot.send_message(message.chat.id, "❌ Ошибка отправки (возможно, бот заблокирован).",
                                  reply_markup=keyboards.admin_users_menu())
        clear_user_state(user_id)