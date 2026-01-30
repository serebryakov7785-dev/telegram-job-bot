import pytest
import utils
from unittest.mock import MagicMock
from datetime import datetime, timedelta

class TestUtils:
    def test_is_valid_uzbek_phone(self):
        assert utils.is_valid_uzbek_phone("901234567")
        assert utils.is_valid_uzbek_phone("+998901234567")
        assert utils.is_valid_uzbek_phone("998901234567")
        assert not utils.is_valid_uzbek_phone("123")
        assert not utils.is_valid_uzbek_phone(None)
        assert not utils.is_valid_uzbek_phone("001234567") # Invalid operator

    def test_format_phone(self):
        assert utils.format_phone("901234567") == "+998901234567"
        assert utils.format_phone("998901234567") == "+998901234567"
        assert utils.format_phone("8901234567") == "8901234567" # Russian-like
        assert utils.format_phone("") == ""
        assert utils.format_phone(None) == ""

    def test_extract_phone_operator(self):
        assert utils.extract_phone_operator("901234567") == "90"
        assert utils.extract_phone_operator("123") is None

    def test_get_operator_name(self):
        assert utils.get_operator_name("90") == "Beeline"
        assert utils.get_operator_name("00") == "Неизвестный оператор"

    def test_is_valid_email(self):
        assert utils.is_valid_email("test@test.uz")
        assert not utils.is_valid_email("test")
        assert not utils.is_valid_email(None)
        assert not utils.is_valid_email("test@test") # No dot
        assert not utils.is_valid_email("test@.uz")
        assert not utils.is_valid_email("test@test.")
        assert not utils.is_valid_email("test..test@test.uz")
        # Long email
        assert not utils.is_valid_email("a" * 65 + "@test.uz")

    def test_extract_email_domain(self):
        assert utils.extract_email_domain("test@test.uz") == "test.uz"
        assert utils.extract_email_domain("invalid") is None

    def test_validate_password(self):
        assert utils.validate_password("Pass123!")[0]
        assert not utils.validate_password("short")[0]
        assert not utils.validate_password("nopassword")[0] # No digit
        assert not utils.validate_password("12345678")[0] # No alpha
        assert not utils.validate_password("password123")[0] # Common
        assert not utils.validate_password("12345678Aa")[0] # Sequential (maybe)
        assert not utils.validate_password("abcdefgH1")[0] # Sequential

    def test_is_sequential(self):
        assert utils.is_sequential("123456")
        assert utils.is_sequential("qwerty")
        assert not utils.is_sequential("q1w2e3r4")

    def test_generate_strong_password(self):
        pwd = utils.generate_strong_password(12)
        assert len(pwd) == 12
        assert any(c.isdigit() for c in pwd)
        assert any(c.isupper() for c in pwd)

    def test_validate_login(self):
        assert utils.validate_login("user_1")[0]
        assert not utils.validate_login("u")[0] # Short
        assert not utils.validate_login(".user")[0] # Starts with dot
        assert not utils.validate_login("user..name")[0] # Double dot
        assert not utils.validate_login(None)[0]

    def test_generate_captcha(self):
        q, a = utils.generate_captcha()
        assert isinstance(q, str)
        assert isinstance(a, int)

    def test_generate_text_captcha(self):
        q, a = utils.generate_text_captcha()
        assert isinstance(q, str)
        assert isinstance(a, str)

    def test_validate_captcha(self):
        assert utils.validate_captcha("4", 4)
        assert utils.validate_captcha("четыре", 4)
        assert utils.validate_captcha("test", "test")
        assert not utils.validate_captcha("5", 4)
        assert not utils.validate_captcha(None, 4)

    def test_cancel_request(self):
        assert utils.cancel_request("отмена")
        assert utils.cancel_request("/cancel")
        assert not utils.cancel_request("hello")
        assert not utils.cancel_request(None)

    def test_create_cancel_keyboard(self):
        kb = utils.create_cancel_keyboard()
        assert 'keyboard' in kb

    def test_show_phone_format_example(self):
        assert "901234567" in utils.show_phone_format_example()

    def test_format_datetime(self):
        now = datetime.now()
        assert utils.format_datetime(now) == "только что"
        assert "мин. назад" in utils.format_datetime(now - timedelta(minutes=5))
        assert "ч. назад" in utils.format_datetime(now - timedelta(hours=2))
        assert "вчера" in utils.format_datetime(now - timedelta(days=1))
        assert "дн. назад" in utils.format_datetime(now - timedelta(days=3))
        assert "." in utils.format_datetime(now - timedelta(days=10))

    def test_sanitize_input(self):
        assert utils.sanitize_input("<script>") == "&lt;script&gt;"
        assert utils.sanitize_input(None) == ""
        assert len(utils.sanitize_input("a" * 600, 500)) == 500

    def test_generate_token(self):
        assert len(utils.generate_token()) == 32

    def test_truncate_text(self):
        assert utils.truncate_text("hello world", 5) == "he..."
        assert utils.truncate_text("hello", 10) == "hello"
        assert utils.truncate_text(None) == ""

    def test_create_pagination(self):
        assert len(utils.create_pagination(1, 10)) > 0
        assert utils.create_pagination(1, 1) == []

    def test_safe_execute(self):
        def func(x): return x + 1
        res, err = utils.safe_execute(func, 1)
        assert res == 2
        assert err is None
        
        def fail(): raise ValueError("Error")
        res, err = utils.safe_execute(fail)
        assert res is None
        assert "Error" in err

    def test_retry_on_error(self):
        mock = MagicMock(side_effect=[Exception, 42])
        wrapped = utils.retry_on_error(mock, max_retries=2, delay=0)
        assert wrapped() == 42
        assert mock.call_count == 2

    def test_validate_name(self):
        assert utils.validate_name("John Doe")[0]
        assert not utils.validate_name("J")[0]
        assert not utils.validate_name("John1")[0]

    def test_validate_age(self):
        assert utils.validate_age("25")[0]
        assert not utils.validate_age("10")[0]
        assert not utils.validate_age("abc")[0]

    def test_generate_random_string(self):
        assert len(utils.generate_random_string(10)) == 10

    def test_calculate_age(self):
        birth = datetime.now() - timedelta(days=365*20 + 5)
        assert utils.calculate_age(birth) == 20

    def test_mask_email(self):
        assert "t**t@test.uz" == utils.mask_email("test@test.uz")
        assert utils.mask_email("invalid") == "invalid"

    def test_mask_phone(self):
        assert "***" in utils.mask_phone("+998901234567")
        assert utils.mask_phone("123") == "123"

    def test_escape_markdown(self):
        assert utils.escape_markdown("*bold*") == "\\*bold\\*"
        assert utils.escape_markdown(None) == ""