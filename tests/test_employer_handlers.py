import pytest
from unittest.mock import MagicMock, patch
from handlers.employer import EmployerHandlers


class TestEmployerHandlers:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return EmployerHandlers(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        return msg

    def test_handle_create_vacancy_not_registered(self, handler, message):
        """Попытка создать вакансию без регистрации"""
        with patch('database.get_user_by_id', return_value=None):
            handler.handle_create_vacancy(message)
            handler.bot.send_message.assert_called_once()
            assert "Сначала зарегистрируйтесь" in handler.bot.send_message.call_args[0][1]

    def test_handle_create_vacancy_success(self, handler, message):
        """Начало создания вакансии"""
        user_data = {'id': 1, 'company_name': 'Test Company', 'telegram_id': 456}

        with patch('database.get_user_by_id', return_value=user_data), \
             patch('database.set_user_state') as mock_set_state:

            handler.handle_create_vacancy(message)

            mock_set_state.assert_called_once()
            call_args = mock_set_state.call_args
            assert call_args[0][0] == 456
            assert call_args[0][1]['step'] == 'vacancy_sphere'

            handler.bot.send_message.assert_called_once()
            assert "Выберите сферу деятельности" in handler.bot.send_message.call_args[0][1]

    def test_process_vacancy_title_short(self, handler, message):
        """Слишком короткое название вакансии"""
        message.text = "Hi"
        with patch('database.get_user_state', return_value={'step': 'vacancy_title'}):
            handler.process_vacancy_title(message)
            handler.bot.send_message.assert_called_with(123, "❌ Слишком короткое название. Попробуйте еще раз:")

    def test_process_vacancy_title_boundary(self, handler, message):
        """Граничное значение длины названия вакансии"""
        message.text = "Dev"  # len 3
        user_state = {'step': 'vacancy_title', 'vacancy_data': {}}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state'):
            handler.process_vacancy_title(message)
            # Убеждаемся, что не было сообщения об ошибке
            call_text = handler.bot.send_message.call_args[0][1]
            assert "короткое" not in call_text
            assert "Введите описание" in call_text

    def test_process_vacancy_title_success(self, handler, message):
        """Успешный ввод названия вакансии"""
        message.text = "Python Developer"
        user_state = {'step': 'vacancy_title', 'vacancy_data': {'employer_id': 1}}

        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set_state:

            handler.process_vacancy_title(message)

            assert user_state['vacancy_data']['title'] == "Python Developer"
            assert user_state['step'] == 'vacancy_description'
            mock_set_state.assert_called_with(456, user_state)
            handler.bot.send_message.assert_called()

    def test_process_vacancy_description_short(self, handler, message):
        """Слишком короткое описание"""
        message.text = "Short"
        with patch('database.get_user_state', return_value={'step': 'vacancy_description'}):
            handler.process_vacancy_description(message)
            handler.bot.send_message.assert_called()
            assert "Описание слишком короткое" in handler.bot.send_message.call_args[0][1]

    def test_process_vacancy_description_success(self, handler, message):
        """Успешный ввод описания"""
        message.text = "Long enough description for the vacancy requirements"
        user_state = {'step': 'vacancy_description', 'vacancy_data': {'title': 'Dev'}}

        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set_state:

            handler.process_vacancy_description(message)

            assert user_state['vacancy_data']['description'] == message.text
            assert user_state['step'] == 'vacancy_language_selection'
            mock_set_state.assert_called_with(456, user_state)

    def test_process_vacancy_salary(self, handler, message):
        """Ввод зарплаты"""
        message.text = "1000$"
        user_state = {'step': 'vacancy_salary', 'vacancy_data': {}}

        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set_state:

            handler.process_vacancy_salary(message)

            assert user_state['vacancy_data']['salary'] == "1000$"
            assert user_state['step'] == 'vacancy_type'
            mock_set_state.assert_called_with(456, user_state)

    def test_process_vacancy_type_invalid(self, handler, message):
        """Неверный тип занятости"""
        message.text = "Invalid Type"
        user_state = {'step': 'vacancy_type', 'vacancy_data': {}}

        with patch('database.get_user_state', return_value=user_state):
            handler.process_vacancy_type(message)
            handler.bot.send_message.assert_called()
            assert "Выберите вариант из меню" in handler.bot.send_message.call_args[0][1]

    @pytest.mark.parametrize("job_type", ['Полный день', 'Частичная занятость', 'Удаленная работа', 'Стажировка'])
    def test_process_vacancy_type_all_valid(self, handler, message, job_type):
        """Тест всех валидных типов занятости"""
        message.text = job_type
        user_state = {'step': 'vacancy_type', 'vacancy_data': {}}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.create_vacancy', return_value=True), \
             patch('database.clear_user_state'):

            handler.process_vacancy_type(message)
            # Проверяем, что не было сообщения об ошибке
            call_text = handler.bot.send_message.call_args[0][1]
            assert "Выберите вариант из меню" not in call_text
            assert "Вакансия успешно создана" in call_text

    def test_process_vacancy_type_success(self, handler, message):
        """Успешное создание вакансии"""
        message.text = "Полный день"
        user_state = {'step': 'vacancy_type',
                      'vacancy_data': {'employer_id': 1, 'title': 'T', 'description': 'D', 'salary': 'S'}}

        with patch('database.get_user_state', return_value=user_state), \
             patch('database.create_vacancy', return_value=True) as mock_create, \
             patch('database.clear_user_state') as mock_clear:

            handler.process_vacancy_type(message)

            assert user_state['vacancy_data']['job_type'] == "Полный день"
            mock_create.assert_called_with(user_state['vacancy_data'])
            handler.bot.send_message.assert_called()
            assert "Вакансия успешно создана" in handler.bot.send_message.call_args[0][1]
            mock_clear.assert_called_with(456)

    def test_handle_my_vacancies_empty(self, handler, message):
        """Просмотр вакансий, когда их нет"""
        user_data = {'id': 1, 'company_name': 'Test Co'}
        with patch('database.get_user_by_id', return_value=user_data), \
             patch('database.get_employer_vacancies', return_value=[]):
            handler.handle_my_vacancies(message)
            assert "У вас пока нет активных вакансий" in handler.bot.send_message.call_args[0][1]

    def test_handle_my_vacancies_with_data(self, handler, message):
        """Просмотр вакансий, когда они есть"""
        user_data = {'id': 1, 'company_name': 'Test Co'}
        vacancies = [{
            'id': 101, 'title': 'Dev', 'salary': '1000',
            'job_type': 'Full', 'description': 'Desc',
            'created_at': '2023-01-01'
        }]

        with patch('database.get_user_by_id', return_value=user_data), \
             patch('database.get_employer_vacancies', return_value=vacancies):

            handler.handle_my_vacancies(message)

            handler.bot.send_message.assert_called()
            # Проверяем, что вызвана отправка карточки вакансии
            args = handler.bot.send_message.call_args
            assert "Dev" in args[0][1]

    def test_handle_find_candidates_success(self, handler, message):
        """Поиск кандидатов: есть активные"""
        user_data = {'id': 1, 'company_name': 'Test Co'}
        seekers = [{
            'id': 2, 'telegram_id': 222, 'full_name': 'Seeker',
            'status': 'active', 'age': 25, 'city': 'Tashkent',
            'profession': 'Dev', 'education': 'High', 'experience': '5y', 'skills': 'Python'
        }]

        with patch('database.get_user_by_id', return_value=user_data), \
             patch('database.get_all_seekers', return_value=seekers):

            handler.handle_find_candidates(message)

            # 1 сообщение заголовок, 1 сообщение карточка
            assert handler.bot.send_message.call_count == 2
            card_text = handler.bot.send_message.call_args_list[1][0][1]
            assert "Seeker" in card_text
            assert "Dev" in card_text

    def test_handle_invitation_callback(self, handler):
        """Отправка приглашения"""
        call = MagicMock()
        call.id = "1"
        call.from_user.id = 111  # Employer
        call.data = "invite_222_333"  # seeker_id=222, vacancy_id=333
        call.message.text = "Card text"
        call.message.chat.id = 111
        call.message.message_id = 999

        employer = {'id': 1, 'company_name': 'Test Co'}
        seeker = {'id': 2, 'full_name': 'Seeker', 'telegram_id': 222}
        vacancy = {'title': 'Dev', 'salary': '100', 'job_type': 'Full', 'description': 'Desc'}

        with patch('database.get_user_by_id', side_effect=[employer, seeker]), \
             patch('database.execute_query') as mock_query:

            # Mock vacancy query result
            mock_query.side_effect = [vacancy, None]  # 1st for vacancy select, 2nd for update status

            handler.handle_invitation_callback(call)

            # Проверяем отправку сообщения соискателю (ID 222)
            handler.bot.send_message.assert_called()
            args = handler.bot.send_message.call_args
            assert args[0][0] == 222
            assert "Вас пригласили" in args[0][1]

    def test_handle_my_vacancy_actions_edit(self, handler):
        """Роутинг действий: редактирование"""
        call = MagicMock()
        call.data = "edit_vac_101"
        call.from_user.id = 111

        with patch.object(handler, 'handle_edit_vacancy') as mock_edit:
            handler.handle_my_vacancy_actions(call)
            mock_edit.assert_called_with(call, 101)

    def test_handle_my_vacancy_actions_delete(self, handler):
        """Роутинг действий: удаление"""
        call = MagicMock()
        call.data = "delete_vac_102"
        call.from_user.id = 111

        with patch.object(handler, 'handle_delete_vacancy') as mock_delete:
            handler.handle_my_vacancy_actions(call)
            mock_delete.assert_called_with(call, 102)

    def test_handle_my_vacancy_actions_invalid_data(self, handler):
        """Роутинг действий: неверный callback_data"""
        call = MagicMock()
        call.data = "invalid_callback"
        call.id = "call_id"

        handler.handle_my_vacancy_actions(call)

        handler.bot.answer_callback_query.assert_called_with(call.id, "❌ Ошибка обработки команды.")

    def test_process_edit_title_no_change(self, handler, message):
        """Редактирование: пропуск поля"""
        message.text = "."
        user_state = {'step': 'edit_vacancy_title', 'edit_data': {}, 'current_vac': {'description': 'Desc'}}

        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:

            handler.process_edit_title(message)

            assert 'title' not in user_state['edit_data']  # Убеждаемся, что поле не добавлено
            assert user_state['step'] == 'edit_vacancy_desc'
            mock_set.assert_called_with(456, user_state)

    def test_handle_edit_vacancy(self, handler):
        """Начало редактирования"""
        call = MagicMock()
        call.message.chat.id = 123
        call.from_user.id = 111

        user_data = {'id': 1}
        vacancies = [{'id': 101, 'title': 'Old Title', 'description': 'Desc', 'salary': '100', 'job_type': 'Full'}]

        with patch('database.get_user_by_id', return_value=user_data), \
             patch('database.get_employer_vacancies', return_value=vacancies), \
             patch('database.set_user_state') as mock_set:

            handler.handle_edit_vacancy(call, 101)

            mock_set.assert_called()
            assert mock_set.call_args[0][1]['step'] == 'edit_vacancy_title'
            handler.bot.send_message.assert_called()
            assert "Old Title" in handler.bot.send_message.call_args[0][1]

    def test_handle_edit_vacancy_not_found(self, handler):
        """Начало редактирования несуществующей вакансии"""
        call = MagicMock()
        call.message.chat.id = 123
        call.from_user.id = 111

        user_data = {'id': 1}
        # Возвращаем пустой список вакансий
        with patch('database.get_user_by_id', return_value=user_data), \
             patch('database.get_employer_vacancies', return_value=[]):

            handler.handle_edit_vacancy(call, 999)  # 999 - несуществующий ID
            handler.bot.send_message.assert_called_with(call.message.chat.id, "❌ Вакансия не найдена.")

    def test_process_edit_type_success(self, handler, message):
        """Завершение редактирования"""
        message.text = "Удаленная работа"
        user_state = {
            'step': 'edit_vacancy_type',
            'vacancy_id': 101,
            'edit_data': {'title': 'New'},
            'current_vac': {'job_type': 'Full'}
        }

        with patch('database.get_user_state', return_value=user_state), \
             patch('database.update_vacancy', return_value=True) as mock_update, \
             patch('database.clear_user_state') as mock_clear:

            handler.process_edit_type(message)

            mock_update.assert_called()
            assert mock_update.call_args[1]['title'] == 'New'
            assert mock_update.call_args[1]['job_type'] == 'Удаленная работа'
            mock_clear.assert_called()
            handler.bot.send_message.assert_called()
            assert "успешно обновлена" in handler.bot.send_message.call_args[0][1]

    def test_process_edit_type_no_changes(self, handler, message):
        """Завершение редактирования без изменений"""
        message.text = "."  # Пропускаем последний шаг
        user_state = {
            'step': 'edit_vacancy_type',
            'vacancy_id': 101,
            'edit_data': {},  # Нет изменений
            'current_vac': {'job_type': 'Full'}
        }

        with patch('database.get_user_state', return_value=user_state), \
             patch('database.update_vacancy') as mock_update, \
             patch('database.clear_user_state'):

            handler.process_edit_type(message)

            mock_update.assert_not_called()  # Обновление не должно вызываться
            handler.bot.send_message.assert_called()
            assert "Данные не были изменены" in handler.bot.send_message.call_args[0][1]

    def test_handle_delete_vacancy(self, handler):
        """Запрос удаления"""
        call = MagicMock()
        call.message.chat.id = 123
        call.message.message_id = 999
        call.message.text = "Vac Info"

        handler.handle_delete_vacancy(call, 101)

        handler.bot.edit_message_text.assert_called()
        assert "Точно удалить" in handler.bot.edit_message_text.call_args[1]['text']

    def test_handle_confirm_delete(self, handler):
        """Подтверждение удаления"""
        call = MagicMock()
        call.data = "confirm_del_101"
        call.message.chat.id = 123
        call.message.message_id = 999

        with patch('database.delete_vacancy') as mock_delete:
            handler.handle_confirm_delete(call)

            mock_delete.assert_called_with(101)
            handler.bot.delete_message.assert_called()
            handler.bot.send_message.assert_called()

    def test_handle_vacancy_responses(self, handler):
        """Тест просмотра откликов на вакансию"""
        call = MagicMock()
        call.data = "responses_vac_101"
        call.message.chat.id = 123

        applicants = [{
            'full_name': 'Applicant One', 'age': 30, 'city': 'Tashkent', 'profession': 'Tester',
            'education': 'None', 'experience': 'None', 'skills': 'None', 'telegram_id': 999
        }]

        with patch('database.execute_query', return_value=applicants):
            handler.handle_vacancy_responses(call, 101)

            # Заголовок + карточка
            assert handler.bot.send_message.call_count == 2
            card_text = handler.bot.send_message.call_args[0][1]
            assert "Applicant One" in card_text
            assert "Tester" in card_text

    def test_handle_employer_chats(self, handler, message):
        """Тест просмотра чатов работодателя"""
        user_data = {'id': 1, 'company_name': 'Test Co'}
        chats = [{'full_name': 'Candidate', 'title': 'Dev', 'telegram_id': 888}]

        with patch('database.get_user_by_id', return_value=user_data), \
             patch('database.execute_query', return_value=chats):

            handler.handle_employer_chats(message)

            # Заголовок + карточка
            assert handler.bot.send_message.call_count == 2
            card_text = handler.bot.send_message.call_args[0][1]
            assert "Candidate" in card_text
            assert "Dev" in card_text

    def test_process_vacancy_type_creation_fails(self, handler, message):
        """Тест ошибки при создании вакансии на последнем шаге"""
        message.text = "Полный день"
        user_state = {'step': 'vacancy_type', 'vacancy_data': {}}

        with patch('database.get_user_state', return_value=user_state), \
             patch('database.create_vacancy', return_value=False), \
             patch('database.clear_user_state') as mock_clear:

            handler.process_vacancy_type(message)

            handler.bot.send_message.assert_called()
            assert "Ошибка при создании вакансии" in handler.bot.send_message.call_args[0][1]
            mock_clear.assert_called_with(456)

    def test_handle_find_candidates_no_active_seekers(self, handler, message):
        """Поиск кандидатов: нет активных соискателей"""
        user_data = {'id': 1, 'company_name': 'Test Co'}
        # Возвращаем пустой список, т.к. get_all_seekers(status='active') не найдет неактивных
        seekers = []

        with patch('database.get_user_by_id', return_value=user_data), \
             patch('database.get_all_seekers', return_value=seekers):

            handler.handle_find_candidates(message)

            handler.bot.send_message.assert_called()
            assert "нет активных соискателей" in handler.bot.send_message.call_args[0][1]

    def test_handle_invitation_callback_errors(self, handler):
        """Тест ошибок при отправке приглашения"""
        call = MagicMock()
        call.id = "1"
        call.from_user.id = 111
        call.data = "invite_222_333"

        # Случай 1: Работодатель не найден
        with patch('database.get_user_by_id', return_value=None):
            handler.handle_invitation_callback(call)
            handler.bot.answer_callback_query.assert_called_with(call.id, "❌ Ошибка: не найден профиль работодателя.")

        # Случай 2: Соискатель не найден
        with patch('database.get_user_by_id', side_effect=[{'company_name': 'Co'}, None]):
            handler.handle_invitation_callback(call)
            handler.bot.answer_callback_query.assert_called_with(call.id, "❌ Ошибка: не найден профиль соискателя.")

    def test_handle_vacancy_responses_empty(self, handler):
        """Тест просмотра откликов при их отсутствии"""
        call = MagicMock()
        call.data = "responses_vac_101"
        call.message.chat.id = 123

        with patch('database.execute_query', return_value=[]):
            handler.handle_vacancy_responses(call, 101)
            handler.bot.send_message.assert_called_with(123, "📭 На эту вакансию пока нет откликов.")

    def test_handle_invitation_callback_api_error(self, handler):
        """Отправка приглашения с ошибкой API"""
        call = MagicMock()
        call.id = "1"
        call.from_user.id = 111
        call.data = "invite_222_333"

        employer = {'id': 1, 'company_name': 'Test Co'}
        seeker = {'id': 2, 'full_name': 'Seeker', 'telegram_id': 222}
        vacancy = {'title': 'Dev'}

        with patch('database.get_user_by_id', side_effect=[employer, seeker]), \
             patch('database.execute_query', return_value=vacancy):

            # Мокаем ошибку при отправке сообщения
            handler.bot.send_message.side_effect = Exception("Blocked by user")

            handler.handle_invitation_callback(call)

            # Проверяем, что было отправлено сообщение об ошибке
            handler.bot.answer_callback_query.assert_called_with(call.id,
                                                                 "❌ Не удалось отправить приглашение. "
                                                                 "Возможно, соискатель заблокировал бота.")

    def test_process_edit_desc_success(self, handler, message):
        """Редактирование описания"""
        message.text = "New Description Long Enough"
        user_state = {'step': 'edit_vacancy_desc', 'edit_data': {}, 'current_vac': {'salary': '100'}}

        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:

            handler.process_edit_desc(message)

            assert user_state['edit_data']['description'] == message.text
            assert user_state['step'] == 'edit_vacancy_languages_prompt'
            mock_set.assert_called()

    def test_process_edit_salary_success(self, handler, message):
        """Редактирование зарплаты"""
        message.text = "2000$"
        user_state = {'step': 'edit_vacancy_salary', 'edit_data': {}, 'current_vac': {'job_type': 'Full'}}

        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:

            handler.process_edit_salary(message)

            assert user_state['edit_data']['salary'] == "2000$"
            assert user_state['step'] == 'edit_vacancy_type'
            mock_set.assert_called()

    def test_process_edit_type_invalid(self, handler, message):
        """Редактирование типа: неверное значение"""
        message.text = "Invalid"
        user_state = {'step': 'edit_vacancy_type'}

        with patch('database.get_user_state', return_value=user_state):
            handler.process_edit_type(message)
            handler.bot.send_message.assert_called()
            assert "Выберите вариант" in handler.bot.send_message.call_args[0][1]

    def test_handle_vacancy_responses_item_error(self, handler):
        """Тест ошибки при обработке одного отклика"""
        call = MagicMock()
        call.data = "responses_vac_101"
        call.message.chat.id = 123

        # Один нормальный, один вызывающий ошибку
        bad_applicant = MagicMock()
        bad_applicant.get.side_effect = Exception("Data Error")

        applicants = [
            {'full_name': 'Good', 'telegram_id': 1},
            bad_applicant
        ]

        with patch('database.execute_query', return_value=applicants), \
             patch('logging.error') as mock_log:

            handler.handle_vacancy_responses(call, 101)

            # Должен отправить сообщение об ошибке
            handler.bot.send_message.assert_called()
            # Проверяем, что залогировано
            mock_log.assert_called()

    def test_handle_employer_chats_item_error(self, handler, message):
        """Тест ошибки при обработке одного чата"""
        user_data = {'id': 1, 'company_name': 'Co'}

        # Чат, вызывающий ошибку при доступе
        bad_chat = MagicMock()
        bad_chat.__getitem__.side_effect = Exception("Chat Error")

        chats = [bad_chat]

        with patch('database.get_user_by_id', return_value=user_data), \
             patch('database.execute_query', return_value=chats), \
             patch('logging.error') as mock_log:

            handler.handle_employer_chats(message)

            mock_log.assert_called()

    def test_process_vacancy_sphere_other(self, handler, message):
        """Выбор 'Другое' в сфере деятельности"""
        message.text = "Другое"
        user_state = {'step': 'vacancy_sphere'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            handler.process_vacancy_sphere(message)
            assert mock_set.call_args[0][1]['step'] == 'vacancy_title'
            handler.bot.send_message.assert_called()

    def test_process_vacancy_sphere_valid(self, handler, message):
        """Выбор валидной сферы деятельности"""
        message.text = "IT и Интернет"
        user_state = {'step': 'vacancy_sphere'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            handler.process_vacancy_sphere(message)
            assert mock_set.call_args[0][1]['step'] == 'vacancy_profession'
            handler.bot.send_message.assert_called()

    def test_process_vacancy_sphere_invalid(self, handler, message):
        """Невалидная сфера деятельности"""
        message.text = "Invalid"
        user_state = {'step': 'vacancy_sphere'}
        with patch('database.get_user_state', return_value=user_state):
            handler.process_vacancy_sphere(message)
            handler.bot.send_message.assert_called_with(message.chat.id, "❌ Выберите сферу из списка.")

    def test_process_vacancy_profession_back(self, handler, message):
        """Кнопка Назад при выборе профессии"""
        message.text = "⬅️ Назад"
        with patch.object(handler, 'handle_create_vacancy') as mock_create:
            handler.process_vacancy_profession(message)
            mock_create.assert_called_with(message)

    def test_process_vacancy_profession_other(self, handler, message):
        """Выбор 'Другое' в профессии"""
        message.text = "Другое"
        user_state = {'step': 'vacancy_profession'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            handler.process_vacancy_profession(message)
            assert mock_set.call_args[0][1]['step'] == 'vacancy_title'

    def test_process_vacancy_profession_valid(self, handler, message):
        """Выбор валидной профессии"""
        message.text = "Dev"
        user_state = {'step': 'vacancy_profession', 'vacancy_data': {}}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state'):
            handler.process_vacancy_profession(message)
            assert user_state['vacancy_data']['title'] == "Dev"
            assert user_state['step'] == 'vacancy_description'

    def test_process_candidate_filter_choice_back(self, handler, message):
        """Фильтр кандидатов: Назад"""
        message.text = "⬅️ Назад"
        handler.process_candidate_filter_choice(message)
        handler.bot.send_message.assert_called()
        assert "Главное меню" in handler.bot.send_message.call_args[0][1]

    def test_process_candidate_filter_choice_city(self, handler, message):
        """Фильтр кандидатов: Выбрать город"""
        message.text = "🏙 Выбрать город"
        msg = MagicMock()
        handler.bot.send_message.return_value = msg
        handler.process_candidate_filter_choice(message)
        handler.bot.register_next_step_handler.assert_called_with(msg, handler.process_candidate_region_choice)

    def test_process_candidate_filter_choice_all(self, handler, message):
        """Фильтр кандидатов: Все (по умолчанию)"""
        message.text = "All"
        with patch.object(handler, 'show_candidates') as mock_show:
            handler.process_candidate_filter_choice(message)
            mock_show.assert_called_with(message, city=None)

    def test_process_candidate_region_choice_back(self, handler, message):
        """Выбор региона: Назад"""
        message.text = "⬅️ Назад"
        with patch.object(handler, 'handle_find_candidates') as mock_find:
            handler.process_candidate_region_choice(message)
            mock_find.assert_called_with(message)

    def test_process_candidate_region_choice_valid(self, handler, message):
        """Выбор региона: Валидный"""
        message.text = "Ташкентская обл."
        msg = MagicMock()
        handler.bot.send_message.return_value = msg
        handler.process_candidate_region_choice(message)
        handler.bot.register_next_step_handler.assert_called_with(msg, handler.process_candidate_city_choice)

    def test_process_candidate_region_choice_invalid(self, handler, message):
        """Выбор региона: Невалидный"""
        message.text = "Invalid"
        # Рекурсивный вызов process_candidate_filter_choice
        with patch.object(handler, 'process_candidate_filter_choice') as mock_filter:
            handler.process_candidate_region_choice(message)
            handler.bot.send_message.assert_called()
            mock_filter.assert_called()

    def test_process_candidate_city_choice_back(self, handler, message):
        """Выбор города: Назад"""
        message.text = "⬅️ Назад"
        msg = MagicMock()
        handler.bot.send_message.return_value = msg
        handler.process_candidate_city_choice(message)
        handler.bot.register_next_step_handler.assert_called_with(msg, handler.process_candidate_region_choice)

    def test_process_candidate_city_choice_valid(self, handler, message):
        """Выбор города: Валидный"""
        message.text = "Tashkent"
        with patch.object(handler, 'show_candidates') as mock_show:
            handler.process_candidate_city_choice(message)
            mock_show.assert_called_with(message, "Tashkent")

    def test_process_vacancy_language_selection_next(self, handler, message):
        """Выбор языков: Далее"""
        message.text = "➡️ Далее"
        user_state = {'temp_languages': [{'name': 'En', 'level': 'B2'}], 'vacancy_data': {}}
        with patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'ask_vacancy_salary') as mock_ask:
            handler.process_vacancy_language_selection(message)
            mock_ask.assert_called()
            assert "En (B2)" in user_state['vacancy_data']['languages']

    def test_process_vacancy_language_selection_skip(self, handler, message):
        """Выбор языков: Пропустить"""
        message.text = "Пропустить"
        user_state = {'vacancy_data': {}}
        with patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'ask_vacancy_salary') as mock_ask:
            handler.process_vacancy_language_selection(message)
            mock_ask.assert_called()
            assert "Не имеет значения" in user_state['vacancy_data']['languages']

    def test_process_vacancy_language_selection_other(self, handler, message):
        """Выбор языков: Другой"""
        message.text = "🌐 Другой"
        user_state = {}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            handler.process_vacancy_language_selection(message)
            assert mock_set.call_args[0][1]['step'] == 'vacancy_language_custom_name'

    def test_process_vacancy_language_selection_valid(self, handler, message):
        """Выбор языков: Валидный язык из списка"""
        message.text = "🇬🇧 Английский"
        user_state = {}
        with patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'show_vacancy_language_level') as mock_show:
            handler.process_vacancy_language_selection(message)
            mock_show.assert_called()
            assert user_state['current_lang_editing'] == 'Английский'

    def test_process_vacancy_language_custom_name_short(self, handler, message):
        """Тест короткого названия языка вакансии"""
        message.text = "A"
        with patch('database.get_user_state', return_value={'step': 'vacancy_language_custom_name'}):
            handler.process_vacancy_language_custom_name(message)
            handler.bot.send_message.assert_called()
            assert "Слишком короткое" in handler.bot.send_message.call_args[0][1]

    def test_process_vacancy_language_custom_name_duplicate(self, handler, message):
        """Тест дубликата языка вакансии"""
        message.text = "English"
        user_state = {'step': 'vacancy_language_custom_name', 'temp_languages': [{'name': 'English', 'level': 'B2'}]}
        with patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'show_vacancy_language_selection') as mock_show:
            handler.process_vacancy_language_custom_name(message)
            handler.bot.send_message.assert_called()
            assert "уже добавлен" in handler.bot.send_message.call_args[0][1]
            mock_show.assert_called()

    def test_process_vacancy_language_level_back(self, handler, message):
        """Тест кнопки Назад при выборе уровня языка вакансии"""
        message.text = "⬅️ Назад"
        with patch('database.get_user_state', return_value={'step': 'vacancy_language_level'}), \
             patch.object(handler, 'show_vacancy_language_selection') as mock_show:
            handler.process_vacancy_language_level(message)
            mock_show.assert_called()

    def test_process_edit_languages_prompt_invalid(self, handler, message):
        """Тест невалидного выбора при редактировании языков"""
        message.text = "Invalid"
        with patch('database.get_user_state', return_value={'step': 'edit_vacancy_languages_prompt'}):
            handler.process_edit_languages_prompt(message)
            handler.bot.send_message.assert_called()
            assert "Выберите действие" in handler.bot.send_message.call_args[0][1]

    def test_process_edit_title_invalid(self, handler, message):
        """Тест невалидного названия при редактировании"""
        message.text = "Hi"
        with patch('database.get_user_state', return_value={'step': 'edit_vacancy_title'}):
            handler.process_edit_title(message)
            handler.bot.send_message.assert_called()
            assert "Слишком короткое" in handler.bot.send_message.call_args[0][1]

    def test_process_edit_desc_invalid(self, handler, message):
        """Тест невалидного описания при редактировании"""
        message.text = "Short"
        with patch('database.get_user_state', return_value={'step': 'edit_vacancy_desc'}):
            handler.process_edit_desc(message)
            handler.bot.send_message.assert_called()
            assert "слишком короткое" in handler.bot.send_message.call_args[0][1]
