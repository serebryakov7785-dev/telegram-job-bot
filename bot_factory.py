import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import telebot

from config import Config
from database.core import (
    check_connection_health,
    clear_user_state,
    get_pool_stats,
    get_user_state,
)
from database.schema import init_database
from database.users import get_user_by_id
from database.vacancies import invalidate_vacancies_cache
from handlers.admin import AdminHandlers
from handlers.auth import AuthHandlers
from handlers.common import CommonHandlers
from handlers.employer import EmployerHandlers
from handlers.profile import ProfileHandlers
from handlers.seeker import SeekerHandlers
from handlers.settings import SettingsHandlers
from handlers.steps import StepHandlers
import keyboards
from localization import get_all_translations, get_text_by_lang
from middleware import setup_middleware
import utils

# Попытка импорта библиотек мониторинга
try:
    import sentry_sdk
    from prometheus_client import start_http_server
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


class JSONFormatter(logging.Formatter):
    """Форматтер для структурированных логов (ELK/Graylog)"""

    def format(self, record):
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage()
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)


def setup_logging():
    """Настраивает систему логирования."""
    log_file = os.getenv('LOG_FILE', 'bot.json.log')

    # Ротация логов: 10 МБ на файл, хранить 5 последних файлов
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(JSONFormatter())

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    )

    # Настраиваем корневой логгер, удаляя старые хендлеры (от database.core)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Очистка существующих хендлеров во избежание дублирования
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

    logging.getLogger("urllib3").setLevel(logging.WARNING)


def create_bot():
    """Создает и настраивает экземпляр бота"""
    setup_logging()
    init_database()

    if not Config.TOKEN:
        logging.critical("❌ Ошибка: Токен бота не найден!")
        raise ValueError("Токен бота не найден! Проверьте файл .env")

    # Настройка многопоточности (для PythonAnywhere лучше False)
    threaded = os.getenv('BOT_THREADED', 'true').lower() == 'true'
    bot = telebot.TeleBot(Config.TOKEN, threaded=threaded)

    # Инициализация обработчиков
    common = CommonHandlers(bot)
    auth = AuthHandlers(bot)
    seeker = SeekerHandlers(bot)
    employer = EmployerHandlers(bot)
    settings = SettingsHandlers(bot)
    profile = ProfileHandlers(bot)
    admin = AdminHandlers(bot)

    steps = StepHandlers(bot)
    steps.set_auth_handlers(auth)
    steps.set_employer_handlers(employer)
    steps.set_admin_handlers(admin)

    # Регистрация маршрутов
    register_routes(bot, common, auth, seeker, employer, settings, profile, admin, steps)

    # Настройка мониторинга и middleware
    if MONITORING_AVAILABLE:
        # Запускаем Prometheus только если это разрешено (по умолчанию True)
        if os.getenv('ENABLE_MONITORING', 'true').lower() == 'true':
            try:
                start_http_server(Config.PROMETHEUS_PORT)
                logging.info(f"✅ Prometheus metrics server running on port {Config.PROMETHEUS_PORT}")
            except Exception as e:
                logging.error(f"❌ Failed to start Prometheus server: {e}")

        if Config.SENTRY_DSN:
            sentry_sdk.init(dsn=Config.SENTRY_DSN, traces_sample_rate=1.0)
            logging.info("✅ Sentry initialized")

    setup_middleware(bot, MONITORING_AVAILABLE)

    return bot


def register_routes(bot, common, auth, seeker, employer, settings, profile, admin, steps):
    """Регистрация всех обработчиков сообщений"""

    # --- Регистрация через классы ---
    common.register(bot)
    admin.register(bot)
    seeker.register(bot)
    employer.register(bot)
    settings.register(bot)
    profile.register(bot)

    # --- Авторизация и Меню ---
    bot.register_message_handler(
        auth.handle_role_selection,
        func=lambda m: m.text in get_all_translations('role_seeker') or
        m.text in get_all_translations('role_employer')
    )
    bot.register_message_handler(
        auth.handle_registration_start,
        func=lambda m: m.text in get_all_translations('register_button')
    )
    bot.register_message_handler(auth.handle_password_recovery, func=lambda m: m.text == '🔑 Забыли пароль?')
    bot.register_message_handler(
        auth.handle_logout,
        func=lambda m: m.text == '🚪 Выйти' or m.text in get_all_translations('menu_logout')
    )

    @bot.message_handler(func=lambda m: m.text in get_all_translations('cancel_button'))
    def cancel_btn_wrapper(message):
        user_id = message.from_user.id
        if get_user_state(user_id):
            steps.cancel_current_step(user_id, message.chat.id)
        else:
            clear_user_state(user_id)
            bot.send_message(
                message.chat.id,
                get_text_by_lang('action_cancelled', 'ru'), # Fallback to ru or get from DB
                reply_markup=keyboards.main_menu('ru')
            )

    bot.register_callback_query_handler(common.handle_start_chat, func=lambda c: c.data.startswith('start_chat_'))


    @bot.message_handler(func=lambda m: m.text in get_all_translations('menu_chat'))
    def chat_menu_wrapper(message):
        user = get_user_by_id(message.from_user.id)
        if not user:
            bot.send_message(message.chat.id, "💬 *Чат*", parse_mode='Markdown')
        elif 'full_name' in user:
            seeker.handle_seeker_chats(message)
        elif 'company_name' in user:
            employer.handle_employer_chats(message)

    # --- Глобальный обработчик (Process All) ---
    @bot.message_handler(content_types=['text', 'photo', 'contact'], func=lambda m: True)
    def process_all_messages(message):
        user_id = message.from_user.id
        try:
            user_state = get_user_state(user_id)

            # Админские шаги
            if user_id in Config.ADMIN_IDS and user_state:
                if user_state.get('step') == 'admin_broadcast_message':
                    return admin.process_broadcast_message(message)
                if user_state.get('step') == 'admin_broadcast_confirm':
                    return admin.process_broadcast_confirm(message)
                if user_state.get('step') == 'admin_search_user':
                    return admin.process_search_user(message)
                if user_state.get('step') == 'admin_reply_message':
                    return admin.process_reply_message(message)
                if user_state.get('step') == 'admin_write_user':
                    return admin.process_write_message(message)

            # Поддержка и чат
            if user_state and user_state.get('step') in ['support_bug_report', 'support_complaint']:
                return common.process_support_message(message)
            if user_state and user_state.get('step') == 'reply_to_admin':
                return common.process_reply_to_admin(message)
            if user_state and user_state.get('step') == 'active_chat':
                return common.handle_chat_message(message)

            # Настройки соискателя
            if user_state and user_state.get('action') == 'edit_seeker_field':
                step = user_state.get('step')
                if step == 'enter_new_value':
                    return settings.process_seeker_field_update(message)
                if step == 'edit_seeker_profession_sphere':
                    return settings.process_seeker_profession_sphere(message)
                if step == 'edit_seeker_profession_specific':
                    return settings.process_seeker_profession_specific(message)

            # Настройки работодателя
            if user_state and user_state.get('action') == 'edit_employer_field':
                if user_state.get('step') == 'enter_new_value':
                    return settings.process_employer_field_update(message)

            # Steps (вакансии, регистрация)
            if steps.handle_steps(message):
                return

            common.handle_unknown(message)

        except Exception as e:
            logging.critical(f"❌ Critical error in process_all_messages: {e}", exc_info=True)
            try:
                bot.send_message(
                    message.chat.id,
                    "❌ System error. Try again later.",
                    reply_markup=keyboards.main_menu()
                )
            except Exception:
                pass