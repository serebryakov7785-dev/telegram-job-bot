# handlers/auth/role_auth.py
import database
import keyboards
import utils

class RoleAuth:
    def __init__(self, bot):
        self.bot = bot
        self.seeker_auth = None
        self.employer_auth = None
    
    def set_handlers(self, seeker_auth, employer_auth):
        self.seeker_auth = seeker_auth
        self.employer_auth = employer_auth
    
    def handle_role_selection(self, message):
        user_id = message.from_user.id
        existing_user = database.get_user_by_id(user_id)
        if existing_user:
            if 'full_name' in existing_user:
                self.bot.send_message(
                    message.chat.id, 
                    f"👋 Здравствуйте, {existing_user['full_name']}!", 
                    parse_mode='Markdown',
                    reply_markup=keyboards.seeker_main_menu()
                )
                if message.text == '🏢 Я работодатель':
                    self.bot.send_message(
                        message.chat.id,
                        "⚠️ Вы уже зарегистрированы как соискатель работы.\n\n"
                        "Если Вы хотите быть Работодателем, войдите пожалуйста в настройки, "
                        "удалите аккаунт и пройдите регистрацию для Работодателя.",
                        parse_mode='Markdown',
                        reply_markup=keyboards.seeker_main_menu()
                    )

            else:
                self.bot.send_message(
                    message.chat.id, 
                    f"👋 Здравствуйте, {existing_user['company_name']}!", 
                    parse_mode='Markdown', 
                    reply_markup=keyboards.employer_main_menu()
                )
                if message.text == '👤 Я ищу работу':
                    self.bot.send_message(
                        message.chat.id,
                        "⚠️ Вы уже зарегистрированы как работодатель.\n\n"
                        "Если Вы хотите быть Соискателем работы, войдите пожалуйста в настройки, "
                        "удалите аккаунт и пройдите регистрацию для Соискателя работы.",
                        parse_mode='Markdown',
                        reply_markup=keyboards.employer_main_menu()
                    )
            return
        if message.text == '👤 Я ищу работу':
            database.set_user_state(user_id, {'role': 'seeker'})
            self.bot.send_message(
                message.chat.id, 
                "👤 *Панель соискателя*\n\nВыберите действие:", 
                parse_mode='Markdown', 
                reply_markup=keyboards.seeker_menu(is_registered=False)
            )
        elif message.text == '🏢 Я работодатель':
            database.set_user_state(user_id, {'role': 'employer'})
            self.bot.send_message(
                message.chat.id, 
                "🏢 *Панель работодателя*\n\nВыберите действие:", 
                parse_mode='Markdown',
                reply_markup=keyboards.employer_menu(is_registered=False)
            )
    
    def handle_registration_start(self, message):
        user_id = message.from_user.id
        existing_user = database.get_user_by_id(user_id)
        if existing_user:
            if 'full_name' in existing_user:
                self.bot.send_message(
                    message.chat.id, 
                    f"👋 Здравствуйте, {existing_user['full_name']}!", 
                    parse_mode='Markdown', 
                    reply_markup=keyboards.seeker_main_menu()
                )
            else:
                self.bot.send_message(
                    message.chat.id, 
                    f"👋 Здравствуйте, {existing_user['company_name']}!", 
                    parse_mode='Markdown', 
                    reply_markup=keyboards.employer_main_menu()
                )
            return
        
        user_state = database.get_user_state(user_id)
        if not user_state or 'role' not in user_state:
            self.bot.send_message(
                message.chat.id, 
                "❌ Сначала выберите роль в главном меню!", 
                parse_mode='Markdown', 
                reply_markup=keyboards.main_menu()
            )
            return
        
        captcha_question, captcha_answer = utils.generate_captcha()
        user_state['captcha_answer'] = captcha_answer
        user_state['step'] = 'captcha'
        database.set_user_state(user_id, user_state)
        
        self.bot.send_message(
            message.chat.id,
            f"🔐 *Проверка безопасности*\n\n"
            f"Для продолжения регистрации решите простой пример:\n\n"
            f"📝 *{captcha_question}* = ?\n\n"
            f"Введите ответ (только положительное число):",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )
    
    def process_captcha(self, message):
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        
        if utils.cancel_request(message.text):
            self.cancel_registration(message.chat.id, user_id, "Регистрация отменена")
            return
        
        if not user_state:
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return
        
        user_answer = message.text.strip()
        correct_answer = user_state.get('captcha_answer')
        
        if not utils.validate_captcha(user_answer, correct_answer):
            captcha_question, captcha_answer = utils.generate_captcha()
            user_state['captcha_answer'] = captcha_answer
            database.set_user_state(user_id, user_state)
            
            self.bot.send_message(
                message.chat.id,
                f"❌ *Неправильный ответ!*\n\n"
                f"Попробуйте еще раз:\n\n"
                f"📝 *{captcha_question}* = ?",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
            return
        
        if 'captcha_answer' in user_state:
            del user_state['captcha_answer']
        
        role = user_state.get('role')
        if role == 'seeker':
            self.start_seeker_registration_after_captcha(message, user_state)
        elif role == 'employer':
            self.start_employer_registration_after_captcha(message, user_state)
    
    def start_seeker_registration_after_captcha(self, message, user_state):
        user_id = message.from_user.id
        existing_user = database.get_user_by_id(user_id)
        if existing_user:
            self.bot.send_message(
                message.chat.id, 
                f"👋 Здравствуйте, {existing_user['full_name']}!", 
                parse_mode='Markdown', 
                reply_markup=keyboards.seeker_main_menu()
            )
            database.clear_user_state(user_id)
            return
        
        user_state['step'] = 'phone'
        user_state['registration_data'] = {}
        database.set_user_state(user_id, user_state)
        
        self.bot.send_message(
            message.chat.id,
            "✅ *Проверка пройдена!*\n\n"
            "👤 *Регистрация соискателя*\n\n"
            "📱 Введите номер телефона Узбекистана:\n\n" +
            utils.show_phone_format_example(),
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )
    
    def start_employer_registration_after_captcha(self, message, user_state):
        user_id = message.from_user.id
        existing_user = database.get_user_by_id(user_id)
        if existing_user:
            self.bot.send_message(
                message.chat.id, 
                f"👋 Здравствуйте, {existing_user['company_name']}!", 
                parse_mode='Markdown', 
                reply_markup=keyboards.employer_main_menu()
            )
            database.clear_user_state(user_id)
            return
        
        user_state['step'] = 'company_name'
        user_state['registration_data'] = {}
        database.set_user_state(user_id, user_state)
        
        self.bot.send_message(
            message.chat.id,
            "✅ *Проверка пройдена!*\n\n"
            "🏢 *Регистрация компании*\n\n"
            "🏢 Введите название компании:",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )
    
    def cancel_registration(self, chat_id, user_id, message_text):
        database.clear_user_state(user_id)
        self.bot.send_message(
            chat_id, 
            f"❌ *{message_text}*", 
            parse_mode='Markdown', 
            reply_markup=keyboards.main_menu()
        )