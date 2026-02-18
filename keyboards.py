# keyboards.py
from typing import Optional, Union

from telebot import types

from localization import get_text_by_lang


def language_menu():
    """Меню выбора языка"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🇺🇿 O'zbekcha", "🇷🇺 Русский", "🇬🇧 English")
    return markup


def main_menu(lang: str = "ru") -> types.ReplyKeyboardMarkup:
    """Главное меню (до выбора роли)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        get_text_by_lang("role_seeker", lang), get_text_by_lang("role_employer", lang)
    )
    markup.row(
        get_text_by_lang("back_to_lang", lang), get_text_by_lang("about_bot", lang)
    )
    return markup


def seeker_menu(is_registered=False, lang="ru"):
    """Меню соискателя ДО авторизации (после выбора роли)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(get_text_by_lang("register_button", lang))
    markup.row(get_text_by_lang("menu_find_vacancies", lang))
    markup.row(get_text_by_lang("back_to_main_menu", lang))
    return markup


def employer_menu(is_registered=False, lang="ru"):
    """Меню работодателя ДО авторизации (после выбора роли)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(get_text_by_lang("register_button", lang))
    markup.row(get_text_by_lang("menu_find_candidates", lang))
    markup.row(get_text_by_lang("back_to_main_menu", lang))
    return markup


def seeker_main_menu(lang="ru"):
    """Главное меню для авторизованного соискателя"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        get_text_by_lang("menu_find_vacancies", lang),
        get_text_by_lang("menu_my_resume", lang),
    )
    markup.row(
        get_text_by_lang("menu_my_responses", lang), get_text_by_lang("menu_chat", lang)
    )
    markup.row(
        get_text_by_lang("menu_settings", lang),
        get_text_by_lang("menu_support", lang),
        get_text_by_lang("menu_logout", lang),
    )
    return markup


def employer_main_menu(lang="ru"):
    """Главное меню для авторизованного работодателя"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        get_text_by_lang("menu_create_vacancy", lang),
        get_text_by_lang("menu_my_vacancies", lang),
    )
    markup.row(
        get_text_by_lang("menu_find_candidates", lang),
        get_text_by_lang("menu_chat", lang),
    )
    markup.row(
        get_text_by_lang("menu_settings", lang),
        get_text_by_lang("menu_support", lang),
        get_text_by_lang("menu_logout", lang),
    )
    return markup


def settings_menu(role: str, lang: str = "ru") -> types.ReplyKeyboardMarkup:
    """Меню настроек"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    if role == "seeker":
        markup.row(
            get_text_by_lang("btn_profession", lang),
            get_text_by_lang("btn_languages", lang),
            get_text_by_lang("btn_skills", lang),
        )
        markup.row(
            get_text_by_lang("btn_education", lang),
            get_text_by_lang("btn_experience", lang),
        )
        markup.row(
            get_text_by_lang("btn_status", lang),
            get_text_by_lang("change_language", lang),
        )
        markup.row(
            get_text_by_lang("btn_delete_account", lang),
            get_text_by_lang("btn_back_to_panel_menu", lang),
        )
    else:
        markup.row(get_text_by_lang("btn_delete_company", lang))
        markup.row(get_text_by_lang("change_language", lang))
        markup.row(get_text_by_lang("btn_back_to_panel_menu", lang))

    return markup


def seeker_status_menu(lang="ru"):
    """Меню выбора статуса соискателя"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(get_text_by_lang("status_active", lang))
    markup.row(get_text_by_lang("status_inactive", lang))
    markup.row(get_text_by_lang("btn_back_settings", lang))
    return markup


def seeker_submenu(
    field_name: str, current_value: Optional[str], lang: str = "ru"
) -> types.ReplyKeyboardMarkup:
    """Подменю для настроек соискателя (профессия/образование/опыт/навыки)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    empty_values = ["Не указана", "Не указано", "Не указаны", "Нет опыта", None, ""]

    if current_value in empty_values:
        markup.row(get_text_by_lang("add_button", lang))
    else:
        markup.row(get_text_by_lang("edit_button", lang))

    markup.row(get_text_by_lang("btn_back_settings", lang))
    return markup


def contact_request_keyboard(lang="ru"):
    """Клавиатура для запроса контакта"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        types.KeyboardButton(
            get_text_by_lang("btn_send_contact", lang), request_contact=True
        )
    )
    markup.row(get_text_by_lang("cancel_button", lang))
    return markup


def cancel_keyboard(lang="ru"):
    """Клавиатура с кнопкой отмены"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(get_text_by_lang("cancel_button", lang))
    return markup


def admin_menu():
    """Меню администратора"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📊 Статистика", "👥 Пользователи")
    markup.row("📢 Рассылка", "💾 Бэкап")
    markup.row("⚠️ Жалобы", "⚙️ Настройки бота")
    markup.row("🏠 Главное меню")
    return markup


def admin_users_menu() -> types.ReplyKeyboardMarkup:
    """Меню управления пользователями"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 Список соискателей", "📋 Список работодателей")
    markup.row("🔎 Поиск пользователя", "↩️ Назад в админку")
    return markup


def support_menu(lang="ru"):
    """Меню поддержки"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        get_text_by_lang("btn_report_bug", lang),
        get_text_by_lang("btn_complaint", lang),
    )
    markup.row(get_text_by_lang("btn_back_to_panel_menu", lang))
    return markup


def recovery_menu():
    """Меню восстановления доступа"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📧 Восстановить пароль")
    markup.row("🏠 Главное меню")
    return markup


def job_type_menu(lang="ru") -> types.ReplyKeyboardMarkup:
    """Меню выбора типа занятости"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        get_text_by_lang("job_type_full_time", lang),
        get_text_by_lang("job_type_part_time", lang),
    )
    markup.row(
        get_text_by_lang("job_type_remote", lang),
        get_text_by_lang("job_type_internship", lang),
    )
    markup.row(get_text_by_lang("cancel_button", lang))
    return markup


def vacancy_actions(vacancy_id: int, lang: str = "ru") -> types.InlineKeyboardMarkup:
    """Клавиатура действий с вакансией"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            get_text_by_lang("btn_apply", lang), callback_data=f"apply_{vacancy_id}"
        )
    )
    return markup


def employer_invite_keyboard(
    seeker_telegram_id: int, vacancy_id: Union[int, None] = None, lang: str = "ru"
) -> types.InlineKeyboardMarkup:
    """Клавиатура для приглашения соискателя работодателем"""
    markup = types.InlineKeyboardMarkup()
    if vacancy_id:
        callback_data = f"invite_{seeker_telegram_id}_{vacancy_id}"
    else:
        callback_data = f"invite_{seeker_telegram_id}"
    markup.add(
        types.InlineKeyboardButton(
            get_text_by_lang("btn_invite", lang), callback_data=callback_data
        )
    )
    return markup


def my_vacancy_actions(vacancy_id: int, lang: str = "ru") -> types.InlineKeyboardMarkup:
    """Клавиатура действий с МОЕЙ вакансией (для работодателя)"""
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = [
        types.InlineKeyboardButton(
            get_text_by_lang("btn_edit_vacancy", lang),
            callback_data=f"edit_vac_{vacancy_id}",
        ),
        types.InlineKeyboardButton(
            get_text_by_lang("btn_delete_vacancy", lang),
            callback_data=f"delete_vac_{vacancy_id}",
        ),
        types.InlineKeyboardButton(
            get_text_by_lang("btn_vacancy_responses", lang),
            callback_data=f"responses_vac_{vacancy_id}",
        ),
    ]
    markup.add(*buttons)
    return markup


def delete_confirmation_keyboard(
    vacancy_id: int, lang: str = "ru"
) -> types.InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления вакансии"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            get_text_by_lang("btn_yes", lang), callback_data=f"confirm_del_{vacancy_id}"
        ),
        types.InlineKeyboardButton(
            get_text_by_lang("btn_no", lang), callback_data=f"cancel_del_{vacancy_id}"
        ),
    )
    return markup


def contact_employer_keyboard(employer_telegram_id: int) -> types.InlineKeyboardMarkup:
    """Клавиатура для связи с работодателем"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "💬 Написать сообщение", callback_data=f"start_chat_{employer_telegram_id}"
        )
    )
    return markup


def contact_seeker_keyboard(seeker_telegram_id: int) -> types.InlineKeyboardMarkup:
    """Клавиатура для связи с соискателем"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "💬 Написать сообщение", callback_data=f"start_chat_{seeker_telegram_id}"
        )
    )
    return markup


def reply_keyboard(target_id: int) -> types.InlineKeyboardMarkup:
    """Клавиатура для ответа"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "↩️ Ответить", callback_data=f"start_chat_{target_id}"
        )
    )
    return markup


def stop_chat_keyboard():
    """Клавиатура завершения чата"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("❌ Завершить чат")
    return markup


def admin_user_action_keyboard(user_id, is_blocked=False):
    """Клавиатура действий админа с пользователем"""
    markup = types.InlineKeyboardMarkup()

    btns = [
        types.InlineKeyboardButton("✉️ Написать", callback_data=f"admin_write_{user_id}")
    ]
    if is_blocked:
        btns.append(
            types.InlineKeyboardButton(
                "🔓 Разблокировать", callback_data=f"admin_unblock_{user_id}"
            )
        )
    else:
        btns.append(
            types.InlineKeyboardButton(
                "🚫 Блокировать", callback_data=f"admin_block_menu_{user_id}"
            )
        )

    markup.add(*btns)
    return markup


def block_duration_keyboard(user_id):
    """Клавиатура выбора длительности блокировки"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("1 Час", callback_data=f"admin_block_{user_id}_1h"),
        types.InlineKeyboardButton(
            "12 Часов", callback_data=f"admin_block_{user_id}_12h"
        ),
        types.InlineKeyboardButton(
            "24 Часа", callback_data=f"admin_block_{user_id}_24h"
        ),
        types.InlineKeyboardButton(
            "Навсегда", callback_data=f"admin_block_{user_id}_forever"
        ),
        types.InlineKeyboardButton(
            "❌ Отмена", callback_data=f"admin_block_{user_id}_cancel"
        ),
    )
    return markup


def user_reply_keyboard(admin_id):
    """Клавиатура ответа админу"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "↩️ Ответить", callback_data=f"reply_admin_{admin_id}"
        )
    )
    return markup
