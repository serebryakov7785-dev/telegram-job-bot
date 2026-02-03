# handlers/employer.py
import database
import logging
import utils
import keyboards
from models import dict_to_employer
from telebot import types
from handlers.profile import PROFESSION_SPHERES, LANGUAGES_DICT, LEVELS

# Список регионов и городов для фильтрации
UZB_REGIONS = {
    "Ташкентская обл.": ["Ташкент", "Чирчик", "Ангрен", "Алмалык", "Бекабад", "Янгиюль", "Нурафшон", "Газалкент"],
    "Самаркандская обл.": ["Самарканд", "Каттакурган", "Ургут", "Акташ", "Булунгур", "Джамбай"],
    "Бухарская обл.": ["Бухара", "Каган", "Гиждуван", "Газли", "Галаасия"],
    "Ферганская обл.": ["Фергана", "Коканд", "Маргилан", "Кувасай", "Кува", "Риштан"],
    "Андижанская обл.": ["Андижан", "Асака", "Ханобад", "Шахрихан", "Карасу"],
    "Наманганская обл.": ["Наманган", "Чуст", "Касансай", "Пап", "Учкурган"],
    "Навоийская обл.": ["Навои", "Зарафшан", "Учкудук", "Нурата"],
    "Кашкадарьинская обл.": ["Карши", "Шахрисабз", "Гузар", "Камаши", "Мубарек"],
    "Сурхандарьинская обл.": ["Термез", "Денау", "Джаркурган", "Шерабад"],
    "Джизакская обл.": ["Джизак", "Гагарин", "Галляарал", "Даштабад"],
    "Сырдарьинская обл.": ["Гулистан", "Янгиер", "Ширин", "Сырдарья"],
    "Хорезмская обл.": ["Ургенч", "Хива", "Питнак", "Ханка"],
    "Респ. Каракалпакстан": ["Нукус", "Беруни", "Кунград", "Тахиаташ", "Турткуль"]
}


class EmployerHandlers:
    def __init__(self, bot):
        self.bot = bot

    def handle_create_vacancy(self, message):
        """Создание вакансии"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data or 'company_name' not in user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала зарегистрируйтесь или войдите как работодатель!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        employer = dict_to_employer(user_data)

        # Начинаем процесс создания вакансии
        database.set_user_state(user_id, {
            'step': 'vacancy_sphere',
            'vacancy_data': {
                'employer_id': user_data['id']
            }
        })

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for sphere in PROFESSION_SPHERES.keys():
            markup.add(types.KeyboardButton(sphere))
        markup.add(types.KeyboardButton("Другое"))
        markup.add(types.KeyboardButton("❌ Отмена"))

        self.bot.send_message(
            message.chat.id,
            f"➕ *Создание вакансии*\n\n"
            f"Компания: *{employer.company_name}*\n\n"
            "Выберите сферу деятельности:",
            parse_mode='Markdown',
            reply_markup=markup
        )

    def process_vacancy_sphere(self, message):
        """Обработка выбора сферы вакансии"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        text = message.text.strip()

        if text == "Другое":
            user_state['step'] = 'vacancy_title'
            database.set_user_state(user_id, user_state)
            self.bot.send_message(
                message.chat.id,
                "Введите название должности (например: *Менеджер по продажам*):",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        if text in PROFESSION_SPHERES:
            user_state['step'] = 'vacancy_profession'
            database.set_user_state(user_id, user_state)

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for prof in PROFESSION_SPHERES[text]:
                markup.add(types.KeyboardButton(prof))
            markup.add(types.KeyboardButton("Другое"))
            markup.add(types.KeyboardButton("⬅️ Назад"))
            markup.add(types.KeyboardButton("❌ Отмена"))

            self.bot.send_message(message.chat.id, f"Выберите должность в сфере {text}:", reply_markup=markup)
            return

        self.bot.send_message(message.chat.id, "❌ Выберите сферу из списка.")

    def process_vacancy_profession(self, message):
        """Обработка выбора профессии"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        text = message.text.strip()

        if text == "⬅️ Назад":
            self.handle_create_vacancy(message)
            return

        if text == "Другое":
            user_state['step'] = 'vacancy_title'
            database.set_user_state(user_id, user_state)
            self.bot.send_message(
                message.chat.id,
                "Введите название должности:",
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        user_state['vacancy_data']['title'] = text
        user_state['step'] = 'vacancy_description'
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            "📝 Введите описание вакансии (требования, обязанности):",
            reply_markup=keyboards.cancel_keyboard()
        )

    def process_vacancy_title(self, message):
        """Обработка названия вакансии"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        title = message.text.strip()
        if len(title) < 3:
            self.bot.send_message(message.chat.id, "❌ Слишком короткое название. Попробуйте еще раз:")
            return

        if utils.contains_profanity(title):
            self.bot.send_message(message.chat.id, "❌ Название содержит недопустимые слова. Пожалуйста, соблюдайте правила.")
            return

        user_state['vacancy_data']['title'] = title
        user_state['step'] = 'vacancy_description'
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            "📝 Введите описание вакансии (требования, обязанности):",
            reply_markup=keyboards.cancel_keyboard()
        )

    def process_vacancy_description(self, message):
        """Обработка описания вакансии"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        description = message.text.strip()
        if len(description) < 10:
            self.bot.send_message(message.chat.id, "❌ Описание слишком короткое. Расскажите подробнее:")
            return

        if utils.contains_profanity(description):
            self.bot.send_message(message.chat.id, "❌ Описание содержит недопустимые слова. Пожалуйста, соблюдайте правила.")
            return

        user_state['vacancy_data']['description'] = description

        # Инициализируем временный список языков и переходим к их выбору
        user_state['temp_languages'] = []
        self.show_vacancy_language_selection(message.chat.id, user_id, user_state)

    def show_vacancy_language_selection(self, chat_id, user_id, user_state):
        """Показ меню выбора языка для вакансии"""
        user_state['step'] = 'vacancy_language_selection'
        database.set_user_state(user_id, user_state)

        selected_langs = [lang['name'] for lang in user_state.get('temp_languages', [])]

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

        # Добавляем доступные языки, исключая уже выбранные
        for btn_text, lang_name in LANGUAGES_DICT.items():
            if lang_name not in selected_langs:
                markup.add(types.KeyboardButton(btn_text))

        markup.add(types.KeyboardButton("🌐 Другой"))

        msg_text = "🗣 *Какие языки требуются от кандидата?*"

        if selected_langs:
            markup.add(types.KeyboardButton("➡️ Далее"))
            langs_list = "\n".join([f"• {lang['name']} - {lang['level']}" for lang in user_state['temp_languages']])
            msg_text += f"\n\n✅ *Добавленные языки:*\n{langs_list}\n\nХотите добавить еще язык или нажмите *Далее*?"
        else:
            markup.add(types.KeyboardButton("Пропустить"))
            msg_text += "\n\nВыберите язык из списка или нажмите 'Другой'."

        markup.add(types.KeyboardButton("❌ Отмена"))

        self.bot.send_message(chat_id, msg_text, parse_mode='Markdown', reply_markup=markup)

    def process_vacancy_language_selection(self, message):
        """Обработка выбора языка для вакансии"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        text = message.text.strip()

        if text == "➡️ Далее":
            if user_state.get('temp_languages'):
                langs_str = ", ".join([f"{lang['name']} ({lang['level']})" for lang in user_state['temp_languages']])

                if user_state.get('is_editing_vacancy'):
                    user_state['edit_data']['languages'] = langs_str
                    self.ask_edit_salary(message.chat.id, user_id, user_state)
                else:
                    user_state['vacancy_data']['languages'] = langs_str
                    self.ask_vacancy_salary(message.chat.id, user_id, user_state)
            else:
                self.bot.send_message(message.chat.id, "❌ Выберите хотя бы один язык или нажмите 'Пропустить'")
            return

        if text == "Пропустить":
            langs_str = "Не имеет значения"
            if user_state.get('is_editing_vacancy'):
                user_state['edit_data']['languages'] = langs_str
                self.ask_edit_salary(message.chat.id, user_id, user_state)
            else:
                user_state['vacancy_data']['languages'] = langs_str
                self.ask_vacancy_salary(message.chat.id, user_id, user_state)
            return

        if text == "🌐 Другой":
            user_state['step'] = 'vacancy_language_custom_name'
            database.set_user_state(user_id, user_state)
            self.bot.send_message(
                message.chat.id,
                "✍️ *Введите название языка:*",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        lang_name = LANGUAGES_DICT.get(text)
        if lang_name:
            user_state['current_lang_editing'] = lang_name
            self.show_vacancy_language_level(message.chat.id, user_id, user_state)
            return

        self.bot.send_message(message.chat.id, "❌ Пожалуйста, используйте кнопки меню.")

    def process_vacancy_language_custom_name(self, message):
        """Обработка ввода названия другого языка"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        lang_name = message.text.strip()
        if len(lang_name) < 2:
            self.bot.send_message(message.chat.id, "❌ Слишком короткое название.")
            return

        # Проверка дубликатов
        selected_names = [lang['name'].lower() for lang in user_state.get('temp_languages', [])]
        if lang_name.lower() in selected_names:
            self.bot.send_message(message.chat.id, "❌ Этот язык уже добавлен.")
            self.show_vacancy_language_selection(message.chat.id, user_id, user_state)
            return

        user_state['current_lang_editing'] = lang_name
        self.show_vacancy_language_level(message.chat.id, user_id, user_state)

    def show_vacancy_language_level(self, chat_id, user_id, user_state):
        """Показ меню выбора уровня языка"""
        user_state['step'] = 'vacancy_language_level'
        database.set_user_state(user_id, user_state)

        lang_name = user_state.get('current_lang_editing', 'этого языка')

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for level in LEVELS:
            markup.add(types.KeyboardButton(level))
        markup.add(types.KeyboardButton("⬅️ Назад"))

        self.bot.send_message(
            chat_id,
            f"📊 Выберите требуемый уровень владения языком *{lang_name}*:",
            parse_mode='Markdown',
            reply_markup=markup
        )

    def ask_vacancy_salary(self, chat_id, user_id, user_state):
        """Переход к вопросу о зарплате"""
        user_state['step'] = 'vacancy_salary'
        if 'temp_languages' in user_state:
            del user_state['temp_languages']
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            chat_id,
            "💰 Укажите зарплату (например: *5 000 000 сум* или *Договорная*):",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )

    def process_vacancy_language_level(self, message):
        """Обработка выбора уровня языка"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        text = message.text.strip()

        if text == "⬅️ Назад":
            self.show_vacancy_language_selection(message.chat.id, user_id, user_state)
            return

        if text not in LEVELS:
            self.bot.send_message(message.chat.id, "❌ Выберите уровень из меню.")
            return

        lang_name = user_state.get('current_lang_editing')
        if not lang_name:
            self.show_vacancy_language_selection(message.chat.id, user_id, user_state)
            return

        if 'temp_languages' not in user_state:
            user_state['temp_languages'] = []

        user_state['temp_languages'].append({'name': lang_name, 'level': text})

        if 'current_lang_editing' in user_state:
            del user_state['current_lang_editing']

        self.show_vacancy_language_selection(message.chat.id, user_id, user_state)

    def process_vacancy_salary(self, message):
        """Обработка зарплаты"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        user_state['vacancy_data']['salary'] = message.text.strip()
        user_state['step'] = 'vacancy_type'
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            "⏱ Выберите тип занятости:",
            reply_markup=keyboards.job_type_menu()
        )

    def process_vacancy_type(self, message):
        """Обработка типа занятости и сохранение"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        job_type = message.text.strip()
        if job_type not in [
            'Полный день', 'Частичная занятость',
            'Удаленная работа', 'Стажировка'
        ]:
            self.bot.send_message(
                message.chat.id,
                "❌ Выберите вариант из меню:",
                reply_markup=keyboards.job_type_menu()
            )
            return

        user_state['vacancy_data']['job_type'] = job_type

        # Сохраняем вакансию
        if database.create_vacancy(user_state['vacancy_data']):
            self.bot.send_message(
                message.chat.id,
                "✅ *Вакансия успешно создана!*\n\n"
                "Теперь соискатели смогут её увидеть.",
                parse_mode='Markdown',
                reply_markup=keyboards.employer_main_menu()
            )
        else:
            self.bot.send_message(
                message.chat.id,
                "❌ Ошибка при создании вакансии.",
                reply_markup=keyboards.employer_main_menu()
            )

        database.clear_user_state(user_id)

    def handle_my_vacancies(self, message):
        """Мои вакансии"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data or 'company_name' not in user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала зарегистрируйтесь или войдите как работодатель!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        vacancies = database.get_employer_vacancies(user_data['id'])

        if not vacancies:
            self.bot.send_message(
                message.chat.id,
                "📋 *Мои вакансии*\n\n"
                "У вас пока нет активных вакансий.\n"
                "Создайте первую вакансию для привлечения сотрудников!",
                parse_mode='Markdown',
                reply_markup=keyboards.employer_main_menu()
            )
            return

        for vac in vacancies:
            self.bot.send_message(
                message.chat.id,
                f"💼 *{vac['title']}*\n\n"
                f"💰 Зарплата: {vac['salary']}\n"
                f"⏱ Тип: {vac['job_type']}\n"
                f"🗣 Языки: {vac.get('languages') or 'Не указаны'}\n"
                f"📝 Описание: {vac['description']}\n\n"
                f"� Создано: {vac['created_at']}",
                parse_mode='Markdown',
                reply_markup=keyboards.my_vacancy_actions(vac['id'])
            )

    def handle_find_candidates(self, message):
        """Поиск сотрудников"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data or 'company_name' not in user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала зарегистрируйтесь или войдите как работодатель!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        # Упрощенный поиск: показываем всех кандидатов
        self.show_candidates(message, city=None)

    def process_candidate_filter_choice(self, message):
        if message.text == "⬅️ Назад":
            self.bot.send_message(message.chat.id, "Главное меню", reply_markup=keyboards.employer_main_menu())
            return

        if message.text == "🏙 Выбрать город":
            # Показываем список регионов
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for region in UZB_REGIONS.keys():
                markup.add(types.KeyboardButton(region))
            markup.add("⬅️ Назад")

            msg = self.bot.send_message(message.chat.id, "Выберите область/регион:", reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.process_candidate_region_choice)
        else:
            # Все города
            self.show_candidates(message, city=None)

    def process_candidate_region_choice(self, message):
        if message.text == "⬅️ Назад":
            self.handle_find_candidates(message)
            return

        region = message.text
        if region in UZB_REGIONS:
            # Показываем города выбранного региона
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for city in UZB_REGIONS[region]:
                markup.add(types.KeyboardButton(city))
            markup.add("⬅️ Назад")

            msg = self.bot.send_message(message.chat.id, f"Выберите город/район в {region}:", reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.process_candidate_city_choice)
        else:
            self.bot.send_message(message.chat.id, "❌ Выберите регион из списка.")
            # Перезапускаем шаг, имитируя нажатие кнопки "Выбрать город"
            message.text = "🏙 Выбрать город"
            self.process_candidate_filter_choice(message)

    def process_candidate_city_choice(self, message):
        if message.text == "⬅️ Назад":
            # Возвращаемся к выбору региона
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for region in UZB_REGIONS.keys():
                markup.add(types.KeyboardButton(region))
            markup.add("⬅️ Назад")

            msg = self.bot.send_message(message.chat.id, "Выберите область/регион:", reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.process_candidate_region_choice)
            return

        city = message.text
        self.show_candidates(message, city)

    def show_candidates(self, message, city=None):
        # Получаем список активных соискателей с фильтром
        seekers = database.get_all_seekers(limit=20, city=city, status='active')

        if not seekers:
            self.bot.send_message(
                message.chat.id,
                "👥 *Поиск сотрудников*\n\n"
                "К сожалению, сейчас нет активных соискателей.",
                parse_mode='Markdown',
                reply_markup=keyboards.employer_main_menu()
            )
            return

        self.bot.send_message(
            message.chat.id,
            f"👥 *Найдено кандидатов: {len(seekers)}*\n\n"
            "Вот список активных соискателей:",
            parse_mode='Markdown',
            reply_markup=keyboards.employer_main_menu()
        )

        for seeker in seekers:
            try:
                age_text = f"{seeker.get('age')} лет" if seeker.get('age') else "Не указан"
                city_text = seeker.get('city', 'Не указан')
                card = (
                    f"👤 *{seeker['full_name']}*\n"
                    f"🏙️ Город: {city_text}\n"
                    f"📅 Возраст: {age_text}\n"
                    f"🎯 *Профессия:* {seeker.get('profession', 'Не указана')}\n"
                    f"🎓 Образование: {seeker.get('education', 'Не указано')}\n"
                    f"🗣 Языки: {seeker.get('languages') or 'Не указаны'}\n"
                    f"💼 Опыт: {seeker.get('experience', 'Нет опыта')}\n"
                    f"🎨 Навыки: {seeker.get('skills', 'Не указаны')}"
                )

                self.bot.send_message(
                    message.chat.id,
                    card,
                    parse_mode='Markdown',
                    # Добавляем кнопку "Пригласить"
                    reply_markup=keyboards.employer_invite_keyboard(seeker['telegram_id'])
                )
            except Exception as e:
                logging.error(f"❌ Ошибка при отправке карточки кандидата: {e}", exc_info=True)

    def handle_invitation_callback(self, call):
        """Обработка нажатия кнопки 'Пригласить'"""
        try:
            employer_telegram_id = call.from_user.id
            parts = call.data.split('_')
            seeker_telegram_id = int(parts[1])
            vacancy_id = int(parts[2]) if len(parts) > 2 else None

            # 1. Получаем данные работодателя
            employer_data = database.get_user_by_id(employer_telegram_id)
            if not employer_data or 'company_name' not in employer_data:
                self.bot.answer_callback_query(call.id, "❌ Ошибка: не найден профиль работодателя.")
                return

            # 2. Получаем данные соискателя
            seeker_data = database.get_user_by_id(seeker_telegram_id)
            if not seeker_data or 'full_name' not in seeker_data:
                self.bot.answer_callback_query(call.id, "❌ Ошибка: не найден профиль соискателя.")
                return

            # 3. Отправляем уведомление соискателю
            company_name = employer_data['company_name']
            seeker_name = seeker_data['full_name']

            # Получаем данные вакансии
            vacancy_title = "Не указана"
            vacancy_salary = "Не указана"
            vacancy_type = "Не указан"
            vacancy_desc = "Нет описания"
            vacancy_languages = "Не указаны"

            if vacancy_id:
                vac_data = database.execute_query(
                    "SELECT title, salary, job_type, description, languages FROM vacancies WHERE id = ?",
                    (vacancy_id,), fetchone=True
                )
                if vac_data:
                    vacancy_title = vac_data.get('title', 'Не указана')
                    vacancy_salary = vac_data.get('salary', 'Не указана')
                    vacancy_type = vac_data.get('job_type', 'Не указан')
                    vacancy_desc = vac_data.get('description', 'Нет описания')
                    vacancy_languages = vac_data.get('languages', 'Не указаны')

            invitation_text = (
                f"🎉 *Вас пригласили на собеседование!*\n\n"
                f"🏢 Компания: *{utils.escape_markdown(company_name)}*\n"
                f"💼 Вакансия: *{utils.escape_markdown(vacancy_title)}*\n"
                f"💰 Зарплата: {utils.escape_markdown(vacancy_salary)}\n"
                f"⏱ Тип: {utils.escape_markdown(vacancy_type)}\n"
                f"🗣 Языки: {utils.escape_markdown(vacancy_languages)}\n"
                f"📝 Описание: {utils.escape_markdown(vacancy_desc)}\n\n"
                f"Нажмите на кнопку ниже, чтобы написать сообщение работодателю."
            )

            # Попытка отправить сообщение
            try:
                self.bot.send_message(
                    seeker_telegram_id,
                    invitation_text,
                    parse_mode='Markdown',
                    reply_markup=keyboards.contact_employer_keyboard(employer_telegram_id)
                )
            except Exception as e:
                logging.error(
                    f"Не удалось отправить приглашение соискателю {seeker_telegram_id}: {e}",
                    exc_info=True
                )
                self.bot.answer_callback_query(
                    call.id,
                    "❌ Не удалось отправить приглашение. Возможно, соискатель заблокировал бота."
                )
                return

            # Если отправка успешна, выполняем остальные действия
            # Если приглашение по вакансии, обновляем статус отклика
            if vacancy_id:
                database.execute_query(
                    "UPDATE applications SET status = 'accepted' "
                    "WHERE vacancy_id = ? AND seeker_id = ?",
                    (vacancy_id, seeker_data['id']),
                    commit=True
                )

            # 4. Отправляем подтверждение работодателю
            self.bot.answer_callback_query(call.id, f"✅ Приглашение для {seeker_name} отправлено!")

            # Обновляем сообщение, добавляя статус
            new_text = call.message.text + "\n\n*✅ Приглашение отправлено!*"
            self.bot.edit_message_text(
                text=new_text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode='Markdown',
                reply_markup=None
            )
        except Exception as e:
            logging.error(f"❌ Ошибка в handle_invitation_callback: {e}", exc_info=True)
            self.bot.answer_callback_query(call.id, "❌ Произошла системная ошибка.")

    def handle_my_vacancy_actions(self, call):
        """Обработка кнопок 'Изменить', 'Удалить', 'Отклики'"""
        try:
            action, _, vacancy_id_str = call.data.partition('_vac_')
            vacancy_id = int(vacancy_id_str)

            if action == 'edit':
                self.handle_edit_vacancy(call, vacancy_id)
            elif action == 'delete':
                self.handle_delete_vacancy(call, vacancy_id)
            elif action == 'responses':
                self.handle_vacancy_responses(call, vacancy_id)
        except (ValueError) as e:
            logging.error(
                f"❌ Ошибка разбора callback_data в handle_my_vacancy_actions: {e}",
                exc_info=True
            )
            self.bot.answer_callback_query(
                call.id,
                "❌ Ошибка обработки команды."
            )

    def handle_edit_vacancy(self, call, vacancy_id):
        """Начало редактирования вакансии"""
        self.bot.answer_callback_query(call.id)
        user_id = call.from_user.id

        # Получаем текущие данные вакансии через список вакансий работодателя
        user_data = database.get_user_by_id(user_id)
        vacancies = database.get_employer_vacancies(user_data['id'])
        target_vac = next((v for v in vacancies if v['id'] == vacancy_id), None)

        if not target_vac:
            self.bot.send_message(call.message.chat.id, "❌ Вакансия не найдена.")
            return

        # Сохраняем состояние
        database.set_user_state(user_id, {
            'step': 'edit_vacancy_title',
            'vacancy_id': vacancy_id,
            'current_vac': target_vac,
            'edit_data': {}
        })

        self.bot.send_message(
            call.message.chat.id,
            f"✏️ *Редактирование вакансии*\n\n"
            f"Текущее название: *{target_vac['title']}*\n\n"
            f"Введите новое название (или отправьте точку . чтобы оставить текущее):",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )

    def process_edit_title(self, message):
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        val = message.text.strip()
        if val != '.':
            if len(val) < 3:
                self.bot.send_message(message.chat.id, "❌ Слишком короткое название.")
                return

            if utils.contains_profanity(val):
                self.bot.send_message(message.chat.id, "❌ Название содержит недопустимые слова.")
                return

            user_state['edit_data']['title'] = val

        user_state['step'] = 'edit_vacancy_desc'
        database.set_user_state(user_id, user_state)

        current_desc = user_state['current_vac']['description']
        self.bot.send_message(
            message.chat.id,
            f"📝 Текущее описание: {current_desc}\n\n"
            "Введите новое описание (или . чтобы оставить):",
            reply_markup=keyboards.cancel_keyboard()
        )

    def process_edit_desc(self, message):
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        val = message.text.strip()
        if val != '.':
            if len(val) < 10:
                self.bot.send_message(message.chat.id, "❌ Описание слишком короткое.")
                return

            if utils.contains_profanity(val):
                self.bot.send_message(message.chat.id, "❌ Описание содержит недопустимые слова.")
                return

            user_state['edit_data']['description'] = val

        # Переход к редактированию языков
        user_state['step'] = 'edit_vacancy_languages_prompt'
        database.set_user_state(user_id, user_state)

        current_langs = user_state['current_vac'].get('languages', 'Не указаны')
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(types.KeyboardButton("✏️ Изменить"), types.KeyboardButton("➡️ Оставить текущие"))
        markup.add(types.KeyboardButton("❌ Отмена"))

        self.bot.send_message(
            message.chat.id,
            f"🗣 Текущие требования к языкам: {current_langs}\n\n"
            "Хотите изменить?",
            reply_markup=markup
        )

    def process_edit_languages_prompt(self, message):
        """Обработка выбора: менять языки или нет"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        text = message.text.strip()

        if text == "➡️ Оставить текущие" or text == '.':
            self.ask_edit_salary(message.chat.id, user_id, user_state)
            return

        if text == "✏️ Изменить":
            user_state['temp_languages'] = []
            user_state['is_editing_vacancy'] = True
            self.show_vacancy_language_selection(message.chat.id, user_id, user_state)
            return

        self.bot.send_message(message.chat.id, "❌ Выберите действие из меню.")

    def ask_edit_salary(self, chat_id, user_id, user_state):
        """Переход к редактированию зарплаты"""
        user_state['step'] = 'edit_vacancy_salary'
        # Очистка временных флагов
        if 'is_editing_vacancy' in user_state:
            del user_state['is_editing_vacancy']
        if 'temp_languages' in user_state:
            del user_state['temp_languages']

        database.set_user_state(user_id, user_state)

        current_salary = user_state['current_vac']['salary']
        self.bot.send_message(
            chat_id,
            f"💰 Текущая зарплата: {current_salary}\n\n"
            "Введите новую зарплату (или . чтобы оставить):",
            reply_markup=keyboards.cancel_keyboard()
        )

    def process_edit_salary(self, message):
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        val = message.text.strip()
        if val != '.':
            user_state['edit_data']['salary'] = val

        user_state['step'] = 'edit_vacancy_type'
        database.set_user_state(user_id, user_state)

        current_type = user_state['current_vac']['job_type']
        self.bot.send_message(
            message.chat.id,
            f"⏱ Текущий тип занятости: {current_type}\n\n"
            "Выберите новый тип (или . чтобы оставить):",
            reply_markup=keyboards.job_type_menu()
        )

    def process_edit_type(self, message):
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        val = message.text.strip()
        if val != '.':
            if val not in ['Полный день', 'Частичная занятость', 'Удаленная работа', 'Стажировка']:
                self.bot.send_message(
                    message.chat.id,
                    "❌ Выберите вариант из меню или отправьте .",
                    reply_markup=keyboards.job_type_menu()
                )
                return
            user_state['edit_data']['job_type'] = val

        # Обновляем данные в БД
        vac_id = user_state['vacancy_id']
        edit_data = user_state['edit_data']

        if edit_data and database.update_vacancy(vac_id, **edit_data):
            self.bot.send_message(
                message.chat.id,
                "✅ Вакансия успешно обновлена!",
                reply_markup=keyboards.employer_main_menu()
            )
        else:
            self.bot.send_message(
                message.chat.id,
                "ℹ️ Данные не были изменены.",
                reply_markup=keyboards.employer_main_menu()
            )

        database.clear_user_state(user_id)

    def handle_delete_vacancy(self, call, vacancy_id):
        """Запрос подтверждения удаления"""
        self.bot.edit_message_text(
            text=f"❓ *Точно удалить эту вакансию?*\n\n{call.message.text}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode='Markdown',
            reply_markup=keyboards.delete_confirmation_keyboard(vacancy_id)
        )

    def handle_confirm_delete(self, call):
        """Подтверждение удаления"""
        vacancy_id = int(call.data.split('_')[2])

        database.delete_vacancy(vacancy_id)

        self.bot.answer_callback_query(call.id, "✅ Вакансия удалена")
        self.bot.delete_message(call.message.chat.id, call.message.message_id)
        self.bot.send_message(
            call.message.chat.id,
            "🗑️ Вакансия успешно удалена.",
            reply_markup=keyboards.employer_main_menu()
        )

    def handle_vacancy_responses(self, call, vacancy_id):
        """Показать отклики на вакансию"""
        self.bot.answer_callback_query(call.id)

        # Получаем данные откликнувшихся соискателей
        query = """
            SELECT js.full_name, js.age, js.city, js.profession, js.education, js.experience, js.skills, js.languages,
                   js.phone,
                   js.email, js.telegram_id
            FROM applications a
            JOIN job_seekers js ON a.seeker_id = js.id
            WHERE a.vacancy_id = ? AND js.status = 'active'
        """
        applicants = database.execute_query(query, (vacancy_id,), fetchall=True)

        if not applicants:
            self.bot.send_message(call.message.chat.id,
                                  "📭 На эту вакансию пока нет откликов.")
            return

        self.bot.send_message(call.message.chat.id, f"📋 *Отклики на вакансию ({len(applicants)}):*", parse_mode='Markdown')

        for app in applicants:
            try:
                # app - это словарь (Row), используем ключи
                age_val = app.get('age')
                # Проверяем, что возраст есть и он больше 0
                age_text = f"({age_val} лет)" if age_val and age_val > 0 else "(возраст не указан)"
                city_text = app.get('city', 'Не указан')

                txt = (
                    f"👤 *{utils.escape_markdown(str(app.get('full_name', '')))}* "
                    f"{age_text}\n"
                    f"🏙️ Город: {utils.escape_markdown(city_text)}\n"
                    f"🎯 {utils.escape_markdown(str(app.get('profession', '')))}\n"
                    f"🎓 {utils.escape_markdown(str(app.get('education', '')))}\n"
                    f"🗣 Языки: {utils.escape_markdown(str(app.get('languages') or 'Не указаны'))}\n"
                    f"💼 {utils.escape_markdown(str(app.get('experience', '')))}\n"
                    f"🎨 {utils.escape_markdown(str(app.get('skills', '')))}"
                )

                self.bot.send_message(
                    call.message.chat.id,
                    txt,
                    parse_mode='Markdown',
                    reply_markup=keyboards.employer_invite_keyboard(
                        app.get('telegram_id'),
                        vacancy_id
                    )
                )
            except Exception as e:
                logging.error(
                    f"❌ Ошибка при отправке карточки отклика для вакансии {vacancy_id}: "
                    f"{e}",
                    exc_info=True
                )
                self.bot.send_message(
                    call.message.chat.id,
                    "⚠️ Не удалось загрузить карточку одного из кандидатов из-за ошибки."
                )

    def handle_employer_chats(self, message):
        """Меню чатов работодателя (список соискателей с которыми есть связь)"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data or 'company_name' not in user_data:
            self.bot.send_message(message.chat.id, "❌ Ошибка авторизации.")
            return

        # Получаем список соискателей, которым отправлено приглашение (status='accepted')
        query = """
            SELECT js.full_name, v.title, js.telegram_id
            FROM applications a
            JOIN vacancies v ON a.vacancy_id = v.id
            JOIN job_seekers js ON a.seeker_id = js.id
            WHERE v.employer_id = ? AND a.status = 'accepted'
        """
        chats = database.execute_query(query, (user_data['id'],), fetchall=True)

        if not chats:
            self.bot.send_message(message.chat.id, "📭 У вас пока нет активных диалогов с соискателями.")
            return

        self.bot.send_message(message.chat.id, f"💬 *Ваши диалоги с соискателями ({len(chats)}):*", parse_mode='Markdown')

        for chat in chats:
            try:
                text = (
                    f"👤 Кандидат: *{utils.escape_markdown(chat['full_name'])}*\n"
                    f"💼 Вакансия: *{utils.escape_markdown(chat['title'])}*"
                )
                self.bot.send_message(
                    message.chat.id,
                    text,
                    parse_mode='Markdown',
                    reply_markup=keyboards.contact_seeker_keyboard(chat['telegram_id'])
                )
            except Exception as e:
                logging.error(f"❌ Ошибка при отправке чата работодателя: {e}", exc_info=True)
