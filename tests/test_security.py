from unittest.mock import MagicMock, patch

from database.users import create_job_seeker, get_user_by_credentials


class TestSecurity:

    def test_sql_injection_login(self, test_db):
        """Попытка SQL-инъекции при поиске пользователя"""

        # Создаем легитимного пользователя
        create_job_seeker(
            {
                "telegram_id": 555,
                "password": "Pass",
                "phone": "+998905555555",
                "email": "victim@test.uz",
                "full_name": "Victim",
                "age": 30,
                "city": "Tashkent",
            }
        )

        # Пытаемся внедрить SQL через email
        # Если бы код был уязвим, это могло бы вернуть первого пользователя в базе
        injection_payload = "' OR '1'='1"
        user, role = get_user_by_credentials(injection_payload)

        # Должно вернуть None, так как execute_query использует параметризацию (?, ?)
        assert user is None
        assert role == ""

    def test_xss_sanitization_utils(self):
        """Проверка очистки ввода (хотя для Telegram это менее критично, чем для Web)"""
        from utils import sanitize_input

        dirty_input = "<script>alert(1)</script> Hello"
        clean = sanitize_input(dirty_input)

        assert "<script>" not in clean
        assert "&lt;script&gt;" in clean
        assert "Hello" in clean

    def test_idor_edit_vacancy(self):
        """
        Тест на IDOR (Insecure Direct Object Reference).
        Пользователь не должен иметь возможности редактировать чужую вакансию,
        просто подменив ID в callback_data.
        """
        from handlers.employer import EmployerHandlers

        handler = EmployerHandlers(MagicMock())
        call = MagicMock()
        call.from_user.id = 123  # ID злоумышленника
        call.message.chat.id = 123

        # Злоумышленник пытается редактировать вакансию 999, которая ему не принадлежит
        # Мокаем, что у пользователя 123 нет вакансии с ID 999
        with patch("database.get_user_by_id", return_value={"id": 1}), patch(
            "database.get_employer_vacancies", return_value=[{"id": 555}]
        ):  # У него есть только 555

            handler.handle_edit_vacancy(call, 999)

            # Бот должен ответить ошибкой, а не открыть меню редактирования
            handler.bot.send_message.assert_called_with(123, "❌ Вакансия не найдена.")
