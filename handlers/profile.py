# handlers/profile.py
import database
import keyboards
import utils
from telebot import types

PROFESSION_SPHERES = {
    "IT и Интернет": ["Backend разработчик", "Frontend разработчик", "Fullstack разработчик", "QA инженер", "Дизайнер",
                      "Product Manager"],
    "Продажи": ["Менеджер по продажам", "Продавец-консультант", "Торговый представитель", "Кассир", "Супервайзер"],
    "Медицина и Фармация": ["Врач", "Медсестра/Медбрат", "Фармацевт", "Лаборант", "Медицинский представитель"],
    "Образование и Наука": ["Учитель", "Преподаватель", "Воспитатель", "Репетитор"],
    "Строительство": ["Инженер", "Архитектор", "Прораб", "Разнорабочий", "Электрик", "Сварщик"],
    "Транспорт и Логистика": ["Водитель", "Логист", "Экспедитор", "Автомеханик", "Курьер"],
    "Финансы": ["Бухгалтер", "Экономист", "Финансовый аналитик", "Аудитор"],
    "Сфера услуг": ["Официант", "Повар", "Парикмахер", "Администратор", "Охранник"],
    "Административный персонал": ["Секретарь", "Офис-менеджер", "Ассистент", "Оператор ПК"]
}

LANGUAGES_DICT = {
    "🇺🇿 Узбекский": "Узбекский",
    "🇷🇺 Русский": "Русский",
    "🇬🇧 Английский": "Английский"
}
LEVELS = ["Базовый", "Практический", "Свободный", "В совершенстве"]


class ProfileHandlers:
    def __init__(self, bot):
        self.bot = bot

    def start_profile_setup(self, message, user_data):
        """Начало заполнения профиля после регистрации"""
        user_id = message.from_user.id

        # Определяем роль пользователя
        role = 'seeker' if 'full_name' in user_data else 'employer'

        # Устанавливаем состояние для заполнения профиля
        database.set_user_state(user_id, {
            'step': 'education',
            'role': role,
            'profile_data': {}
        })

        if role == 'seeker':  # Соискатель
            self.bot.send_message(
                message.chat.id,
                "🎉 *Регистрация завершена!*\n\n"
                "Теперь заполните ваш профиль для лучшего поиска работы.\n\n"
                " *Введите ваше образование:*\n"
                "Пример: *Высшее техническое, Среднее специальное, Бакалавр*\n"
                "Или напишите 'Пропустить'",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
        else:  # Работодатель - СРАЗУ В МЕНЮ, без доп вопросов
            database.clear_user_state(user_id)
            self.bot.send_message(
                message.chat.id,
                f"✅ *Регистрация компании завершена!*\n\n"
                f"🏢 Компания: *{user_data.get('company_name', '')}*\n"
                f"👤 Контакт: *{user_data.get('contact_person', '')}*\n"
                f"📞 Телефон: {user_data.get('phone', '')}\n"
                f"📧 Email: {user_data.get('email', '')}\n\n"
                f"Используйте меню для поиска сотрудников:",
                parse_mode='Markdown',
                reply_markup=keyboards.employer_main_menu()
            )

    def process_education(self, message):
        """Обработка образования"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return

        if not user_state or user_state.get('step') != 'education':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        if message.text.strip().lower() == 'пропустить':
            education = 'Не указано'
        else:
            education = message.text.strip()
            # Проверка ввода
            if len(education) < 2:
                self.bot.send_message(
                    message.chat.id,
                    "❌ Слишком короткое описание!\n"
                    "Введите образование/требования:",
                    reply_markup=keyboards.cancel_keyboard()
                )
                return

            if utils.contains_profanity(education):
                self.bot.send_message(message.chat.id, "❌ Текст содержит недопустимые слова.")
                return

        user_state['profile_data']['education'] = education

        if user_state['role'] == 'seeker':
            user_state['step'] = 'profession_sphere'
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
        else:
            # Работодателю не задаем вопросы о требованиях
            self.save_profile_data(user_id, user_state)
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=True)

    def process_profession_sphere(self, message):
        """Обработка выбора сферы деятельности"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return

        if not user_state or user_state.get('step') != 'profession_sphere':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        sphere = message.text.strip()

        # Если выбрано "Другое" или сфера не из списка (ручной ввод), просим ввести профессию вручную
        if sphere == "Другое" or sphere not in PROFESSION_SPHERES:
            user_state['step'] = 'profession_specific'
            database.set_user_state(user_id, user_state)

            self.bot.send_message(
                message.chat.id,
                "🎯 *Введите название вашей профессии:*",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        # Если сфера выбрана из списка, показываем профессии
        user_state['step'] = 'profession_specific'
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

    def process_profession_specific(self, message):
        """Обработка выбора конкретной профессии"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        # Обработка кнопки Назад
        if message.text == "⬅️ Назад":
            user_state['step'] = 'profession_sphere'
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

        if utils.cancel_request(message.text):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return

        if not user_state or user_state.get('step') != 'profession_specific':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        profession = message.text.strip()

        if profession == "Другое":
            self.bot.send_message(
                message.chat.id,
                "✍️ *Введите название вашей профессии вручную:*",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        # Проверка ввода
        if len(profession) < 2:
            self.bot.send_message(
                message.chat.id,
                "❌ Слишком короткое название!\n"
                "Введите профессию/сферу деятельности:",
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        if utils.contains_profanity(profession):
            self.bot.send_message(message.chat.id, "❌ Название содержит недопустимые слова.")
            return

        user_state['profile_data']['profession'] = profession

        if user_state['role'] == 'seeker':
            user_state['temp_languages'] = []
            self.show_language_selection(message.chat.id, user_id, user_state)
        else:
            # Работодателю не задаем вопросы о требованиях
            self.save_profile_data(user_id, user_state)
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=True)

    def show_language_selection(self, chat_id, user_id, user_state):
        """Показ меню выбора языка"""
        user_state['step'] = 'language_selection'
        database.set_user_state(user_id, user_state)

        selected_langs = [lang['name'] for lang in user_state.get('temp_languages', [])]

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

        # Add available languages excluding selected ones
        for btn_text, lang_name in LANGUAGES_DICT.items():
            if lang_name not in selected_langs:
                markup.add(types.KeyboardButton(btn_text))

        markup.add(types.KeyboardButton("🌐 Другой"))

        msg_text = "🗣 *Какими языками вы владеете?*"

        if selected_langs:
            markup.add(types.KeyboardButton("➡️ Далее"))
            langs_list = "\n".join([f"• {lang['name']} - {lang['level']}" for lang in user_state['temp_languages']])
            msg_text += (
                f"\n\n✅ *Добавленные языки:*\n{langs_list}\n\n"
                f"Хотите добавить еще язык или нажмите кнопку *Далее* для продолжения?"
            )
        else:
            markup.add(types.KeyboardButton("Пропустить"))
            msg_text += "\n\nВыберите язык из списка или нажмите 'Другой'."

        if user_state.get('source') == 'settings':
            markup.add(types.KeyboardButton("❌ Отмена"))

        self.bot.send_message(chat_id, msg_text, parse_mode='Markdown', reply_markup=markup)

    def process_language_selection(self, message):
        """Обработка выбора языка"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        text = message.text.strip()

        if utils.cancel_request(message.text):
            if user_state.get('source') == 'settings':
                database.clear_user_state(user_id)
                self.bot.send_message(message.chat.id, "❌ Изменение отменено", reply_markup=keyboards.seeker_main_menu())
                return

            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return

        if text == "➡️ Далее":
            if user_state.get('temp_languages'):
                # Save and move on
                langs_str = ", ".join([f"{lang['name']} ({lang['level']})"
                                       for lang in user_state['temp_languages']])
                if user_state.get('source') == 'settings':
                    database.update_seeker_profile(telegram_id=user_id, languages=langs_str)
                    database.clear_user_state(user_id)
                    self.bot.send_message(message.chat.id, f"✅ Языки успешно обновлены!\n\nНовое значение: *{langs_str}*",
                                          parse_mode='Markdown', reply_markup=keyboards.seeker_main_menu())
                    return

                user_state['profile_data']['languages'] = langs_str
                self._ask_experience(message.chat.id, user_id, user_state)
            else:
                self.bot.send_message(message.chat.id, "❌ Выберите хотя бы один язык или нажмите 'Пропустить'")
            return

        if text == "Пропустить":
            return self._handle_language_skip(message, user_id, user_state)

        if text == "🌐 Другой":
            user_state['step'] = 'language_custom_name'
            database.set_user_state(user_id, user_state)
            self.bot.send_message(
                message.chat.id,
                "✍️ *Введите название языка:*",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        # Check standard languages
        lang_name = LANGUAGES_DICT.get(text)
        if lang_name:
            user_state['current_lang_editing'] = lang_name
            self.show_level_selection(message.chat.id, user_id, user_state)
            return

        self.bot.send_message(message.chat.id, "❌ Пожалуйста, используйте кнопки меню.")

    def _handle_language_skip(self, message, user_id, user_state):
        if not user_state.get('temp_languages'):
            if user_state.get('source') == 'settings':
                database.update_seeker_profile(telegram_id=user_id, languages="Не указаны")
                database.clear_user_state(user_id)
                self.bot.send_message(message.chat.id, "✅ Список языков очищен.",
                                      reply_markup=keyboards.seeker_main_menu())
                return

            user_state['profile_data']['languages'] = "Не указаны"
            self._ask_experience(message.chat.id, user_id, user_state)
        else:
            # Should not happen if logic is correct (button changes to Next)
            self.process_language_selection(message)  # Retry

    def _ask_experience(self, chat_id, user_id, user_state):
        user_state['step'] = 'experience'
        if 'temp_languages' in user_state:
            del user_state['temp_languages']
        database.set_user_state(user_id, user_state)
        self.bot.send_message(
            chat_id,
            "💼 *Введите ваш опыт работы:*\n"
            "Пример: *3 года в IT, 5 лет в продажах, Нет опыта*\n"
            "Или напишите 'Пропустить'",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )

    def process_language_custom_name(self, message):
        """Обработка ввода названия другого языка"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if utils.cancel_request(message.text):
            if user_state.get('source') == 'settings':
                database.clear_user_state(user_id)
                self.bot.send_message(message.chat.id, "❌ Изменение отменено", reply_markup=keyboards.seeker_main_menu())
                return

            self.show_language_selection(message.chat.id, user_id, user_state)
            return

        lang_name = message.text.strip()
        if len(lang_name) < 2:
            self.bot.send_message(message.chat.id, "❌ Слишком короткое название.")
            return

        # Check duplicates
        selected_names = [lang['name'].lower() for lang in user_state.get('temp_languages', [])]
        if lang_name.lower() in selected_names:
            self.bot.send_message(message.chat.id, "❌ Этот язык уже добавлен.")
            self.show_language_selection(message.chat.id, user_id, user_state)
            return

        user_state['current_lang_editing'] = lang_name
        self.show_level_selection(message.chat.id, user_id, user_state)

    def show_level_selection(self, chat_id, user_id, user_state):
        """Показ меню выбора уровня"""
        user_state['step'] = 'language_level'
        database.set_user_state(user_id, user_state)

        lang_name = user_state.get('current_lang_editing', 'этого языка')

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for level in LEVELS:
            markup.add(types.KeyboardButton(level))
        markup.add(types.KeyboardButton("⬅️ Назад"))

        self.bot.send_message(
            chat_id,
            f"📊 Выберите уровень владения языком *{lang_name}*:",
            parse_mode='Markdown',
            reply_markup=markup
        )

    def process_language_level(self, message):
        """Обработка выбора уровня"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        text = message.text.strip()

        if text == "⬅️ Назад":
            self.show_language_selection(message.chat.id, user_id, user_state)
            return

        if text not in LEVELS:
            self.bot.send_message(message.chat.id, "❌ Выберите уровень из меню.")
            return

        lang_name = user_state.get('current_lang_editing')
        if not lang_name:
            self.show_language_selection(message.chat.id, user_id, user_state)
            return

        # Add to list
        if 'temp_languages' not in user_state:
            user_state['temp_languages'] = []

        user_state['temp_languages'].append({'name': lang_name, 'level': text})

        # Clear current editing
        if 'current_lang_editing' in user_state:
            del user_state['current_lang_editing']

        # Back to selection
        self.show_language_selection(message.chat.id, user_id, user_state)

    def process_experience(self, message):
        """Обработка опыта работы"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if utils.cancel_request(message.text):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return

        if not user_state or user_state.get('step') != 'experience':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        if message.text.strip().lower() == 'пропустить':
            experience = 'Нет опыта'
        else:
            experience = message.text.strip()
            if len(experience) < 2:
                self.bot.send_message(
                    message.chat.id,
                    "❌ Слишком короткое описание!\n"
                    "Введите опыт работы/требования:",
                    reply_markup=keyboards.cancel_keyboard()
                )
                return

            if utils.contains_profanity(experience):
                self.bot.send_message(message.chat.id, "❌ Текст содержит недопустимые слова.")
                return

        user_state['profile_data']['experience'] = experience
        user_state['step'] = 'skills'
        database.set_user_state(user_id, user_state)

        if user_state['role'] == 'seeker':
            self.bot.send_message(
                message.chat.id,
                "🎨 *Введите ваши навыки:*\n"
                "Пример: *Python, Работа с возражениями, Обучаемость*\n"
                "Или напишите 'Пропустить'",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
        else:
            # Работодателю не задаем вопросы о требованиях
            self.save_profile_data(user_id, user_state)
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=True)

    def process_skills(self, message):
        """Обработка навыков/хобби"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if utils.cancel_request(message.text):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return

        if not user_state or user_state.get('step') != 'skills':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        if message.text.strip().lower() == 'пропустить':
            skills = 'Не указаны'
        else:
            skills = message.text.strip()
            if len(skills) < 2:
                self.bot.send_message(
                    message.chat.id,
                    "❌ Слишком короткое описание!\n"
                    "Введите навыки:",
                    reply_markup=keyboards.cancel_keyboard()
                )
                return

            if utils.contains_profanity(skills):
                self.bot.send_message(message.chat.id, "❌ Текст содержит недопустимые слова.")
                return

        user_state['profile_data']['skills'] = skills

        # Сохраняем данные профиля в базу
        self.save_profile_data(user_id, user_state)
        self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=True)

    def save_profile_data(self, user_id, user_state):
        """Сохранение данных профиля в базу"""
        profile_data = user_state['profile_data']

        if user_state['role'] == 'seeker':
            # Обновляем профиль соискателя
            success = database.update_seeker_profile(
                telegram_id=user_id,
                profession=profile_data.get('profession', 'Не указана'),
                education=profile_data.get('education', 'Не указано'),
                experience=profile_data.get('experience', 'Нет опыта'),
                skills=profile_data.get('skills', 'Не указаны'),
                languages=profile_data.get('languages', 'Не указаны')
            )

            if success:
                print(f"✅ Профиль соискателя {user_id} обновлен")
            else:
                print(f"⚠️ Не удалось обновить профиль соискателя {user_id}")

        else:
            # Для работодателя сохраняем в существующее описание
            current_user = database.get_user_by_id(user_id)
            if current_user and 'company_name' in current_user:
                current_description = current_user.get('description', '')

                # Формируем новое описание с профилем
                new_description = f"{current_description}\n\n"
                new_description += "*Дополнительная информация:*\n"
                new_description += f"• Сфера деятельности: {profile_data.get('profession', 'Не указана')}\n"
                new_description += f"• Требования к образованию: {profile_data.get('education', 'Не указано')}\n"
                new_description += f"• Требования к опыту: {profile_data.get('experience', 'Не указано')}\n"
                new_description += f"• Дополнительные пожелания: {profile_data.get('skills', 'Не указано')}"

                success = database.update_employer_profile(
                    telegram_id=user_id,
                    description=new_description
                )

                if success:
                    print(f"✅ Профиль работодателя {user_id} обновлен")
                else:
                    print(f"⚠️ Не удалось обновить профиль работодателя {user_id}")

    def finish_profile_setup(self, chat_id, user_id, user_state, show_summary=False):
        """Завершение заполнения профиля"""
        database.clear_user_state(user_id)

        if show_summary:
            profile_data = user_state['profile_data']

            if user_state['role'] == 'seeker':
                summary = (
                    f"✅ *Профиль успешно заполнен!*\n\n"
                    f"📋 *Ваш профиль:*\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"🎯 *Профессия:* {profile_data.get('profession', 'Не указана')}\n"
                    f"🎓 *Образование:* {profile_data.get('education', 'Не указано')}\n"
                    f"🗣 *Языки:* {profile_data.get('languages', 'Не указаны')}\n"
                    f"💼 *Опыт работы:* {profile_data.get('experience', 'Нет опыта')}\n"
                    f"🎨 *Навыки:* {profile_data.get('skills', 'Не указаны')}\n\n"
                    f"Теперь работодатели смогут лучше вас найти!"
                )
                keyboard = keyboards.seeker_main_menu()
            else:
                summary = (
                    f"✅ *Профиль компании успешно заполнен!*\n\n"
                    f"📋 *Профиль компании:*\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"🏢 *Сфера деятельности:* {profile_data.get('profession', 'Не указана')}\n"
                    f"📊 *Требования к образованию:* {profile_data.get('education', 'Не указано')}\n"
                    f"👔 *Требования к опыту:* {profile_data.get('experience', 'Не указано')}\n"
                    f"🌟 *Дополнительные пожелания:* {profile_data.get('skills', 'Не указано')}\n\n"
                    f"Теперь соискатели смогут лучше вас найти!"
                )
                keyboard = keyboards.employer_main_menu()

            self.bot.send_message(
                chat_id,
                summary,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        else:
            # Если пользователь отменил заполнение
            if user_state['role'] == 'seeker':
                self.bot.send_message(
                    chat_id,
                    "✅ *Вы можете заполнить профиль позже в настройках.*\n\n"
                    "Используйте меню для поиска работы:",
                    parse_mode='Markdown',
                    reply_markup=keyboards.seeker_main_menu()
                )
            else:
                self.bot.send_message(
                    chat_id,
                    "✅ *Вы можете заполнить профиль компании позже в настройках.*\n\n"
                    "Используйте меню для поиска сотрудников:",
                    parse_mode='Markdown',
                    reply_markup=keyboards.employer_main_menu()
                )

    def handle_complete_profile(self, message):
        """Ручной запуск заполнения профиля из меню"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала зарегистрируйтесь или войдите в аккаунт!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        # Проверяем, есть ли уже профиль
        role = user_data.get('role')

        if role == 'seeker':
            # Проверяем, заполнен ли уже профиль
            if user_data.get('profession') != 'Не указана' and user_data.get('skills') != 'Не указаны':
                self.bot.send_message(
                    message.chat.id,
                    "ℹ️ *Ваш профиль уже заполнен.*\n\n"
                    "Используйте меню для поиска работы.",
                    parse_mode='Markdown',
                    reply_markup=keyboards.seeker_main_menu()
                )
                return

            # Начинаем заполнение профиля
            self.start_profile_setup(message, user_data)

        else:  # employer
            # Работодателю больше не предлагаем заполнять профиль
            self.bot.send_message(
                message.chat.id,
                "ℹ️ *Профиль компании не требует дополнительного заполнения.*\n\n"
                "Используйте меню для поиска сотрудников.",
                parse_mode='Markdown',
                reply_markup=keyboards.employer_main_menu()
            )
