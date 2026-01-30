# handlers/employer.py
import database
import logging
import utils
import keyboards
from models import dict_to_employer

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
            'step': 'vacancy_title',
            'vacancy_data': {
                'employer_id': user_data['id']
            }
        })
        
        self.bot.send_message(
            message.chat.id,
            f"➕ *Создание вакансии*\n\n"
            f"Компания: *{employer.company_name}*\n\n"
            "Введите название должности (например: *Менеджер по продажам*):",
            parse_mode='Markdown',
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
            
        user_state['vacancy_data']['description'] = description
        user_state['step'] = 'vacancy_salary'
        database.set_user_state(user_id, user_state)
        
        self.bot.send_message(
            message.chat.id,
            "💰 Укажите зарплату (например: *5 000 000 сум* или *Договорная*):",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )

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
        if job_type not in ['Полный день', 'Частичная занятость', 'Удаленная работа', 'Стажировка']:
            self.bot.send_message(message.chat.id, "❌ Выберите вариант из меню:", reply_markup=keyboards.job_type_menu())
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
                f"📋 *Мои вакансии*\n\n"
                f"У вас пока нет активных вакансий.\n"
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
                f"📝 Описание: {vac['description']}\n\n"
                f"📅 Создано: {vac['created_at']}",
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
        
        # Получаем список соискателей
        seekers = database.get_all_seekers(limit=20)
        
        # Фильтруем только активных
        active_seekers = [s for s in seekers if s.get('status') == 'active']
        
        if not active_seekers:
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
            f"👥 *Найдено кандидатов: {len(active_seekers)}*\n\n"
            "Вот список активных соискателей:",
            parse_mode='Markdown',
            reply_markup=keyboards.employer_main_menu()
        )
        
        for seeker in active_seekers:
            try:
                age_text = f"{seeker.get('age')} лет" if seeker.get('age') else "Не указан"
                city_text = seeker.get('city', 'Не указан')
                card = (
                    f"👤 *{seeker['full_name']}*\n"
                    f"🏙️ Город: {city_text}\n"
                    f"📅 Возраст: {age_text}\n"
                    f"🎯 *Профессия:* {seeker.get('profession', 'Не указана')}\n"
                    f"🎓 Образование: {seeker.get('education', 'Не указано')}\n"
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

            if vacancy_id:
                vac_data = database.execute_query("SELECT title, salary, job_type, description FROM vacancies WHERE id = ?", (vacancy_id,), fetchone=True)
                if vac_data:
                    vacancy_title = vac_data.get('title', 'Не указана')
                    vacancy_salary = vac_data.get('salary', 'Не указана')
                    vacancy_type = vac_data.get('job_type', 'Не указан')
                    vacancy_desc = vac_data.get('description', 'Нет описания')
            
            invitation_text = (
                f"🎉 *Вас пригласили на собеседование!*\n\n"
                f"🏢 Компания: *{utils.escape_markdown(company_name)}*\n"
                f"💼 Вакансия: *{utils.escape_markdown(vacancy_title)}*\n"
                f"💰 Зарплата: {utils.escape_markdown(vacancy_salary)}\n"
                f"⏱ Тип: {utils.escape_markdown(vacancy_type)}\n"
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
                logging.error(f"Не удалось отправить приглашение соискателю {seeker_telegram_id}: {e}", exc_info=True)
                self.bot.answer_callback_query(call.id, "❌ Не удалось отправить приглашение. Возможно, соискатель заблокировал бота.")
                return # Выходим, если не удалось отправить
            
            # Если отправка успешна, выполняем остальные действия
            # Если приглашение по вакансии, обновляем статус отклика
            if vacancy_id:
                database.execute_query(
                    "UPDATE applications SET status = 'accepted' WHERE vacancy_id = ? AND seeker_id = ?",
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
                reply_markup=None # Убираем кнопку после нажатия
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
            logging.error(f"❌ Ошибка разбора callback_data в handle_my_vacancy_actions: {e}", exc_info=True)
            self.bot.answer_callback_query(call.id, "❌ Ошибка обработки команды.")

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
            user_state['edit_data']['description'] = val
            
        user_state['step'] = 'edit_vacancy_salary'
        database.set_user_state(user_id, user_state)
        
        current_salary = user_state['current_vac']['salary']
        self.bot.send_message(
            message.chat.id,
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
                self.bot.send_message(message.chat.id, "❌ Выберите вариант из меню или отправьте .", reply_markup=keyboards.job_type_menu())
                return
            user_state['edit_data']['job_type'] = val
            
        # Обновляем данные в БД
        vac_id = user_state['vacancy_id']
        edit_data = user_state['edit_data']
        
        if edit_data and database.update_vacancy(vac_id, **edit_data):
            self.bot.send_message(message.chat.id, "✅ Вакансия успешно обновлена!", reply_markup=keyboards.employer_main_menu())
        else:
            self.bot.send_message(message.chat.id, "ℹ️ Данные не были изменены.", reply_markup=keyboards.employer_main_menu())
        
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
        self.bot.send_message(call.message.chat.id, "🗑️ Вакансия успешно удалена.", reply_markup=keyboards.employer_main_menu())

    def handle_vacancy_responses(self, call, vacancy_id):
        """Показать отклики на вакансию"""
        self.bot.answer_callback_query(call.id)
        
        # Получаем данные откликнувшихся соискателей
        query = """
            SELECT js.full_name, js.age, js.city, js.profession, js.education, js.experience, js.skills, js.phone, js.email, js.telegram_id
            FROM applications a
            JOIN job_seekers js ON a.seeker_id = js.id
            WHERE a.vacancy_id = ? AND js.status = 'active'
        """
        applicants = database.execute_query(query, (vacancy_id,), fetchall=True)
        
        if not applicants:
            self.bot.send_message(call.message.chat.id, "📭 На эту вакансию пока нет откликов.")
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
                    f"👤 *{utils.escape_markdown(str(app.get('full_name', '')))}* {age_text}\n"
                    f"🏙️ Город: {utils.escape_markdown(city_text)}\n"
                    f"🎯 {utils.escape_markdown(str(app.get('profession', '')))}\n"
                    f"🎓 {utils.escape_markdown(str(app.get('education', '')))}\n"
                    f"💼 {utils.escape_markdown(str(app.get('experience', '')))}\n"
                    f"🎨 {utils.escape_markdown(str(app.get('skills', '')))}"
                )
                
                self.bot.send_message(
                    call.message.chat.id, 
                    txt, 
                    parse_mode='Markdown',
                    reply_markup=keyboards.employer_invite_keyboard(app.get('telegram_id'), vacancy_id)
                )
            except Exception as e:
                logging.error(f"❌ Ошибка при отправке карточки отклика для вакансии {vacancy_id}: {e}", exc_info=True)
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