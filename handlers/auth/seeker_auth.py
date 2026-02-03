import database
import keyboards
import utils
from telebot import types
import logging

UZ_REGIONS = {
    "Ташкентская обл.": ["Ташкент", "Нурафшон", "Алмалык", "Ангрен", "Ахангаран", "Бекабад", "Бука", "Газалкент",
                         "Келес", "Паркент", "Пскент", "Тойтепа", "Чиназ", "Чирчик", "Янгиабад", "Янгиюль"],
    "Андижанская обл.": ["Андижан", "Асака", "Карасу", "Кургантепа", "Мархамат", "Пайтуг", "Пахтаабад", "Ханабад",
                         "Ходжаабад", "Шахрихан"],
    "Бухарская обл.": ["Бухара", "Алат", "Вабкент", "Газли", "Гиждуван", "Каган", "Каракуль", "Караулбазар",
                       "Ромитан", "Шафиркан"],
    "Джизакская обл.": ["Джизак", "Гагарин", "Галляарал", "Даштабад", "Дустлик", "Заамин", "Пахтакор"],
    "Кашкадарьинская обл.": ["Карши", "Бешкент", "Гузар", "Камаши", "Касан", "Китаб", "Мубарек", "Талимарджан",
                             "Чиракчи", "Шахрисабз", "Яккабаг"],
    "Навоийская обл.": ["Навои", "Зарафшан", "Кызылтепа", "Нурата", "Учкудук", "Янгирабат"],
    "Наманганская обл.": ["Наманган", "Касансай", "Пап", "Туракурган", "Учкурган", "Хаккулабад", "Чуст", "Чартак"],
    "Самаркандская обл.": ["Самарканд", "Акташ", "Булунгур", "Джамбай", "Джума", "Иштыхан", "Каттакурган", "Нурабад",
                           "Пайарык", "Ургут", "Челек"],
    "Сурхандарьинская обл.": ["Термез", "Байсун", "Денау", "Джаркурган", "Кумкурган", "Шаргунь", "Шерабад", "Шурчи"],
    "Сырдарьинская обл.": ["Гулистан", "Бахт", "Сырдарья", "Ширин", "Янгиер"],
    "Ферганская обл.": ["Фергана", "Бешарык", "Коканд", "Кува", "Кувасай", "Маргилан", "Риштан", "Хамза", "Яйпан"],
    "Хорезмская обл.": ["Ургенч", "Гурлен", "Питнак", "Хива", "Ханка", "Шават"],
    "Респ. Каракалпакстан": ["Нукус", "Беруни", "Бустон", "Кунград", "Мангит", "Муйнак", "Тахиаташ", "Турткуль",
                             "Ходжейли", "Чимбай", "Шуманай"]
}


class SeekerAuth:
    def __init__(self, bot):
        self.bot = bot

    def process_seeker_phone(self, message):
        """Обработка телефона соискателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            self.cancel_seeker_registration(message.chat.id, user_id, "Регистрация отменена")
            return

        if not user_state or user_state.get('step') != 'phone':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        phone = message.text.strip()

        if not utils.is_valid_uzbek_phone(phone):
            self.bot.send_message(
                message.chat.id,
                "❌ Неверный формат номера!\n\n" +
                utils.show_phone_format_example() +
                "\n\nВведите номер:",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        formatted_phone = utils.format_phone(phone)
        clean_phone = formatted_phone.lstrip('+')  # Версия без плюса для проверки

        logging.info(f"🔍 Проверка уникальности телефона: {formatted_phone}")

        # Проверяем уникальность телефона (в обеих таблицах)
        # Ищем и с плюсом, и без, чтобы наверняка найти дубликат
        is_exist_seeker = database.execute_query(
            "SELECT id FROM job_seekers WHERE phone = ? OR phone = ?",
            (formatted_phone, clean_phone),
            fetchone=True
        )
        is_exist_employer = database.execute_query(
            "SELECT id FROM employers WHERE phone = ? OR phone = ?",
            (formatted_phone, clean_phone),
            fetchone=True
        )

        if is_exist_seeker or is_exist_employer:
            logging.warning(f"❌ Телефон {formatted_phone} уже занят!")
            self.bot.send_message(
                message.chat.id,
                "❌ Данный номер телефона уже зарегестрирован! Пожалуйста укажите другой номер телефона.",
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        if 'registration_data' not in user_state:
            user_state['registration_data'] = {}
        user_state['registration_data']['phone'] = formatted_phone
        user_state['step'] = 'email'
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            f"✅ Телефон принят: {formatted_phone}\n\n"
            "📧 Введите ваш email:",
            reply_markup=keyboards.cancel_keyboard()
        )

    def process_seeker_email(self, message):
        """Обработка email соискателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            self.cancel_seeker_registration(message.chat.id, user_id, "Регистрация отменена")
            return

        if not user_state or user_state.get('step') != 'email':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        email = message.text.strip().lower()

        if not utils.is_valid_email(email):
            self.bot.send_message(
                message.chat.id,
                "❌ Неверный формат email!\nВведите email:",
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        logging.info(f"🔍 Проверка уникальности email: {email}")

        # Проверяем уникальность email (в обеих таблицах)
        # Используем LOWER() для нечувствительности к регистру
        is_exist_seeker = database.execute_query(
            "SELECT id FROM job_seekers WHERE LOWER(email) = ?",
            (email,),
            fetchone=True
        )
        is_exist_employer = database.execute_query(
            "SELECT id FROM employers WHERE LOWER(email) = ?",
            (email,),
            fetchone=True
        )

        if is_exist_seeker or is_exist_employer:
            logging.warning(f"❌ Email {email} уже занят!")
            self.bot.send_message(
                message.chat.id,
                "❌ Данный email уже зарегестрирован! Пожалуйста укажите другой email.",
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        user_state['registration_data']['email'] = email
        # Генерируем случайный пароль, так как шаг ввода пароля убран
        user_state['registration_data']['password'] = utils.generate_random_string(16)
        user_state['step'] = 'full_name'
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            "✅ Email принят!\n\n"
            "👤 Введите ваше ФИО:",
            reply_markup=keyboards.cancel_keyboard()
        )

    def process_seeker_name(self, message):
        """Обработка ФИО соискателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            self.cancel_seeker_registration(message.chat.id, user_id, "Регистрация отменена")
            return

        if not user_state or user_state.get('step') != 'full_name':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        full_name = message.text.strip()

        is_valid, error_msg = utils.validate_name(full_name)
        if not is_valid:
            self.bot.send_message(message.chat.id, error_msg)
            return

        logging.info(f"🔍 Проверка уникальности имени: {full_name}")

        # Проверяем уникальность имени (регистронезависимо)
        is_exist = database.execute_query(
            "SELECT id FROM job_seekers WHERE LOWER(full_name) = ?",
            (full_name.lower(),),
            fetchone=True
        )
        if is_exist:
            logging.warning(f"❌ Имя {full_name} уже занято!")
            self.bot.send_message(
                message.chat.id,
                "❌ Пользователь с таким именем уже зарегистрирован! "
                "Пожалуйста, укажите другое имя (например, добавьте отчество).",
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        user_state['registration_data']['full_name'] = full_name
        user_state['step'] = 'region'
        database.set_user_state(user_id, user_state)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(*[types.KeyboardButton(reg) for reg in UZ_REGIONS.keys()])
        markup.row(types.KeyboardButton("❌ Отмена"))

        self.bot.send_message(
            message.chat.id,
            "🌍 Выберите вашу область/регион:",
            reply_markup=markup
        )

    def process_seeker_region(self, message):
        """Обработка выбора региона соискателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if utils.cancel_request(message.text):
            self.cancel_seeker_registration(message.chat.id, user_id, "Регистрация отменена")
            return

        if not user_state or user_state.get('step') != 'region':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        region = message.text.strip()
        if region not in UZ_REGIONS:
            self.bot.send_message(message.chat.id, "❌ Пожалуйста, выберите регион из списка:", reply_markup=None)
            return

        user_state['registration_data']['region'] = region
        user_state['step'] = 'city_selection'
        database.set_user_state(user_id, user_state)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(*[types.KeyboardButton(city) for city in UZ_REGIONS[region]])
        markup.row(types.KeyboardButton("⬅️ Назад"), types.KeyboardButton("❌ Отмена"))

        self.bot.send_message(
            message.chat.id,
            f"🏙️ Выберите город в регионе {region}:",
            reply_markup=markup
        )

    def process_seeker_city_selection(self, message):
        """Обработка выбора города соискателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        if message.text == "⬅️ Назад":
            user_state['step'] = 'region'
            database.set_user_state(user_id, user_state)

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(*[types.KeyboardButton(reg) for reg in UZ_REGIONS.keys()])
            markup.row(types.KeyboardButton("❌ Отмена"))

            self.bot.send_message(message.chat.id, "🌍 Выберите вашу область/регион:", reply_markup=markup)
            return

        if utils.cancel_request(message.text):
            self.cancel_seeker_registration(message.chat.id, user_id, "Регистрация отменена")
            return

        if not user_state or user_state.get('step') != 'city_selection':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        city = message.text.strip()

        region = user_state.get('registration_data', {}).get('region')
        cities_in_region = UZ_REGIONS.get(region, [])
        if city not in cities_in_region:
            self.bot.send_message(message.chat.id, "❌ Пожалуйста, выберите город из списка.")
            return

        user_state['registration_data']['city'] = city
        user_state['step'] = 'age'
        database.set_user_state(user_id, user_state)

        self.bot.send_message(
            message.chat.id,
            "📅 Введите ваш возраст:",
            reply_markup=keyboards.cancel_keyboard()
        )

    def finish_seeker_registration(self, message):
        """Завершение регистрации соискателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)

        # Проверка отмены
        if utils.cancel_request(message.text):
            self.cancel_seeker_registration(message.chat.id, user_id, "Регистрация отменена")
            return

        if not user_state or user_state.get('step') != 'age':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        try:
            age = int(message.text.strip())
            if age < 16 or age > 100:
                raise ValueError
        except ValueError:
            self.bot.send_message(
                message.chat.id,
                "❌ Введите возраст от 16 до 100 лет:",
                reply_markup=keyboards.cancel_keyboard()
            )
            return

        # Финальная проверка перед регистрацией
        existing_user = database.get_user_by_id(user_id)
        if existing_user:
            self.bot.send_message(
                message.chat.id,
                "❌ *Вы уже зарегистрированы!*\n\n"
                "Войдите в аккаунт.",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            database.clear_user_state(user_id)
            return

        # Получаем данные регистрации
        reg_data = user_state['registration_data']
        reg_data['telegram_id'] = user_id
        reg_data['age'] = age

        # Сохраняем в базу данных
        success = database.create_job_seeker(reg_data)

        if success:
            # Очищаем состояние регистрации
            database.clear_user_state(user_id)

            # Запускаем заполнение профиля
            from handlers.profile import ProfileHandlers
            profile_handler = ProfileHandlers(self.bot)
            profile_handler.start_profile_setup(message, reg_data)
        else:
            self.bot.send_message(
                message.chat.id,
                "❌ Ошибка регистрации! Возможно, вы уже зарегистрированы.",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            database.clear_user_state(user_id)

    def cancel_seeker_registration(self, chat_id, user_id, message_text):
        """Отмена регистрации соискателя"""
        database.clear_user_state(user_id)
        self.bot.send_message(
            chat_id,
            f"❌ *{message_text}*",
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu()
        )
