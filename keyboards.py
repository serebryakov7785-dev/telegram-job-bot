# keyboards.py
from telebot import types


def main_menu():
    """Главное меню (до выбора роли)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('👤 Я ищу работу', '🏢 Я работодатель')
    markup.row('ℹ️ О боте')
    return markup


def seeker_menu(is_registered=False):
    """Меню соискателя ДО авторизации (после выбора роли)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('📝 Зарегистрироваться')
    markup.row('🏠 На главную')
    return markup


def employer_menu(is_registered=False):
    """Меню работодателя ДО авторизации (после выбора роли)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('📝 Зарегистрироваться')
    markup.row('🏠 На главную')
    return markup


def seeker_main_menu():
    """Главное меню для авторизованного соискателя"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🔍 Найти вакансии', '📄 Мое резюме')
    markup.row('📋 Мои отклики', '💬 Чат')
    markup.row('⚙️ Настройки', '📞 Поддержка', '🚪 Выйти')
    return markup


def employer_main_menu():
    """Главное меню для авторизованного работодателя"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('➕ Создать вакансию', '📋 Мои вакансии')
    markup.row('👥 Найти сотрудников', '💬 Чат')
    markup.row('⚙️ Настройки', '📞 Поддержка', '🚪 Выйти')
    return markup


def settings_menu(role: str):
    """Меню настроек"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    if role == 'seeker':
        markup.row('🎯 Профессия', '🗣 Языки', '🎨 Навыки')
        markup.row('🎓 Образование', '💼 Опыт', '📊 Статус')
        markup.row('🗑️ Удалить аккаунт', '↩️ Назад в меню')
    else:
        markup.row('🗑️ Удалить компанию')
        markup.row('↩️ Назад в меню')

    return markup


def seeker_status_menu():
    """Меню выбора статуса соискателя"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('✅ Активно ищет работу')
    markup.row('⛔ Нашел работу')
    markup.row('↩️ Назад в настройки')
    return markup


def seeker_submenu(field_name: str, current_value: str):
    """Подменю для настроек соискателя (профессия/образование/опыт/навыки)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    empty_values = ['Не указана', 'Не указано', 'Не указаны', 'Нет опыта', None, '']

    if current_value in empty_values:
        markup.row('➕ Добавить')
    else:
        markup.row('✏️ Изменить')

    markup.row('↩️ Назад в настройки')
    return markup


def cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('❌ Отмена')
    return markup


def admin_menu():
    """Меню администратора"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('📊 Статистика', '👥 Пользователи')
    markup.row('📢 Рассылка', '💾 Бэкап')
    markup.row('⚠️ Жалобы', '⚙️ Настройки бота')
    markup.row('🏠 Главное меню')
    return markup


def admin_users_menu():
    """Меню управления пользователями"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('📋 Список соискателей', '📋 Список работодателей')
    markup.row('🔎 Поиск пользователя', '↩️ Назад в админку')
    return markup


def support_menu():
    """Меню поддержки"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🐛 Ошибка', '⚠️ Жалоба')
    markup.row('🏠 Главное меню')
    return markup


def recovery_menu():
    """Меню восстановления доступа"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('📧 Восстановить пароль')
    markup.row('🏠 Главное меню')
    return markup


def job_type_menu():
    """Меню выбора типа занятости"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('Полный день', 'Частичная занятость')
    markup.row('Удаленная работа', 'Стажировка')
    markup.row('❌ Отмена')
    return markup


def vacancy_actions(vacancy_id: int):
    """Клавиатура действий с вакансией"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📝 Откликнуться", callback_data=f"apply_{vacancy_id}"))
    return markup


def employer_invite_keyboard(seeker_telegram_id: int, vacancy_id: int = None):
    """Клавиатура для приглашения соискателя работодателем"""
    markup = types.InlineKeyboardMarkup()
    if vacancy_id:
        callback_data = f"invite_{seeker_telegram_id}_{vacancy_id}"
    else:
        callback_data = f"invite_{seeker_telegram_id}"
    markup.add(types.InlineKeyboardButton("✉️ Пригласить", callback_data=callback_data))
    return markup


def my_vacancy_actions(vacancy_id: int):
    """Клавиатура действий с МОЕЙ вакансией (для работодателя)"""
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = [
        types.InlineKeyboardButton("✏️ Изменить", callback_data=f"edit_vac_{vacancy_id}"),
        types.InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_vac_{vacancy_id}"),
        types.InlineKeyboardButton("📩 Отклики", callback_data=f"responses_vac_{vacancy_id}")
    ]
    markup.add(*buttons)
    return markup


def delete_confirmation_keyboard(vacancy_id: int):
    """Клавиатура подтверждения удаления вакансии"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Да", callback_data=f"confirm_del_{vacancy_id}"),
        types.InlineKeyboardButton("❌ Нет", callback_data=f"cancel_del_{vacancy_id}")
    )
    return markup


def contact_employer_keyboard(employer_telegram_id: int):
    """Клавиатура для связи с работодателем"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 Написать сообщение", callback_data=f"start_chat_{employer_telegram_id}"))
    return markup


def contact_seeker_keyboard(seeker_telegram_id: int):
    """Клавиатура для связи с соискателем"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 Написать сообщение", callback_data=f"start_chat_{seeker_telegram_id}"))
    return markup


def reply_keyboard(target_id: int):
    """Клавиатура для ответа"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("↩️ Ответить", callback_data=f"start_chat_{target_id}"))
    return markup


def stop_chat_keyboard():
    """Клавиатура завершения чата"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('❌ Завершить чат')
    return markup
