from unittest.mock import MagicMock, patch

import pytest

from handlers.settings import SettingsHandlers


class TestSettingsCoverage:
    @pytest.fixture
    def bot(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, bot):
        return SettingsHandlers(bot)

    @pytest.fixture
    def message(self):
        msg = MagicMock()
        msg.chat.id = 123
        msg.from_user.id = 456
        msg.text = "Test"
        msg.content_type = "text"
        msg.contact = None
        return msg

    def test_handle_settings_menu_no_user(self, handler, message):
        """Test settings menu when user is not found in DB"""
        with patch("database.get_user_by_id", return_value=None):
            handler.handle_settings_menu(message)
            handler.bot.send_message.assert_called()
            assert (
                "Сначала зарегистрируйтесь" in handler.bot.send_message.call_args[0][1]
            )

    def test_handle_seeker_setting_no_user(self, handler, message):
        """Test seeker setting when user is not found"""
        with patch("database.get_user_by_id", return_value=None):
            handler.handle_seeker_setting(message, "profession")
            handler.bot.send_message.assert_called()
            assert "Сначала войдите" in handler.bot.send_message.call_args[0][1]

    def test_handle_seeker_submenu_action_expired(self, handler, message):
        """Test submenu action with expired session"""
        with patch("database.get_user_state", return_value=None):
            handler.handle_seeker_submenu_action(message)
            handler.bot.send_message.assert_called()
            assert "Сессия истекла" in handler.bot.send_message.call_args[0][1]

    def test_handle_seeker_submenu_action_unknown(self, handler, message):
        """Test unknown action in submenu"""
        message.text = "Unknown Action"
        user_state = {
            "action": "edit_seeker_field",
            "field": "f",
            "field_display": "D",
            "current_value": "V",
        }
        with patch("database.get_user_state", return_value=user_state):
            handler.handle_seeker_submenu_action(message)
            handler.bot.send_message.assert_called()
            assert "Неизвестное действие" in handler.bot.send_message.call_args[0][1]

    def test_process_seeker_field_update_expired(self, handler, message):
        """Test field update with expired session"""
        with patch(
            "handlers.settings_seeker.database.get_user_state", return_value=None
        ):
            handler.process_seeker_field_update(message)
            handler.bot.send_message.assert_called()
            assert "Сессия истекла" in handler.bot.send_message.call_args[0][1]

    def test_handle_status_settings_no_user(self, handler, message):
        """Test status settings when user is not found"""
        with patch("database.get_user_by_id", return_value=None):
            handler.handle_status_settings(message)
            handler.bot.send_message.assert_called()
            assert "Сначала войдите" in handler.bot.send_message.call_args[0][1]

    def test_handle_employer_action_no_user(self, handler, message):
        """Test employer action when user is not found"""
        with patch("database.get_user_by_id", return_value=None):
            handler.handle_employer_action(message)
            handler.bot.send_message.assert_called()
            assert "Сначала войдите" in handler.bot.send_message.call_args[0][1]

    def test_handle_employer_setting_no_user(self, handler, message):
        """Test employer setting when user is not found"""
        with patch("database.get_user_by_id", return_value=None):
            handler.handle_employer_setting(message, "company_name")
            handler.bot.send_message.assert_called()
            assert "Сначала войдите" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_field_update_expired(self, handler, message):
        """Test employer field update with expired session"""
        with patch(
            "handlers.settings_employer.database.get_user_state", return_value=None
        ):
            handler.process_employer_field_update(message)
            handler.bot.send_message.assert_called()
            assert "Сессия истекла" in handler.bot.send_message.call_args[0][1]

    def test_handle_delete_account_no_user(self, handler, message):
        """Test delete account when user is not found"""
        with patch("database.get_user_by_id", return_value=None):
            handler.handle_delete_account(message)
            handler.bot.send_message.assert_called()
            assert (
                "Сначала зарегистрируйтесь" in handler.bot.send_message.call_args[0][1]
            )

    def test_confirm_delete_account_expired(self, handler, message):
        """Test confirm delete with expired session"""
        with patch("database.get_user_state", return_value=None):
            handler.confirm_delete_account(message)
            handler.bot.send_message.assert_called()
            assert "Сессия истекла" in handler.bot.send_message.call_args[0][1]

    def test_confirm_delete_account_wrong_action(self, handler, message):
        """Test confirm delete with wrong action in state"""
        with patch("database.get_user_state", return_value={"action": "not_delete"}):
            handler.confirm_delete_account(message)
            handler.bot.send_message.assert_called()
            assert "Сессия истекла" in handler.bot.send_message.call_args[0][1]

    def test_handle_change_language(self, handler, message):
        """Test the change language handler."""
        with patch("keyboards.language_menu") as mock_keyboard, patch(
            "handlers.settings.get_text_by_lang", return_value="Select language"
        ):

            handler.handle_change_language(message)

            handler.bot.send_message.assert_called_once_with(
                message.chat.id,
                "Select language",
                reply_markup=mock_keyboard.return_value,
            )

    def test_confirm_delete_account_cancel_employer(self, handler, message):
        """Test cancelling account deletion for an employer."""
        message.text = "cancel_delete"
        user_state = {"role": "employer", "action": "delete_account"}

        with patch("database.get_user_state", return_value=user_state), patch(
            "database.clear_user_state"
        ) as mock_clear, patch(
            "handlers.settings.TRANSLATIONS", {"ru": {"cancel_delete": "cancel_delete"}}
        ), patch(
            "handlers.settings.get_text_by_lang", side_effect=lambda key, lang: key
        ), patch(
            "keyboards.employer_main_menu"
        ) as mock_keyboard:

            handler.confirm_delete_account(message)

            mock_clear.assert_called_with(message.from_user.id)
            handler.bot.send_message.assert_called_once()
            assert "delete_cancelled" in handler.bot.send_message.call_args[0][1]
            assert (
                handler.bot.send_message.call_args[1]["reply_markup"]
                == mock_keyboard.return_value
            )

    def test_handle_delete_account_employer(self, handler, message):
        """Test delete account prompt for employer."""
        user_data = {"company_name": "Test Corp"}
        with patch("database.get_user_by_id", return_value=user_data), patch(
            "database.set_user_state"
        ) as mock_set_state, patch(
            "handlers.settings.get_text_by_lang", side_effect=lambda key, lang: key
        ):

            handler.handle_delete_account(message)

            mock_set_state.assert_called()
            state = mock_set_state.call_args[0][1]
            assert state["action"] == "delete_account"
            assert state["role"] == "employer"
            assert state["name"] == "Test Corp"
            handler.bot.send_message.assert_called()
            assert "delete_account_warning" in handler.bot.send_message.call_args[0][1]

    def test_is_seeker_submenu(self, handler, message):
        """Test the _is_seeker_submenu filter function."""
        message.text = "✏️ Изменить"

        with patch(
            "database.get_user_state", return_value={"action": "edit_seeker_field"}
        ):
            assert handler._is_seeker_submenu(message) is True

        with patch(
            "database.get_user_state", return_value={"action": "some_other_action"}
        ):
            assert handler._is_seeker_submenu(message) is False

        with patch("database.get_user_state", return_value=None):
            assert not handler._is_seeker_submenu(message)

        message.text = "Не та кнопка"
        with patch(
            "database.get_user_state", return_value={"action": "edit_seeker_field"}
        ):
            assert handler._is_seeker_submenu(message) is False

    def test_handle_set_status_wrapper(self, handler, message):
        """Test the wrapper for setting seeker status."""
        message.text = "Активен"
        with patch(
            "handlers.settings.get_all_translations", return_value=["Активен"]
        ), patch.object(handler, "set_seeker_status") as mock_set_status:
            handler.handle_set_status_wrapper(message)
            mock_set_status.assert_called_once_with(message, "active")

        message.text = "Неактивен"
        with patch(
            "handlers.settings.get_all_translations",
            side_effect=lambda k: ["Неактивен"] if k == "status_inactive" else [],
        ), patch.object(handler, "set_seeker_status") as mock_set_status:
            handler.handle_set_status_wrapper(message)
            mock_set_status.assert_called_once_with(message, "inactive")

    def test_handle_seeker_settings_wrapper(self, handler, message):
        """Test the wrapper for seeker settings handlers."""
        message.text = "Профессия"
        with patch(
            "handlers.settings.get_all_translations", return_value=["Профессия"]
        ), patch.object(handler, "handle_seeker_setting") as mock_handle:
            handler.handle_seeker_settings_wrapper(message)
            mock_handle.assert_called_once_with(message, "profession")

    def test_is_seeker_setting(self, handler, message):
        """Test the _is_seeker_setting filter function."""
        with patch("handlers.settings.get_all_translations") as mock_get_all:
            mock_get_all.side_effect = lambda k: (
                ["Профессия"] if k == "btn_profession" else []
            )
            message.text = "Профессия"
            assert handler._is_seeker_setting(message) is True

            mock_get_all.side_effect = lambda k: (
                ["Профессия"] if k == "btn_profession" else []
            )
            message.text = "Неизвестная кнопка"
            assert handler._is_seeker_setting(message) is False

    def test_handle_employer_action_back(self, handler, message):
        """Test employer action: back to menu"""
        message.text = "↩️ Назад в меню"
        user_data = {"company_name": "Corp"}
        with patch("database.get_user_by_id", return_value=user_data):
            handler.handle_employer_action(message)
            handler.bot.send_message.assert_called()
            assert "Неизвестное действие" in handler.bot.send_message.call_args[0][1]

    def test_handle_employer_action_invalid(self, handler, message):
        """Test employer action: unknown action"""
        message.text = "Unknown Action"
        user_data = {"company_name": "Corp"}
        with patch("database.get_user_by_id", return_value=user_data):
            handler.handle_employer_action(message)
            handler.bot.send_message.assert_called()
            assert "Неизвестное действие" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_field_update_invalid_phone(self, handler, message):
        """Test employer field update with invalid phone"""
        message.text = "123"
        user_state = {
            "step": "enter_new_value",
            "action": "edit_employer_field",
            "field": "phone",
        }
        with patch(
            "handlers.settings_employer.database.get_user_state",
            return_value=user_state,
        ), patch("utils.is_valid_uzbek_phone", return_value=False):
            handler.process_employer_field_update(message)
            handler.bot.send_message.assert_called()
            assert "Неверный формат номера" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_field_update_invalid_email(self, handler, message):
        """Test employer field update with invalid email"""
        message.text = "bad-email"
        user_state = {
            "step": "enter_new_value",
            "action": "edit_employer_field",
            "field": "email",
        }
        with patch(
            "handlers.settings_employer.database.get_user_state",
            return_value=user_state,
        ), patch("utils.is_valid_email", return_value=False):
            handler.process_employer_field_update(message)
            handler.bot.send_message.assert_called()
            assert "Неверный формат email" in handler.bot.send_message.call_args[0][1]

    def test_handle_seeker_submenu_action_languages(self, handler, message):
        """Test submenu action for languages (special flow)"""
        message.text = "✏️ Изменить"
        user_state = {
            "action": "edit_seeker_field",
            "field": "languages",
            "field_display": "Языки",
            "current_value": "En",
        }
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:
            handler.handle_seeker_submenu_action(message)
            assert mock_set.call_args[0][1]["step"] == "language_selection"
            assert mock_set.call_args[0][1]["source"] == "settings"
            handler.bot.send_message.assert_called()

    def test_process_seeker_field_update_profanity(self, handler, message):
        message.text = "this is a badword and it is long enough"
        user_state = {
            "step": "enter_new_value",
            "field": "profession",
            "field_display": "Prof",
        }
        with patch(
            "handlers.settings_seeker.database.get_user_state", return_value=user_state
        ), patch("utils.contains_profanity", return_value=True):
            handler.process_seeker_field_update(message)
            handler.bot.send_message.assert_called()
            assert "недопустимые слова" in handler.bot.send_message.call_args[0][1]

    def test_process_employer_field_update_profanity(self, handler, message):
        message.text = "badword badword badword"
        user_state = {
            "step": "enter_new_value",
            "action": "edit_employer_field",
            "field": "company_name",
        }
        with patch(
            "handlers.settings_employer.database.get_user_state",
            return_value=user_state,
        ), patch(
            "utils.contains_profanity", return_value=True
        ):  # noqa
            handler.process_employer_field_update(message)
            handler.bot.send_message.assert_called()
            assert "недопустимые слова" in handler.bot.send_message.call_args[0][1]

    def test_process_seeker_profession_sphere_other(self, handler, message):
        message.text = "Другое"
        user_state = {"step": "edit_seeker_profession_sphere"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:
            handler.process_seeker_profession_sphere(message)
            assert mock_set.call_args[0][1]["step"] == "enter_new_value"

    def test_process_seeker_profession_specific_other(self, handler, message):
        message.text = "Другое"
        user_state = {"step": "edit_seeker_profession_specific"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:
            handler.process_seeker_profession_specific(message)
            assert mock_set.call_args[0][1]["step"] == "enter_new_value"

    def test_process_seeker_profession_sphere_other_manual(self, handler, message):
        """Test 'Other' option in profession sphere settings"""
        message.text = "Другое"
        user_state = {"step": "edit_seeker_profession_sphere"}
        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:
            handler.process_seeker_profession_sphere(message)
            assert mock_set.call_args[0][1]["step"] == "enter_new_value"
            handler.bot.send_message.assert_called()
            assert "Введите название" in handler.bot.send_message.call_args[0][1]

    def test_handle_seeker_submenu_action_gender(self, handler, message):
        """Test submenu action for gender"""
        message.text = "✏️ Изменить"
        user_state = {
            "action": "edit_seeker_field",
            "field": "gender",
            "field_display": "Пол",
            "current_value": "M",
        }

        with patch("database.get_user_state", return_value=user_state), patch(
            "database.set_user_state"
        ) as mock_set:

            handler.handle_seeker_submenu_action(message)

            mock_set.assert_called()
            assert mock_set.call_args[0][1]["step"] == "edit_seeker_gender"
            handler.bot.send_message.assert_called()

    def test_process_seeker_gender_update_invalid(self, handler, message):
        """Test invalid gender selection"""
        message.text = "Invalid Gender"
        with patch(
            "handlers.settings_seeker.get_text_by_lang", side_effect=lambda k, l: k
        ), patch("localization.get_user_language", return_value="ru"):
            handler.process_seeker_gender_update(message)
            handler.bot.send_message.assert_called()
            assert "select_from_list" in handler.bot.send_message.call_args[0][1]

    def test_process_seeker_field_update_contact(self, handler, message):
        """Test field update with contact object"""
        message.contact = MagicMock(phone_number="+998901234567")
        message.text = None
        user_state = {
            "step": "enter_new_value",
            "field": "phone",
            "field_display": "Phone",
        }

        with patch(
            "handlers.settings_seeker.database.get_user_state", return_value=user_state
        ), patch(
            "handlers.settings_seeker.database.update_seeker_profile", return_value=True
        ), patch(
            "handlers.settings_seeker.database.clear_user_state"
        ) as mock_clear, patch(
            "utils.is_valid_uzbek_phone", return_value=True
        ), patch(
            "utils.format_phone", return_value="+998901234567"
        ):

            handler.process_seeker_field_update(message)

            mock_clear.assert_called()
            handler.bot.send_message.assert_called()
            assert "успешно обновлено" in handler.bot.send_message.call_args[0][1]

    def test_handle_seeker_setting_as_employer(self, handler, message):
        """Test accessing seeker setting as employer (should fail)"""
        # User exists but has no full_name (so it's an employer)
        user_data = {"company_name": "Corp", "id": 1}
        with patch("database.get_user_by_id", return_value=user_data):
            handler.handle_seeker_setting(message, "profession")
            handler.bot.send_message.assert_called()
            assert (
                "Сначала войдите как соискатель"
                in handler.bot.send_message.call_args[0][1]
            )
