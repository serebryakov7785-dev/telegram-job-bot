from unittest.mock import MagicMock, patch

import pytest

import keyboards  # noqa: F401
from handlers.auth.employer_auth import EmployerAuth


class TestEmployerAuth:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return EmployerAuth(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        return msg

    def test_process_employer_name_valid(self, handler, message, test_db):
        """Ввод корректного названия компании"""
        message.text = "Tech Corp"
        with patch(
            "database.get_user_state",
            return_value={"step": "company_name", "registration_data": {}},
        ), patch("database.set_user_state") as mock_set:

            handler.process_employer_name(message)

            mock_set.assert_called()
            assert mock_set.call_args[0][1]["step"] == "phone"
            assert (
                mock_set.call_args[0][1]["registration_data"]["company_name"]
                == "Tech Corp"
            )

    def test_process_employer_name_invalid(self, handler, message):
        """Test invalid (too short) company name."""
        message.text = "A"
        user_state = {"step": "company_name"}
        with patch("database.get_user_state", return_value=user_state):
            handler.process_employer_name(message)
            handler.bot.send_message.assert_called()
            assert (
                "Название компании слишком короткое"
                in handler.bot.send_message.call_args[0][1]
            )

    def test_process_employer_name_cancel(self, handler, message):
        """Test cancellation at company name step."""
        message.text = "отмена"
        user_state = {"step": "company_name"}
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value=user_state
        ), patch.object(handler, "cancel_employer_registration") as mock_cancel:
            handler.process_employer_name(message)
            mock_cancel.assert_called_once()

    def test_process_employer_phone_valid(self, handler, message):
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

            handler.process_employer_phone(message)

            assert mock_set.call_args[0][1]["step"] == "email"
            assert (
                mock_set.call_args[0][1]["registration_data"]["phone"]
                == "+998901234567"
            )

    def test_process_employer_email_invalid(self, handler, message):
        """Test invalid email format."""
        message.text = "invalid-email"
        user_state = {"step": "email"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "utils.is_valid_email", return_value=False
        ):
            handler.process_employer_email(message)
            handler.bot.send_message.assert_called()
            assert "Неверный формат email" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_phone_invalid(self, handler, message):
        """Test invalid phone number input."""
        message.text = "123"
        user_state = {"step": "phone"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "utils.is_valid_uzbek_phone", return_value=False
        ):
            handler.process_employer_phone(message)
            handler.bot.send_message.assert_called()
            assert "Неверный формат номера" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_email_valid(self, handler, message):
        """Ввод корректного email"""
        message.text = "corp@test.uz"
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

            handler.process_employer_email(message)

            assert mock_set.call_args[0][1]["step"] == "contact_person"
            assert (
                mock_set.call_args[0][1]["registration_data"]["email"] == "corp@test.uz"
            )

    def test_process_employer_email_duplicate(self, handler, message):
        """Test duplicate email input."""
        message.text = "duplicate@test.com"
        user_state = {"step": "email"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "utils.is_valid_email", return_value=True
        ), patch(
            "database.execute_query", return_value={"id": 1}
        ):  # Simulate finding a duplicate
            handler.process_employer_email(message)
            handler.bot.send_message.assert_called()
            assert "уже зарегестрирован" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_contact(self, handler, message):
        """Ввод контактного лица"""
        message.text = "Director"
        with patch(
            "database.get_user_state",
            return_value={"step": "contact_person", "registration_data": {}},
        ), patch("database.set_user_state") as mock_set:

            handler.process_employer_contact(message)

            assert mock_set.call_args[0][1]["step"] == "region"
            assert (
                mock_set.call_args[0][1]["registration_data"]["contact_person"]
                == "Director"
            )

    def test_process_employer_contact_cancel(self, handler, message):
        """Test cancellation at contact person step."""
        message.text = "отмена"
        user_state = {"step": "contact_person"}
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value=user_state
        ), patch.object(handler, "cancel_employer_registration") as mock_cancel:
            handler.process_employer_contact(message)
            mock_cancel.assert_called_once()

    def test_process_employer_region_invalid(self, handler, message):
        """Test invalid region selection."""
        message.text = "Invalid Region"
        user_state = {"step": "region"}
        with patch("database.get_user_state", return_value=user_state):
            handler.process_employer_region(message)
            handler.bot.send_message.assert_called_with(
                message.chat.id,
                "❌ Пожалуйста, выберите вариант из списка:",
                reply_markup=None,
            )

    def test_process_employer_city_back(self, handler, message):
        """Test going back from city selection to region selection."""
        message.text = "⬅️ Назад"
        user_state = {"step": "city_selection"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:

            handler.process_employer_city_selection(message)

            mock_set.assert_called()
            assert mock_set.call_args[0][1]["step"] == "region"
            handler.bot.send_message.assert_called()
            assert "Выберите область/регион" in handler.bot.send_message.call_args[0][1]

    def test_process_business_activity_success(self, handler, message, test_db):
        """Успешное завершение регистрации работодателя"""
        message.text = "IT"
        reg_data = {
            "company_name": "C",
            "phone": "1",
            "email": "2",
            "contact_person": "P",
            "region": "R",
            "city": "Ci",
        }

        with patch(
            "database.get_user_state",
            return_value={"step": "business_activity", "registration_data": reg_data},
        ), patch("database.get_user_by_id", return_value=None), patch(
            "database.create_employer", return_value=True
        ), patch(
            "database.clear_user_state"
        ) as mock_clear:

            handler.process_business_activity(message)

            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert (
                "Регистрация компании завершена"
                in handler.bot.send_message.call_args[0][1]
            )

    def test_process_business_activity_invalid(self, handler, message):
        """Test invalid (too short) business activity."""
        message.text = "A"
        user_state = {"step": "business_activity_custom", "registration_data": {}}
        with patch("database.get_user_state", return_value=user_state):
            handler.process_business_activity(message)
            handler.bot.send_message.assert_called()
            assert (
                "Род деятельности слишком короткий"
                in handler.bot.send_message.call_args[0][1]
            )

    def test_process_business_activity_db_fail(self, handler, message):
        """Test database failure on final employer creation."""
        message.text = "IT"
        reg_data = {
            "company_name": "C",
            "phone": "1",
            "email": "2",
            "contact_person": "P",
            "region": "R",
            "city": "Ci",
        }
        user_state = {"step": "business_activity", "registration_data": reg_data}

        with patch("database.get_user_state", return_value=user_state), patch(
            "database.get_user_by_id", return_value=None
        ), patch(
            "database.create_employer", return_value=False
        ):  # Simulate DB failure

            handler.process_business_activity(message)
            handler.bot.send_message.assert_called()
            assert "Ошибка регистрации" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_phone_duplicate_seeker(self, handler, message):
        """Ввод телефона, который уже есть у соискателя"""
        message.text = "901234567"
        with patch("database.get_user_state", return_value={"step": "phone"}), patch(
            "utils.is_valid_uzbek_phone", return_value=True
        ), patch("utils.format_phone", return_value="+998901234567"), patch(
            "database.execute_query"
        ) as mock_query:

            # Первый вызов (работодатели) -> None, Второй (соискатели) -> ID
            mock_query.side_effect = [None, {"id": 1}]
            # mock_query.return_value = {'id': 1}

            handler.process_employer_phone(message)

            # Check if the error message is sent or not
            # You can modify this part based on your test case
            # assert "уже зарегестрирован" in mock_send.call_args[0][1]
            handler.bot.send_message.assert_called()
            assert "уже зарегестрирован" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_email_duplicate_seeker(self, handler, message):
        """Ввод email, который уже есть у соискателя"""
        message.text = "dup@test.uz"
        with patch("database.get_user_state", return_value={"step": "email"}), patch(
            "utils.is_valid_email", return_value=True
        ), patch("database.execute_query") as mock_query:

            mock_query.side_effect = [None, {"id": 1}]

            handler.process_employer_email(message)

            handler.bot.send_message.assert_called()
            assert "уже зарегестрирован" in handler.bot.send_message.call_args[0][1]

    def test_process_business_activity_already_registered(self, handler, message):
        """Попытка завершения регистрации, если пользователь уже существует"""
        message.text = "IT"
        with patch(
            "database.get_user_state", return_value={"step": "business_activity"}
        ), patch("database.get_user_by_id", return_value={"id": 1}), patch(
            "database.clear_user_state"
        ) as mock_clear:

            handler.process_business_activity(message)

            mock_clear.assert_called_with(456)
            handler.bot.send_message.assert_called()
            assert "Вы уже зарегистрированы" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_steps_session_expired(self, handler, message):
        """Тест истечения сессии на разных шагах"""
        steps = [
            ("process_employer_name", "company_name"),
            ("process_employer_phone", "phone"),
            ("process_employer_email", "email"),
            ("process_employer_contact", "contact_person"),
            ("process_employer_region", "region"),
            ("process_employer_city_selection", "city_selection"),  # noqa
            ("process_business_activity", "business_activity"),
        ]

        with patch("keyboards.main_menu") as mock_menu:
            mock_kb = MagicMock()
            mock_menu.return_value = mock_kb

            for method_name, expected_step in steps:
                # Имитируем состояние с НЕПРАВИЛЬНЫМ шагом
                with patch(
                    "database.get_user_state", return_value={"step": "wrong_step"}
                ):
                    method = getattr(handler, method_name)
                    method(message)
                    handler.bot.send_message.assert_called_with(
                        message.chat.id, "❌ Сессия истекла!", reply_markup=mock_kb
                    )

    def test_process_employer_region_cancel(self, handler, message):
        """Отмена на шаге выбора региона"""
        message.text = "❌ Отмена"
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value={"step": "region"}
        ), patch.object(handler, "cancel_employer_registration") as mock_cancel:

            handler.process_employer_region(message)
            mock_cancel.assert_called_once()

    def test_process_employer_city_cancel(self, handler, message):
        """Отмена на шаге выбора города"""
        message.text = "❌ Отмена"
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value={"step": "city_selection"}
        ), patch.object(handler, "cancel_employer_registration") as mock_cancel:

            handler.process_employer_city_selection(message)
            mock_cancel.assert_called_once()

    def test_process_employer_phone_cancel(self, handler, message):
        """Отмена на шаге телефона"""
        message.text = "❌ Отмена"
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value={"step": "phone"}
        ), patch.object(handler, "cancel_employer_registration") as mock_cancel:
            handler.process_employer_phone(message)
            mock_cancel.assert_called_once()

    def test_process_employer_email_cancel(self, handler, message):
        """Отмена на шаге email"""
        message.text = "❌ Отмена"
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value={"step": "email"}
        ), patch.object(handler, "cancel_employer_registration") as mock_cancel:
            handler.process_employer_email(message)
            mock_cancel.assert_called_once()

    def test_process_business_activity_cancel(self, handler, message):
        """Отмена на шаге деятельности"""
        message.text = "❌ Отмена"
        with patch("utils.cancel_request", return_value=True), patch(
            "database.get_user_state", return_value={"step": "business_activity"}
        ), patch.object(handler, "cancel_employer_registration") as mock_cancel:
            handler.process_business_activity(message)
            mock_cancel.assert_called_once()
