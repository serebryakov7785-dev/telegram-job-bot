import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import utils as utils_validators  # noqa: E402


class TestUtilsValidators:
    @pytest.mark.parametrize(
        "phone, expected",
        [
            ("901234567", True),
            ("998931234567", True),
            ("+998941234567", True),
            ("90 123 45 67", True),
            ("12345", False),  # noqa
            ("701234567", False),  # Invalid operator
            (None, False),  # noqa
            (123456789, False),  # Not a string
        ],
    )
    def test_is_valid_uzbek_phone(self, phone, expected):
        assert utils_validators.is_valid_uzbek_phone(phone) is expected  # noqa

    @pytest.mark.parametrize(
        "email, expected",
        [
            ("test@example.com", True),
            ("test.name@example.co.uk", True),
            ("test@sub.domain.com", True),
            ("test@example", False),
            ("test@.com", False),
            ("test@com.", False),
            ("test..name@example.com", False),
            ("test@com..com", False),
            ("a" * 65 + "@example.com", False),
            (None, False),
            (123, False),
        ],
    )
    def test_is_valid_email(self, email, expected):
        assert utils_validators.is_valid_email(email) is expected

    @pytest.mark.parametrize(
        "password, is_valid, message_part",
        [
            ("StrongPass1!", True, "принят"),
            ("short", False, "8 символов"),
            ("nouppercase1!", False, "заглавную букву"),
            ("NOLOWERCASE1!", False, "строчную букву"),
            ("NoDigits!", False, "одну цифру"),
            ("12345!@#$", False, "одну букву"),
            ("NoSpecial1", False, "специальный символ"),
            ("12345678aA!", False, "последовательность"),
            ("qwerty123aA!", False, "последовательность"),
            ("password123A!", True, "принят"),
            (None, False, "пустым"),
        ],
    )
    def test_validate_password(self, password, is_valid, message_part):
        valid, msg = utils_validators.validate_password(password)
        assert valid is is_valid
        assert message_part in msg

    def test_is_sequential(self):
        assert utils_validators.is_sequential("1234567") is True  # noqa
        assert utils_validators.is_sequential("abcdefg") is True
        assert utils_validators.is_sequential("qwertyuiop") is True  # noqa
        assert utils_validators.is_sequential("aaabbbccc") is True  # Repeated chars
        assert utils_validators.is_sequential("complex") is False

    @pytest.mark.parametrize(
        "login, is_valid, message_part",
        [
            ("valid_login", True, "принят"),
            ("v-l", True, "принят"),
            ("v.l", True, "принят"),
            ("sh", False, "3 символа"),
            ("a" * 51, False, "слишком длинный"),
            ("invalid#char", False, "только буквы"),
            (".start", False, "начинаться"),
            ("end-", False, "заканчиваться"),
            ("double..dot", False, "две точки"),
            (None, False, "пустым"),
        ],
    )
    def test_validate_login(self, login, is_valid, message_part):
        valid, msg = utils_validators.validate_login(login)
        assert valid is is_valid
        assert message_part in msg

    @pytest.mark.parametrize(
        "name, is_valid, message_part",
        [
            ("Valid Name", True, "принято"),
            ("O'zbekcha Ism", True, "принято"),
            ("A", False, "короткое"),
            ("Name123", False, "недопустимые символы"),
            ("Double  Space", False, "лишние пробелы"),
            (None, False, "пустым"),
        ],
    )
    def test_validate_name(self, name, is_valid, message_part):
        valid, msg = utils_validators.validate_name(name)
        assert valid is is_valid
        assert message_part in msg

    @pytest.mark.parametrize(
        "age_str, is_valid, message_part",
        [
            ("25", True, "принят"),
            ("16", True, "принят"),
            ("100", True, "принят"),
            ("15", False, "Минимальный возраст"),
            ("101", False, "превышать 100"),
            ("abc", False, "Введите число"),
        ],
    )
    def test_validate_age(self, age_str, is_valid, message_part):
        valid, age, msg = utils_validators.validate_age(age_str)
        assert valid is is_valid
        assert message_part in msg

    @pytest.mark.parametrize(
        "user_answer, correct_answer, expected",
        [
            ("5", 5, True),
            (" 5 ", 5, True),
            ("five", "five", True),
            ("Five", "five", True),
            ("4", 5, False),
            ("six", "five", False),
            (None, 5, False),  # noqa
            ("abc", 5, False),
            ("0", 0, False),  # Should be > 0
        ],
    )
    def test_validate_captcha(self, user_answer, correct_answer, expected):
        assert (
            utils_validators.validate_captcha(user_answer, correct_answer) is expected
        )
