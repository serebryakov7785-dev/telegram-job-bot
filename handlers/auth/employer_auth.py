# handlers/auth/employer_auth.py
import database
import keyboards
import utils
from telebot import types

UZ_REGIONS = {
    "Ташкентская обл.": ["Ташкент", "Нурафшон", "Алмалык", "Ангрен", "Ахангаран", "Бекабад", "Бука", "Газалкент", "Келес", "Паркент", "Пскент", "Тойтепа", "Чиназ", "Чирчик", "Янгиабад", "Янгиюль"],
    "Андижанская обл.": ["Андижан", "Асака", "Карасу", "Кургантепа", "Мархамат", "Пайтуг", "Пахтаабад", "Ханабад", "Ходжаабад", "Шахрихан"],
    "Бухарская обл.": ["Бухара", "Алат", "Вабкент", "Газли", "Гиждуван", "Каган", "Каракуль", "Караулбазар", "Ромитан", "Шафиркан"],
    "Джизакская обл.": ["Джизак", "Гагарин", "Галляарал", "Даштабад", "Дустлик", "Заамин", "Пахтакор"],
    "Кашкадарьинская обл.": ["Карши", "Бешкент", "Гузар", "Камаши", "Касан", "Китаб", "Мубарек", "Талимарджан", "Чиракчи", "Шахрисабз", "Яккабаг"],
    "Навоийская обл.": ["Навои", "Зарафшан", "Кызылтепа", "Нурата", "Учкудук", "Янгирабат"],
    "Наманганская обл.": ["Наманган", "Касансай", "Пап", "Туракурган", "Учкурган", "Хаккулабад", "Чуст", "Чартак"],
    "Самаркандская обл.": ["Самарканд", "Акташ", "Булунгур", "Джамбай", "Джума", "Иштыхан", "Каттакурган", "Нурабад", "Пайарык", "Ургут", "Челек"],
    "Сурхандарьинская обл.": ["Термез", "Байсун", "Денау", "Джаркурган", "Кумкурган", "Шаргунь", "Шерабад", "Шурчи"],
    "Сырдарьинская обл.": ["Гулистан", "Бахт", "Сырдарья", "Ширин", "Янгиер"],
    "Ферганская обл.": ["Фергана", "Бешарык", "Коканд", "Кува", "Кувасай", "Маргилан", "Риштан", "Хамза", "Яйпан"],
    "Хорезмская обл.": ["Ургенч", "Гурлен", "Питнак", "Хива", "Ханка", "Шават"],
    "Респ. Каракалпакстан": ["Нукус", "Беруни", "Бустон", "Кунград", "Мангит", "Муйнак", "Тахиаташ", "Турткуль", "Ходжейли", "Чимбай", "Шуманай"]
}

class EmployerAuth:
    def __init__(self, bot):
        self.bot = bot
    
    def process_employer_name(self, message):
        """Обработка названия компании"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        
        # Проверка отмены
        if utils.cancel_request(message.text):
            self.cancel_employer_registration(message.chat.id, user_id, "Регистрация отменена")
            return
        
        if not user_state or user_state.get('step') != 'company_name':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return
        
        company_name = message.text.strip()
        
        if len(company_name) < 2:
            msg = self.bot.send_message(
                message.chat.id,
                "❌ Название компании слишком короткое!\nВведите название:",
                reply_markup=keyboards.cancel_keyboard()
            )
            return
        
        user_state['registration_data']['company_name'] = company_name
        user_state['step'] = 'phone'
        database.set_user_state(user_id, user_state)
        
        self.bot.send_message(
            message.chat.id,
            "📱 Введите номер телефона компании:\n\n" +
            utils.show_phone_format_example(),
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )
    
    def process_employer_phone(self, message):
        """Обработка телефона компании"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        
        # Проверка отмены
        if utils.cancel_request(message.text):
            self.cancel_employer_registration(message.chat.id, user_id, "Регистрация отменена")
            return
        
        if not user_state or user_state.get('step') != 'phone':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return
        
        phone = message.text.strip()
        
        if not utils.is_valid_uzbek_phone(phone):
            msg = self.bot.send_message(
                message.chat.id,
                "❌ Неверный формат номера!\n\n" +
                utils.show_phone_format_example() +
                "\n\nВведите номер:",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return
        
        formatted_phone = utils.format_phone(phone)
        clean_phone = formatted_phone.lstrip('+') # Версия без плюса
        
        print(f"🔍 Проверка уникальности телефона: {formatted_phone}")
        
        # Проверяем уникальность телефона (в обеих таблицах)
        is_exist_employer = database.execute_query(
            "SELECT id FROM employers WHERE phone = ? OR phone = ?", 
            (formatted_phone, clean_phone), 
            fetchone=True
        )
        is_exist_seeker = database.execute_query(
            "SELECT id FROM job_seekers WHERE phone = ? OR phone = ?", 
            (formatted_phone, clean_phone), 
            fetchone=True
        )
        
        if is_exist_employer or is_exist_seeker:
            print(f"❌ Телефон {formatted_phone} уже занят!")
            msg = self.bot.send_message(
                message.chat.id,
                "❌ Данный номер телефона уже зарегестрирован! Пожалуйста укажите другой номер телефона.",
                reply_markup=keyboards.cancel_keyboard()
            )
            return
        
        user_state['registration_data']['phone'] = formatted_phone
        user_state['step'] = 'email'
        database.set_user_state(user_id, user_state)
        
        self.bot.send_message(
            message.chat.id,
            f"✅ Телефон принят: {formatted_phone}\n\n"
            "📧 Введите email компании:",
            reply_markup=keyboards.cancel_keyboard()
        )
    
    def process_employer_email(self, message):
        """Обработка email компании"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        
        # Проверка отмены
        if utils.cancel_request(message.text):
            self.cancel_employer_registration(message.chat.id, user_id, "Регистрация отменена")
            return
        
        if not user_state or user_state.get('step') != 'email':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return
        
        email = message.text.strip().lower()
        
        if not utils.is_valid_email(email):
            msg = self.bot.send_message(
                message.chat.id,
                "❌ Неверный формат email!\nВведите email:",
                reply_markup=keyboards.cancel_keyboard()
            )
            return
        
        print(f"🔍 Проверка уникальности email: {email}")

        # Проверяем уникальность email (в обеих таблицах)
        is_exist_employer = database.execute_query(
            "SELECT id FROM employers WHERE LOWER(email) = ?", 
            (email,), 
            fetchone=True
        )
        is_exist_seeker = database.execute_query(
            "SELECT id FROM job_seekers WHERE LOWER(email) = ?", 
            (email,), 
            fetchone=True
        )
        
        if is_exist_employer or is_exist_seeker:
            print(f"❌ Email {email} уже занят!")
            msg = self.bot.send_message(
                message.chat.id,
                "❌ Данный email уже зарегестрирован! Пожалуйста укажите другой email.",
                reply_markup=keyboards.cancel_keyboard()
            )
            return
        
        user_state['registration_data']['email'] = email
        # Генерируем случайный пароль, так как шаг ввода пароля убран
        user_state['registration_data']['password'] = utils.generate_random_string(16)
        user_state['step'] = 'contact_person'
        database.set_user_state(user_id, user_state)
        
        self.bot.send_message(
            message.chat.id,
            "✅ Email принят!\n\n"
            "👤 Введите ФИО контактного лица:",
            reply_markup=keyboards.cancel_keyboard()
        )
    
    def process_employer_contact(self, message):
        """Обработка контактного лица"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        
        # Проверка отмены
        if utils.cancel_request(message.text):
            self.cancel_employer_registration(message.chat.id, user_id, "Регистрация отменена")
            return
        
        if not user_state or user_state.get('step') != 'contact_person':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return
        
        contact_person = message.text.strip()
        user_state['registration_data']['contact_person'] = contact_person
        user_state['step'] = 'region'
        database.set_user_state(user_id, user_state)
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(*[types.KeyboardButton(reg) for reg in UZ_REGIONS.keys()])
        markup.row(types.KeyboardButton("❌ Отмена"))
        
        self.bot.send_message(
            message.chat.id,
            "🌍 Выберите область/регион компании:",
            reply_markup=markup
        )
    
    def process_employer_region(self, message):
        """Обработка выбора региона работодателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        
        if utils.cancel_request(message.text):
            self.cancel_employer_registration(message.chat.id, user_id, "Регистрация отменена")
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

    def process_employer_city_selection(self, message):
        """Обработка выбора города работодателя"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        
        if message.text == "⬅️ Назад":
            user_state['step'] = 'region'
            database.set_user_state(user_id, user_state)
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(*[types.KeyboardButton(reg) for reg in UZ_REGIONS.keys()])
            markup.row(types.KeyboardButton("❌ Отмена"))
            
            self.bot.send_message(message.chat.id, "🌍 Выберите область/регион компании:", reply_markup=markup)
            return

        if utils.cancel_request(message.text):
            self.cancel_employer_registration(message.chat.id, user_id, "Регистрация отменена")
            return
            
        if not user_state or user_state.get('step') != 'city_selection':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return

        city = message.text.strip()
        user_state['registration_data']['city'] = city
        user_state['step'] = 'business_activity'
        database.set_user_state(user_id, user_state)
        
        self.bot.send_message(
            message.chat.id,
            "📋 Введите род деятельности компании:\n"
            "Пример: *IT и программирование*\n"
            "Пример: *Строительство и недвижимость*\n"
            "Пример: *Торговля и логистика*\n"
            "Пример: *Образование и обучение*",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )

    def process_business_activity(self, message):
        """Обработка рода деятельности компании"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        
        # Проверка отмены
        if utils.cancel_request(message.text):
            self.cancel_employer_registration(message.chat.id, user_id, "Регистрация отменена")
            return
        
        if not user_state or user_state.get('step') != 'business_activity':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return
        
        business_activity = message.text.strip()
        
        if len(business_activity) < 2:
            msg = self.bot.send_message(
                message.chat.id,
                "❌ Род деятельности слишком короткий!\nВведите род деятельности:",
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
        reg_data['business_activity'] = business_activity
        reg_data['description'] = 'Описание не указано'  # Добавляем дефолтное описание
        
        # Сохраняем в базу данных
        success = database.create_employer(reg_data)
        
        if success:
            # Очищаем состояние
            database.clear_user_state(user_id)
            
            # Итоговое сообщение
            self.bot.send_message(
                message.chat.id,
                f"✅ *Регистрация компании завершена!*\n\n"
                f"🏢 *Компания:* {reg_data['company_name']}\n"
                f"🏙️ *Город:* {reg_data['city']}\n"
                f"📋 *Род деятельности:* {reg_data['business_activity']}\n"
                f"👤 *Контакт:* {reg_data['contact_person']}\n"
                f"📞 *Телефон:* {reg_data['phone']}\n"
                f"📧 *Email:* {reg_data['email']}\n\n"
                f"Используйте меню для поиска сотрудников:",
                parse_mode='Markdown',
                reply_markup=keyboards.employer_main_menu()
            )
        else:
            self.bot.send_message(
                message.chat.id,
                "❌ Ошибка регистрации! Возможно, вы уже зарегистрированы.",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            database.clear_user_state(user_id)
    
    def cancel_employer_registration(self, chat_id, user_id, message_text):
        """Отмена регистрации работодателя"""
        database.clear_user_state(user_id)
        self.bot.send_message(
            chat_id,
            f"❌ *{message_text}*",
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu()
        )
