import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from utils import (
    is_valid_uzbek_phone,
    format_phone,
    is_valid_email,
    validate_password,
    validate_login,
    mask_phone,
    validate_name,
    validate_age,
    generate_strong_password,
    generate_captcha,
        generate_text_captcha,
    generate_random_string,
    escape_markdown,
    is_sequential,
    validate_captcha,
    calculate_age,
    mask_email, 
    generate_token,
    truncate_text, create_pagination,
    safe_execute,
    retry_on_error,
    format_datetime,
    cancel_request
)
import re
import time


class TestValidation:
    
    @pytest.mark.parametrize("phone,expected", [
        ("901234567", True),          # Короткий формат
        ("998901234567", True),       # Полный без плюса
        ("+998901234567", True),      # Полный с плюсом
        ("+998 90 123 45 67", True),  # С пробелами
        ("123456789", False),         # Неверный код оператора (12)
        ("90123456", False),          # Короткий
        ("abc", False),               # Буквы
        ("9989012345678", False),     # Слишком длинный
        (None, False),                # None
        (901234567, False),           # Не строка
    ])
    def test_phone_validation(self, phone, expected):
        assert is_valid_uzbek_phone(phone) == expected

    def test_phone_formatting(self):
        assert format_phone("901234567") == "+998901234567"
        assert format_phone("998901234567") == "+998901234567"
        assert format_phone("+998 90 123-45-67") == "+998901234567"
        # Test Russian format (line 108)
        assert format_phone("8901234567") == "8901234567"

    @pytest.mark.parametrize("email,expected", [
        ("test@example.com", True),
        ("user.name@domain.uz", True),
        ("invalid-email", False),
        ("@domain.com", False),
        ("user@", False),
        ("test@.com", False),
    ])
    def test_email_validation(self, email, expected):
        assert is_valid_email(email) == expected

    def test_is_valid_email_uncommon_domain(self):
        """Тест валидации email с редким доменом (покрытие строки 122)"""
        assert is_valid_email("test@domain.xyz") is True

    def test_is_valid_email_pass_block(self):
        # Line 122 (pass block for non-uz domains)
        assert is_valid_email("test@google.ca") is True

    @pytest.mark.parametrize("password, is_valid, message_part", [
        ("short", False, "минимум 8 символов"),
        ("a"*101, False, "слишком длинный"),
        ("PasswordWithoutDigit!", False, "хотя бы одну цифру"),
        ("passwordwithoutupper1!", False, "хотя бы одну заглавную"),
        ("PASSWORDWITHOUTLOWER1!", False, "хотя бы одну строчную"),
        ("PasswordWithDigit1", False, "хотя бы один специальный символ"),
        ("password", False, "хотя бы одну цифру"),
        ("password123", False, "слишком простой"),
        ("12345678", False, "хотя бы одну букву"),
        ("StrongMix1!", True, "Пароль принят"),
        (None, False, "не может быть пустым"),
        # Test special chars (line 151)
        ("Password123", False, "хотя бы один специальный символ"),
        # Test sequential (line 180)
        ("12345678Aa!", False, "простую последовательность"),
    ])
    def test_password_validation(self, password, is_valid, message_part):
        valid, msg = validate_password(password)
        assert valid == is_valid
        assert message_part in msg

    def test_login_validation(self):
        assert validate_login("user_123")[0] is True
        assert validate_login("us")[0] is False  # Короткий
        assert validate_login("user name")[0] is False # Пробелы
        assert validate_login(".user")[0] is False # Начинается с точки
        # Test ends with dot/dash (line 211)
        assert validate_login("user.")[0] is False

class TestErrorHandling:
    def test_safe_execute(self):
        """Тест безопасного выполнения функции"""
        def success_func():
            return "OK"
        
        def error_func():
            raise ValueError("Test Error")

        res, err = safe_execute(success_func)
        assert res == "OK"
        assert err is None

        res, err = safe_execute(error_func)
        assert res is None
        assert "Test Error" in err

    def test_retry_on_error(self):
        """Тест декоратора повторных попыток"""
        mock_func = MagicMock()
        mock_func.side_effect = [ValueError("Fail 1"), ValueError("Fail 2"), "Success"]

        # Оборачиваем мок-функцию в декоратор
        decorated_func = retry_on_error(mock_func, max_retries=3, delay=0.01)
        
        result = decorated_func()

        assert result == "Success"
        assert mock_func.call_count == 3

    def test_retry_on_error_fails(self):
        """Тест, когда все попытки неудачны"""
        mock_func = MagicMock(side_effect=ValueError("Always Fail"))
        decorated_func = retry_on_error(mock_func, max_retries=2, delay=0.01)
        with pytest.raises(ValueError, match="Always Fail"):
            decorated_func()
        assert mock_func.call_count == 2

    def test_retry_on_error_with_args(self):
        """Тест декоратора с аргументами"""
        mock_func = MagicMock()
        mock_func.side_effect = [TypeError("Fail"), "Success"]

        decorated_func = retry_on_error(mock_func, max_retries=2, delay=0.01)
        
        result = decorated_func(1, "test", key="value")
        assert result == "Success"
        mock_func.assert_called_with(1, "test", key="value")

class TestFormattingAndGenerators:

    def test_phone_masking(self):
        assert mask_phone("+998901234567") == "+998901***567"
        assert mask_phone("901234567") == "+998901***567"
        assert mask_phone("invalid") == "invalid"

    @pytest.mark.parametrize("name,is_valid", [
        ("John Doe", True),
        ("O'zbekiston", True),
        ("Абдураҳмон", True),
        ("J", False), # too short
        ("John123", False), # contains numbers
        ("  ", False), # only spaces
        ("John  Doe", False), # double space
    ])
    def test_name_validation(self, name, is_valid):
        valid, msg = validate_name(name)
        assert valid == is_valid

    def test_validate_name_none(self):
        """Тест валидации имени None (покрытие строки 530)"""
        assert validate_name(None)[0] is False

    @pytest.mark.parametrize("age_str,is_valid,expected_age", [
        ("25", True, 25),
        ("16", True, 16),
        ("15", False, 15),
        ("101", False, 101),
        ("abc", False, 0),
    ])
    def test_age_validation(self, age_str, is_valid, expected_age):
        valid, age, msg = validate_age(age_str)
        assert valid == is_valid
        assert age == expected_age

    def test_generate_strong_password(self):
        password = generate_strong_password(12)
        assert len(password) == 12
        assert any(c.islower() for c in password)
        assert any(c.isupper() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(not c.isalnum() for c in password)

    def test_generate_captcha(self):
        question, answer = generate_captcha()
        assert isinstance(question, str)
        assert isinstance(answer, int)
        assert answer > 0

    def test_generate_captcha_multiplication(self):
        """Тест генерации капчи с умножением (покрытие строк 278-281)"""
        with patch('random.choice', return_value='*'):
            q, a = generate_captcha()
            assert '*' in q or '×' in q

    def test_generate_text_captcha(self):
        """Тест генерации текстовой капчи (покрытие строк 271-274)"""
        q, a = generate_text_captcha()
        assert isinstance(q, str)
        assert isinstance(a, str)

    def test_generate_random_string(self):
        s = generate_random_string(10, include_digits=True)
        assert len(s) == 10
        assert s.isalnum()
        
        s_no_digits = generate_random_string(10, include_digits=False)
        assert len(s_no_digits) == 10
        assert s_no_digits.isalpha()

    def test_escape_markdown(self):
        assert escape_markdown("`*_[]`") == "\\`\\*\\_\\[\\]\\`"
        assert escape_markdown("Hello_world*") == "Hello\\_world\\*"
        assert escape_markdown(None) == ""
        assert escape_markdown(123) == "123"

    def test_is_sequential(self):
        assert is_sequential("1234567") is True
        assert is_sequential("abcdef") is True
        assert is_sequential("qwerty") is True
        assert is_sequential("aaabbbccc") is True # Repeated chars
        assert is_sequential("Strong123") is False

    @pytest.mark.parametrize("user_answer, correct_answer, expected", [
        ("5", 5, True),
        (" 5 ", 5, True),
        ("пять", 5, True),
        ("шесть", 5, False),
        ("abc", 5, False),
        ("7", "7", True),
        ("семь", "7", False), # string vs string
        # Test number words (line 248)
        ("0", 5, False),
        ("-1", 5, False),
        ("пять", 5, True),
    ])
    def test_validate_captcha(self, user_answer, correct_answer, expected):
        assert validate_captcha(user_answer, correct_answer) == expected

    def test_calculate_age(self):
        # To make test deterministic, we mock datetime.now()
        class MockDateTime(datetime):
            @classmethod
            def now(cls):
                return cls(2026, 1, 28)

        with patch('utils.datetime', MockDateTime):
            birth_date = datetime(2000, 1, 1)
            assert calculate_age(birth_date) == 26
            
            birth_date_later_in_year = datetime(2000, 12, 31)
            assert calculate_age(birth_date_later_in_year) == 25

    def test_mask_email(self):
        assert mask_email("test.user@gmail.com") == "t*******r@gmail.com"
        assert mask_email("me@domain.com") == "me***@domain.com"
        assert mask_email("invalid") == "invalid"

    def test_generate_token(self):
        token1 = generate_token()
        token2 = generate_token()
        assert isinstance(token1, str)
        assert len(token1) == 32
        assert token1 != token2

    def test_format_datetime(self):
        """Тест форматирования даты"""
        now = datetime.now()
        assert format_datetime(now - timedelta(seconds=30)) == "только что"
        assert format_datetime(now - timedelta(minutes=5)) == "5 мин. назад"
        assert format_datetime(now - timedelta(hours=2)) == "2 ч. назад"
        assert format_datetime(now - timedelta(days=1)) == "вчера"
        assert format_datetime(now - timedelta(days=3)) == "3 дн. назад"
        assert format_datetime(now - timedelta(days=8)) == (now - timedelta(days=8)).strftime("%d.%m.%Y")
        assert format_datetime(datetime(2020, 1, 1)) == "01.01.2020"

class TestCancelRequest:
    @pytest.mark.parametrize("text, expected", [
        ("отмена", True),
        ("ОТМЕНА", True),
        (" /cancel ", True),
        ("❌", True),
        ("стоп", True),
        ("назад", True),
        (None, False),
        ("", False),
        ("продолжить", False),
        ("ok", False),
    ])
    def test_cancel_words(self, text, expected):
        """Тест на точные слова отмены и неверные варианты"""
        assert cancel_request(text) is expected

    def test_partial_match(self):
        """Тест на частичное совпадение в строке"""
        assert cancel_request("я хочу отменить действие") is True
        assert cancel_request("нажми стоп") is True
        assert cancel_request("просто текст без команд") is False

class TestTextAndPagination:
    def test_truncate_text(self):
        assert truncate_text("short text", 20) == "short text"
        assert truncate_text("a very long text that needs to be truncated", 20) == "a very long text..."
        assert truncate_text("another long one", 10, suffix=">>") == "another>>"
        assert truncate_text(None, 10) == ""

    def test_create_pagination(self):
        # No pagination for 1 page
        assert create_pagination(1, 1) == []
        
        # First page of many
        pagination1 = create_pagination(1, 10)
        assert len(pagination1) == 6 # 1,2,3,4,5, ->
        assert pagination1[0]['text'] == "• 1 •"
        assert pagination1[-1]['text'] == "Вперед ▶️"

        # Middle page
        pagination2 = create_pagination(5, 10)
        assert len(pagination2) == 7 # <-, 3,4,5,6,7, ->
        assert pagination2[0]['text'] == "◀️ Назад"
        assert pagination2[3]['text'] == "• 5 •"
        assert pagination2[-1]['text'] == "Вперед ▶️"

        # Last page
        pagination3 = create_pagination(10, 10)
        assert len(pagination3) == 6 # <-, 6,7,8,9,10
        assert pagination3[0]['text'] == "◀️ Назад"
        assert pagination3[-1]['text'] == "• 10 •"