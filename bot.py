# bot.py
import telebot
from datetime import datetime
import logging
import time
from collections import defaultdict
import json

# Попытка импорта библиотек мониторинга
try:
    import sentry_sdk
    from prometheus_client import start_http_server, Counter, Summary
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# Загрузка конфигурации
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Импорт модулей
from config import TOKEN, init_config, ADMIN_IDS, SENTRY_DSN, PROMETHEUS_PORT
from database.schema import init_database
from database.users import get_user_by_id
from database.core import get_user_state, clear_user_state, close_all_connections
from database.vacancies import invalidate_vacancies_cache
from handlers.common import CommonHandlers
from handlers.auth import AuthHandlers
from handlers.seeker import SeekerHandlers
from handlers.employer import EmployerHandlers
from handlers.settings import SettingsHandlers
from handlers.steps import StepHandlers
from handlers.profile import ProfileHandlers
from handlers.admin import AdminHandlers
import keyboards

# Предварительная проверка токена
if not TOKEN or ':' not in TOKEN:
    print("❌ Ошибка: Неверный токен бота!")
    print(f"   Текущее значение: '{TOKEN}'")
    print("   Убедитесь, что в файле .env указан корректный TELEGRAM_BOT_TOKEN.")
    print("   Токен должен содержать двоеточие (например: 123456789:ABC...)")
    import sys
    sys.exit(1)

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# ================= НАСТРОЙКА ЛОГИРОВАНИЯ =================


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
    # JSON Handler для файла (машиночитаемый)
    file_handler = logging.FileHandler("bot.json.log", encoding='utf-8')
    file_handler.setFormatter(JSONFormatter())

    # Stream Handler для консоли (человекочитаемый)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, stream_handler]
    )
    # Уменьшаем "шум" от библиотеки telebot
    logging.getLogger("urllib3").setLevel(logging.WARNING)


common_handlers = CommonHandlers(bot)
auth_handlers = AuthHandlers(bot)
seeker_handlers = SeekerHandlers(bot)
employer_handlers = EmployerHandlers(bot)
settings_handlers = SettingsHandlers(bot)
profile_handlers = ProfileHandlers(bot)
admin_handlers = AdminHandlers(bot)

# Создаем обработчик шагов И передаем ему auth_handlers
step_handlers = StepHandlers(bot)
step_handlers.set_auth_handlers(auth_handlers)
step_handlers.set_employer_handlers(employer_handlers)

# ================= МОНИТОРИНГ =================
if MONITORING_AVAILABLE:
    # Метрики Prometheus
    METRIC_MESSAGES = Counter('bot_messages_total', 'Total messages processed', ['type'])
    METRIC_ERRORS = Counter('bot_errors_total', 'Total errors encountered', ['type'])
    METRIC_LATENCY = Summary('bot_processing_seconds', 'Time spent processing messages')

    # Запуск сервера метрик
    try:
        start_http_server(PROMETHEUS_PORT)
        logging.info(f"✅ Prometheus metrics server running on port {PROMETHEUS_PORT}")
    except Exception as e:
        logging.error(f"❌ Failed to start Prometheus server: {e}")

    # Инициализация Sentry
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=1.0)
        logging.info("✅ Sentry initialized")


# ================= РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ =================

# Команды
@bot.message_handler(commands=['start', 'restart'])
def start_command(message):
    common_handlers.handle_start(message)


@bot.message_handler(commands=['help', 'помощь'])
def help_command(message):
    common_handlers.handle_help(message)


@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ У вас нет прав доступа к этой команде.")
        return
    common_handlers.handle_admin(message)


@bot.message_handler(commands=['backup'])
def backup_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ У вас нет прав доступа к этой команде.")
        return
    admin_handlers.handle_create_backup(message)


@bot.message_handler(commands=['cancel', 'отмена', 'отменить'])
def cancel_command(message):
    """Обработчик команды /cancel"""
    clear_user_state(message.from_user.id)
    bot.send_message(
        message.chat.id,
        "❌ Действие отменено",
        parse_mode='Markdown',
        reply_markup=keyboards.main_menu()
    )


@bot.message_handler(commands=['debug', 'отладка'])
def debug_command(message):
    """Команда отладки для проверки состояния"""
    user_id = message.from_user.id

    user_data = get_user_by_id(user_id)
    user_state = get_user_state(user_id)

    debug_info = "🛠️ *Информация для отладки*\n\n"
    debug_info += f"🆔 Ваш Telegram ID: `{user_id}`\n"

    if user_data:
        if 'full_name' in user_data:
            debug_info += "👤 *Тип:* Соискатель\n"
            debug_info += f"📛 *Имя:* {user_data['full_name']}\n"
            debug_info += f"📞 *Телефон:* {user_data.get('phone', 'N/A')}\n"
            debug_info += f"📧 *Email:* {user_data.get('email', 'N/A')}\n"
            debug_info += f"📅 *ID в базе:* {user_data.get('id', 'N/A')}\n"
        else:
            debug_info += "🏢 *Тип:* Работодатель\n"
            debug_info += f"🏢 *Компания:* {user_data.get('company_name', 'N/A')}\n"
            debug_info += f"👤 *Контакт:* {user_data.get('contact_person', 'N/A')}\n"
            debug_info += f"📞 *Телефон:* {user_data.get('phone', 'N/A')}\n"
            debug_info += f"📧 *Email:* {user_data.get('email', 'N/A')}\n"
            debug_info += f"📅 *ID в базе:* {user_data.get('id', 'N/A')}\n"
    else:
        debug_info += "❌ *Статус:* Не зарегистрирован\n"

    if user_state:
        debug_info += "\n📋 *Текущее состояние:*\n"
        for key, value in user_state.items():
            debug_info += f"  • {key}: {value}\n"
    else:
        debug_info += "\n📋 *Текущее состояние:* Нет активного состояния\n"

    bot.send_message(
        message.chat.id,
        debug_info,
        parse_mode='Markdown'
    )

    # Показываем соответствующее меню
    if user_data:
        if 'full_name' in user_data:
            bot.send_message(message.chat.id, "👇 Используйте меню соискателя:", reply_markup=keyboards.seeker_main_menu())
        else:
            bot.send_message(message.chat.id, "👇 Используйте меню работодателя:", reply_markup=keyboards.employer_main_menu())
    else:
        bot.send_message(message.chat.id, "👇 Используйте главное меню:", reply_markup=keyboards.main_menu())


# Главное меню и навигация
@bot.message_handler(func=lambda m: m.text in ['👤 Я ищу работу', '🏢 Я работодатель'])
def role_selection(message):
    auth_handlers.handle_role_selection(message)


@bot.message_handler(func=lambda m: m.text in ['🏠 На главную', '🏠 Главное меню'])
def back_to_main(message):
    common_handlers.handle_back_to_main(message)


@bot.message_handler(func=lambda m: m.text == '↩️ Назад в меню')
def back_to_profile(message):
    common_handlers.handle_back_to_profile(message)


# Авторизация

@bot.message_handler(func=lambda m: m.text == '📝 Зарегистрироваться')
def register_handler(message):
    auth_handlers.handle_registration_start(message)


@bot.message_handler(func=lambda m: m.text == '🔑 Забыли пароль?')
def recovery_handler(message):
    auth_handlers.handle_password_recovery(message)


@bot.message_handler(func=lambda m: m.text == '🚪 Выйти')
def logout_handler(message):
    auth_handlers.handle_logout(message)


# Соискатели
@bot.message_handler(func=lambda m: m.text == '🔍 Найти вакансии')
def find_vacancies_handler(message):
    seeker_handlers.handle_find_vacancies(message)


@bot.message_handler(func=lambda m: m.text == '📄 Мое резюме')
def my_resume_handler(message):
    seeker_handlers.handle_my_resume(message)


@bot.message_handler(func=lambda m: m.text == '📋 Мои отклики')
def my_responses_handler(message):
    seeker_handlers.handle_my_responses(message)


# Работодатели
@bot.message_handler(func=lambda m: m.text == '➕ Создать вакансию')
def create_vacancy_handler(message):
    employer_handlers.handle_create_vacancy(message)


@bot.message_handler(func=lambda m: m.text == '👥 Найти сотрудников')
def find_candidates_handler(message):
    employer_handlers.handle_find_candidates(message)


@bot.message_handler(func=lambda m: m.text == '📋 Мои вакансии')
def my_vacancies_handler(message):
    employer_handlers.handle_my_vacancies(message)


# Админ-панель
@bot.message_handler(func=lambda m: m.text == '📊 Статистика' and m.from_user.id in ADMIN_IDS)
def admin_stats_handler(message):
    admin_handlers.handle_statistics(message)


@bot.message_handler(func=lambda m: m.text == '📢 Рассылка' and m.from_user.id in ADMIN_IDS)
def admin_broadcast_handler(message):
    admin_handlers.handle_broadcast_start(message)


@bot.message_handler(func=lambda m: m.text == '👥 Пользователи' and m.from_user.id in ADMIN_IDS)
def admin_users_handler(message):
    admin_handlers.handle_users(message)


@bot.message_handler(func=lambda m: m.text == '📋 Список соискателей' and m.from_user.id in ADMIN_IDS)
def admin_list_seekers(message):
    admin_handlers.handle_list_seekers(message)


@bot.message_handler(func=lambda m: m.text == '📋 Список работодателей' and m.from_user.id in ADMIN_IDS)
def admin_list_employers(message):
    admin_handlers.handle_list_employers(message)


@bot.message_handler(func=lambda m: m.text == '⚠️ Жалобы' and m.from_user.id in ADMIN_IDS)
def admin_complaints_handler(message):
    admin_handlers.handle_complaints(message)


@bot.message_handler(func=lambda m: m.text == '🔎 Поиск пользователя' and m.from_user.id in ADMIN_IDS)
def admin_search_user(message):
    admin_handlers.handle_search_user_prompt(message)


@bot.message_handler(func=lambda m: m.text == '↩️ Назад в админку' and m.from_user.id in ADMIN_IDS)
def admin_back_to_menu(message):
    common_handlers.handle_admin(message)


@bot.message_handler(func=lambda m: m.text == '⚙️ Настройки бота' and m.from_user.id in ADMIN_IDS)
def admin_settings_handler(message):
    admin_handlers.handle_admin_settings(message)


@bot.message_handler(func=lambda m: m.text == '💾 Бэкап' and m.from_user.id in ADMIN_IDS)
def admin_backup_handler(message):
    admin_handlers.handle_create_backup(message)


# Настройки
@bot.message_handler(func=lambda m: m.text in ['⚙️ Настройки', '⚙️ Настройки компании'])
def settings_handler(message):
    settings_handlers.handle_settings_menu(message)


# Обработка кнопок настроек соискателя
@bot.message_handler(func=lambda m: m.text in ['🎯 Профессия', '🎓 Образование', '🗣 Языки', '💼 Опыт', '🎨 Навыки'])
def seeker_settings_handler(message):
    field_map = {
        '🎯 Профессия': 'profession',
        '🎓 Образование': 'education',
        '🗣 Языки': 'languages',
        '💼 Опыт': 'experience',
        '🎨 Навыки': 'skills'
    }

    field = field_map.get(message.text)
    if field:
        settings_handlers.handle_seeker_setting(message, field)


@bot.message_handler(func=lambda m: m.text == '📊 Статус')
def seeker_status_handler(message):
    settings_handlers.handle_status_settings(message)


@bot.message_handler(func=lambda m: m.text in ['✅ Активно ищет работу', '⛔ Нашел работу'])
def set_status_handler(message):
    status = 'active' if message.text == '✅ Активно ищет работу' else 'inactive'
    settings_handlers.set_seeker_status(message, status)


def is_seeker_submenu(message):
    """Проверка, что сообщение относится к подменю настроек соискателя"""
    if message.text not in ['✏️ Изменить', '➕ Добавить', '↩️ Назад в настройки']:
        return False
    state = get_user_state(message.from_user.id)
    return state and state.get('action') == 'edit_seeker_field'


@bot.message_handler(func=is_seeker_submenu)
def seeker_submenu_handler(message):
    settings_handlers.handle_seeker_submenu_action(message)


# Удаление аккаунта
@bot.message_handler(func=lambda m: m.text in ['🗑️ Удалить аккаунт', '🗑️ Удалить компанию'])
def delete_account_handler(message):
    settings_handlers.handle_delete_account(message)


# Подтверждение удаления аккаунта
@bot.message_handler(func=lambda m: m.text in ['✅ Да, удалить аккаунт', '❌ Нет, отменить'])
def confirm_delete_handler(message):
    settings_handlers.confirm_delete_account(message)


# Заполнение профиля
@bot.message_handler(func=lambda m: m.text in ['📝 Заполнить профиль', '🏢 Заполнить профиль компании'])
def complete_profile_handler(message):
    profile_handlers.handle_complete_profile(message)


# Общие функции
@bot.message_handler(func=lambda m: m.text == 'ℹ️ О боте')
def about_handler(message):
    common_handlers.handle_about(message)


@bot.message_handler(func=lambda m: m.text == '📞 Поддержка')
def support_handler(message):
    common_handlers.handle_support(message)


@bot.message_handler(func=lambda m: m.text == '🐛 Ошибка')
def bug_report_handler(message):
    common_handlers.handle_report_bug(message)


@bot.message_handler(func=lambda m: m.text == '⚠️ Жалоба')
def complaint_handler(message):
    common_handlers.handle_complaint(message)


# Обработка кнопки "Отмена"
@bot.message_handler(func=lambda m: m.text == '❌ Отмена')
def cancel_button_handler(message):
    user_id = message.from_user.id
    user_state = get_user_state(user_id)
    if user_state:
        step_handlers.cancel_current_step(user_id, message.chat.id)
    else:
        clear_user_state(user_id)
        bot.send_message(
            message.chat.id,
            "❌ Действие отменено",
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu()
        )


# Обработка callback-запросов (например, отклик на вакансию)
@bot.callback_query_handler(func=lambda call: call.data.startswith('apply_'))
def application_callback(call):
    seeker_handlers.handle_application_callback(call)


# Обработка callback-запросов (приглашение от работодателя)
@bot.callback_query_handler(func=lambda call: call.data.startswith('invite_'))
def invitation_callback(call):
    employer_handlers.handle_invitation_callback(call)


# Обработка callback-запросов для управления вакансиями работодателя
@bot.callback_query_handler(func=lambda call: call.data.startswith(('edit_vac_', 'delete_vac_', 'responses_vac_')))
def my_vacancy_actions_callback(call):
    employer_handlers.handle_my_vacancy_actions(call)


# Обработка подтверждения/отмены удаления вакансии
@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def confirm_delete_callback(call):
    employer_handlers.handle_confirm_delete(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_del_'))
def cancel_delete_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🏠 Возврат в меню", reply_markup=keyboards.employer_main_menu())


# Обработка начала чата
@bot.callback_query_handler(func=lambda call: call.data.startswith('start_chat_'))
def start_chat_callback(call):
    common_handlers.handle_start_chat(call)


# Обработка действий администратора
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_action_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Доступ запрещен")
        return

    if call.data == 'admin_clear_cache':
        invalidate_vacancies_cache()
        bot.answer_callback_query(call.id, "✅ Кэш вакансий очищен")
    elif call.data == 'admin_maintenance':
        bot.answer_callback_query(call.id, "🛠 Функция в разработке")
    elif call.data.startswith('admin_resolve_complaint_'):
        admin_handlers.handle_resolve_complaint(call)
    elif call.data.startswith('admin_reply_'):
        admin_handlers.handle_reply_prompt(call)


# Обработка завершения чата
@bot.message_handler(func=lambda m: m.text == '❌ Завершить чат')
def stop_chat_handler(message):
    common_handlers.handle_stop_chat(message)


# Обработка кнопки "Чат" из главного меню
@bot.message_handler(func=lambda m: m.text == '💬 Чат')
def chat_menu_handler(message):
    user_id = message.from_user.id
    user_data = get_user_by_id(user_id)

    if user_data:
        if 'full_name' in user_data:
            # Если это соискатель - показываем список приглашений
            seeker_handlers.handle_seeker_chats(message)
        elif 'company_name' in user_data:
            # Если это работодатель - показываем список чатов
            employer_handlers.handle_employer_chats(message)
    else:
        bot.send_message(
            message.chat.id,
            "💬 *Чат*\n\n"
            "Чтобы начать диалог, перейдите в приглашение или отклик и нажмите кнопку связи.",
            parse_mode='Markdown'
        )


# ================= RATE LIMITING =================
RATE_LIMIT = 5  # сообщений
TIME_WINDOW = 10  # секунд
MUTE_DURATION = 30  # секунд

# defaultdict(list) удобнее, чем обычный dict, так как не требует проверки на наличие ключа
user_requests = defaultdict(list)
muted_users = {}  # {user_id: mute_end_timestamp}


def check_rate_limit(message):
    """Проверка лимита запросов для сообщения"""
    if not message.from_user:
        return True

    user_id = message.from_user.id
    current_time = time.time()

    # 1. Проверка, не заглушен ли пользователь
    if user_id in muted_users:
        if current_time < muted_users[user_id]:
            return False  # Просто игнорируем сообщение
        else:
            del muted_users[user_id]  # Снимаем мьют

    # 2. Обновление и проверка лимита
    user_requests[user_id] = [t for t in user_requests[user_id] if current_time - t < TIME_WINDOW]

    # 3. Проверяем, не превышено ли количество запросов
    if len(user_requests[user_id]) >= RATE_LIMIT:
        muted_users[user_id] = current_time + MUTE_DURATION
        logging.warning(f"Rate limit exceeded for user {user_id}. Muting for {MUTE_DURATION} seconds.")
        try:
            bot.send_message(user_id,
                             f"⏳ Вы отправляете сообщения слишком часто. Пожалуйста, подождите {MUTE_DURATION} секунд.")
        except Exception as e:
            logging.error(f"Could not send rate limit warning to user {user_id}: {e}")
        return False

    # 4. Запись текущего запроса
    user_requests[user_id].append(current_time)
    return True

# Патчим обработку сообщений для глобального Rate Limiting


original_process_new_messages = bot.process_new_messages


def custom_process_new_messages(messages):
    valid_messages = []
    for message in messages:
        if check_rate_limit(message):
            valid_messages.append(message)
            if MONITORING_AVAILABLE:
                METRIC_MESSAGES.labels(type='incoming_message').inc()

    if valid_messages:
        if MONITORING_AVAILABLE:
            with METRIC_LATENCY.time():
                original_process_new_messages(valid_messages)
        else:
            original_process_new_messages(valid_messages)


bot.process_new_messages = custom_process_new_messages


# Патчим обработку callback_query для глобального Rate Limiting
original_process_new_callback_query = bot.process_new_callback_query


def custom_process_new_callback_query(callback_queries):
    valid_queries = []
    for callback_query in callback_queries:
        # Передаем сам объект callback_query, так как у него тоже есть атрибут from_user
        if check_rate_limit(callback_query):
            valid_queries.append(callback_query)
            if MONITORING_AVAILABLE:
                METRIC_MESSAGES.labels(type='callback_query').inc()
        else:
            # Если лимит превышен, показываем уведомление на кнопке
            try:
                bot.answer_callback_query(callback_query.id, "⏳ Слишком много запросов. Подождите.", show_alert=True)
            except Exception:
                pass

    if valid_queries:
        original_process_new_callback_query(valid_queries)


bot.process_new_callback_query = custom_process_new_callback_query


# ================= ОБРАБОТКА ВСЕХ ОСТАЛЬНЫХ СООБЩЕНИЙ =================
@bot.message_handler(content_types=['text', 'photo'], func=lambda m: True)
def process_all_messages(message):  # noqa: C901
    """Обработка всех остальных сообщений (step-by-step, профиль, неизвестные)"""

    user_id = message.from_user.id

    try:
        user_state = get_user_state(user_id)

        # 0. Проверяем админские шаги
        if user_id in ADMIN_IDS and user_state:
            if user_state.get('step') == 'admin_broadcast_message':
                admin_handlers.process_broadcast_message(message)
                return
            if user_state.get('step') == 'admin_broadcast_confirm':
                admin_handlers.process_broadcast_confirm(message)
                return
            if user_state.get('step') == 'admin_search_user':
                admin_handlers.process_search_user(message)
                return
            if user_state.get('step') == 'admin_reply_message':
                admin_handlers.process_reply_message(message)
                return

        # Обработка обращений в поддержку
        if user_state and user_state.get('step') in ['support_bug_report', 'support_complaint']:
            common_handlers.process_support_message(message)
            return

        # 1. Проверяем активный чат
        if user_state and user_state.get('step') == 'active_chat':
            common_handlers.handle_chat_message(message)
            return

        # 2. Проверяем заполнение профиля
        profile_steps = [
            'profession', 'profession_sphere', 'profession_specific',
            'education', 'languages', 'experience', 'skills',
            'language_selection', 'language_level', 'language_custom_name'
        ]

        if user_state and user_state.get('step') in profile_steps:
            step = user_state['step']
            if step == 'profession':
                # Legacy support or fallback
                profile_handlers.process_profession_specific(message)
            elif step == 'profession_sphere':
                profile_handlers.process_profession_sphere(message)
            elif step == 'profession_specific':
                profile_handlers.process_profession_specific(message)
            elif step == 'education':
                profile_handlers.process_education(message)
            elif step == 'languages':
                # Legacy redirect to new flow
                user_state['temp_languages'] = []
                profile_handlers.show_language_selection(message.chat.id, user_id, user_state)
            elif step == 'language_selection':
                profile_handlers.process_language_selection(message)
            elif step == 'language_level':
                profile_handlers.process_language_level(message)
            elif step == 'language_custom_name':
                profile_handlers.process_language_custom_name(message)
            elif step == 'experience':
                profile_handlers.process_experience(message)
            elif step == 'skills':
                profile_handlers.process_skills(message)
            return

        # 3. Проверяем редактирование поля соискателя
        if user_state and user_state.get('action') == 'edit_seeker_field':
            step = user_state.get('step')
            if step == 'enter_new_value':
                settings_handlers.process_seeker_field_update(message)
                return
            elif step == 'edit_seeker_profession_sphere':
                settings_handlers.process_seeker_profession_sphere(message)
                return
            elif step == 'edit_seeker_profession_specific':
                settings_handlers.process_seeker_profession_specific(message)
                return

        # 4. Пробуем обработать как step-by-step сообщение
        if step_handlers.handle_steps(message):
            return

        # 5. Если не обработано - неизвестное сообщение
        common_handlers.handle_unknown(message)

    except Exception as e:
        if MONITORING_AVAILABLE:
            METRIC_ERRORS.labels(type='critical_exception').inc()
        logging.critical(f"❌ Критическая ошибка обработки сообщения: {e}", exc_info=True)
        try:
            bot.send_message(
                message.chat.id,
                "❌ Произошла системная ошибка. Пожалуйста, попробуйте позже.",
                reply_markup=keyboards.main_menu()
            )
        except Exception as inner_e:
            logging.error(f"Не удалось отправить сообщение об ошибке пользователю: {inner_e}")
            pass


# ================= ЗАПУСК БОТА =================
def run_bot():
    setup_logging()
    init_config()
    init_database()

    logging.info("=" * 60)
    logging.info("🤖 БОТ ДЛЯ ПОИСКА РАБОТЫ - УЗБЕКИСТАН 🇺🇿")
    logging.info("=" * 60)
    logging.info("🚀 Запуск: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    logging.info("📱 Только номера: +998")
    logging.info("=" * 60)

    logging.info("✅ Бот запущен! Откройте Telegram и найдите своего бота")
    logging.info("=" * 60)

    # Удаляем вебхук перед запуском polling, чтобы избежать конфликтов
    try:
        bot.remove_webhook()
    except Exception:
        pass

    while True:
        try:
            try:
                bot.polling(non_stop=True, timeout=60, long_polling_timeout=60)
            except Exception as e:
                logging.critical(f"❌ Критическая ошибка в цикле polling: {e}", exc_info=True)
                close_all_connections()
                logging.info("🔄 Перезапуск polling через 5 секунд...")
                time.sleep(5)
                continue

            logging.warning("⚠️ Polling завершил работу. Перезапуск через 5 секунд...")
            time.sleep(5)
        except (KeyboardInterrupt, SystemExit):
            logging.info("\n🛑 Бот остановлен пользователем (Ctrl+C). Выход...")
            bot.stop_bot()
            break


if __name__ == "__main__":
    run_bot()
