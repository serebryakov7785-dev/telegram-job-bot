from telebot import types

import database
import keyboards
from handlers.settings_employer import EmployerSettingsMixin
from handlers.settings_seeker import SeekerSettingsMixin
from localization import (
    TRANSLATIONS,
    get_all_translations,
    get_text_by_lang,
    get_user_language,
)


class SettingsHandlers(SeekerSettingsMixin, EmployerSettingsMixin):
    def __init__(self, bot):
        self.bot = bot

    def register(self, bot):
        bot.register_message_handler(self.handle_settings_menu,
                                     func=lambda m: m.text in get_all_translations('menu_settings'))
        bot.register_message_handler(self.handle_change_language,
                                     func=lambda m: m.text in get_all_translations('change_language'))

        # Настройки соискателя
        bot.register_message_handler(self.handle_seeker_settings_wrapper, func=self._is_seeker_setting)

        # Статус
        bot.register_message_handler(self.handle_status_settings,
                                     func=lambda m: m.text in get_all_translations('btn_status'))
        bot.register_message_handler(self.handle_set_status_wrapper,
                                     func=lambda m: m.text in get_all_translations('status_active') or m.text in get_all_translations('status_inactive'))

        # Подменю соискателя
        bot.register_message_handler(self.handle_seeker_submenu_action, func=self._is_seeker_submenu)

        # Удаление аккаунта
        bot.register_message_handler(self.handle_delete_account, func=lambda m: m.text in get_all_translations('btn_delete_account') or m.text in get_all_translations('btn_delete_company'))
        bot.register_message_handler(self.confirm_delete_account, func=lambda m: m.text in get_all_translations('confirm_delete') or m.text in get_all_translations('cancel_delete'))

    def _is_seeker_setting(self, m):
        keys = ['btn_profession', 'btn_education', 'btn_languages', 'btn_experience', 'btn_skills']
        return any(m.text in get_all_translations(k) for k in keys)

    def handle_seeker_settings_wrapper(self, message):
        key_map = {'btn_profession': 'profession', 'btn_education': 'education', 'btn_languages': 'languages', 'btn_experience': 'experience', 'btn_skills': 'skills'}
        for key, value in key_map.items():
            if message.text in get_all_translations(key):
                self.handle_seeker_setting(message, value)
                return

    def handle_set_status_wrapper(self, message):
        status = 'active' if message.text in get_all_translations('status_active') else 'inactive'
        self.set_seeker_status(message, status)

    def _is_seeker_submenu(self, message):
        if message.text not in ['✏️ Изменить', '➕ Добавить', '↩️ Назад в настройки']:
            return False
        state = database.get_user_state(message.from_user.id)
        return state and state.get('action') == 'edit_seeker_field'

    def handle_settings_menu(self, message):
        """Меню настроек"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)

        if not user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала зарегистрируйтесь или войдите!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        if 'full_name' in user_data:
            # Соискатель
            role = 'seeker'
            name = user_data['full_name']
            menu_text = get_text_by_lang('settings_seeker_header', lang)
        else:
            # Работодатель
            role = 'employer'
            name = user_data['company_name']
            menu_text = get_text_by_lang('settings_employer_header', lang)

        self.bot.send_message(
            message.chat.id,
            f"{menu_text}\n\n"
            f"{get_text_by_lang('profile_label_settings', lang)} *{name}*\n\n"
            f"{get_text_by_lang('choose_action', lang)}",
            parse_mode='Markdown',
            reply_markup=keyboards.settings_menu(role, lang=lang)
        )

    def handle_delete_account(self, message):
        """Удаление аккаунта"""
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        user_data = database.get_user_by_id(user_id)

        if not user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала зарегистрируйтесь или войдите!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        if 'full_name' in user_data:
            # Соискатель
            role = 'seeker'
            name = user_data['full_name']
        else:
            # Работодатель
            role = 'employer'
            name = user_data['company_name']

        account_type_key = 'account_type_seeker' if role == 'seeker' else 'account_type_employer'
        role_type_key = 'role_type_seeker' if role == 'seeker' else 'role_type_employer'
        account_type = get_text_by_lang(account_type_key, lang)

        # Сохраняем состояние для подтверждения
        database.set_user_state(user_id, {
            'action': 'delete_account',
            'role': role,
            'name': name,
            'account_type': account_type
        })

        # Создаем клавиатуру подтверждения
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(get_text_by_lang('confirm_delete', lang), get_text_by_lang('cancel_delete', lang))

        self.bot.send_message(
            message.chat.id,
            get_text_by_lang('delete_account_warning', lang).format(
                account_type=account_type,
                name=name,
                role_type=get_text_by_lang(role_type_key, lang)
            ),
            parse_mode='Markdown',
            reply_markup=markup
        )

    def confirm_delete_account(self, message):
        """Подтверждение удаления аккаунта"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        lang = get_user_language(user_id)

        if not user_state or user_state.get('action') != 'delete_account':
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла или действие отменено.",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        all_cancel_btns = [d.get('cancel_delete', '') for d in TRANSLATIONS.values()]
        all_confirm_btns = [d.get('confirm_delete', '') for d in TRANSLATIONS.values()]

        if message.text in all_cancel_btns:
            database.clear_user_state(user_id)

            if user_state['role'] == 'seeker':
                self.bot.send_message(
                    message.chat.id,
                    get_text_by_lang('delete_cancelled', lang),
                    parse_mode='Markdown',
                    reply_markup=keyboards.seeker_main_menu()
                )
            else:
                self.bot.send_message(
                    message.chat.id,
                    get_text_by_lang('delete_cancelled', lang),
                    parse_mode='Markdown',
                    reply_markup=keyboards.employer_main_menu()
                )
            return

        elif message.text in all_confirm_btns:
            role = user_state['role']
            name = user_state.get('name', '')
            account_type = user_state.get('account_type', '')

            # Удаляем аккаунт из базы данных
            if role == 'seeker':
                success = database.delete_seeker_account(user_id)
            else:
                success = database.delete_employer_account(user_id)

            # Очищаем состояние в любом случае
            database.clear_user_state(user_id)

            if success:
                self.bot.send_message(
                    message.chat.id,
                    f"{get_text_by_lang('account_deleted_title', lang)}\n\n"
                    f"{get_text_by_lang('account_deleted_body', lang).format(account_type=account_type, name=name)}",
                    parse_mode='Markdown'
                )
                self.bot.send_message(
                    message.chat.id,
                    get_text_by_lang('select_language', 'ru'),
                    reply_markup=keyboards.language_menu()
                )
            else:
                self.bot.send_message(
                    message.chat.id,
                    get_text_by_lang('delete_error', lang),
                    parse_mode='Markdown',
                    reply_markup=keyboards.main_menu()
                )
        else:
            # Если введен неправильный ответ
            self.bot.send_message(
                message.chat.id,
                "❌ Пожалуйста, выберите один из вариантов.",
                parse_mode='Markdown'
            )
            # Повторно показываем меню подтверждения
            self.handle_delete_account(message)

    def handle_change_language(self, message):
        """Обработка смены языка"""
        self.bot.send_message(
            message.chat.id,
            get_text_by_lang('select_language', 'ru'),
            reply_markup=keyboards.language_menu()
        )
