# handlers/profile.py
import database
import logging
import keyboards
import utils

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
                "🎓 *Введите ваше образование:*\n"
                "Пример: *Высшее техническое, Среднее специальное, Бакалавр*",
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
    
    def process_profession(self, message):
        """Обработка профессии/сферы деятельности"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        
        # Проверка отмены
        if utils.cancel_request(message.text):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return
        
        if not user_state or user_state.get('step') != 'profession':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return
        
        profession = message.text.strip()
        
        # Проверка ввода
        if len(profession) < 2:
            msg = self.bot.send_message(
                message.chat.id,
                "❌ Слишком короткое название!\n"
                "Введите профессию/сферу деятельности:",
                reply_markup=keyboards.cancel_keyboard()
            )
            return
        
        user_state['profile_data']['profession'] = profession
        user_state['step'] = 'languages'
        database.set_user_state(user_id, user_state)
        
        if user_state['role'] == 'seeker':
            self.bot.send_message(
                message.chat.id,
                "🗣 *Какие языки вы знаете?*\n"
                "Пример: *Русский, Узбекский, Английский (B2)*",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
        else:
            # Работодателю не задаем вопросы о требованиях
            self.save_profile_data(user_id, user_state)
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=True)
    
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
        
        education = message.text.strip()
        
        # Проверка ввода
        if len(education) < 2:
            msg = self.bot.send_message(
                message.chat.id,
                "❌ Слишком короткое описание!\n"
                "Введите образование/требования:",
                reply_markup=keyboards.cancel_keyboard()
            )
            return
        
        user_state['profile_data']['education'] = education
        user_state['step'] = 'profession'
        database.set_user_state(user_id, user_state)
        
        if user_state['role'] == 'seeker':
            self.bot.send_message(
                message.chat.id,
                "🎯 *Введите вашу профессию:*\n"
                "Пример: *Программист, Менеджер, Учитель, Врач*",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
        else:
            # Работодателю не задаем вопросы о требованиях
            self.save_profile_data(user_id, user_state)
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=True)
    
    def process_languages(self, message):
        """Обработка языков"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        
        # Проверка отмены
        if utils.cancel_request(message.text):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return
        
        if not user_state or user_state.get('step') != 'languages':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return
        
        languages = message.text.strip()
        
        # Проверка ввода
        if len(languages) < 2:
            msg = self.bot.send_message(
                message.chat.id,
                "❌ Слишком короткое описание!\n"
                "Введите языки, которые вы знаете:",
                reply_markup=keyboards.cancel_keyboard()
            )
            return
        
        user_state['profile_data']['languages'] = languages
        user_state['step'] = 'experience'
        database.set_user_state(user_id, user_state)
        
        if user_state['role'] == 'seeker':
            self.bot.send_message(
                message.chat.id,
                "💼 *Введите ваш опыт работы:*\n"
                "Пример: *3 года в IT, 5 лет в продажах, Нет опыта*",
                parse_mode='Markdown',
                reply_markup=keyboards.cancel_keyboard()
            )
    
    def process_experience(self, message):
        """Обработка опыта работы"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        
        # Проверка отмены
        if utils.cancel_request(message.text):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return
        
        if not user_state or user_state.get('step') != 'experience':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return
        
        experience = message.text.strip()
        
        # Проверка ввода
        if len(experience) < 2:
            msg = self.bot.send_message(
                message.chat.id,
                "❌ Слишком короткое описание!\n"
                "Введите опыт работы/требования:",
                reply_markup=keyboards.cancel_keyboard()
            )
            return
        
        user_state['profile_data']['experience'] = experience
        user_state['step'] = 'skills'
        database.set_user_state(user_id, user_state)
        
        self.bot.send_message(
            message.chat.id,
            "🎨 *Введите ваши профессиональные навыки через запятую:*\n"
            "Пример: *Python, Excel, Вождение, SQL*",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )
    
    def process_skills(self, message):
        """Обработка навыков"""
        user_id = message.from_user.id
        user_state = database.get_user_state(user_id)
        
        if utils.cancel_request(message.text):
            self.finish_profile_setup(message.chat.id, user_id, user_state, show_summary=False)
            return
        
        if not user_state or user_state.get('step') != 'skills':
            self.bot.send_message(message.chat.id, "❌ Сессия истекла!", reply_markup=keyboards.main_menu())
            return
        
        skills = message.text.strip()
        
        if len(skills) < 2:
            self.bot.send_message(
                message.chat.id,
                "❌ Слишком короткое описание!\n"
                "Введите ваши навыки:",
                reply_markup=keyboards.cancel_keyboard()
            )
            return
            
        user_state['profile_data']['skills'] = skills
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
                languages=profile_data.get('languages', 'Не указаны'),
                experience=profile_data.get('experience', 'Нет опыта'),
                skills=profile_data.get('skills', 'Не указаны')
            )
            
            if success:
                logging.info(f"✅ Профиль соискателя {user_id} обновлен")
            else:
                logging.warning(f"⚠️ Не удалось обновить профиль соискателя {user_id}")
                
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
                new_description += f"• Требования к опыту: {profile_data.get('experience', 'Не указано')}"
                
                success = database.update_employer_profile(
                    telegram_id=user_id,
                    description=new_description
                )
                
                if success:
                    logging.info(f"✅ Профиль работодателя {user_id} обновлен")
                else:
                    logging.warning(f"⚠️ Не удалось обновить профиль работодателя {user_id}")
    
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
                    f"👔 *Требования к опыту:* {profile_data.get('experience', 'Не указано')}\n\n"
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