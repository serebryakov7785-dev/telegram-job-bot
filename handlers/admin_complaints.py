import logging
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
from database.users import get_user_by_id


class AdminComplaintsMixin:
    bot: Any

    def _ensure_complaints_table_columns(self):
        try:
            columns = execute_query("PRAGMA table_info(complaints)", (), fetchall=True)
            if columns:
                col_names = [col['name'] for col in columns]
                if 'photo_id' not in col_names:
                    execute_query("ALTER TABLE complaints ADD COLUMN photo_id TEXT", commit=True)
                if 'status' not in col_names:
                    execute_query("ALTER TABLE complaints ADD COLUMN status TEXT DEFAULT 'new'", commit=True)
                if 'is_replied' not in col_names:
                    execute_query("ALTER TABLE complaints ADD COLUMN is_replied INTEGER DEFAULT 0", commit=True)
        except Exception as e:
            logging.error(f"Error migrating complaints table: {e}")

    def handle_complaints(self, message):
        self._ensure_complaints_table_columns()
        try:
            query = "SELECT id, user_id, user_name, type, message, photo_id, status, created_at, is_replied FROM " \
                    "complaints WHERE status = 'new' ORDER BY id DESC LIMIT 10"
            complaints = execute_query(query, (), fetchall=True)
        except Exception:
            complaints = []

        if not complaints:
            self.bot.send_message(message.chat.id, "📭 Список жалоб пуст.")
            return

        self.bot.send_message(message.chat.id, f"⚠️ *Новые жалобы ({len(complaints)}):*", parse_mode='Markdown')
        for c in complaints:
            self._send_complaint_item(message.chat.id, c)

    def _send_complaint_item(self, chat_id, c):
        reg_date = utils.format_db_datetime_to_tashkent(c.get('created_at'), '%d.%m.%Y %H:%M')
        user_info = get_user_by_id(c['user_id'])
        role_str, phone, email = "Неизвестно", "Не указан", "Не указан"
        if user_info:
            role_str = "Соискатель" if 'full_name' in user_info else "Работодатель"
            phone = user_info.get('phone', phone)
            email = user_info.get('email', email)

        text = f"ID: `{c['id']}` | 📌 {c['type']}\n👤 {utils.escape_markdown(c['user_name'])} (ID: `{c['user_id']}`)\n" \
               f"🎭 Роль: {role_str}\n📞 {utils.escape_markdown(phone)} | 📧 {utils.escape_markdown(email)}\n📝 " \
               f"{utils.escape_markdown(c['message'])}\n📅 {reg_date}"

        markup = types.InlineKeyboardMarkup(row_width=2)
        resolve_btn = types.InlineKeyboardButton("✅ Решено", callback_data=f"admin_resolve_complaint_{c['id']}")
        if not c.get('is_replied'):
            markup.add(resolve_btn,
                       types.InlineKeyboardButton("💬 Ответить", callback_data=f"admin_reply_{c['user_id']}_{c['id']}"))
        else:
            markup.add(resolve_btn)

        if c.get('photo_id'):
            try:
                self.bot.send_photo(chat_id, c['photo_id'], caption=text, parse_mode='Markdown', reply_markup=markup)
            except Exception:
                self.bot.send_message(chat_id, f"🖼️ *Не удалось загрузить фото*\n\n{text}", parse_mode='Markdown',
                                      reply_markup=markup)
        else:
            self.bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)

    def handle_resolve_complaint(self, call):
        try:
            complaint_id = int(call.data.split('_')[-1])
            execute_query("UPDATE complaints SET status = 'resolved' WHERE id = ?", (complaint_id,), commit=True)
            self.bot.answer_callback_query(call.id, "✅ Жалоба решена")
            new_text = (call.message.caption or call.message.text) + "\n\n*✅ Решено*"
            if call.message.photo:
                self.bot.edit_message_caption(caption=new_text, chat_id=call.message.chat.id,
                                              message_id=call.message.message_id, parse_mode='Markdown',
                                              reply_markup=None)
            else:
                self.bot.edit_message_text(text=new_text, chat_id=call.message.chat.id,
                                           message_id=call.message.message_id, parse_mode='Markdown',
                                           reply_markup=None)
        except Exception:
            self.bot.answer_callback_query(call.id, "❌ Ошибка")

    def handle_reply_prompt(self, call):
        data = call.data.split('_')
        set_user_state(call.from_user.id,
                       {'step': 'admin_reply_message', 'target_user_id': int(data[2]),
                        'complaint_id': int(data[3]) if len(data) > 3 else None,
                        'complaint_msg_id': call.message.message_id, 'complaint_chat_id': call.message.chat.id})
        self.bot.send_message(
            call.message.chat.id, "✍️ *Введите ответ пользователю:*",
            parse_mode='Markdown', reply_markup=keyboards.cancel_keyboard()
        )
        self.bot.answer_callback_query(call.id)

    def process_reply_message(self, message):
        user_id = message.from_user.id
        state = get_user_state(user_id)
        if utils.cancel_request(message.text):
            clear_user_state(user_id)
            self.bot.send_message(message.chat.id, "❌ Отменено", reply_markup=keyboards.admin_menu())
            return
        try:
            self.bot.send_message(state['target_user_id'], f"🔔 *Сообщение от администрации:*\n\n{message.text}",
                                  parse_mode='Markdown')
            self.bot.send_message(message.chat.id, "✅ Сообщение отправлено.", reply_markup=keyboards.admin_menu())
            if state.get('complaint_id'):
                execute_query("UPDATE complaints SET is_replied = 1 WHERE id = ?", (state['complaint_id'],), commit=True)
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton(
                        "✅ Решено", callback_data=f"admin_resolve_complaint_{state['complaint_id']}"
                    )
                )
                self.bot.edit_message_reply_markup(chat_id=state['complaint_chat_id'],
                                                   message_id=state['complaint_msg_id'], reply_markup=markup)
        except Exception:
            self.bot.send_message(message.chat.id, "❌ Не удалось отправить сообщение.",
                                  reply_markup=keyboards.admin_menu())
        clear_user_state(user_id)