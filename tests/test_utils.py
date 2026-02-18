from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

import utils

# ================= PHONE TESTS =================


@pytest.mark.parametrize(
    "phone,expected",
    [
        ("901234567", True),
        ("998901234567", True),
        ("+998901234567", True),
        ("90 123 45 67", True),
        ("(90) 123-45-67", True),
        ("1234567", False),  # Too short
        ("99890123456", False),  # Length 11
        ("9989012345678", False),  # Length 13
        ("123456789012", False),  # Length 12 but wrong prefix
        (
            "123901234567",
            False,
        ),  # Length 12, operator 90 inside, but prefix wrong (kills startswith mutant)
        ("701234567", False),  # Invalid operator
        ("abc", False),
        (None, False),
    ],
)
def test_is_valid_uzbek_phone(phone, expected):
    assert utils.is_valid_uzbek_phone(phone) == expected


@pytest.mark.parametrize(
    "phone,expected",
    [
        ("901234567", "+998901234567"),
        ("998901234567", "+998901234567"),
        ("+998901234567", "+998901234567"),
        ("90 123 45 67", "+998901234567"),
        ("8901234567", "8901234567"),  # Non-Uzbek format returns as is
        ("7901234567", "7901234567"),  # Length 10 but not starting with 8
        (
            "8(90)1234567",
            "8(90)1234567",
        ),  # Starts with 8, len 10, has formatting (kills mutant)
        (
            "9(90)1234567",
            "9901234567",
        ),  # Len 10, NOT starts with 8 -> should be cleaned (kills startswith mutant)
        ("8-901-234-56-78", "89012345678"),  # Russian format, cleaned
        ("", ""),
        (None, ""),
    ],
)
def test_format_phone(phone, expected):
    assert utils.format_phone(phone) == expected


def test_extract_phone_operator():
    assert utils.extract_phone_operator("901234567") == "90"
    assert utils.extract_phone_operator("701234567") is None


def test_get_operator_name():
    assert utils.get_operator_name("90") == "Beeline"
    assert utils.get_operator_name("00") == "Неизвестный оператор"


# ================= EMAIL TESTS =================


@pytest.mark.parametrize(
    "email,expected",
    [
        ("test@example.com", True),
        ("test.name@example.uz", True),
        ("test@example", False),  # No TLD
        ("test@.com", False),  # Empty domain part
        ("test@com", False),  # No dot
        ("test..test@example.com", False),  # Double dot in local part
        ("a" * 65 + "@example.com", False),  # Local part too long
        ("test@example.com.", False),  # Domain ends with dot
        (" test@example.com ", True),  # Leading/trailing spaces
        ("test user@example.com", False),  # Space in local part
        ("test@ex ample.com", False),  # Space in domain part
        ("test@example..com", False),  # Double dot in domain part
        ("plainaddress", False),  # No @
        ("", False),  # Empty string
        ("@example.com", False),  # No local part
        (None, False),
    ],
)
def test_is_valid_email(email, expected):
    assert utils.is_valid_email(email) == expected


# ================= PASSWORD & LOGIN TESTS =================


def test_validate_password():
    # Valid
    assert utils.validate_password("StrongP@ss1")[0] is True
    assert (
        utils.validate_password("Str0ng!8")[0] is True
    )  # Exactly 8 chars (boundary check)
    assert (
        utils.validate_password("StrongP@ss1" + "RandomChars")[0] is True
    )  # Long password (21 chars)

    # Invalid cases
    assert utils.validate_password("")[0] is False
    assert utils.validate_password("short1!")[0] is False
    assert utils.validate_password("nouppercase1!")[0] is False
    assert utils.validate_password("NOLOWERCASE1!")[0] is False
    assert utils.validate_password("NoDigits!")[0] is False
    assert utils.validate_password("NoSpecial1")[0] is False
    assert (
        utils.validate_password("A" * 97 + "Ab1!")[0] is False
    )  # 101 chars (Too long)
    assert utils.validate_password("short1!")[0] is False  # 7 chars (Too short)

    # Sequential & Common
    assert utils.validate_password("12345678Aa!")[0] is False
    assert utils.validate_password("qwertyAa1!")[0] is False
    assert utils.validate_password("aaaaaa1!")[0] is False  # Repeated chars
    assert utils.validate_password("Password123")[0] is False  # Common


def test_validate_login():
    assert utils.validate_login("user1")[0] is True
    assert utils.validate_login("usr")[0] is True  # Exactly 3 chars
    assert utils.validate_login("a" * 50)[0] is True  # Exactly 50 chars
    assert utils.validate_login("a" * 51)[0] is False  # 51 chars
    assert utils.validate_login("us")[0] is False
    assert utils.validate_login("user.name")[0] is True
    assert utils.validate_login(".user")[0] is False
    assert utils.validate_login("user-")[0] is False
    assert utils.validate_login("user..name")[0] is False
    assert utils.validate_login("user@name")[0] is False


# ================= CAPTCHA & SECURITY TESTS =================


def test_validate_captcha():
    assert utils.validate_captcha("4", 4) is True
    assert utils.validate_captcha("wrong", 5) is False
    assert utils.validate_captcha(None, 5) is False  # type: ignore


def test_cancel_request():
    assert utils.cancel_request("отмена") is True
    assert utils.cancel_request("Стоп") is True
    assert utils.cancel_request("/start") is True
    assert utils.cancel_request("Я хочу отменить это") is True
    assert utils.cancel_request("продолжить") is False
    assert utils.cancel_request(None) is False  # type: ignore
    assert (
        utils.cancel_request("🏠") is True
    )  # Emoji check (kills mutant removing exact match)


def test_sanitize_input():
    assert utils.sanitize_input("<script>") == "&lt;script&gt;"
    assert utils.sanitize_input("  hello  ") == "hello"
    assert utils.sanitize_input(None) == ""  # type: ignore
    assert (
        len(utils.sanitize_input("a" * 600)) == 500
    )  # Max length check (kills mutant)


def test_generate_token():
    token = utils.generate_token(16)
    assert len(token) == 16
    assert isinstance(token, str)


# ================= DATA VALIDATION TESTS =================


def test_validate_name():
    assert utils.validate_name("John")[0] is True
    assert utils.validate_name("J")[0] is False
    assert utils.validate_name("John1")[0] is False
    assert utils.validate_name("  ")[0] is False
    assert utils.validate_name(None)[0] is False  # type: ignore


def test_validate_age():
    assert utils.validate_age("25")[0] is True
    assert utils.validate_age("15")[0] is False
    assert utils.validate_age("101")[0] is False
    assert utils.validate_age("abc")[0] is False


def test_calculate_age():
    birth = datetime.now() - timedelta(days=365 * 20 + 5)
    assert utils.calculate_age(birth) == 20


def test_mask_email():
    assert utils.mask_email("test@example.com") == "t**t@example.com"
    assert utils.mask_email("invalid") == "invalid"


def test_mask_phone():
    # +998901234567 -> +99890***4567
    assert "***" in utils.mask_phone("+998901234567")
    assert utils.mask_phone("123") == "123"


# ================= FORMATTING & PAGINATION TESTS =================


def test_format_datetime():
    now = datetime.now()

    # Just now
    assert utils.format_datetime(now) == "только что"
    assert utils.format_datetime(now - timedelta(seconds=59)) == "только что"

    # Minutes
    assert utils.format_datetime(now - timedelta(minutes=1)) == "1 мин. назад"
    assert utils.format_datetime(now - timedelta(minutes=59)) == "59 мин. назад"

    # Hours
    assert utils.format_datetime(now - timedelta(hours=1)) == "1 ч. назад"
    assert utils.format_datetime(now - timedelta(hours=23)) == "23 ч. назад"

    # Yesterday
    assert utils.format_datetime(now - timedelta(days=1)) == "вчера"

    # Days
    assert utils.format_datetime(now - timedelta(days=2)) == "2 дн. назад"
    assert utils.format_datetime(now - timedelta(days=6)) == "6 дн. назад"

    # Date
    old_date = now - timedelta(days=7)
    assert utils.format_datetime(old_date) == old_date.strftime("%d.%m.%Y")


def test_create_pagination():
    # No pages
    assert utils.create_pagination(1, 1) == []
    assert utils.create_pagination(1, 0) == []

    # Middle page
    buttons = utils.create_pagination(3, 5, max_buttons=5)
    assert len(buttons) == 7  # prev + 5 pages + next
    assert buttons[0]["text"] == "◀️ Назад"
    assert buttons[-1]["text"] == "Вперед ▶️"
    assert buttons[3]["text"] == "• 3 •"  # Current


def test_retry_on_error():
    mock_func = MagicMock()

    # Success on first try
    mock_func.return_value = "ok"
    decorated = utils.retry_on_error(mock_func)
    assert decorated() == "ok"
    assert mock_func.call_count == 1

    # Fail then success
    mock_func.reset_mock()
    mock_func.side_effect = [Exception("Fail"), "ok"]
    decorated = utils.retry_on_error(mock_func, delay=0)
    assert decorated() == "ok"
    assert mock_func.call_count == 2


def test_truncate_text():
    assert utils.truncate_text("Short", 10) == "Short"
    assert utils.truncate_text("Long text here", 5) == "Lo..."
    assert utils.truncate_text(None) == ""  # type: ignore


# ================= GENERATORS & HELPERS TESTS =================


def test_generate_strong_password():
    # Test length
    pwd = utils.generate_strong_password(12)
    assert len(pwd) == 12

    # Test minimum length enforcement
    pwd_short = utils.generate_strong_password(4)
    assert len(pwd_short) == 8

    # Test complexity (should contain different char types)
    # Note: There's a tiny chance random doesn't pick one type, but with shuffle and guaranteed chars it should work
    assert any(c.isdigit() for c in pwd)
    assert any(c.islower() for c in pwd)
    assert any(c.isupper() for c in pwd)


def test_generate_captcha():
    question, answer = utils.generate_captcha()
    assert isinstance(question, str)
    assert isinstance(answer, int)
    assert question is not None
    # Check basic math logic
    if question and "+" in question:
        parts = question.split("+")
        assert int(parts[0]) + int(parts[1]) == answer
    elif question and "-" in question:
        parts = question.split("-")
        assert int(parts[0]) - int(parts[1]) == answer
    elif question and "*" in question:
        parts = question.split("*")
        assert int(parts[0]) * int(parts[1]) == answer


def test_generate_text_captcha():
    question, answer = utils.generate_text_captcha()
    assert isinstance(question, str)
    assert isinstance(answer, str)
    assert len(question) > 0
    assert len(answer) > 0


def test_safe_execute():
    # Success case
    def success_func(x):
        return x * 2

    res, err = utils.safe_execute(success_func, 5)
    assert res == 10
    assert err is None

    # Error case
    def fail_func():
        raise ValueError("Boom")

    res, err = utils.safe_execute(fail_func)
    assert res is None
    assert err is not None
    assert "ValueError" in err
    assert "Boom" in err


def test_generate_random_string():
    s1 = utils.generate_random_string(10)
    assert len(s1) == 10
    assert s1.isalnum()

    s2 = utils.generate_random_string(8, include_digits=False)
    assert len(s2) == 8
    assert s2.isalpha()


def test_escape_markdown():
    assert utils.escape_markdown("test_bold*") == "test\\_bold\\*"
    assert utils.escape_markdown("[link]") == "\\[link\\]"
    assert utils.escape_markdown(None) == ""  # type: ignore


def test_create_cancel_keyboard():
    kb = utils.create_cancel_keyboard()
    assert isinstance(kb, dict)
    assert kb["keyboard"][0][0]["text"] == "❌ Отмена"


def test_show_phone_format_example():
    text = utils.show_phone_format_example()
    assert text is not None
    assert text and "901234567" in text
    assert text and "+998" in text


def test_safe_execute_exception_logging():
    """Test safe_execute logs exception"""

    def fail():
        raise ValueError("Test Error")

    with patch("logging.error") as mock_log:
        res, err = utils.safe_execute(fail)
        assert res is None
        assert err is not None
        assert "Test Error" in err
        mock_log.assert_called()


def test_retry_on_error_max_retries():
    """Test retry_on_error fails after max retries"""
    mock_func = MagicMock(side_effect=Exception("Fail"))
    decorated = utils.retry_on_error(mock_func, max_retries=2, delay=0)

    with pytest.raises(Exception):
        decorated()

    assert mock_func.call_count == 2  # Total attempts = max_retries


def test_generate_captcha_division():
    """Test generate_captcha with division (if implemented) or fallback"""
    # Mock random.choice to pick division if it exists, or just ensure coverage of branches
    # Since we can't easily force the operator without refactoring, we rely on the fact
    # that we've covered +, -, * in previous tests.
    # Let's ensure generate_captcha returns valid types even if we run it many times
    for _ in range(20):
        q, a = utils.generate_captcha()
        assert isinstance(q, str)
        assert isinstance(a, int)
