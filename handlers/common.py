# handlers/common.py
import logging
import database
import keyboards
import utils


class CommonHandlers:
    def __init__(self, bot):
        self.bot = bot

    def handle_start(self, message):
        """Обработка команды /start"""
        user_id = message.from_user.id
        database.clear_user_state(user_id)

        # Проверяем, есть ли пользователь в базе (автоматический вход)
        existing_user = database.get_user_by_id(user_id)
        if existing_user:
            if 'full_name' in existing_user:
                self.bot.send_message(
                    message.chat.id,
                    f"👋 Здравствуйте, {existing_user['full_name']}!",
                    reply_markup=keyboards.seeker_main_menu()
                )
            else:
                self.bot.send_message(
                    message.chat.id,
                    f"👋 Здравствуйте, {existing_user['company_name']}!",
                    reply_markup=keyboards.employer_main_menu()
                )
            return

        self.bot.send_message(
            message.chat.id,
            "👋 *Добро пожаловать на профессиональную биржу труда!*\n\n"
            "Я помогу найти работу или сотрудников в Узбекистане.\n"
            "Выберите вашу роль:",
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu()
        )

    def handle_back_to_main(self, message):
        """Возврат в главное меню"""
        user_id = message.from_user.id
        database.clear_user_state(user_id)

        self.bot.send_message(
            message.chat.id,
            "👋 *Главное меню*",
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu()
        )

    def handle_back_to_profile(self, message):
        """Возврат в профиль из настроек"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data:
            self.handle_back_to_main(message)
            return

        if 'full_name' in user_data:
            # Соискатель
            self.bot.send_message(
                message.chat.id,
                "👤 *Панель соискателя*",
                parse_mode='Markdown',
                reply_markup=keyboards.seeker_main_menu()
            )
        else:
            # Работодатель
            self.bot.send_message(
                message.chat.id,
                "🏢 *Панель работодателя*",
                parse_mode='Markdown',
                reply_markup=keyboards.employer_main_menu()
            )

    def handle_about(self, message):
        """Информация о боте"""
        self.bot.send_message(
            message.chat.id,
            "🤖 *О боте*\n\n"
            "Профессиональная биржа труда Узбекистана\n\n"
            "*Функции:*\n"
            "• Регистрация соискателей и работодателей\n"
            "• Поиск работы и сотрудников\n"
            "• Создание резюме и вакансий\n"
            "• Только номера +998 Узбекистана\n\n"
            "*Версия:* 2.0",
            parse_mode='Markdown'
        )

    def handle_support(self, message):
        """Поддержка"""
        self.bot.send_message(
            message.chat.id,
            "📞 *Поддержка*\n\n"
            "Выберите тему обращения:",
            parse_mode='Markdown',
            reply_markup=keyboards.support_menu()
        )

    def handle_report_bug(self, message):
        """Обработка нажатия 'Ошибка'"""
        database.set_user_state(message.from_user.id, {'step': 'support_bug_report'})
        self.bot.send_message(
            message.chat.id,
            "🐛 *Сообщить об ошибке*\n\n"
            "Опишите проблему. Вы можете отправить текст или прикрепить скриншот с описанием в подписи.",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )

    def handle_complaint(self, message):
        """Обработка нажатия 'Жалоба'"""
        database.set_user_state(message.from_user.id, {'step': 'support_complaint'})
        self.bot.send_message(
            message.chat.id,
            "⚠️ *Подать жалобу*\n\n"
            "Опишите вашу жалобу (на пользователя, вакансию или работу бота). Вы также можете прикрепить скриншот.",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )

    def _ensure_complaints_table(self):
        """Создание и миграция таблицы жалоб"""
        database.execute_query("""
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
        """, commit=True)

        try:
            columns = database.execute_query("PRAGMA table_info(complaints)", (), fetchall=True)
            if columns:
                col_names = [col['name'] for col in columns]
                if 'photo_id' not in col_names:
                    database.execute_query("ALTER TABLE complaints ADD COLUMN photo_id TEXT", commit=True)
                if 'status' not in col_names:
                    database.execute_query("ALTER TABLE complaints ADD COLUMN status TEXT DEFAULT 'new'", commit=True)
                if 'is_replied' not in col_names:
                    database.execute_query("ALTER TABLE complaints ADD COLUMN is_replied INTEGER DEFAULT 0", commit=True)
        except Exception as e:
            logging.error(f"Ошибка миграции таблицы complaints: {e}")

    def process_support_message(self, message):
        """Обработка текста или фото обращения в поддержку"""
        user_id = message.from_user.id
        support_text = message.caption or message.text

        if utils.cancel_request(support_text):
            self._cancel_support(user_id, message.chat.id)
            return

        if not self._validate_support_message(message, support_text):
            return

        if not support_text and message.photo:
            support_text = "Пользователь прислал изображение без описания."

        user_state = database.get_user_state(user_id)
        topic = "Ошибка" if user_state.get('step') == 'support_bug_report' else "Жалоба"
        photo_file_id = message.photo[-1].file_id if message.photo else None

        self._ensure_complaints_table()

        # Сохраняем обращение в базу данных
        database.execute_query(
            "INSERT INTO complaints (user_id, user_name, type, message, photo_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, message.from_user.first_name, topic, support_text, photo_file_id),
            commit=True
        )

        database.clear_user_state(user_id)

        # Определяем, в какое меню вернуть пользователя
        user_data = database.get_user_by_id(user_id)
        markup = keyboards.main_menu()
        if user_data:
            if 'full_name' in user_data:
                markup = keyboards.seeker_main_menu()
            elif 'company_name' in user_data:
                markup = keyboards.employer_main_menu()

        self.bot.send_message(
            message.chat.id,
            "✅ *Ваше сообщение принято!*\n\nАдминистраторы рассмотрят его в ближайшее время.",
            parse_mode='Markdown',
            reply_markup=markup
        )

    def _cancel_support(self, user_id, chat_id):
        database.clear_user_state(user_id)
        user_data = database.get_user_by_id(user_id)
        markup = keyboards.main_menu()
        if user_data:
            if 'full_name' in user_data:
                markup = keyboards.seeker_main_menu()
            elif 'company_name' in user_data:
                markup = keyboards.employer_main_menu()
        self.bot.send_message(chat_id, "❌ Отменено", reply_markup=markup)

    def _validate_support_message(self, message, support_text):
        if not support_text and not message.photo:
            self.bot.send_message(message.chat.id, "Пожалуйста, опишите вашу проблему текстом или приложите скриншот.")
            return False

        if utils.contains_profanity(support_text):
            self.bot.send_message(message.chat.id, "❌ Сообщение содержит недопустимые слова.")
            return False
        return True

    def handle_help(self, message):
        """Помощь"""
        self.bot.send_message(
            message.chat.id,
            "ℹ️ *Помощь*\n\n"
            "*Основные команды:*\n"
            "• /start - Главное меню\n"
            "• /help - Эта справка\n\n"
            "*Как пользоваться:*\n"
            "1. Выберите роль (соискатель/работодатель)\n"
            "2. Зарегистрируйтесь или войдите\n"
            "3. Используйте функции меню\n\n"
            "*Вопросы и поддержка:* @support_jobs_bot",
            parse_mode='Markdown'
        )

    def handle_admin(self, message):
        """Админ-панель"""
        # Проверка прав администратора выполняется в bot.py
        try:
            # Используем прямой запрос, так как get_statistics может отсутствовать
            seekers_res = database.execute_query("SELECT COUNT(*) as cnt FROM job_seekers", (), fetchone=True)
            employers_res = database.execute_query("SELECT COUNT(*) as cnt FROM employers", (), fetchone=True)

            seekers_count = seekers_res['cnt'] if seekers_res else 0
            employers_count = employers_res['cnt'] if employers_res else 0
            total_count = seekers_count + employers_count

            self.bot.send_message(
                message.chat.id,
                f"👑 *Панель администратора*\n\n"
                f"Добро пожаловать, {message.from_user.first_name}!\n\n"
                f"*Краткая статистика:*\n"
                f"• 👤 Соискатели: {seekers_count}\n"
                f"• 🏢 Работодатели: {employers_count}\n"
                f"• 👥 Всего: {total_count}\n\n"
                f"Выберите действие:",
                parse_mode='Markdown',
                reply_markup=keyboards.admin_menu()
            )
        except Exception as e:
            logging.error(f"Error in handle_admin: {e}")
            self.bot.send_message(message.chat.id, "❌ Произошла ошибка при загрузке админ-панели.")

    def handle_unknown(self, message):
        """Обработка неизвестных сообщений"""
        if message.text.startswith('/'):
            self.bot.send_message(
                message.chat.id,
                "🤖 *Неизвестная команда!*\n\n"
                "Используйте /start для начала работы.",
                parse_mode='Markdown'
            )
        else:
            user_id = message.from_user.id
            user_data = database.get_user_by_id(user_id)

            if user_data:
                if 'full_name' in user_data:
                    # Соискатель
                    self.bot.send_message(
                        message.chat.id,
                        "🤔 *Не понимаю ваше сообщение!*\n\n"
                        "Используйте кнопки меню для навигации.",
                        parse_mode='Markdown',
                        reply_markup=keyboards.seeker_main_menu()
                    )
                else:
                    # Работодатель
                    self.bot.send_message(
                        message.chat.id,
                        "🤔 *Не понимаю ваше сообщение!*\n\n"
                        "Используйте кнопки меню для навигации.",
                        parse_mode='Markdown',
                        reply_markup=keyboards.employer_main_menu()
                    )
            else:
                self.bot.send_message(
                    message.chat.id,
                    "🤔 *Не понимаю ваше сообщение!*\n\n"
                    "Используйте /start для начала работы.",
                    parse_mode='Markdown',
                    reply_markup=keyboards.main_menu()
                )

    def handle_start_chat(self, call):
        """Начало чата"""
        try:
            target_id = int(call.data.split('_')[2])
            user_id = call.from_user.id

            target_user = database.get_user_by_id(target_id)
            if not target_user:
                self.bot.answer_callback_query(call.id, "❌ Пользователь не найден")
                return

            target_name = target_user.get('company_name') or target_user.get('full_name') or "Пользователь"

            database.set_user_state(user_id, {
                'step': 'active_chat',
                'target_id': target_id,
                'target_name': target_name
            })

            self.bot.send_message(
                user_id,
                f"💬 *Чат с {utils.escape_markdown(target_name)}*\n\n"
                f"Напишите ваше сообщение. Оно будет отправлено получателю.",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            self.bot.answer_callback_query(call.id)
        except Exception as e:
            logging.error(f"Error starting chat: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка")

    def handle_chat_message(self, message):
        """Обработка сообщения в чате"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if not user_state or 'target_id' not in user_state:
            self.handle_stop_chat(message, "❌ Сессия чата истекла.")
            return

        target_id = user_state['target_id']
        sender = database.get_user_by_id(user_id)
        sender_name = sender.get('company_name') or sender.get('full_name') or "Пользователь"

        if utils.contains_profanity(message.text):
            self.bot.send_message(user_id, "❌ Сообщение не отправлено: обнаружена нецензурная лексика.")
            return

        try:
            # Отправляем получателю
            self.bot.send_message(
                target_id,
                f"📩 *Сообщение от {utils.escape_markdown(sender_name)}:*\n\n"
                f"{utils.escape_markdown(message.text)}",
                parse_mode='Markdown',
                reply_markup=keyboards.reply_keyboard(user_id)
            )
            # Подтверждаем отправителю и автоматически завершаем чат
            self.handle_stop_chat(message, "✅ Сообщение отправлено.")
        except Exception as e:
            print(f"Failed to send chat message: {e}")
            # Завершаем чат при ошибке
            self.handle_stop_chat(message, "❌ Не удалось отправить сообщение. Возможно, пользователь заблокировал бота.")

    def handle_stop_chat(self, message, custom_text: str = None):
        """Завершение чата"""
        user_id = message.from_user.id
        database.clear_user_state(user_id)

        user_data = database.get_user_by_id(user_id)
        if user_data:
            if 'full_name' in user_data:
                markup = keyboards.seeker_main_menu()
            else:
                markup = keyboards.employer_main_menu()
        else:
            markup = keyboards.main_menu()

        text_to_send = custom_text if custom_text is not None else "❌ Чат завершен."

        self.bot.send_message(
            message.chat.id,
            text_to_send,
            reply_markup=markup
        )
