from telebot import types
import database
import keyboards
import utils
from handlers.profile import PROFESSION_SPHERES, LANGUAGES_DICT


class SettingsHandlers:
    def __init__(self, bot):
        self.bot = bot

    def handle_settings_menu(self, message):
        """Меню настроек"""
        user_id = message.from_user.id
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
            menu_text = "👤 *Настройки соискателя*"
        else:
            # Работодатель
            role = 'employer'
            name = user_data['company_name']
            menu_text = "🏢 *Настройки компании*"

        self.bot.send_message(
            message.chat.id,
            f"{menu_text}\n\n"
            f"Профиль: *{name}*\n\n"
            f"Выберите действие:",
            parse_mode='Markdown',
            reply_markup=keyboards.settings_menu(role)
        )

    def handle_seeker_setting(self, message, field: str):
        """Обработка нажатия на кнопку настройки соискателя"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data or 'full_name' not in user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала войдите как соискатель!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        # Определяем название поля для отображения
        field_names = {
            'profession': '🎯 Профессия',
            'education': '🎓 Образование',
            'experience': '💼 Опыт работы',
            'skills': '🎨 Навыки',
            'languages': '🗣 Языки'
        }

        field_display = field_names.get(field, field)
        current_value = user_data.get(field, 'Не указано')

        # Сохраняем состояние для следующего шага
        database.set_user_state(user_id, {
            'action': 'edit_seeker_field',
            'field': field,
            'field_display': field_display,
            'current_value': current_value
        })

        # Показываем подменю
        if current_value and current_value not in ['Не указана', 'Не указано', 'Не указаны', 'Нет опыта']:
            message_text = f"{field_display}\n\n*Текущее значение:*\n{current_value}\n\nВыберите действие:"
        else:
            message_text = f"{field_display}\n\nПоле еще не заполнено.\n\nВыберите действие:"

        self.bot.send_message(
            message.chat.id,
            message_text,
            parse_mode='Markdown',
            reply_markup=keyboards.seeker_submenu(field, current_value)
        )

    def handle_seeker_submenu_action(self, message):
        """Обработка действий в подменю соискателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if not user_state or user_state.get('action') != 'edit_seeker_field':
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла!",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        field = user_state['field']
        field_display = user_state['field_display']
        current_value = user_state['current_value']

        if message.text == '↩️ Назад в настройки':
            database.clear_user_state(user_id)
            self.handle_settings_menu(message)
            return

        elif message.text == '✏️ Изменить' or message.text == '➕ Добавить':
            # Если это профессия, запускаем выбор сферы
            if field == 'profession':
                user_state['step'] = 'edit_seeker_profession_sphere'
                database.set_user_state(user_id, user_state)

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                for sphere in PROFESSION_SPHERES.keys():
                    markup.add(types.KeyboardButton(sphere))
                markup.add(types.KeyboardButton("Другое"))
                markup.add(types.KeyboardButton("❌ Отмена"))

                self.bot.send_message(
                    message.chat.id,
                    "📂 *Выберите сферу деятельности:*",
                    parse_mode='Markdown',
                    reply_markup=markup
                )
                return

            # Если это языки, запускаем интерактивный выбор
            if field == 'languages':
                user_state['step'] = 'language_selection'
                user_state['source'] = 'settings'
                user_state['temp_languages'] = []
                database.set_user_state(user_id, user_state)

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                for btn_text in LANGUAGES_DICT.keys():
                    markup.add(types.KeyboardButton(btn_text))
                markup.add(types.KeyboardButton("🌐 Другой"))
                markup.add(types.KeyboardButton("Пропустить"))
                markup.add(types.KeyboardButton("❌ Отмена"))

                self.bot.send_message(message.chat.id, "🗣 *Какими языками вы владеете?*\n\nВыберите язык из списка.",
                                      parse_mode='Markdown', reply_markup=markup)
                return

            # Устанавливаем состояние для ввода нового значения
            user_state['step'] = 'enter_new_value'
            database.set_user_state(user_id, user_state)

            if message.text == '✏️ Изменить':
                prompt = f"Введите новое значение для {field_display.lower()}:\n\nТекущее значение: *{current_value}*"
            else:
                prompt = f"Введите значение для {field_display.lower()}:"

            self.bot.send_message(
                message.chat.id,
                f"✏️ *{field_display}*\n\n"
                f"{prompt}\n\n"
                f"Используйте /cancel или кнопку '❌ Отмена' для отмены.",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        else:
            # Неизвестное действие, возвращаем в подменю
            self.bot.send_message(
                message.chat.id,
                f"❌ Неизвестное действие!\n\n"
                f"Возврат в {field_display}...",
                parse_mode='Markdown',
                reply_markup=keyboards.seeker_submenu(field, current_value)
            )

    def process_seeker_profession_sphere(self, message):
        """Обработка выбора сферы деятельности в настройках"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if utils.cancel_request(message.text):
            database.clear_user_state(user_id)
            self.bot.send_message(message.chat.id, "❌ Изменение отменено", reply_markup=keyboards.seeker_main_menu())
            return

        sphere = message.text.strip()

        # Если выбрано "Другое" или сфера не из списка (ручной ввод)
        if sphere == "Другое" or sphere not in PROFESSION_SPHERES:
            user_state['step'] = 'enter_new_value'
            database.set_user_state(user_id, user_state)

            self.bot.send_message(
                message.chat.id,
                "🎯 *Введите название вашей профессии:*",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        # Показываем профессии
        user_state['step'] = 'edit_seeker_profession_specific'
        database.set_user_state(user_id, user_state)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for prof in PROFESSION_SPHERES[sphere]:
            markup.add(types.KeyboardButton(prof))
        markup.add(types.KeyboardButton("Другое"))
        markup.add(types.KeyboardButton("⬅️ Назад"))

        self.bot.send_message(
            message.chat.id,
            f"🎯 *Выберите профессию в сфере {sphere}:*\n"
            "Или введите свое название, если его нет в списке.",
            parse_mode='Markdown',
            reply_markup=markup
        )

    def process_seeker_profession_specific(self, message):
        """Обработка выбора конкретной профессии в настройках"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if message.text == "⬅️ Назад":
            user_state['step'] = 'edit_seeker_profession_sphere'
            database.set_user_state(user_id, user_state)

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for sphere in PROFESSION_SPHERES.keys():
                markup.add(types.KeyboardButton(sphere))
            markup.add(types.KeyboardButton("Другое"))
            markup.add(types.KeyboardButton("❌ Отмена"))

            self.bot.send_message(message.chat.id, "📂 *Выберите сферу деятельности:*", parse_mode='Markdown',
                                  reply_markup=markup)
            return

        if utils.cancel_request(message.text):
            database.clear_user_state(user_id)
            self.bot.send_message(message.chat.id, "❌ Изменение отменено", reply_markup=keyboards.seeker_main_menu())
            return

        profession = message.text.strip()

        if profession == "Другое":
            user_state['step'] = 'enter_new_value'
            database.set_user_state(user_id, user_state)
            self.bot.send_message(
                message.chat.id,
                "✍️ *Введите название вашей профессии вручную:*",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        if utils.contains_profanity(profession):
            self.bot.send_message(message.chat.id, "❌ Название содержит недопустимые слова.")
            return

        # Сохраняем
        if database.update_seeker_profile(telegram_id=user_id, profession=profession):
            database.clear_user_state(user_id)
            self.bot.send_message(
                message.chat.id,
                f"✅ Профессия успешно обновлена!\n\nНовое значение: *{profession}*",
                parse_mode='Markdown',
                reply_markup=keyboards.seeker_main_menu()
            )
        else:
            self.bot.send_message(message.chat.id, "❌ Ошибка при обновлении.")

    def process_seeker_field_update(self, message):
        """Обработка ввода нового значения для поля соискателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            database.clear_user_state(user_id)
            self.bot.send_message(
                message.chat.id,
                "❌ Изменение отменено",
                parse_mode='Markdown',
                reply_markup=keyboards.seeker_main_menu()
            )
            return

        if not user_state or user_state.get('step') != 'enter_new_value':
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла!",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        new_value = message.text.strip()

        return self._save_seeker_field(message, user_id, user_state, new_value)

    def _save_seeker_field(self, message, user_id, user_state, new_value):
        field = user_state['field']
        field_display = user_state['field_display']

        # Валидация специфичных полей
        if field == 'phone':
            if not utils.is_valid_uzbek_phone(new_value):
                self.bot.send_message(
                    message.chat.id,
                    "❌ Неверный формат номера!\n\n" + utils.show_phone_format_example(),
                    parse_mode='Markdown',
                    reply_markup=keyboards.cancel_keyboard()
                )
                return
            new_value = utils.format_phone(new_value)
        elif field == 'email':
            if not utils.is_valid_email(new_value):
                self.bot.send_message(message.chat.id, "❌ Неверный формат email!\n\nПопробуйте еще раз:",
                                      reply_markup=keyboards.cancel_keyboard())
                return

        if not new_value or len(new_value) < 2:
            self.bot.send_message(
                message.chat.id,
                f"❌ Значение слишком короткое!\n\n"
                f"Введите новое значение для {field_display.lower()}:",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        if len(new_value) > 500:
            self.bot.send_message(
                message.chat.id,
                f"❌ Значение слишком длинное! Максимум 500 символов.\n\n"
                f"Введите новое значение для {field_display.lower()}:",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        if utils.contains_profanity(new_value):
            self.bot.send_message(message.chat.id, "❌ Значение содержит недопустимые слова.")
            return

        # Обновляем поле в базе данных
        success = database.update_seeker_profile(
            telegram_id=user_id,
            **{field: new_value}
        )

        if success:
            database.clear_user_state(user_id)
            self.bot.send_message(
                message.chat.id,
                f"✅ {field_display} успешно обновлено!\n\n"
                f"Новое значение: *{new_value}*",
                parse_mode='Markdown',
                reply_markup=keyboards.seeker_main_menu()
            )
        else:
            self.bot.send_message(
                message.chat.id,
                f"❌ Ошибка при обновлении {field_display}!\n\n"
                f"Попробуйте еще раз:",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )

    def handle_status_settings(self, message):
        """Меню настройки статуса"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data or 'full_name' not in user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала войдите как соискатель!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        status = user_data.get('status', 'active')
        status_text = "✅ Активно ищет работу" if status == 'active' else "⛔ Нашел работу"

        self.bot.send_message(
            message.chat.id,
            f"📊 *Статус поиска*\n\n"
            f"Текущий статус: *{status_text}*\n\n"
            f"Выберите новый статус:",
            parse_mode='Markdown',
            reply_markup=keyboards.seeker_status_menu()
        )

    def set_seeker_status(self, message, status_code):
        """Установка статуса соискателя"""
        user_id = message.from_user.id

        success = database.update_seeker_profile(
            telegram_id=user_id,
            status=status_code
        )

        status_text = "✅ Активно ищет работу" if status_code == 'active' else "⛔ Нашел работу"

        if success:
            self.bot.send_message(
                message.chat.id,
                f"✅ Статус успешно изменен!\n\n"
                f"Новый статус: *{status_text}*",
                parse_mode='Markdown',
                reply_markup=keyboards.settings_menu('seeker')
            )
        else:
            self.bot.send_message(message.chat.id, "❌ Ошибка обновления статуса")

    def handle_employer_action(self, message):
        """Обработка действий работодателя"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data or 'company_name' not in user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала войдите как работодатель!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        if message.text == '🗑️ Удалить компанию':
            self.handle_delete_account(message)
        elif message.text == '↩️ Назад в меню':
            self.bot.send_message(
                message.chat.id,
                "🏢 *Панель работодателя*",
                parse_mode='Markdown',
                reply_markup=keyboards.employer_main_menu()
            )
        else:
            self.bot.send_message(
                message.chat.id,
                "❌ Неизвестное действие",
                parse_mode='Markdown',
                reply_markup=keyboards.employer_main_menu()
            )

    def handle_employer_setting(self, message, field: str):
        """Обработка нажатия на кнопку настройки работодателя"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data or 'company_name' not in user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала войдите как работодатель!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        field_names = {
            'company_name': 'Название компании',
            'contact_person': 'Контактное лицо',
            'description': 'Описание компании',
            'business_activity': 'Род деятельности',
            'phone': 'Телефон',
            'email': 'Email',
            'city': 'Город'
        }

        field_display = field_names.get(field, field)
        current_value = user_data.get(field, 'Не указано')

        database.set_user_state(user_id, {
            'action': 'edit_employer_field',
            'field': field,
            'field_display': field_display,
            'current_value': current_value,
            'step': 'enter_new_value'
        })

        self.bot.send_message(
            message.chat.id,
            f"✏️ *{field_display}*\n\nВведите новое значение:",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )

    def process_employer_field_update(self, message):
        """Обработка ввода нового значения для поля работодателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if utils.cancel_request(message.text):
            database.clear_user_state(user_id)
            self.bot.send_message(
                message.chat.id,
                "❌ Изменение отменено",
                parse_mode='Markdown',
                reply_markup=keyboards.employer_main_menu()
            )
            return

        if not user_state or user_state.get('step') != 'enter_new_value' or user_state.get('action') != 'edit_employer_field':
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла!",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        field = user_state['field']
        field_display = user_state.get('field_display', 'Поле')
        new_value = message.text.strip()

        # Валидация специфичных полей
        if field == 'phone':
            if not utils.is_valid_uzbek_phone(new_value):
                self.bot.send_message(
                    message.chat.id,
                    "❌ Неверный формат номера!\n\n" + utils.show_phone_format_example(),
                    parse_mode='Markdown',
                    reply_markup=keyboards.cancel_keyboard()
                )
                return
            new_value = utils.format_phone(new_value)
        elif field == 'email':
            if not utils.is_valid_email(new_value):
                self.bot.send_message(message.chat.id, "❌ Неверный формат email!\n\nПопробуйте еще раз:",
                                      reply_markup=keyboards.cancel_keyboard())
                return

        if utils.contains_profanity(new_value):
            self.bot.send_message(message.chat.id, "❌ Значение содержит недопустимые слова.")
            return

        success = database.update_employer_profile(
            telegram_id=user_id,
            **{field: new_value}
        )

        if success:
            database.clear_user_state(user_id)
            self.bot.send_message(
                message.chat.id,
                f"✅ {field_display} успешно обновлено!",
                parse_mode='Markdown',
                reply_markup=keyboards.employer_main_menu()
            )
        else:
            self.bot.send_message(
                message.chat.id,
                f"❌ Ошибка при обновлении {field_display}!",
                parse_mode='Markdown'
            )

    def handle_delete_account(self, message):
        """Удаление аккаунта"""
        user_id = message.from_user.id
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
            account_type = "соискателя"
        else:
            # Работодатель
            role = 'employer'
            name = user_data['company_name']
            account_type = "компании"

        # Сохраняем состояние для подтверждения
        database.set_user_state(user_id, {
            'action': 'delete_account',
            'role': role,
            'name': name,
            'account_type': account_type
        })

        # Создаем клавиатуру подтверждения
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('✅ Да, удалить аккаунт', '❌ Нет, отменить')

        self.bot.send_message(
            message.chat.id,
            f"⚠️ *ВНИМАНИЕ!*\n\n"
            f"Вы собираетесь удалить аккаунт {account_type}!\n\n"
            f"*Профиль:* {name}\n"
            f"*Тип:* {'Соискатель' if role == 'seeker' else 'Работодатель'}\n\n"
            f"❗ *Это действие нельзя отменить!*\n"
            f"❗ *Все ваши данные будут удалены безвозвратно!*\n\n"
            f"Вы уверены, что хотите удалить аккаунт?",
            parse_mode='Markdown',
            reply_markup=markup
        )

    def confirm_delete_account(self, message):
        """Подтверждение удаления аккаунта"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if not user_state or user_state.get('action') != 'delete_account':
            self.bot.send_message(
                message.chat.id,
                "❌ Сессия истекла или действие отменено.",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        if message.text == '❌ Нет, отменить':
            database.clear_user_state(user_id)

            if user_state['role'] == 'seeker':
                self.bot.send_message(
                    message.chat.id,
                    "✅ Удаление отменено.",
                    parse_mode='Markdown',
                    reply_markup=keyboards.seeker_main_menu()
                )
            else:
                self.bot.send_message(
                    message.chat.id,
                    "✅ Удаление отменено.",
                    parse_mode='Markdown',
                    reply_markup=keyboards.employer_main_menu()
                )
            return

        elif message.text == '✅ Да, удалить аккаунт':
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
                    f"🗑️ *Аккаунт удален!*\n\n"
                    f"✅ Аккаунт {account_type} *{name}* успешно удален.\n\n"
                    f"Все ваши данные были удалены из системы.\n"
                    f"Для повторной регистрации нажмите /start",
                    parse_mode='Markdown',
                    reply_markup=keyboards.main_menu()
                )
            else:
                self.bot.send_message(
                    message.chat.id,
                    "❌ Ошибка при удалении аккаунта! Обратитесь в поддержку.",
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
