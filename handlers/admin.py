# handlers/admin.py
from database.core import execute_query, set_user_state, get_user_state, clear_user_state
from database.users import get_user_by_id
from database.backup import create_backup
import keyboards
import utils
import logging
from telebot import types
import time
import os
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    try:
        # For Python < 3.9
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        ZoneInfo = None


class AdminHandlers:
    def __init__(self, bot):
        self.bot = bot

    def handle_statistics(self, message):
        """Показывает статистику"""
        # Используем прямой запрос
        seekers_res = execute_query("SELECT COUNT(*) as cnt FROM job_seekers", (), fetchone=True)
        employers_res = execute_query("SELECT COUNT(*) as cnt FROM employers", (), fetchone=True)

        seekers_count = seekers_res['cnt'] if seekers_res else 0
        employers_count = employers_res['cnt'] if employers_res else 0
        total_count = seekers_count + employers_count

        self.bot.send_message(
            message.chat.id,
            f"📊 *Статистика бота*\n\n"
            f"• 👤 Соискатели: {seekers_count}\n"
            f"• 🏢 Работодатели: {employers_count}\n"
            f"• 👥 Всего пользователей: {total_count}\n"
            f"\nДля возврата в админ-меню нажмите /admin",
            parse_mode='Markdown',
            reply_markup=keyboards.admin_menu()
        )

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
            f"----------\n"
            f"{message.text}\n"
            f"----------\n\n"
            f"Сообщение будет отправлено всем пользователям.",
            parse_mode='Markdown',
            reply_markup=markup
        )

    def process_broadcast_confirm(self, message):  # noqa: C901
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
            self.bot.send_message(user_id, "❌ Ошибка: сообщение для рассылки не найдено. Попробуйте снова.",
                                  reply_markup=keyboards.admin_menu())
            return

        clear_user_state(user_id)
        self.bot.send_message(user_id, "⏳ *Начинаю рассылку...*", parse_mode='Markdown', reply_markup=keyboards.admin_menu())

        # Получаем ID всех пользователей напрямую
        all_users = set()

        seekers = execute_query("SELECT telegram_id FROM job_seekers", (), fetchall=True)
        if seekers:
            for s in seekers:
                all_users.add(s['telegram_id'])

        employers = execute_query("SELECT telegram_id FROM employers", (), fetchall=True)
        if employers:
            for e in employers:
                all_users.add(e['telegram_id'])

        sent_count = 0
        failed_count = 0

        for telegram_id in all_users:
            try:
                self.bot.send_message(telegram_id, broadcast_message, parse_mode='Markdown')
                sent_count += 1
                time.sleep(0.1)  # Задержка, чтобы не превышать лимиты Telegram
            except Exception as e:
                logging.warning(f"Failed to send message to {telegram_id}: {e}")
                failed_count += 1

        self.bot.send_message(
            user_id,
            f"✅ *Рассылка завершена!*\n\n"
            f"• Отправлено: {sent_count}\n"
            f"• Ошибок: {failed_count}",
            parse_mode='Markdown'
        )

    def handle_users(self, message):
        """Меню управления пользователями"""
        self.bot.send_message(
            message.chat.id,
            "👥 *Управление пользователями*\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=keyboards.admin_users_menu()
        )

    def handle_list_seekers(self, message):
        """Список последних соискателей"""
        query = "SELECT telegram_id, full_name, phone, email, created_at FROM job_seekers ORDER BY id DESC LIMIT 10"
        users = execute_query(query, (), fetchall=True)

        if not users:
            self.bot.send_message(message.chat.id, "Список пуст.")
            return

        text = "📋 *Последние 10 соискателей (время по Ташкенту):*\n\n"
        for u in users:
            reg_date_str = u.get('created_at')
            if reg_date_str:
                try:
                    # Assuming format 'YYYY-MM-DD HH:MM:SS' from SQLite in UTC
                    utc_dt = datetime.strptime(str(reg_date_str).split('.')[0], '%Y-%m-%d %H:%M:%S')
                    if ZoneInfo:
                        tashkent_dt = utc_dt.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo("Asia/Tashkent"))
                    else:
                        tashkent_dt = utc_dt + timedelta(hours=5)
                    reg_date = tashkent_dt.strftime('%d.%m.%Y %H:%M')
                except (ValueError, TypeError):
                    reg_date = reg_date_str  # Fallback
            else:
                reg_date = "N/A"

            text += f"👤 *{utils.escape_markdown(u['full_name'])}*\n"
            text += f"🆔 `{u['telegram_id']}` | 📞 {u['phone']}\n"
            text += f"📧 {utils.escape_markdown(u.get('email') or 'Не указан')}\n"
            text += f"📅 {reg_date}\n\n"

        self.bot.send_message(message.chat.id, text, parse_mode='Markdown')

    def handle_list_employers(self, message):
        """Список последних работодателей"""
        query = "SELECT telegram_id, company_name, phone, email, created_at FROM employers ORDER BY id DESC LIMIT 10"
        users = execute_query(query, (), fetchall=True)

        if not users:
            self.bot.send_message(message.chat.id, "Список пуст.")
            return

        text = "📋 *Последние 10 работодателей (время по Ташкенту):*\n\n"
        for u in users:
            reg_date_str = u.get('created_at')
            if reg_date_str:
                try:
                    # Assuming format 'YYYY-MM-DD HH:MM:SS' from SQLite in UTC
                    utc_dt = datetime.strptime(str(reg_date_str).split('.')[0], '%Y-%m-%d %H:%M:%S')
                    if ZoneInfo:
                        tashkent_dt = utc_dt.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo("Asia/Tashkent"))
                    else:
                        tashkent_dt = utc_dt + timedelta(hours=5)
                    reg_date = tashkent_dt.strftime('%d.%m.%Y %H:%M')
                except (ValueError, TypeError):
                    reg_date = reg_date_str  # Fallback
            else:
                reg_date = "N/A"

            text += f"🏢 *{utils.escape_markdown(u['company_name'])}*\n"
            text += f"🆔 `{u['telegram_id']}` | 📞 {u['phone']}\n"
            text += f"📧 {utils.escape_markdown(u.get('email') or 'Не указан')}\n"
            text += f"📅 {reg_date}\n\n"

        self.bot.send_message(message.chat.id, text, parse_mode='Markdown')

    def handle_search_user_prompt(self, message):
        """Запрос на поиск пользователя"""
        set_user_state(message.from_user.id, {'step': 'admin_search_user'})
        self.bot.send_message(
            message.chat.id,
            "🔎 *Поиск пользователя*\n\n"
            "Введите Telegram ID, номер телефона или часть имени/названия компании:",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )

    def process_search_user(self, message):
        """Обработка поиска"""
        user_id = message.from_user.id
        if utils.cancel_request(message.text):
            clear_user_state(user_id)
            self.handle_users(message)
            return

        search_query = message.text.strip()

        # Поиск по соискателям
        sql_seekers = """
            SELECT 'seeker' as type, telegram_id, full_name as name, phone
            FROM job_seekers
            WHERE telegram_id LIKE ? OR phone LIKE ? OR full_name LIKE ?
            LIMIT 5
        """
        params = (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%")
        seekers = execute_query(sql_seekers, params, fetchall=True) or []

        # Поиск по работодателям
        sql_employers = """
            SELECT 'employer' as type, telegram_id, company_name as name, phone
            FROM employers
            WHERE telegram_id LIKE ? OR phone LIKE ? OR company_name LIKE ?
            LIMIT 5
        """
        employers = execute_query(sql_employers, params, fetchall=True) or []

        results = seekers + employers

        if not results:
            self.bot.send_message(message.chat.id, "❌ Пользователи не найдены.", reply_markup=keyboards.admin_users_menu())
            clear_user_state(user_id)
            return

        text = f"🔎 *Результаты поиска по запросу* \"{utils.escape_markdown(search_query)}\":\n\n"
        for u in results:
            icon = "👤" if u['type'] == 'seeker' else "🏢"
            text += f"{icon} *{utils.escape_markdown(u['name'])}*\n"
            text += f"🆔 `{u['telegram_id']}` | 📞 {u['phone']}\n\n"

        clear_user_state(user_id)
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=keyboards.admin_users_menu())

    def _ensure_complaints_table_columns(self):
        """Миграция таблицы complaints"""
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
            logging.error(f"Ошибка миграции таблицы complaints в админке: {e}")

    def handle_complaints(self, message):
        """Обработка кнопки жалоб"""
        self._ensure_complaints_table_columns()
        chat_id = message.chat.id
        # Показываем только новые жалобы (status='new')
        try:
            query = (
                "SELECT id, user_id, user_name, type, message, photo_id, status, created_at, is_replied "
                "FROM complaints WHERE status = 'new' ORDER BY id DESC LIMIT 10"
            )
            complaints = execute_query(query, (), fetchall=True)
        except Exception as e:
            # Если колонок status/photo_id еще нет, пробуем старый запрос
            logging.warning(f"Ошибка получения новых жалоб: {e}. Пробую старый формат.")
            try:
                query = "SELECT id, user_id, user_name, type, message, created_at FROM complaints ORDER BY id DESC LIMIT 10"
                complaints = execute_query(query, (), fetchall=True)
            except Exception:
                complaints = []

        if not complaints:
            self.bot.send_message(chat_id, "📭 Список жалоб пуст.")
            return

        self.bot.send_message(chat_id, f"⚠️ *Новые жалобы и ошибки ({len(complaints)}):*", parse_mode='Markdown')

        for c in complaints:
            self._send_complaint_item(chat_id, c)

    def _format_date(self, date_str):
        if not date_str:
            return "N/A"
        try:
            utc_dt = datetime.strptime(str(date_str).split('.')[0], '%Y-%m-%d %H:%M:%S')
            if ZoneInfo:
                tashkent_dt = utc_dt.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo("Asia/Tashkent"))
            else:
                tashkent_dt = utc_dt + timedelta(hours=5)
            return tashkent_dt.strftime('%d.%m.%Y %H:%M')
        except (ValueError, TypeError):
            return str(date_str)

    def _send_complaint_item(self, chat_id, c):
        """Отправка одной карточки жалобы"""
        reg_date = self._format_date(c.get('created_at'))

        # Получаем данные пользователя для отображения
        user_info = get_user_by_id(c['user_id'])
        role_str = "Неизвестно"
        phone = "Не указан"
        email = "Не указан"

        if user_info:
            if 'full_name' in user_info:
                role_str = "Соискатель"
            elif 'company_name' in user_info:
                role_str = "Работодатель"
            phone = user_info.get('phone', 'Не указан')
            email = user_info.get('email', 'Не указан')

        # Формируем текст для подписи или сообщения
        text = f"ID: `{c['id']}` | 📌 {c['type']}\n"
        text += f"👤 {utils.escape_markdown(c['user_name'])} (ID: `{c['user_id']}`)\n"
        text += f"🎭 Роль: {role_str}\n"
        text += f"📞 {utils.escape_markdown(phone)} | 📧 {utils.escape_markdown(email)}\n"
        text += f"📝 {utils.escape_markdown(c['message'])}\n"
        text += f"📅 {reg_date}"

        markup = types.InlineKeyboardMarkup(row_width=2)
        resolve_btn = types.InlineKeyboardButton("✅ Решено", callback_data=f"admin_resolve_complaint_{c['id']}")

        if not c.get('is_replied'):
            reply_btn = types.InlineKeyboardButton("💬 Ответить", callback_data=f"admin_reply_{c['user_id']}_{c['id']}")
            markup.add(resolve_btn, reply_btn)
        else:
            markup.add(resolve_btn)

        photo_id = c.get('photo_id')

        # Если есть скриншот, отправляем его с подписью
        if photo_id:
            try:
                self.bot.send_photo(chat_id, photo_id, caption=text, parse_mode='Markdown', reply_markup=markup)
            except Exception as e:
                logging.error(f"Не удалось отправить фото жалобы {c['id']}: {e}")
                # Если фото не отправляется, отправляем текстом
                fallback_text = f"🖼️ *Не удалось загрузить скриншот для жалобы ID {c['id']}*\n\n{text}"
                self.bot.send_message(chat_id, fallback_text, parse_mode='Markdown', reply_markup=markup)
        else:
            # Если скриншота нет, отправляем просто текст
            self.bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)

    def handle_resolve_complaint(self, call):
        """Помечает жалобу как решенную"""
        try:
            complaint_id = int(call.data.split('_')[-1])
            # Вместо удаления, меняем статус
            execute_query("UPDATE complaints SET status = 'resolved' WHERE id = ?", (complaint_id,), commit=True)
            self.bot.answer_callback_query(call.id, "✅ Жалоба помечена как решенная")

            # Редактируем сообщение, чтобы убрать кнопки и добавить статус
            new_text = call.message.caption or call.message.text
            new_text += "\n\n*✅ Решено*"

            if call.message.photo:
                self.bot.edit_message_caption(caption=new_text, chat_id=call.message.chat.id,
                                              message_id=call.message.message_id, parse_mode='Markdown', reply_markup=None)
            else:
                self.bot.edit_message_text(text=new_text, chat_id=call.message.chat.id,
                                           message_id=call.message.message_id, parse_mode='Markdown', reply_markup=None)

        except Exception as e:
            logging.error(f"Error resolving complaint: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка")

    def handle_admin_settings(self, message):
        """Обработка настроек админ-панели"""
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🔄 Очистить кэш", callback_data="admin_clear_cache"),
            types.InlineKeyboardButton("🛠 Режим обслуживания", callback_data="admin_maintenance")
        )

        self.bot.send_message(
            message.chat.id,
            "⚙️ *Настройки бота*\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=markup
        )

    def handle_create_backup(self, message):
        """Создание резервной копии БД"""
        self.bot.send_message(message.chat.id, "⏳ *Создание резервной копии...*", parse_mode='Markdown')

        success, result = create_backup()

        if success:
            try:
                with open(result, 'rb') as f:
                    self.bot.send_document(
                        message.chat.id,
                        f,
                        caption=f"✅ *Бэкап успешно создан*\n📁 Файл: `{os.path.basename(result)}`",
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logging.error(f"Failed to send backup file: {e}")
                self.bot.send_message(
                    message.chat.id,
                    f"✅ *Бэкап создан*, но не удалось отправить файл.\nПуть: `{result}`",
                    parse_mode='Markdown'
                )
        else:
            self.bot.send_message(
                message.chat.id,
                f"❌ *Ошибка при создании бэкапа:*\n{result}",
                parse_mode='Markdown'
            )

    def handle_reply_prompt(self, call):
        """Запрос текста ответа пользователю"""
        try:
            data_parts = call.data.split('_')
            user_id = int(data_parts[2])
            complaint_id = int(data_parts[3]) if len(data_parts) > 3 else None

            set_user_state(call.from_user.id, {
                'step': 'admin_reply_message',
                'target_user_id': user_id,
                'complaint_id': complaint_id,
                'complaint_msg_id': call.message.message_id,
                'complaint_chat_id': call.message.chat.id
            })
            self.bot.send_message(
                call.message.chat.id,
                "✍️ *Введите текст ответа пользователю:*\n\n"
                "Сообщение будет отправлено от имени администрации.",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            self.bot.answer_callback_query(call.id)
        except Exception as e:
            logging.error(f"Error in handle_reply_prompt: {e}")

    def process_reply_message(self, message):
        """Отправка ответа пользователю"""
        user_id = message.from_user.id
        state = get_user_state(user_id)
        target_id = state.get('target_user_id')
        complaint_id = state.get('complaint_id')
        complaint_msg_id = state.get('complaint_msg_id')
        complaint_chat_id = state.get('complaint_chat_id')

        if utils.cancel_request(message.text):
            clear_user_state(user_id)
            self.bot.send_message(message.chat.id, "❌ Отменено", reply_markup=keyboards.admin_menu())
            return

        try:
            # Отправляем сообщение пользователю
            self.bot.send_message(
                target_id,
                f"🔔 *Сообщение от администрации:*\n\n{message.text}",
                parse_mode='Markdown'
            )
            self.bot.send_message(message.chat.id, "✅ Сообщение успешно отправлено.", reply_markup=keyboards.admin_menu())

            # Помечаем в базе, что ответ был дан
            if complaint_id:
                try:
                    execute_query("UPDATE complaints SET is_replied = 1 WHERE id = ?", (complaint_id,), commit=True)
                except Exception as e:
                    logging.error(f"Не удалось обновить статус ответа жалобы: {e}")

            # Обновляем сообщение с жалобой: убираем кнопку "Ответить", оставляем "Решено"
            if complaint_id and complaint_msg_id and complaint_chat_id:
                try:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("✅ Решено",
                                                          callback_data=f"admin_resolve_complaint_{complaint_id}"))
                    self.bot.edit_message_reply_markup(chat_id=complaint_chat_id, message_id=complaint_msg_id,
                                                       reply_markup=markup)
                except Exception as e:
                    logging.error(f"Не удалось обновить кнопки жалобы: {e}")

        except Exception as e:
            logging.error(f"Failed to send admin reply: {e}")
            self.bot.send_message(message.chat.id, "❌ Не удалось отправить сообщение.", reply_markup=keyboards.admin_menu())

        clear_user_state(user_id)
