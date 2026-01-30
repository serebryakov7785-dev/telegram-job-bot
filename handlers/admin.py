# handlers/admin.py
import database
import keyboards
import utils
import logging
from telebot import types
import time
import os

class AdminHandlers:
    def __init__(self, bot):
        self.bot = bot

    def handle_statistics(self, message):
        """Показывает статистику"""
        # Используем прямой запрос
        seekers_res = database.execute_query("SELECT COUNT(*) as cnt FROM job_seekers", (), fetchone=True)
        employers_res = database.execute_query("SELECT COUNT(*) as cnt FROM employers", (), fetchone=True)
        
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
        database.set_user_state(message.from_user.id, {'step': 'admin_broadcast_message'})
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
            database.clear_user_state(user_id)
            self.bot.send_message(user_id, "❌ Рассылка отменена.", reply_markup=keyboards.admin_menu())
            return

        user_state = database.get_user_state(user_id) or {}
        user_state['broadcast_message'] = message.text
        user_state['step'] = 'admin_broadcast_confirm'
        database.set_user_state(user_id, user_state)

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

    def process_broadcast_confirm(self, message):
        """Подтверждение и отправка рассылки"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if message.text == '❌ Нет, отменить':
            database.clear_user_state(user_id)
            self.bot.send_message(user_id, "❌ Рассылка отменена.", reply_markup=keyboards.admin_menu())
            return

        if message.text != '✅ Да, отправить':
            self.bot.send_message(message.chat.id, "Пожалуйста, выберите один из вариантов.")
            return

        broadcast_message = user_state.get('broadcast_message')
        if not broadcast_message:
            database.clear_user_state(user_id)
            self.bot.send_message(user_id, "❌ Ошибка: сообщение для рассылки не найдено. Попробуйте снова.", reply_markup=keyboards.admin_menu())
            return

        database.clear_user_state(user_id)
        self.bot.send_message(user_id, "⏳ *Начинаю рассылку...*", parse_mode='Markdown', reply_markup=keyboards.admin_menu())

        # Получаем ID всех пользователей напрямую
        all_users = set()
        
        seekers = database.execute_query("SELECT telegram_id FROM job_seekers", (), fetchall=True)
        if seekers:
            for s in seekers:
                all_users.add(s['telegram_id'])
                
        employers = database.execute_query("SELECT telegram_id FROM employers", (), fetchall=True)
        if employers:
            for e in employers:
                all_users.add(e['telegram_id'])

        sent_count = 0
        failed_count = 0

        for telegram_id in all_users:
            try:
                self.bot.send_message(telegram_id, broadcast_message, parse_mode='Markdown')
                sent_count += 1
                time.sleep(0.1) # Задержка, чтобы не превышать лимиты Telegram
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
        query = "SELECT telegram_id, full_name, phone, created_at FROM job_seekers ORDER BY id DESC LIMIT 10"
        users = database.execute_query(query, (), fetchall=True)
        
        if not users:
            self.bot.send_message(message.chat.id, "Список пуст.")
            return

        text = "📋 *Последние 10 соискателей:*\n\n"
        for u in users:
            reg_date = u['created_at'] if u.get('created_at') else "N/A"
            text += f"👤 *{utils.escape_markdown(u['full_name'])}*\n"
            text += f"🆔 `{u['telegram_id']}` | 📞 {u['phone']}\n"
            text += f"📅 {reg_date}\n\n"
        
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown')

    def handle_list_employers(self, message):
        """Список последних работодателей"""
        query = "SELECT telegram_id, company_name, phone, created_at FROM employers ORDER BY id DESC LIMIT 10"
        users = database.execute_query(query, (), fetchall=True)
        
        if not users:
            self.bot.send_message(message.chat.id, "Список пуст.")
            return

        text = "📋 *Последние 10 работодателей:*\n\n"
        for u in users:
            reg_date = u['created_at'] if u.get('created_at') else "N/A"
            text += f"🏢 *{utils.escape_markdown(u['company_name'])}*\n"
            text += f"🆔 `{u['telegram_id']}` | 📞 {u['phone']}\n"
            text += f"📅 {reg_date}\n\n"
        
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown')

    def handle_search_user_prompt(self, message):
        """Запрос на поиск пользователя"""
        database.set_user_state(message.from_user.id, {'step': 'admin_search_user'})
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
            database.clear_user_state(user_id)
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
        seekers = database.execute_query(sql_seekers, params, fetchall=True) or []

        # Поиск по работодателям
        sql_employers = """
            SELECT 'employer' as type, telegram_id, company_name as name, phone 
            FROM employers 
            WHERE telegram_id LIKE ? OR phone LIKE ? OR company_name LIKE ?
            LIMIT 5
        """
        employers = database.execute_query(sql_employers, params, fetchall=True) or []
        
        results = seekers + employers
        
        if not results:
            self.bot.send_message(message.chat.id, "❌ Пользователи не найдены.", reply_markup=keyboards.admin_users_menu())
            database.clear_user_state(user_id)
            return

        text = f"🔎 *Результаты поиска по запросу* \"{utils.escape_markdown(search_query)}\":\n\n"
        for u in results:
            icon = "👤" if u['type'] == 'seeker' else "🏢"
            text += f"{icon} *{utils.escape_markdown(u['name'])}*\n"
            text += f"🆔 `{u['telegram_id']}` | 📞 {u['phone']}\n\n"
        
        database.clear_user_state(user_id)
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=keyboards.admin_users_menu())

    def handle_admin_settings(self, message):
        """Обработка настроек админ-панели (заглушка)"""
        self.bot.send_message(message.chat.id, "⚙️ *Настройки бота*\n\nЭта функция находится в разработке.", parse_mode='Markdown', reply_markup=keyboards.admin_menu())

    def handle_create_backup(self, message):
        """Создание резервной копии БД"""
        self.bot.send_message(message.chat.id, "⏳ *Создание резервной копии...*", parse_mode='Markdown')
        
        success, result = database.create_backup()
        
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