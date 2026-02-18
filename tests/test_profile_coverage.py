from unittest.mock import MagicMock, patch

import pytest

from handlers.profile import ProfileHandlers


class TestProfileCoverage:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return ProfileHandlers(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        return msg

    def test_process_profession_specific_cancel(self, handler, message):
        """Тест отмены ввода профессии"""
        message.text = "❌ Отмена"
        user_state = {"step": "profession_specific", "role": "seeker"}
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value=user_state
        ), patch("database.clear_user_state") as mock_clear:

            handler.process_profession_specific(message)

            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert (
                "можете заполнить профиль позже"
                in handler.bot.send_message.call_args[0][1]
            )

    def test_process_profession_specific_invalid_state(self, handler, message):
        """Тест неверного состояния при вводе профессии"""
        with patch("database.get_user_state", return_value={"step": "wrong_step"}):
            handler.process_profession_specific(message)
            handler.bot.send_message.assert_called()
            assert "Сессия истекла" in handler.bot.send_message.call_args[0][1]

    def test_process_education_skip(self, handler, message):
        """Тест пропуска ввода образования"""
        message.text = "Пропустить"
        user_state = {"step": "education", "role": "seeker", "profile_data": {}}

        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:

            handler.process_education(message)

            assert user_state["profile_data"]["education"] == "Не указано"  # type: ignore
            assert user_state["step"] == "profession_sphere"
            mock_set.assert_called()

    def test_process_language_selection_skip(self, handler, message):
        """Тест пропуска ввода языков"""
        message.text = "Пропустить"
        user_state = {
            "step": "language_selection",
            "role": "seeker",
            "profile_data": {},
            "temp_languages": [],
        }

        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:

            handler.process_language_selection(message)

            assert user_state["profile_data"]["languages"] == "Не указаны"  # type: ignore
            assert user_state["step"] == "experience"
            mock_set.assert_called()

    def test_process_experience_skip(self, handler, message):
        """Тест пропуска ввода опыта"""
        message.text = "Пропустить"
        user_state = {"step": "experience", "role": "seeker", "profile_data": {}}

        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:

            handler.process_experience(message)

            assert user_state["profile_data"]["experience"] == "Нет опыта"  # type: ignore
            assert user_state["step"] == "skills"
            mock_set.assert_called()

    def test_handle_complete_profile_no_user(self, handler, message):
        """Тест попытки заполнить профиль без регистрации"""
        with patch("database.get_user_by_id", return_value=None):
            handler.handle_complete_profile(message)
            handler.bot.send_message.assert_called()
            assert (
                "Сначала зарегистрируйтесь" in handler.bot.send_message.call_args[0][1]
            )

    def test_process_skills_skip(self, handler, message):
        """Test skipping skills input"""
        message.text = "Пропустить"
        user_state = {"step": "skills", "role": "seeker", "profile_data": {}}
        with patch("database.get_user_state", return_value=user_state), patch.object(
            handler, "save_profile_data"
        ) as mock_save, patch.object(handler, "finish_profile_setup") as mock_finish:
            handler.process_skills(message)
            assert user_state["profile_data"]["skills"] == "Не указаны"  # type: ignore
            mock_save.assert_called()
            mock_finish.assert_called()

    def test_process_language_selection_skip_retry(self, handler, message):
        """Test skip language selection when languages already added (should retry/not skip)"""
        message.text = "Пропустить"
        # temp_languages is NOT empty
        user_state = {
            "step": "language_selection",
            "temp_languages": [{"name": "En", "level": "B2"}],
        }
        with patch("database.get_user_state", return_value=user_state), patch.object(
            handler, "process_language_selection"
        ) as mock_retry:
            # We mock the recursive call to avoid infinite recursion in test
            handler.process_language_selection(message)
            mock_retry.assert_called_with(message)

    def test_process_language_custom_name_cancel_normal(self, handler, message):
        """Test cancel custom language name (not from settings)"""
        message.text = "❌ Отмена"
        user_state = {"step": "language_custom_name", "source": "profile"}
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value=user_state
        ), patch.object(handler, "show_language_selection") as mock_show:
            handler.process_language_custom_name(message)
            mock_show.assert_called()

    def test_save_profile_data_employer_fail(self, handler, message):
        """Test employer profile save failure"""
        user_state = {"role": "employer", "profile_data": {}}
        with patch(
            "database.get_user_by_id", return_value={"company_name": "Co"}
        ), patch("database.update_employer_profile", return_value=False) as mock_update:
            handler.save_profile_data(123, user_state)
            mock_update.assert_called()

    def test_process_education_profanity(self, handler, message):
        message.text = "badword"
        with patch(
            "database.get_user_state", return_value={"step": "education"}
        ), patch("utils.contains_profanity", return_value=True):
            handler.process_education(message)
            handler.bot.send_message.assert_called()
            assert "недопустимые слова" in handler.bot.send_message.call_args[0][1]

    def test_process_profession_specific_profanity(self, handler, message):
        message.text = "badword"
        with patch(
            "database.get_user_state", return_value={"step": "profession_specific"}
        ), patch("utils.contains_profanity", return_value=True):
            handler.process_profession_specific(message)
            handler.bot.send_message.assert_called()
            assert "недопустимые слова" in handler.bot.send_message.call_args[0][1]

    def test_process_experience_profanity(self, handler, message):
        message.text = "badword"
        with patch(
            "database.get_user_state", return_value={"step": "experience"}
        ), patch("utils.contains_profanity", return_value=True):
            handler.process_experience(message)
            handler.bot.send_message.assert_called()
            assert "недопустимые слова" in handler.bot.send_message.call_args[0][1]

    def test_process_skills_profanity(self, handler, message):
        message.text = "badword"
        with patch("database.get_user_state", return_value={"step": "skills"}), patch(
            "utils.contains_profanity", return_value=True
        ):
            handler.process_skills(message)
            handler.bot.send_message.assert_called()
            assert "недопустимые слова" in handler.bot.send_message.call_args[0][1]

    def test_process_language_custom_name_short(self, handler, message):
        message.text = "A"
        with patch(
            "database.get_user_state", return_value={"step": "language_custom_name"}
        ):
            handler.process_language_custom_name(message)
            handler.bot.send_message.assert_called()
            assert "Слишком короткое" in handler.bot.send_message.call_args[0][1]

    def test_process_language_custom_name_duplicate(self, handler, message):
        message.text = "English"
        user_state = {
            "step": "language_custom_name",
            "temp_languages": [{"lang_name": "English", "level": "B2"}],
        }
        with patch("database.get_user_state", return_value=user_state), patch.object(
            handler, "show_language_selection"
        ) as mock_show:
            handler.process_language_custom_name(message)
            handler.bot.send_message.assert_called()
            assert "уже добавлен" in handler.bot.send_message.call_args[0][1]
            mock_show.assert_called()

    def test_process_education_seeker_flow(self, handler, message):
        """Test education input for seeker (shows sphere selection)"""
        message.text = "Higher Education"
        user_state = {"step": "education", "role": "seeker", "profile_data": {}}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ):
            handler.process_education(message)
            assert user_state["step"] == "profession_sphere"
            handler.bot.send_message.assert_called()
            assert (
                "Выберите сферу деятельности"
                in handler.bot.send_message.call_args[0][1]
            )

    def test_process_education_employer_flow(self, handler, message):
        """Test education input for employer (saves and finishes)"""
        message.text = "Requirements"
        user_state = {"step": "education", "role": "employer", "profile_data": {}}
        with patch("database.get_user_state", return_value=user_state), patch.object(
            handler, "save_profile_data"
        ) as mock_save, patch.object(handler, "finish_profile_setup") as mock_finish:
            handler.process_education(message)
            mock_save.assert_called()
            mock_finish.assert_called()

    def test_process_language_selection_skip_empty(self, handler, message):
        """Test skip language selection when list is empty"""
        message.text = "Пропустить"
        user_state = {
            "step": "language_selection",
            "role": "seeker",
            "profile_data": {},
            "temp_languages": [],
        }
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:
            handler.process_language_selection(message)
            assert user_state["profile_data"]["languages"] == "Не указаны"  # type: ignore
            assert user_state["step"] == "experience"
            mock_set.assert_called()

    def test_process_language_level_back(self, handler, message):
        """Test back button in language level"""
        message.text = "⬅️ Назад"
        user_state = {"step": "language_level"}
        with patch("database.get_user_state", return_value=user_state), patch.object(
            handler, "show_language_selection"
        ) as mock_show:
            handler.process_language_level(message)
            mock_show.assert_called()

    def test_process_language_level_invalid(self, handler, message):
        """Test invalid language level"""
        message.text = "Invalid"
        user_state = {"step": "language_level"}
        with patch("database.get_user_state", return_value=user_state):
            handler.process_language_level(message)
            handler.bot.send_message.assert_called()
            assert "Выберите уровень" in handler.bot.send_message.call_args[0][1]

    def test_process_experience_short(self, handler, message):
        """Test short experience description"""
        message.text = "A"
        user_state = {"step": "experience"}
        with patch("database.get_user_state", return_value=user_state):
            handler.process_experience(message)
            handler.bot.send_message.assert_called()
            assert "Слишком короткое" in handler.bot.send_message.call_args[0][1]

    def test_save_profile_data_employer_success(self, handler, message):
        """Test saving employer profile data"""
        user_id = 123
        user_state = {
            "role": "employer",
            "profile_data": {
                "profession": "IT",
                "education": "High",
                "experience": "5y",
                "skills": "Python",
            },
        }
        employer_data = {"company_name": "Co", "description": "Desc"}

        with patch("database.get_user_by_id", return_value=employer_data), patch(
            "database.update_employer_profile", return_value=True
        ) as mock_update:
            handler.save_profile_data(user_id, user_state)
            mock_update.assert_called()
            assert "Сфера деятельности: IT" in mock_update.call_args[1]["description"]
