import os
import sys
from unittest.mock import patch

import pytest

import keyboards

# Add project root to path;
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestKeyboards:
    @pytest.fixture(autouse=True)
    def mock_get_text(self):
        # Мокаем локализацию, чтобы она возвращала ключ для удобства тестирования
        with patch("keyboards.get_text_by_lang", side_effect=lambda key, lang: key):
            yield

    def test_language_menu(self):
        markup = keyboards.language_menu()
        assert hasattr(markup, "keyboard")
        assert len(markup.keyboard) == 1
        assert len(markup.keyboard[0]) == 3
        assert markup.keyboard[0][1]["text"] == "🇷🇺 Русский"

    def test_main_menu(self):
        markup = keyboards.main_menu()
        assert hasattr(markup, "keyboard")
        texts = {btn["text"] for row in markup.keyboard for btn in row}
        assert "role_seeker" in texts
        assert "role_employer" in texts
        assert "about_bot" in texts

    def test_seeker_menu(self):
        markup = keyboards.seeker_menu()
        assert hasattr(markup, "keyboard")
        texts = {btn["text"] for row in markup.keyboard for btn in row}
        assert "register_button" in texts
        assert "back_to_main_menu" in texts

    def test_employer_menu(self):
        markup = keyboards.employer_menu()
        assert hasattr(markup, "keyboard")
        texts = {btn["text"] for row in markup.keyboard for btn in row}
        assert "register_button" in texts
        assert "back_to_main_menu" in texts

    def test_seeker_main_menu(self):
        markup = keyboards.seeker_main_menu()
        assert hasattr(markup, "keyboard")
        texts = {btn["text"] for row in markup.keyboard for btn in row}
        assert "menu_find_vacancies" in texts
        assert "menu_my_resume" in texts
        assert "menu_logout" in texts

    def test_employer_main_menu(self):
        markup = keyboards.employer_main_menu()
        assert hasattr(markup, "keyboard")
        texts = {btn["text"] for row in markup.keyboard for btn in row}
        assert "menu_create_vacancy" in texts
        assert "menu_find_candidates" in texts
        assert "menu_logout" in texts

    def test_settings_menu(self):
        # Роль соискателя
        markup_seeker = keyboards.settings_menu(role="seeker")
        assert hasattr(markup_seeker, "keyboard")
        seeker_texts = {btn["text"] for row in markup_seeker.keyboard for btn in row}
        assert "btn_profession" in seeker_texts
        assert "btn_experience" in seeker_texts
        assert "btn_delete_account" in seeker_texts
        assert "btn_delete_company" not in seeker_texts

        # Роль работодателя
        markup_employer = keyboards.settings_menu(role="employer")
        assert hasattr(markup_employer, "keyboard")
        employer_texts = {
            btn["text"] for row in markup_employer.keyboard for btn in row
        }
        assert "btn_delete_company" in employer_texts
        assert "btn_profession" not in employer_texts

    def test_seeker_status_menu(self):
        markup = keyboards.seeker_status_menu()
        texts = {btn["text"] for row in markup.keyboard for btn in row}
        assert "status_active" in texts
        assert "status_inactive" in texts
        assert "btn_back_settings" in texts

    def test_seeker_submenu(self):
        # С пустым значением -> кнопка 'add'
        markup_add = keyboards.seeker_submenu("profession", None)
        add_texts = {btn["text"] for row in markup_add.keyboard for btn in row}
        assert "add_button" in add_texts
        assert "edit_button" not in add_texts

        # С существующим значением -> кнопка 'edit'
        markup_edit = keyboards.seeker_submenu("profession", "Developer")
        edit_texts = {btn["text"] for row in markup_edit.keyboard for btn in row}
        assert "edit_button" in edit_texts
        assert "add_button" not in edit_texts

    def test_admin_menus(self):
        markup_admin = keyboards.admin_menu()
        admin_texts = {btn["text"] for row in markup_admin.keyboard for btn in row}
        assert "📊 Статистика" in admin_texts
        assert "📢 Рассылка" in admin_texts

        markup_users = keyboards.admin_users_menu()
        users_texts = {btn["text"] for row in markup_users.keyboard for btn in row}
        assert "📋 Список соискателей" in users_texts
        assert "🔎 Поиск пользователя" in users_texts

    def test_support_menu(self):
        markup = keyboards.support_menu()
        texts = {btn["text"] for row in markup.keyboard for btn in row}
        assert "btn_report_bug" in texts
        assert "btn_complaint" in texts

    def test_recovery_menu(self):
        markup = keyboards.recovery_menu()
        texts = {btn["text"] for row in markup.keyboard for btn in row}
        assert "📧 Восстановить пароль" in texts

    def test_job_type_menu(self):
        markup = keyboards.job_type_menu()
        texts = {btn["text"] for row in markup.keyboard for btn in row}
        assert "job_type_full_time" in texts
        assert "job_type_remote" in texts

    def test_vacancy_actions(self):
        markup = keyboards.vacancy_actions(123)
        assert hasattr(markup, "keyboard")
        button = markup.keyboard[0][0]
        assert button.text == "btn_apply"
        assert button.callback_data == "apply_123"

    def test_employer_invite_keyboard(self):
        # Без vacancy_id
        markup1 = keyboards.employer_invite_keyboard(seeker_telegram_id=777)
        button1 = markup1.keyboard[0][0]
        assert button1.text == "btn_invite"
        assert button1.callback_data == "invite_777"

        # С vacancy_id
        markup2 = keyboards.employer_invite_keyboard(
            seeker_telegram_id=777, vacancy_id=101
        )
        button2 = markup2.keyboard[0][0]
        assert button2.text == "btn_invite"
        assert button2.callback_data == "invite_777_101"

    def test_my_vacancy_actions(self):
        markup = keyboards.my_vacancy_actions(456)
        assert hasattr(markup, "keyboard")
        buttons = markup.keyboard[0]
        assert len(buttons) == 3
        assert buttons[0].callback_data == "edit_vac_456"
        assert buttons[1].callback_data == "delete_vac_456"
        assert buttons[2].callback_data == "responses_vac_456"

    def test_delete_confirmation_keyboard(self):
        markup = keyboards.delete_confirmation_keyboard(789)
        assert hasattr(markup, "keyboard")
        buttons = markup.keyboard[0]
        assert buttons[0].callback_data == "confirm_del_789"
        assert buttons[1].callback_data == "cancel_del_789"
        assert buttons[0].text == "btn_yes"

    def test_contact_keyboards(self):
        markup_emp = keyboards.contact_employer_keyboard(111)
        assert markup_emp.keyboard[0][0].callback_data == "start_chat_111"

        markup_seeker = keyboards.contact_seeker_keyboard(222)
        assert markup_seeker.keyboard[0][0].callback_data == "start_chat_222"

    def test_reply_keyboard(self):
        markup = keyboards.reply_keyboard(333)
        assert markup.keyboard[0][0].callback_data == "start_chat_333"

    def test_stop_chat_keyboard(self):
        markup = keyboards.stop_chat_keyboard()
        assert markup.keyboard[0][0]["text"] == "❌ Завершить чат"

    def test_admin_user_action_keyboard(self):
        # Не заблокирован
        markup_not_blocked = keyboards.admin_user_action_keyboard(
            user_id=555, is_blocked=False
        )
        buttons_nb = markup_not_blocked.keyboard[0]
        assert buttons_nb[0].callback_data == "admin_write_555"
        assert buttons_nb[1].callback_data == "admin_block_menu_555"
        assert buttons_nb[1].text == "🚫 Блокировать"

        # Заблокирован
        markup_blocked = keyboards.admin_user_action_keyboard(
            user_id=555, is_blocked=True
        )
        buttons_b = markup_blocked.keyboard[0]
        assert buttons_b[1].callback_data == "admin_unblock_555"
        assert buttons_b[1].text == "🔓 Разблокировать"

    def test_block_duration_keyboard(self):
        markup = keyboards.block_duration_keyboard(user_id=666)
        assert len(markup.keyboard) == 3
        assert markup.keyboard[0][0].callback_data == "admin_block_666_1h"
        assert markup.keyboard[1][1].callback_data == "admin_block_666_forever"
        assert markup.keyboard[2][0].callback_data == "admin_block_666_cancel"

    def test_user_reply_keyboard(self):
        markup = keyboards.user_reply_keyboard(admin_id=999)
        assert markup.keyboard[0][0].callback_data == "reply_admin_999"
