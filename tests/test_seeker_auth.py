from unittest.mock import MagicMock, patch

import pytest

from handlers.auth.seeker_auth import SeekerAuth


class TestSeekerAuth:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return SeekerAuth(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        return msg

    def test_process_seeker_phone_valid(self, handler, message):
        """Ввод корректного телефона"""
        message.text = "901234567"
        with patch(
            "database.get_user_state",
            return_value={"step": "phone", "registration_data": {}},
        ), patch("utils.is_valid_uzbek_phone", return_value=True), patch(
            "utils.format_phone", return_value="+998901234567"
        ), patch(
            "database.execute_query", return_value=None
        ), patch(
            "database.set_user_state"
        ) as mock_set:

            handler.process_seeker_phone(message)

            mock_set.assert_called()
            # Проверяем переход на следующий шаг
            assert mock_set.call_args[0][1]["step"] == "email"
            assert (
                mock_set.call_args[0][1]["registration_data"]["phone"]
                == "+998901234567"
            )

    def test_process_seeker_phone_duplicate(self, handler, message):
        """Ввод уже зарегистрированного телефона"""
        message.text = "901234567"
        with patch("database.get_user_state", return_value={"step": "phone"}), patch(
            "utils.is_valid_uzbek_phone", return_value=True
        ), patch("utils.format_phone", return_value="+998901234567"), patch(
            "database.execute_query", return_value={"id": 1}
        ), patch(
            "logging.warning"
        ) as mock_log:  # Нашли дубликат

            handler.process_seeker_phone(message)

            handler.bot.send_message.assert_called()
            assert "уже зарегестрирован" in handler.bot.send_message.call_args[0][1]
            mock_log.assert_called()  # Проверяем вызов logging

    def test_process_seeker_phone_invalid(self, handler, message):
        """Test invalid phone number input."""
        message.text = "123"
        user_state = {"step": "phone"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "utils.is_valid_uzbek_phone", return_value=False
        ):
            handler.process_seeker_phone(message)
            handler.bot.send_message.assert_called()
            assert "Неверный формат номера" in handler.bot.send_message.call_args[0][1]

    def test_process_seeker_email_invalid(self, handler, message):
        """Test invalid email input."""
        message.text = "invalid-email"
        user_state = {"step": "email"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "utils.is_valid_email", return_value=False
        ):
            handler.process_seeker_email(message)
            handler.bot.send_message.assert_called()
            assert "Неверный формат email" in handler.bot.send_message.call_args[0][1]

    def test_process_seeker_email_valid(self, handler, message):
        """Ввод корректного email"""
        message.text = "test@test.uz"
        with patch(
            "database.get_user_state",
            return_value={"step": "email", "registration_data": {}},
        ), patch("utils.is_valid_email", return_value=True), patch(
            "database.execute_query", return_value=None
        ), patch(
            "utils.generate_random_string", return_value="pass"
        ), patch(
            "database.set_user_state"
        ) as mock_set:

            handler.process_seeker_email(message)

            assert mock_set.call_args[0][1]["step"] == "full_name"
            assert (
                mock_set.call_args[0][1]["registration_data"]["email"] == "test@test.uz"
            )

    def test_process_seeker_name_invalid(self, handler, message):
        """Ввод невалидного имени (слишком короткое)"""
        message.text = "A"
        with patch(
            "database.get_user_state",
            return_value={"step": "full_name", "registration_data": {}},
        ), patch("utils.validate_name", return_value=(False, "❌ Слишком короткое")):

            handler.process_seeker_name(message)

            handler.bot.send_message.assert_called_with(
                message.chat.id, "❌ Слишком короткое"
            )

    def test_process_seeker_name(self, handler, message, test_db):
        """Ввод имени"""
        message.text = "John Doe"
        with patch(
            "database.get_user_state",
            return_value={"step": "full_name", "registration_data": {}},
        ), patch("database.set_user_state") as mock_set:

            handler.process_seeker_name(message)

            assert mock_set.call_args[0][1]["step"] == "gender"
            assert (
                mock_set.call_args[0][1]["registration_data"]["full_name"] == "John Doe"
            )

    def test_process_seeker_region_valid(self, handler, message):
        """Выбор региона"""
        message.text = "Ташкентская обл."
        with patch(
            "database.get_user_state",
            return_value={"step": "region", "registration_data": {}},
        ), patch("database.set_user_state") as mock_set:

            handler.process_seeker_region(message)

            assert mock_set.call_args[0][1]["step"] == "city_selection"
            assert (
                mock_set.call_args[0][1]["registration_data"]["region"]
                == "Ташкентская обл."
            )

    def test_process_seeker_city_selection(self, handler, message):
        """Выбор города"""
        message.text = "Ташкент"
        user_state = {
            "step": "city_selection",
            "registration_data": {"region": "Ташкентская обл."},
        }
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:

            handler.process_seeker_city_selection(message)

            mock_set.assert_called_once()
            assert mock_set.call_args[0][1]["step"] == "age"
            assert mock_set.call_args[0][1]["registration_data"]["city"] == "Ташкент"

    def test_process_seeker_city_back(self, handler, message):
        """Test going back from city selection to region selection."""
        message.text = "⬅️ Назад"
        user_state = {"step": "city_selection"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:
            handler.process_seeker_city_selection(message)
            mock_set.assert_called()
            assert mock_set.call_args[0][1]["step"] == "region"
            handler.bot.send_message.assert_called()
            assert (
                "Выберите вашу область/регион"
                in handler.bot.send_message.call_args[0][1]
            )

    def test_finish_seeker_registration_success(self, handler, message):
        """Успешное завершение регистрации"""
        message.text = "25"
        reg_data = {"phone": "1", "email": "2", "full_name": "3"}

        with patch(
            "database.get_user_state",
            return_value={"step": "age", "registration_data": reg_data},
        ), patch("database.get_user_by_id", return_value=None), patch(
            "database.create_job_seeker", return_value=True
        ), patch(
            "database.clear_user_state"
        ), patch(
            "handlers.profile.ProfileHandlers.start_profile_setup"
        ) as mock_profile:

            handler.finish_seeker_registration(message)

            # Проверяем очистку состояния
            # mock_clear.assert_called_with(456)
            # Проверяем запуск настройки профиля
            mock_profile.assert_called()

    @pytest.mark.parametrize("age_input", ["15", "101", "abc"])
    def test_finish_seeker_registration_invalid_age(self, handler, message, age_input):
        """Test invalid age input on final registration step."""
        message.text = age_input
        user_state = {"step": "age"}
        with patch("database.get_user_state", return_value=user_state):
            handler.finish_seeker_registration(message)
            handler.bot.send_message.assert_called()
            assert (
                "Введите возраст от 16 до 100 лет"
                in handler.bot.send_message.call_args[0][1]
            )

    def test_finish_seeker_registration_db_fail(self, handler, message):
        """Test database failure on final seeker creation."""
        message.text = "25"
        reg_data = {"phone": "1", "email": "2", "full_name": "3"}
        user_state = {"step": "age", "registration_data": reg_data}

        with patch("database.get_user_state", return_value=user_state), patch(
            "database.get_user_by_id", return_value=None
        ), patch(
            "database.create_job_seeker", return_value=False
        ):  # Simulate DB failure

            handler.finish_seeker_registration(message)
            handler.bot.send_message.assert_called()
            assert "Ошибка регистрации" in handler.bot.send_message.call_args[0][1]

    def test_process_seeker_phone_duplicate_employer(self, handler, message):
        """Ввод телефона, который уже есть у работодателя"""
        message.text = "901234567"
        with patch("database.get_user_state", return_value={"step": "phone"}), patch(
            "utils.is_valid_uzbek_phone", return_value=True
        ), patch("utils.format_phone", return_value="+998901234567"), patch(
            "database.execute_query"
        ) as mock_query:

            # Первый вызов (соискатели) -> None, Второй (работодатели) -> ID
            mock_query.side_effect = [None, {"id": 1}]

            handler.process_seeker_phone(message)

            handler.bot.send_message.assert_called()
            assert "уже зарегестрирован" in handler.bot.send_message.call_args[0][1]

    def test_process_seeker_email_duplicate(self, handler, message):
        """Ввод email, который уже есть"""
        message.text = "dup@test.uz"
        with patch("database.get_user_state", return_value={"step": "email"}), patch(
            "utils.is_valid_email", return_value=True
        ), patch("database.execute_query", return_value={"id": 1}):

            handler.process_seeker_email(message)

            handler.bot.send_message.assert_called()
            assert "уже зарегистрирован" in handler.bot.send_message.call_args[0][1]

    def test_finish_seeker_registration_already_registered(self, handler, message):
        """Попытка завершения регистрации, если пользователь уже существует"""
        message.text = "25"
        with patch("database.get_user_state", return_value={"step": "age"}), patch(
            "database.get_user_by_id", return_value={"id": 1}
        ), patch("database.clear_user_state") as mock_clear:

            handler.finish_seeker_registration(message)

            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Вы уже зарегистрированы" in handler.bot.send_message.call_args[0][1]

    def test_cancel_seeker_registration_call(self, handler, message):
        """Прямой тест вызова отмены регистрации соискателя"""
        with patch("database.clear_user_state") as mock_clear:
            handler.cancel_seeker_registration(
                message.chat.id, message.from_user.id, "Тестовая отмена"
            )
            mock_clear.assert_called_with(message.from_user.id)
            handler.bot.send_message.assert_called()
            assert "Тестовая отмена" in handler.bot.send_message.call_args[0][1]

    def test_process_seeker_steps_session_expired(self, handler, message):
        """Тест истечения сессии на разных шагах"""
        steps = [
            ("process_seeker_phone", "phone"),
            ("process_seeker_email", "email"),
            ("process_seeker_name", "full_name"),
            ("process_seeker_region", "region"),
            ("process_seeker_city_selection", "city_selection"),
            ("finish_seeker_registration", "age"),
        ]

        with patch("keyboards.main_menu") as mock_menu:
            mock_kb = MagicMock()
            mock_menu.return_value = mock_kb

            for method_name, expected_step in steps:
                with patch(
                    "database.get_user_state", return_value={"step": "wrong_step"}
                ):
                    method = getattr(handler, method_name)
                    method(message)
                    handler.bot.send_message.assert_called_with(
                        message.chat.id, "❌ Сессия истекла!", reply_markup=mock_kb
                    )

    def test_process_seeker_steps_cancel(self, handler, message):
        """Тест отмены на разных шагах"""
        steps = [
            ("process_seeker_phone", "phone"),
            ("process_seeker_email", "email"),
            ("process_seeker_name", "full_name"),
            ("process_seeker_region", "region"),
            ("process_seeker_city_selection", "city_selection"),
            ("finish_seeker_registration", "age"),
        ]

        message.text = "❌ Отмена"

        with patch("utils.cancel_request", return_value=True), patch.object(
            handler, "cancel_seeker_registration"
        ) as mock_cancel:

            for method_name, step in steps:
                with patch("database.get_user_state", return_value={"step": step}):
                    method = getattr(handler, method_name)
                    method(message)
                    mock_cancel.assert_called_with(
                        message.chat.id, message.from_user.id, "Регистрация отменена"
                    )
                    mock_cancel.reset_mock()

    def test_process_seeker_region_invalid(self, handler, message):
        """Тест выбора невалидного региона"""
        message.text = "Invalid Region"
        with patch("database.get_user_state", return_value={"step": "region"}), patch(
            "utils.cancel_request", return_value=False
        ):

            handler.process_seeker_region(message)

            handler.bot.send_message.assert_called_with(
                message.chat.id,
                "❌ Пожалуйста, выберите вариант из списка:",
                reply_markup=None,
            )

    def test_process_seeker_email_duplicate_employer(self, handler, message):
        """Ввод email, который уже есть у работодателя"""
        message.text = "dup@test.uz"
        with patch("database.get_user_state", return_value={"step": "email"}), patch(
            "utils.is_valid_email", return_value=True
        ), patch("database.execute_query") as mock_query:

            # Первый вызов (соискатели) -> None, Второй (работодатели) -> ID
            mock_query.side_effect = [None, {"id": 1}]

            handler.process_seeker_email(message)

            handler.bot.send_message.assert_called()
            assert "уже зарегистрирован" in handler.bot.send_message.call_args[0][1]

    def test_process_seeker_city_invalid(self, handler, message):
        """Тест выбора невалидного города"""
        message.text = "Invalid City"
        user_state = {
            "step": "city_selection",
            "registration_data": {"region": "Ташкентская обл."},
        }
        with patch("database.get_user_state", return_value=user_state), patch(
            "utils.cancel_request", return_value=False
        ):

            handler.process_seeker_city_selection(message)

            handler.bot.send_message.assert_called()
            assert (
                "выберите вариант" in handler.bot.send_message.call_args[0][1].lower()
            )

    def test_process_seeker_city_selection_cancel(self, handler, message):
        """Test cancel in city selection"""
        message.text = "❌ Отмена"
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value={"step": "city_selection"}
        ), patch.object(handler, "cancel_seeker_registration") as mock_cancel:

            handler.process_seeker_city_selection(message)
            mock_cancel.assert_called_once()

    def test_process_seeker_region_cancel(self, handler, message):
        """Test cancel in region selection"""
        message.text = "❌ Отмена"
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value={"step": "region"}
        ), patch.object(handler, "cancel_seeker_registration") as mock_cancel:

            handler.process_seeker_region(message)
            mock_cancel.assert_called_once()
