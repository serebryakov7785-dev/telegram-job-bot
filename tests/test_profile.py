from unittest.mock import MagicMock, patch

import pytest

import keyboards
from handlers.profile import ProfileHandlers


class TestProfileHandlers:
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

    def test_start_profile_setup_seeker(self, handler, message):
        """Начало заполнения профиля соискателя"""
        user_data = {"full_name": "John"}
        with patch("database.set_user_state") as mock_set:
            handler.start_profile_setup(message, user_data)

            mock_set.assert_called()
            assert mock_set.call_args[0][1]["step"] == "education"
            assert mock_set.call_args[0][1]["role"] == "seeker"
            handler.bot.send_message.assert_called()
            assert "Регистрация завершена" in handler.bot.send_message.call_args[0][1]

    def test_start_profile_setup_employer(self, handler, message):
        """Начало заполнения профиля работодателя (сразу в меню)"""
        user_data = {"company_name": "Corp Inc.", "telegram_id": 456}
        with patch("database.clear_user_state") as mock_clear:
            handler.start_profile_setup(message, user_data)
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert (
                "Регистрация компании завершена"
                in handler.bot.send_message.call_args[0][1]
            )

    def test_process_profession_specific_success(self, handler, message):
        """Ввод профессии"""
        message.text = "Developer"
        user_state = {
            "step": "profession_specific",
            "role": "seeker",
            "profile_data": {},
        }

        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:

            handler.process_profession_specific(message)

            assert user_state["profile_data"]["profession"] == "Developer"  # type: ignore
            assert user_state["step"] == "language_selection"
            mock_set.assert_called_with(456, user_state)

    def test_process_profession_specific_cancel(self, handler, message):
        """Отмена на шаге ввода профессии"""
        message.text = "отмена"
        user_state = {
            "step": "profession_specific",
            "role": "seeker",
            "profile_data": {},
        }
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value=user_state
        ), patch.object(handler, "finish_profile_setup") as mock_finish:
            handler.process_profession_specific(message)
            mock_finish.assert_called_once_with(
                message.chat.id, message.from_user.id, user_state, show_summary=False
            )

    def test_process_profession_specific_invalid(self, handler, message):
        """Ввод невалидной профессии"""
        message.text = "A"
        user_state = {"step": "profession_specific"}
        with patch("database.get_user_state", return_value=user_state):
            handler.process_profession_specific(message)
            handler.bot.send_message.assert_called()
            assert (
                "Слишком короткое название" in handler.bot.send_message.call_args[0][1]
            )

    def test_process_step_expired_session(self, handler, message):
        """Тест обработки шага с истекшей сессией (неверный step)"""
        message.text = "Some text"
        # Устанавливаем неверный шаг, чтобы имитировать истекшую сессию
        user_state = {"step": "wrong_step"}
        with patch("database.get_user_state", return_value=user_state):
            handler.process_education(message)  # Вызываем любой обработчик шага

            # Проверяем, что send_message был вызван
            handler.bot.send_message.assert_called_once()

            # Получаем аргументы вызова
            args, kwargs = handler.bot.send_message.call_args

            # Проверяем текст и chat_id
            assert args == (message.chat.id, "❌ Сессия истекла!")
            # Проверяем, что была передана правильная клавиатура, сравнивая их JSON-представления
            assert "reply_markup" in kwargs
            assert kwargs["reply_markup"].to_json() == keyboards.main_menu().to_json()

    def test_process_education_success(self, handler, message):
        """Ввод образования"""
        message.text = "Higher"
        user_state = {"step": "education", "role": "seeker", "profile_data": {}}

        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:

            handler.process_education(message)

            assert user_state["profile_data"]["education"] == "Higher"  # type: ignore
            assert user_state["step"] == "profession_sphere"
            mock_set.assert_called_with(456, user_state)

    def test_process_education_cancel(self, handler, message):
        """Отмена на шаге ввода образования"""
        message.text = "отмена"
        user_state = {"step": "education", "role": "seeker", "profile_data": {}}
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value=user_state
        ), patch.object(handler, "finish_profile_setup") as mock_finish:
            handler.process_education(message)
            mock_finish.assert_called_once_with(
                message.chat.id, message.from_user.id, user_state, show_summary=False
            )

    def test_process_education_invalid(self, handler, message):
        """Ввод невалидного образования"""
        message.text = "A"
        user_state = {"step": "education"}
        with patch("database.get_user_state", return_value=user_state):
            handler.process_education(message)
            assert (
                "Слишком короткое описание" in handler.bot.send_message.call_args[0][1]
            )

    def test_process_language_selection_success(self, handler, message):
        """Ввод языков"""
        message.text = "➡️ Далее"
        user_state = {
            "step": "language_selection",
            "role": "seeker",
            "profile_data": {},
            "temp_languages": [{"name": "Русский", "level": "Свободный"}],
        }
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:

            handler.process_language_selection(message)

            expected_json = (
                '[{"name": "\\u0420\\u0443\\u0441\\u0441\\u043a\\u0438\\u0439", '
                '"level": "\\u0421\\u0432\\u043e\\u0431\\u043e\\u0434\\u043d\\u044b\\u0439"}]'
            )
            assert user_state["profile_data"]["languages"] == expected_json  # type: ignore
            assert user_state["step"] == "experience"
            mock_set.assert_called_with(456, user_state)

    def test_process_language_selection_invalid(self, handler, message):
        """Ввод невалидных языков"""
        message.text = "Невалидный язык"
        user_state = {"step": "language_selection", "temp_languages": []}
        with patch("database.get_user_state", return_value=user_state):

            handler.process_language_selection(message)

            assert (
                "Пожалуйста, используйте кнопки меню"
                in handler.bot.send_message.call_args[0][1]
            )

    def test_process_experience_success(self, handler, message):
        """Ввод опыта"""
        message.text = "5 years"
        user_state = {"step": "experience", "role": "seeker", "profile_data": {}}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:
            handler.process_experience(message)
            assert user_state["profile_data"]["experience"] == "5 years"  # type: ignore
            assert user_state["step"] == "skills"
            mock_set.assert_called_with(456, user_state)

    def test_process_experience_invalid(self, handler, message):
        """Ввод невалидного опыта"""
        message.text = "1"
        user_state = {"step": "experience"}
        with patch("database.get_user_state", return_value=user_state):
            handler.process_experience(message)
            handler.bot.send_message.assert_called()
            assert (
                "Слишком короткое описание" in handler.bot.send_message.call_args[0][1]
            )

    def test_process_skills_success(self, handler, message):
        """Ввод навыков и завершение"""
        message.text = "Python, SQL"
        user_state = {"step": "skills", "role": "seeker", "profile_data": {}}

        with patch("database.get_user_state", return_value=user_state), patch(
            "database.update_seeker_profile", return_value=True
        ), patch("database.clear_user_state") as mock_clear:

            handler.process_skills(message)

            assert user_state["profile_data"]["skills"] == "Python, SQL"  # type: ignore
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert (
                "Профиль успешно заполнен" in handler.bot.send_message.call_args[0][1]
            )

    def test_process_skills_cancel(self, handler, message):
        """Отмена на шаге ввода навыков"""
        message.text = "отмена"
        user_state = {"step": "skills", "role": "seeker", "profile_data": {}}
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value=user_state
        ), patch.object(handler, "finish_profile_setup") as mock_finish:
            handler.process_skills(message)
            mock_finish.assert_called_once_with(
                message.chat.id, message.from_user.id, user_state, show_summary=False
            )

    def test_process_skills_invalid(self, handler, message):
        """Ввод невалидных навыков"""
        message.text = "A"
        user_state = {"step": "skills"}
        with patch("database.get_user_state", return_value=user_state):
            handler.process_skills(message)
            handler.bot.send_message.assert_called()
            assert (
                "Слишком короткое описание" in handler.bot.send_message.call_args[0][1]
            )

    def test_process_skills_too_long(self, handler, message):
        """Тест ввода слишком длинного списка навыков"""
        message.text = "A" * 501
        user_state = {"step": "skills"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "handlers.profile.get_text_by_lang", side_effect=lambda key, lang: key
        ):
            handler.process_skills(message)
            handler.bot.send_message.assert_called()
            assert "skills_too_long" in handler.bot.send_message.call_args[0][1]

    def test_process_skills_db_fail(self, handler, message):
        """Тест ошибки БД при сохранении навыков"""
        message.text = "Python, SQL"
        user_state = {"step": "skills", "role": "seeker", "profile_data": {}}

        with patch("database.get_user_state", return_value=user_state), patch.object(
            handler, "save_profile_data", return_value=False
        ), patch("database.clear_user_state") as mock_clear, patch(
            "handlers.profile.get_text_by_lang", side_effect=lambda key, lang: key
        ):

            handler.process_skills(message)

            # Состояние должно быть очищено
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            # Проверяем, что отправлено сообщение об ошибке
            assert "profile_save_error" in handler.bot.send_message.call_args[0][1]

    def test_handle_complete_profile_not_logged_in(self, handler, message):
        """Попытка заполнить профиль без входа"""
        with patch("database.get_user_by_id", return_value=None):
            handler.handle_complete_profile(message)
            handler.bot.send_message.assert_called()
            assert (
                "Сначала зарегистрируйтесь" in handler.bot.send_message.call_args[0][1]
            )

    def test_handle_complete_profile_already_filled(self, handler, message):
        """Попытка заполнить уже заполненный профиль"""
        user_data = {"role": "seeker", "profession": "Dev", "skills": "Python"}
        with patch("database.get_user_by_id", return_value=user_data):
            handler.handle_complete_profile(message)
            handler.bot.send_message.assert_called()
            assert (
                "Ваш профиль уже заполнен" in handler.bot.send_message.call_args[0][1]
            )

    def test_handle_complete_profile_for_employer(self, handler, message):
        """Попытка заполнить профиль для работодателя"""
        user_data = {"role": "employer", "company_name": "Corp"}
        with patch("database.get_user_by_id", return_value=user_data):
            handler.handle_complete_profile(message)
            handler.bot.send_message.assert_called()
            assert (
                "не требует дополнительного заполнения"
                in handler.bot.send_message.call_args[0][1]
            )

    def test_finish_profile_setup_on_cancel(self, handler, message):
        """Завершение настройки при отмене (show_summary=False)"""
        user_state = {"role": "seeker", "profile_data": {}}
        with patch("database.clear_user_state") as mock_clear:
            handler.finish_profile_setup(
                message.chat.id, message.from_user.id, user_state, show_summary=False
            )
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "заполнить профиль позже" in handler.bot.send_message.call_args[0][1]

    def test_save_profile_data_for_employer(self, handler, message):
        """Тест сохранения данных профиля для работодателя"""
        user_id = message.from_user.id
        user_state = {
            "role": "employer",
            "profile_data": {
                "profession": "IT",
                "education": "Higher",
                "experience": "5 years",
            },
        }
        employer_data = {
            "id": 1,
            "company_name": "TestCo",
            "description": "Initial desc.",
        }

        with patch("database.get_user_by_id", return_value=employer_data), patch(
            "database.update_employer_profile"
        ) as mock_update:

            handler.save_profile_data(user_id, user_state)

            mock_update.assert_called_once()
            # Проверяем, что новое описание содержит данные из профиля
            updated_description = mock_update.call_args[1]["description"]
            assert "Initial desc." in updated_description
            assert "Сфера деятельности: IT" in updated_description
            assert "Требования к образованию: Higher" in updated_description
            assert "Требования к опыту: 5 years" in updated_description

    def test_save_profile_data_seeker_fails(self, handler, message):
        """Тест ошибки сохранения данных профиля соискателя"""
        user_id = message.from_user.id
        user_state = {"role": "seeker", "profile_data": {"profession": "Test"}}

        with patch("database.update_seeker_profile", return_value=False) as mock_update:
            handler.save_profile_data(user_id, user_state)
            mock_update.assert_called_once()

    def test_process_language_selection_cancel(self, handler, message):
        """Отмена на шаге языков"""
        message.text = "отмена"
        user_state = {
            "step": "language_selection",
            "role": "seeker",
            "profile_data": {},
        }
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value=user_state
        ), patch.object(handler, "finish_profile_setup") as mock_finish:
            handler.process_language_selection(message)
            mock_finish.assert_called_once()

    def test_process_experience_cancel(self, handler, message):
        """Отмена на шаге опыта"""
        message.text = "отмена"
        user_state = {"step": "experience", "role": "seeker", "profile_data": {}}
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value=user_state
        ), patch.object(handler, "finish_profile_setup") as mock_finish:
            handler.process_experience(message)
            mock_finish.assert_called_once()

    def test_finish_profile_setup_success(self, handler, message):
        """Успешное завершение настройки профиля"""
        user_state = {
            "role": "seeker",
            "profile_data": {
                "profession": "Dev",
                "education": "High",
                "languages": "En",
                "experience": "5y",
                "skills": "Py",
            },
        }
        with patch("database.clear_user_state") as mock_clear, patch.object(
            handler, "save_profile_data", return_value=True
        ):

            handler.finish_profile_setup(
                message.chat.id, message.from_user.id, user_state, show_summary=True
            )

            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert (
                "Профиль успешно заполнен" in handler.bot.send_message.call_args[0][1]
            )
            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert (
                "Профиль успешно заполнен" in handler.bot.send_message.call_args[0][1]
            )

    def test_process_profession_sphere_success(self, handler, message):
        """Тест выбора сферы деятельности"""
        message.text = "IT и Интернет"
        user_state = {"step": "profession_sphere"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:
            handler.process_profession_sphere(message)
            mock_set.assert_called()
            assert mock_set.call_args[0][1]["step"] == "profession_specific"
            handler.bot.send_message.assert_called()
            assert "Выберите профессию" in handler.bot.send_message.call_args[0][1]

    def test_process_profession_sphere_invalid(self, handler, message):
        """Тест невалидного ввода сферы деятельности (ручной ввод)"""
        message.text = "Some Sphere"
        user_state = {"step": "profession_sphere"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:
            handler.process_profession_sphere(message)
            mock_set.assert_called()
            assert mock_set.call_args[0][1]["step"] == "profession_specific"
            handler.bot.send_message.assert_called()
            assert "Введите название" in handler.bot.send_message.call_args[0][1]

    def test_process_profession_specific_back(self, handler, message):
        """Тест кнопки Назад при выборе конкретной профессии"""
        message.text = "⬅️ Назад"
        user_state = {"step": "profession_specific"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:
            handler.process_profession_specific(message)
            mock_set.assert_called()
            assert mock_set.call_args[0][1]["step"] == "profession_sphere"
            handler.bot.send_message.assert_called()
            assert "Выберите сферу" in handler.bot.send_message.call_args[0][1]

    def test_process_profession_specific_other(self, handler, message):
        """Тест выбора 'Другое' в конкретной профессии"""
        message.text = "Другое"
        user_state = {"step": "profession_specific"}
        with patch("database.get_user_state", return_value=user_state):
            handler.process_profession_specific(message)
            handler.bot.send_message.assert_called()
            assert "Введите название" in handler.bot.send_message.call_args[0][1]

    def test_process_language_selection_next_empty(self, handler, message):
        """Тест нажатия Далее без выбранных языков"""
        message.text = "➡️ Далее"
        user_state = {"step": "language_selection", "temp_languages": []}
        with patch("database.get_user_state", return_value=user_state):
            handler.process_language_selection(message)
            handler.bot.send_message.assert_called()
            assert (
                "Выберите хотя бы один язык" in handler.bot.send_message.call_args[0][1]
            )

    def test_process_language_selection_next_settings(self, handler, message):
        """Тест сохранения языков из настроек"""
        message.text = "➡️ Далее"
        user_state = {
            "step": "language_selection",
            "temp_languages": [{"name": "En", "level": "B2"}],
            "source": "settings",
        }
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.update_seeker_profile"
        ) as mock_update, patch("database.clear_user_state") as mock_clear:
            handler.process_language_selection(message)
            mock_update.assert_called()
            mock_clear.assert_called()
            handler.bot.send_message.assert_called()
            assert "Языки успешно обновлены" in handler.bot.send_message.call_args[0][1]

    def test_process_language_selection_skip_settings(self, handler, message):
        """Тест очистки языков из настроек"""
        message.text = "Пропустить"
        user_state = {
            "step": "language_selection",
            "temp_languages": [],
            "source": "settings",
        }
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.update_seeker_profile"
        ) as mock_update, patch("database.clear_user_state") as mock_clear:
            handler.process_language_selection(message)
            mock_update.assert_called()
            mock_clear.assert_called()
            handler.bot.send_message.assert_called()
            assert "Список языков очищен" in handler.bot.send_message.call_args[0][1]

    def test_process_language_selection_other(self, handler, message):
        """Тест выбора 'Другой' язык"""
        message.text = "🌐 Другой"
        user_state = {"step": "language_selection"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:
            handler.process_language_selection(message)
            mock_set.assert_called()
            assert mock_set.call_args[0][1]["step"] == "language_custom_name"
            handler.bot.send_message.assert_called()
            assert "Введите название языка" in handler.bot.send_message.call_args[0][1]

    def test_process_language_selection_valid(self, handler, message):
        """Тест выбора языка из списка"""
        message.text = "🇬🇧 Английский"
        user_state = {"step": "language_selection"}
        with patch("database.get_user_state", return_value=user_state), patch.object(
            handler, "show_level_selection"
        ) as mock_show:
            handler.process_language_selection(message)
            mock_show.assert_called()

    def test_process_language_level_no_lang(self, handler, message):
        """Тест выбора уровня без выбранного языка (ошибка состояния)"""
        message.text = "Свободный"
        user_state = {"step": "language_level"}  # нет current_lang_editing
        with patch("database.get_user_state", return_value=user_state), patch.object(
            handler, "show_language_selection"
        ) as mock_show:
            handler.process_language_level(message)
            mock_show.assert_called()

    def test_process_language_custom_name_success(self, handler, message):
        """Тест ввода кастомного языка"""
        message.text = "Немецкий"
        user_state = {"step": "language_custom_name", "temp_languages": []}
        with patch("database.get_user_state", return_value=user_state), patch.object(
            handler, "show_level_selection"
        ) as mock_show_level:
            handler.process_language_custom_name(message)
            mock_show_level.assert_called()
            # state = mock_show_level.call_args[0][2]
            # assert user_state['current_lang_editing'] == 'Немецкий'

    def test_process_language_level_success(self, handler, message):
        """Тест выбора уровня языка"""
        message.text = "Свободный"
        user_state = {
            "step": "language_level",
            "current_lang_editing": "Немецкий",
            "temp_languages": [],
        }
        with patch("database.get_user_state", return_value=user_state), patch.object(
            handler, "show_language_selection"
        ) as mock_show_selection:
            handler.process_language_level(message)
            mock_show_selection.assert_called()
            # state = mock_show_selection.call_args[0][2]
            # assert state['temp_languages'][0]['name'] == 'Немецкий'
            # assert state['temp_languages'][0]['level'] == 'Свободный'

    def test_process_language_custom_name_short(self, handler, message):
        """Тест ввода слишком короткого названия языка"""
        message.text = "A"
        user_state = {"step": "language_custom_name"}
        with patch("database.get_user_state", return_value=user_state):
            handler.process_language_custom_name(message)
            handler.bot.send_message.assert_called()
            assert "Слишком короткое" in handler.bot.send_message.call_args[0][1]

    def test_process_language_custom_name_duplicate(self, handler, message):
        """Тест ввода дубликата языка"""
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

    def test_process_language_custom_name_cancel_settings(self, handler, message):
        """Тест отмены ввода языка из настроек"""
        message.text = "❌ Отмена"
        user_state = {"step": "language_custom_name", "source": "settings"}
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value=user_state
        ), patch("database.clear_user_state") as mock_clear:
            handler.process_language_custom_name(message)
            mock_clear.assert_called()
            handler.bot.send_message.assert_called()
            assert "Изменение отменено" in handler.bot.send_message.call_args[0][1]

    def test_process_language_level_back(self, handler, message):
        """Тест кнопки Назад при выборе уровня"""
        message.text = "⬅️ Назад"
        user_state = {"step": "language_level"}
        with patch("database.get_user_state", return_value=user_state), patch.object(
            handler, "show_language_selection"
        ) as mock_show:
            handler.process_language_level(message)
            mock_show.assert_called()

    def test_process_language_level_invalid(self, handler, message):
        """Тест невалидного уровня"""
        message.text = "Invalid Level"
        user_state = {"step": "language_level"}
        with patch("database.get_user_state", return_value=user_state):
            handler.process_language_level(message)
            handler.bot.send_message.assert_called()
            assert "Выберите уровень" in handler.bot.send_message.call_args[0][1]

    def test_process_profession_sphere_other(self, handler, message):
        """Тест выбора 'Другое' в сфере деятельности"""
        message.text = "Другое"
        user_state = {"step": "profession_sphere"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:
            handler.process_profession_sphere(message)
            mock_set.assert_called()
            assert mock_set.call_args[0][1]["step"] == "profession_specific"
            handler.bot.send_message.assert_called()
            assert "Введите название" in handler.bot.send_message.call_args[0][1]
