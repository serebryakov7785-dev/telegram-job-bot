import logging
import database
import keyboards
import utils
from datetime import datetime
from models import dict_to_job_seeker
from telebot import types
from database.core import execute_query

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


class SeekerHandlers:
    def __init__(self, bot):
        self.bot = bot

    def handle_find_vacancies(self, message):
        """Поиск вакансий"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data or 'full_name' not in user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала зарегистрируйтесь или войдите как соискатель!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        # Упрощенный поиск: показываем все вакансии
        self.show_vacancies(message, city=None)

    def process_vacancy_filter_choice(self, message):
        if message.text == "⬅️ Назад":
            self.bot.send_message(message.chat.id, "Главное меню", reply_markup=keyboards.seeker_main_menu())
            return

        if message.text == "🏙 Выбрать город":
            # Показываем список регионов
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for region in UZB_REGIONS.keys():
                markup.add(types.KeyboardButton(region))
            markup.add("⬅️ Назад")

            msg = self.bot.send_message(message.chat.id, "Выберите область/регион:", reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.process_vacancy_region_choice)
        else:
            self.show_vacancies(message, city=None)

    def process_vacancy_region_choice(self, message):
        if message.text == "⬅️ Назад":
            self.handle_find_vacancies(message)
            return

        region = message.text
        if region in UZB_REGIONS:
            # Показываем города выбранного региона
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for city in UZB_REGIONS[region]:
                markup.add(types.KeyboardButton(city))
            markup.add("⬅️ Назад")

            msg = self.bot.send_message(message.chat.id, f"Выберите город/район в {region}:", reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.process_vacancy_city_choice)
        else:
            self.bot.send_message(message.chat.id, "❌ Выберите регион из списка.")
            # Перезапускаем шаг, имитируя нажатие кнопки "Выбрать город"
            message.text = "🏙 Выбрать город"
            self.process_vacancy_filter_choice(message)

    def process_vacancy_city_choice(self, message):
        if message.text == "⬅️ Назад":
            # Возвращаемся к выбору региона
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            for region in UZB_REGIONS.keys():
                markup.add(types.KeyboardButton(region))
            markup.add("⬅️ Назад")

            msg = self.bot.send_message(message.chat.id, "Выберите область/регион:", reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.process_vacancy_region_choice)
            return

        city = message.text
        self.show_vacancies(message, city)

    def show_vacancies(self, message, city=None):
        # Формируем запрос с фильтром
        query = """
            SELECT v.*, e.company_name, e.city
            FROM vacancies v
            JOIN employers e ON v.employer_id = e.id
            WHERE v.status = 'active'
        """
        params = []
        if city:
            query += " AND e.city LIKE ?"
            params.append(f"%{city}%")

        query += " ORDER BY v.created_at DESC LIMIT 20"

        vacancies = execute_query(query, tuple(params), fetchall=True)

        if not vacancies:
            self.bot.send_message(
                message.chat.id,
                "🔍 *Поиск вакансий*\n\n"
                "К сожалению, сейчас нет активных вакансий.",
                parse_mode='Markdown',
                reply_markup=keyboards.seeker_main_menu()
            )
            return

        self.bot.send_message(
            message.chat.id,
            f"🔍 *Найдено вакансий: {len(vacancies)}*\n\n"
            "Вот список доступных вакансий:",
            parse_mode='Markdown',
            reply_markup=keyboards.seeker_main_menu()
        )

        for vac in vacancies:
            try:
                card = (
                    f"💼 *{vac['title']}*\n"
                    f"🏢 Компания: *{vac['company_name']}*\n"
                    f"🏙️ Город: {vac['city']}\n"
                    f"💰 Зарплата: {vac['salary']}\n"
                    f"⏱ Тип: {vac['job_type']}\n"
                    f"🗣 Языки: {vac.get('languages') or 'Не указаны'}\n"
                    f"📝 Описание: {vac['description']}"
                )

                self.bot.send_message(
                    message.chat.id,
                    card,
                    parse_mode='Markdown',
                    reply_markup=keyboards.vacancy_actions(vac['id'])
                )
            except Exception as e:
                logging.error(f"❌ Ошибка при отправке карточки вакансии: {e}", exc_info=True)

    def handle_application_callback(self, call):
        """Обработка нажатия кнопки 'Откликнуться'"""
        try:
            user_id = call.from_user.id
            vacancy_id = int(call.data.split('_')[1])

            user_data = database.get_user_by_id(user_id)
            if not user_data or 'full_name' not in user_data:
                self.bot.answer_callback_query(call.id, "❌ Вы должны быть авторизованы как соискатель!")
                return

            # Проверяем, не откликался ли уже
            if database.check_application_exists(vacancy_id, user_data['id']):
                self.bot.answer_callback_query(call.id, "⚠️ Вы уже откликнулись на эту вакансию!")
                return

            # Создаем отклик
            if database.create_application(vacancy_id, user_data['id']):
                self.bot.answer_callback_query(call.id, "✅ Отклик отправлен!")
                self.bot.send_message(
                    call.message.chat.id,
                    "✅ Вы успешно откликнулись на вакансию!"
                )
            else:
                self.bot.answer_callback_query(call.id, "❌ Ошибка при отправке отклика.")
        except Exception as e:
            logging.error(f"❌ Ошибка в handle_application_callback: {e}", exc_info=True)
            self.bot.answer_callback_query(call.id, "❌ Произошла ошибка.")

    def handle_my_resume(self, message):
        """Просмотр резюме"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data or 'full_name' not in user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала зарегистрируйтесь или войдите как соискатель!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        # Преобразуем в модель
        seeker = dict_to_job_seeker(user_data)

        age_text = f"{seeker.age} лет" if seeker.age is not None and seeker.age > 0 else "Не указан"
        status_text = "✅ Активно ищет работу" if seeker.status == 'active' else "⛔ Нашел работу"

        resume_text = (
            "📄 *ВАШЕ РЕЗЮМЕ*\n"
            f"═══════════════════════════\n\n"
            f"👤 *ФИО:* {seeker.full_name}\n"
            f"🏙️ *Город:* {seeker.city}\n"
            f"📅 *Возраст:* {age_text}\n"
            f"📞 *Телефон:* {seeker.phone}\n"
            f"📧 *Email:* {seeker.email}\n"
            f"🎯 *Профессия:* {seeker.profession}\n\n"

            f"🎓 *ОБРАЗОВАНИЕ:*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{seeker.education}\n\n"

            f"🗣 *ЯЗЫКИ:*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{seeker.languages}\n\n"

            f"� *НАВЫКИ:*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{seeker.skills}\n\n"

            f"📋 *ОПЫТ РАБОТЫ:*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{seeker.experience}\n\n"

            f"═══════════════════════════\n"
            f"*Статус:* {status_text}"
        )

        self.bot.send_message(
            message.chat.id,
            resume_text,
            parse_mode='Markdown',
            reply_markup=keyboards.seeker_main_menu()
        )

    def handle_my_responses(self, message):
        """Мои отклики"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data or 'full_name' not in user_data:
            self.bot.send_message(
                message.chat.id,
                "❌ *Сначала зарегистрируйтесь или войдите как соискатель!*",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
            return

        # Получаем список откликов
        applications = database.get_seeker_applications(user_data['id'])

        if not applications:
            self.bot.send_message(
                message.chat.id,
                "📋 *Мои отклики*\n\n"
                "У вас пока нет активных откликов.\n"
                "Перейдите в раздел '🔍 Найти вакансии', чтобы откликнуться!",
                parse_mode='Markdown',
                reply_markup=keyboards.seeker_main_menu()
            )
            return

        self.bot.send_message(
            message.chat.id,
            f"📋 *Ваши отклики ({len(applications)}):*",
            parse_mode='Markdown',
            reply_markup=keyboards.seeker_main_menu()
        )

        for app in applications:
            status_map = {
                'pending': '⏳ Ожидает',
                'accepted': '✅ Приглашение',
                'rejected': '❌ Отказ'
            }
            status_text = status_map.get(app.get('status'), '❓ Неизвестно')

            created_at_raw = app.get('created_at')
            created_at_text = created_at_raw
            if created_at_raw:
                try:
                    # Преобразуем дату в более читаемый формат
                    dt_obj = datetime.strptime(str(created_at_raw).split('.')[0], '%Y-%m-%d %H:%M:%S')
                    created_at_text = dt_obj.strftime('%d.%m.%Y')
                except (ValueError, AttributeError):
                    pass  # Если формат другой, оставляем как есть

            card = (
                f"💼 *{app.get('title', 'Без названия')}*\n"
                f"🏢 {app.get('company_name', 'Компания не указана')}\n"
                f"💰 {app.get('salary', 'Не указана')}\n"
                f"📅 Отклик: {created_at_text}\n"
                f"📊 Статус: {status_text}"
            )

            self.bot.send_message(
                message.chat.id,
                card,
                parse_mode='Markdown'
            )

    def handle_seeker_chats(self, message):
        """Меню чатов соискателя (список приглашений)"""
        user_id = message.from_user.id
        user_data = database.get_user_by_id(user_id)

        if not user_data or 'full_name' not in user_data:
            self.bot.send_message(message.chat.id, "❌ Ошибка авторизации.")
            return

        # Получаем список приглашений (отклики со статусом accepted)
        query = """
            SELECT v.title, e.company_name, e.telegram_id
            FROM applications a
            JOIN vacancies v ON a.vacancy_id = v.id
            JOIN employers e ON v.employer_id = e.id
            WHERE a.seeker_id = ? AND a.status = 'accepted'
        """
        invitations = database.execute_query(query, (user_data['id'],), fetchall=True)

        if not invitations:
            self.bot.send_message(message.chat.id, "📭 У вас пока нет активных приглашений (чатов).")
            return

        self.bot.send_message(message.chat.id, f"💬 *Ваши приглашения и чаты ({len(invitations)}):*", parse_mode='Markdown')

        for inv in invitations:
            text = (
                f"🏢 Компания: *{utils.escape_markdown(inv['company_name'])}*\n"
                f"💼 Вакансия: *{utils.escape_markdown(inv['title'])}*\n"
                f"✅ *Приглашение на собеседование*"
            )
            self.bot.send_message(message.chat.id, text, parse_mode='Markdown',
                                  reply_markup=keyboards.contact_employer_keyboard(inv['telegram_id']))
