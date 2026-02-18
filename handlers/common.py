import logging

import database
import keyboards
from config import Config
from database.core import (
    check_connection_health,
    get_pool_stats,
    get_user_state,
    set_user_state,
)
from handlers.chat import ChatMixin
from handlers.support import SupportMixin
from localization import (
    LANGUAGE_MAP,
    TRANSLATIONS,
    get_text_by_lang,
    get_user_language,
)


class CommonHandlers(ChatMixin, SupportMixin):
    def __init__(self, bot):
        self.bot = bot

    def register(self, bot):
        """Регистрация обработчиков общих команд"""
        bot.register_message_handler(self.handle_start, commands=['start', 'restart'])
        bot.register_message_handler(self.handle_help, commands=['help', 'помощь'])
        bot.register_message_handler(self.handle_admin, commands=['admin'])
        bot.register_message_handler(self.handle_health, commands=['health'])
        bot.register_message_handler(self.handle_version, commands=['version'])
        bot.register_message_handler(self.handle_cancel, commands=['cancel', 'отмена', 'отменить'])
        bot.register_message_handler(self.handle_debug, commands=['debug', 'отладка'])

        # Язык
        bot.register_message_handler(
            self.handle_language_selection,
            func=self._is_initial_language_selection
        )
        bot.register_message_handler(
            self.handle_back_to_lang,
            func=lambda m: m.text in [d.get('back_to_lang', '') for d in TRANSLATIONS.values()]
        )

        # Навигация
        bot.register_message_handler(
            self.handle_back_to_main,
            func=lambda m: m.text in [d.get('back_to_main_menu', '') for d in TRANSLATIONS.values()] or
            m.text in ['🏠 На главную', '🏠 Главное меню']
        )
        bot.register_message_handler(
            self.handle_back_to_profile,
            func=lambda m: m.text in [d.get('btn_back_to_panel_menu', '') for d in TRANSLATIONS.values()]
        )

        # Инфо и поддержка
        bot.register_message_handler(self.handle_about, func=lambda m: m.text in [d.get('about_bot', '') for d in TRANSLATIONS.values()])
        bot.register_message_handler(self.handle_support, func=lambda m: m.text in [d.get('menu_support', '') for d in TRANSLATIONS.values()])
        bot.register_message_handler(self.handle_report_bug, func=lambda m: m.text in ['🐛 Ошибка', '🐛 Xato', '🐛 Bug'])
        bot.register_message_handler(self.handle_complaint, func=lambda m: m.text in ['⚠️ Жалоба', '⚠️ Shikoyat', '⚠️ Complaint'])

        # Чат
        bot.register_callback_query_handler(self.handle_start_chat, func=lambda c: c.data.startswith('start_chat_'))
        bot.register_message_handler(self.handle_stop_chat, func=lambda m: m.text == '❌ Завершить чат')
        bot.register_callback_query_handler(
            self.handle_reply_admin_prompt,
            func=lambda c: c.data.startswith('reply_admin_')
        )
        bot.register_message_handler(
            self.handle_admin,
            func=lambda m: m.text == '↩️ Назад в админку' and m.from_user.id in Config.ADMIN_IDS
        )

    def handle_health(self, message):
        if check_connection_health():
            stats = get_pool_stats()
            stats_msg = f"\nСтатистика пула: {stats}" if stats else ""
            self.bot.reply_to(message, f"✅ БД работает исправно{stats_msg}")
        else:
            self.bot.reply_to(message, "❌ Проблемы с подключением к БД!")

    def handle_version(self, message):
        self.bot.reply_to(message, f"🤖 Версия бота: `{Config.BOT_VERSION}`", parse_mode='Markdown')

    def handle_cancel(self, message):
        database.clear_user_state(message.from_user.id)
        self.bot.send_message(message.chat.id, "❌ Действие отменено", reply_markup=keyboards.main_menu())

    def handle_debug(self, message):
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)
        user_state = get_user_state(user_id)
        debug_info = f"🛠️ *Debug Info*\nID: `{user_id}`\n"
        if user_data:
            role = "Seeker" if 'full_name' in user_data else "Employer"
            debug_info += f"Role: {role}\nName: {user_data.get('full_name') or user_data.get('company_name')}\n"
        else:
            debug_info += "Status: Not registered\n"
        if user_state:
            debug_info += "\nState:\n" + "\n".join([f"{k}: {v}" for k, v in user_state.items()])
        self.bot.send_message(message.chat.id, debug_info, parse_mode='Markdown')

    def handle_back_to_lang(self, message):
        self.bot.send_message(
            message.chat.id,
            get_text_by_lang('select_language', 'ru'),
            reply_markup=keyboards.language_menu()
        )

    def handle_start(self, message):
        """Обработка команды /start"""
        user_id = message.from_user.id
        database.clear_user_state(user_id)

        # Проверяем, есть ли пользователь в базе (автоматический вход)
        existing_user = database.get_user_by_id(user_id)
        if existing_user:
            lang = existing_user.get('language_code', 'ru')
            if 'full_name' in existing_user:
                self.bot.send_message(
                    message.chat.id,
                    f"👋 {get_text_by_lang('welcome_back', lang)}, {existing_user['full_name']}!",
                    reply_markup=keyboards.seeker_main_menu(lang=lang)
                )
            else:
                self.bot.send_message(
                    message.chat.id,
                    f"👋 {get_text_by_lang('welcome_back', lang)}, {existing_user['company_name']}!",
                    reply_markup=keyboards.employer_main_menu(lang=lang)
                )
            return

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang('select_language', 'ru'),  # Это сообщение всегда на всех языках
            reply_markup=keyboards.language_menu()
        )

    def handle_back_to_main(self, message):
        """Возврат в главное меню"""
        user_id = message.from_user.id

        # Пытаемся сохранить язык перед очисткой состояния
        user_state = get_user_state(user_id)
        lang = get_user_language(user_id)

        # Проверяем, был ли установлен язык (в БД или в состоянии)
        has_lang_set = False
        if database.get_user_by_id(user_id):
            has_lang_set = True
        elif user_state and 'language_code' in user_state:
            has_lang_set = True

        database.clear_user_state(user_id)

        # Если пользователя нет в базе и язык не был выбран -> меню выбора языка
        if not has_lang_set:
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang('select_language', 'ru'),
                reply_markup=keyboards.language_menu()
            )
            return

        # Если пользователя нет в базе, восстанавливаем язык в состоянии,
        # так как clear_user_state его удалил
        if not database.get_user_by_id(user_id):
            database.set_user_state(user_id, {'language_code': lang})

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang('main_menu', lang),
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu(lang)
        )

    def handle_back_to_profile(self, message):
        """Возврат в профиль из настроек"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)

        if not user_data:
            self.handle_back_to_main(message)
            return

        if 'full_name' in user_data:
            # Соискатель
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang('back_to_seeker_panel', lang),
                parse_mode='Markdown',
                reply_markup=keyboards.seeker_main_menu(lang=lang)
            )
        else:
            # Работодатель
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang('back_to_employer_panel', lang),
                parse_mode='Markdown',
                reply_markup=keyboards.employer_main_menu(lang=lang)
            )

    def handle_about(self, message):
        """Информация о боте"""
        lang = get_user_language(message.from_user.id)
        self.bot.send_message(
            message.chat.id,
            get_text_by_lang('about_bot_text', lang),
            parse_mode='Markdown'
        )

    def handle_help(self, message):
        """Помощь"""
        lang = get_user_language(message.from_user.id)
        self.bot.send_message(
            message.chat.id,
            get_text_by_lang('help_text', lang),
            parse_mode='Markdown'
        )

    def handle_admin(self, message):
        """Админ-панель"""
        if message.from_user.id not in Config.ADMIN_IDS:
            self.bot.send_message(message.chat.id, "❌ У вас нет прав доступа.")
            return

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
        lang = get_user_language(message.from_user.id)
        if message.text.startswith('/'):
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang('unknown_command', lang),
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
                        get_text_by_lang('unknown_message_logged_in', lang),
                        parse_mode='Markdown',
                        reply_markup=keyboards.seeker_main_menu(lang=lang)
                    )
                else:
                    # Работодатель
                    self.bot.send_message(
                        message.chat.id,
                        get_text_by_lang('unknown_message_logged_in', lang),
                        parse_mode='Markdown',
                        reply_markup=keyboards.employer_main_menu(lang=lang)
                    )
            else:
                self.bot.send_message(
                    message.chat.id,
                    get_text_by_lang('unknown_message_not_logged_in', lang),
                    parse_mode='Markdown',
                    reply_markup=keyboards.main_menu(lang=lang)
                )

    def handle_language_selection(self, message):
        """Обработка выбора языка и сохранение"""
        lang_code = LANGUAGE_MAP.get(message.text)
        if not lang_code:
            return

        user_id = message.from_user.id

        user = database.get_user_by_id(user_id)

        if user:
            # Если пользователь уже зарегистрирован, обновляем язык в его профиле
            table = 'job_seekers' if 'full_name' in user else 'employers'
            database.execute_query(f"UPDATE {table} SET language_code = ? WHERE telegram_id = ?",  # nosec
                                   (lang_code, user_id), commit=True)

            # Возвращаем в главное меню соответствующей роли
            if 'full_name' in user:
                self.bot.send_message(
                    message.chat.id,
                    get_text_by_lang('back_to_seeker_panel', lang_code),
                    parse_mode='Markdown',
                    reply_markup=keyboards.seeker_main_menu(lang=lang_code)
                )
            else:
                self.bot.send_message(
                    message.chat.id,
                    get_text_by_lang('back_to_employer_panel', lang_code),
                    parse_mode='Markdown',
                    reply_markup=keyboards.employer_main_menu(lang=lang_code)
                )
        else:
            # Если это новый пользователь, сохраняем язык в его временном состоянии
            set_user_state(user_id, {'language_code': lang_code})
            # и показываем ему стартовое меню выбора роли
            self.bot.send_message(
                message.chat.id,
                get_text_by_lang('welcome', lang_code),
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu(lang_code)
            )

    def _is_initial_language_selection(self, message):
        """
        Фильтр, который пропускает сообщения с кнопками языков, только если
        пользователь не находится в процессе выбора языков для профиля или вакансии.
        """
        if message.text not in LANGUAGE_MAP:
            return False

        user_state = get_user_state(message.from_user.id)
        if user_state and user_state.get('step') in ['language_selection', 'vacancy_language_selection']:
            return False
        return True
