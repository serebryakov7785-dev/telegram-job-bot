import pytest
from unittest.mock import MagicMock, patch
from handlers.employer import EmployerHandlers


class TestEmployerCoverage:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return EmployerHandlers(bot)

    @pytest.fixture
    def call(self):
        c = MagicMock()
        c.id = "call_id"
        c.from_user.id = 456
        c.message.chat.id = 123
        c.data = "test_data"
        return c

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        return msg

    def test_handle_invitation_callback_vacancy_not_found(self, handler, call):
        """Test invitation when vacancy is not found (optional ID provided but invalid)"""
        call.data = "invite_222_999"  # 999 is invalid vacancy ID
        employer = {'id': 1, 'company_name': 'Co'}
        seeker = {'id': 2, 'full_name': 'Seeker'}

        with patch('database.get_user_by_id', side_effect=[employer, seeker]), \
             patch('database.execute_query', return_value=None):  # Vacancy not found

            handler.handle_invitation_callback(call)

            # Should still send invitation but with default text
            handler.bot.send_message.assert_called()
            args = handler.bot.send_message.call_args[0]
            assert "Не указана" in args[1]  # Vacancy title default

    def test_handle_my_vacancy_actions_value_error(self, handler, call):
        """Test ValueError in callback data parsing"""
        call.data = "edit_vac_invalid"
        handler.handle_my_vacancy_actions(call)
        handler.bot.answer_callback_query.assert_called_with(call.id, "❌ Ошибка обработки команды.")

    def test_handle_employer_chats_exception(self, handler, message):
        """Test exception inside the loop of employer chats"""
        user_data = {'id': 1, 'company_name': 'Co'}
        chats = [{'full_name': 'Seeker', 'title': 'Dev', 'telegram_id': 123}]

        with patch('database.get_user_by_id', return_value=user_data), \
             patch('database.execute_query', return_value=chats), \
             patch.object(handler.bot, 'send_message', side_effect=[None, Exception("Send Error")]), \
             patch('logging.error') as mock_log:

            handler.handle_employer_chats(message)
            mock_log.assert_called()

    def test_process_vacancy_language_custom_name_success(self, handler, message):
        """Test successful custom language name input"""
        message.text = "Java"
        user_state = {'step': 'vacancy_language_custom_name', 'temp_languages': []}
        with patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'show_vacancy_language_level') as mock_show:
            handler.process_vacancy_language_custom_name(message)
            mock_show.assert_called()
            assert user_state['current_lang_editing'] == "Java"

    def test_process_edit_languages_prompt_keep(self, handler, message):
        """Test keeping current languages during edit"""
        message.text = "➡️ Оставить текущие"
        user_state = {'step': 'edit_vacancy_languages_prompt', 'current_vac': {'salary': '100'}}
        with patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'ask_edit_salary') as mock_ask:
            handler.process_edit_languages_prompt(message)
            mock_ask.assert_called()

    def test_process_edit_languages_prompt_change(self, handler, message):
        """Test changing languages during edit"""
        message.text = "✏️ Изменить"
        user_state = {'step': 'edit_vacancy_languages_prompt'}
        with patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'show_vacancy_language_selection') as mock_show:
            handler.process_edit_languages_prompt(message)
            mock_show.assert_called()
            assert user_state['is_editing_vacancy'] is True
            assert user_state['temp_languages'] == []

    def test_process_edit_title_success(self, handler, message):
        """Test successful title edit"""
        message.text = "New Title"
        user_state = {'step': 'edit_vacancy_title', 'edit_data': {}, 'current_vac': {'description': 'Desc'}}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            handler.process_edit_title(message)
            assert user_state['edit_data']['title'] == "New Title"
            assert user_state['step'] == 'edit_vacancy_desc'
            mock_set.assert_called()

    def test_show_candidates_exception(self, handler, message):
        """Test exception handling in show_candidates loop"""
        seekers = [{'full_name': 'S1'}, {'full_name': 'S2'}]
        with patch('database.get_all_seekers', return_value=seekers), \
             patch('logging.error') as mock_log:
            # First call succeeds, second raises exception
            handler.bot.send_message.side_effect = [None, None, Exception("Send Error")]
            handler.show_candidates(message)
            mock_log.assert_called()

    def test_handle_invitation_callback_with_vacancy(self, handler, call):
        """Test invitation with vacancy_id updates application status"""
        call.data = "invite_222_333"
        with patch('database.get_user_by_id', side_effect=[{'company_name': 'Co'}, {'full_name': 'Seeker', 'id': 2}]), \
             patch('database.execute_query') as mock_query:
            mock_query.side_effect = [{'title': 'Vac'}, None]  # Vacancy data, then UPDATE
            handler.handle_invitation_callback(call)
            # Verify UPDATE query was called
            update_call = [c for c in mock_query.call_args_list if "UPDATE applications" in c[0][0]]
            assert len(update_call) > 0

    def test_process_vacancy_title_profanity(self, handler, message):
        """Test vacancy title with profanity"""
        message.text = "badword"
        with patch('utils.contains_profanity', return_value=True):
            handler.process_vacancy_title(message)
            handler.bot.send_message.assert_called()
            assert "недопустимые слова" in handler.bot.send_message.call_args[0][1]

    def test_process_vacancy_description_profanity(self, handler, message):
        """Test vacancy description with profanity"""
        message.text = "badword description"
        with patch('utils.contains_profanity', return_value=True):
            handler.process_vacancy_description(message)
            handler.bot.send_message.assert_called()
            assert "недопустимые слова" in handler.bot.send_message.call_args[0][1]

    def test_process_vacancy_language_selection_next_empty(self, handler, message):
        """Test 'Next' with no languages selected"""
        message.text = "➡️ Далее"
        user_state = {'temp_languages': []}
        with patch('database.get_user_state', return_value=user_state):
            handler.process_vacancy_language_selection(message)
            handler.bot.send_message.assert_called()
            assert "Выберите хотя бы один язык" in handler.bot.send_message.call_args[0][1]

    def test_process_vacancy_language_custom_name_short(self, handler, message):
        """Test custom language name too short"""
        message.text = "A"
        user_state = {'step': 'vacancy_language_custom_name'}
        with patch('database.get_user_state', return_value=user_state):
            handler.process_vacancy_language_custom_name(message)
            handler.bot.send_message.assert_called()
            assert "Слишком короткое" in handler.bot.send_message.call_args[0][1]

    def test_process_edit_salary_skip(self, handler, message):
        """Test skipping salary edit with '.'"""
        message.text = "."
        user_state = {'step': 'edit_vacancy_salary', 'current_vac': {'job_type': 'Full'}}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            handler.process_edit_salary(message)
            # edit_data should not be updated with salary if skipped
            assert 'salary' not in user_state.get('edit_data', {})
            assert mock_set.call_args[0][1]['step'] == 'edit_vacancy_type'

    def test_process_edit_type_skip(self, handler, message):
        """Test skipping type edit with '.'"""
        message.text = "."
        user_state = {'step': 'edit_vacancy_type', 'vacancy_id': 1, 'edit_data': {}}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.update_vacancy') as mock_update, \
             patch('database.clear_user_state'):
            handler.process_edit_type(message)
            mock_update.assert_not_called()

    def test_process_vacancy_profession_other(self, handler, message):
        """Test 'Other' option in vacancy profession"""
        message.text = "Другое"
        user_state = {'step': 'vacancy_profession'}
        with patch('database.get_user_state', return_value=user_state), \
             patch('database.set_user_state') as mock_set:
            handler.process_vacancy_profession(message)
            assert mock_set.call_args[0][1]['step'] == 'vacancy_title'
            handler.bot.send_message.assert_called()

    def test_process_vacancy_language_selection_skip(self, handler, message):
        """Test 'Skip' in language selection"""
        message.text = "Пропустить"
        user_state = {'step': 'vacancy_language_selection', 'vacancy_data': {}}
        with patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'ask_vacancy_salary') as mock_ask:
            handler.process_vacancy_language_selection(message)
            mock_ask.assert_called()
            assert user_state['vacancy_data']['languages'] == "Не имеет значения"

    def test_process_vacancy_language_level_back(self, handler, message):
        """Test 'Back' in language level"""
        message.text = "⬅️ Назад"
        user_state = {'step': 'vacancy_language_level'}
        with patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'show_vacancy_language_selection') as mock_show:
            handler.process_vacancy_language_level(message)
            mock_show.assert_called()

    def test_process_vacancy_language_level_invalid(self, handler, message):
        """Test invalid language level"""
        message.text = "Invalid"
        user_state = {'step': 'vacancy_language_level'}
        with patch('database.get_user_state', return_value=user_state):
            handler.process_vacancy_language_level(message)
            handler.bot.send_message.assert_called()
            assert "Выберите уровень" in handler.bot.send_message.call_args[0][1]

    def test_process_edit_languages_prompt_invalid(self, handler, message):
        """Test invalid choice in edit languages prompt"""
        message.text = "Invalid"
        user_state = {'step': 'edit_vacancy_languages_prompt'}
        with patch('database.get_user_state', return_value=user_state):
            handler.process_edit_languages_prompt(message)
            handler.bot.send_message.assert_called()
            assert "Выберите действие" in handler.bot.send_message.call_args[0][1]

    def test_process_vacancy_language_custom_name_duplicate(self, handler, message):
        """Test custom language name duplicate"""
        message.text = "English"
        user_state = {'step': 'vacancy_language_custom_name', 'temp_languages': [{'name': 'English', 'level': 'B2'}]}
        with patch('database.get_user_state', return_value=user_state), \
             patch.object(handler, 'show_vacancy_language_selection') as mock_show:
            handler.process_vacancy_language_custom_name(message)
            handler.bot.send_message.assert_called()
            assert "уже добавлен" in handler.bot.send_message.call_args[0][1]
            mock_show.assert_called()

    def test_process_candidate_filter_choice_back(self, handler, message):
        """Test back button in candidate filter"""
        message.text = "⬅️ Назад"
        handler.process_candidate_filter_choice(message)
        handler.bot.send_message.assert_called()
        assert "Главное меню" in handler.bot.send_message.call_args[0][1]

    def test_handle_invitation_callback_exception(self, handler, call):
        """Test exception in invitation callback"""
        call.data = "invite_1_2"
        with patch('database.get_user_by_id', side_effect=Exception("DB Error")):
            handler.handle_invitation_callback(call)
            handler.bot.answer_callback_query.assert_called_with(call.id, "❌ Произошла системная ошибка.")
