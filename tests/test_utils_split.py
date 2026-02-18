import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import formatters as utils_formatters  # noqa: E402
import misc as utils_misc  # noqa: E402
import security as utils_security  # noqa: E402
import utils as utils_validators  # noqa: E402


class TestUtilsSplit:
    # --- utils_formatters ---
    def test_format_phone(self):
        assert utils_formatters.format_phone("901234567") == "+998901234567"
        assert utils_formatters.format_phone("123") == "123"

    def test_extract_phone_operator(self):
        assert utils_formatters.extract_phone_operator("901234567") == "90"

    def test_get_operator_name(self):
        assert utils_formatters.get_operator_name("90") == "Beeline"

    def test_format_datetime(self):
        now = datetime.now()
        assert utils_formatters.format_datetime(now) == "только что"

    def test_truncate_text(self):
        assert utils_formatters.truncate_text("Hello World", 5) == "He..."

    def test_mask_email(self):
        assert utils_formatters.mask_email("test@test.com") == "t**t@test.com"

    def test_mask_phone(self):
        assert utils_formatters.mask_phone("+998901234567") == "+998901***567"

    # --- utils_misc ---
    def test_cancel_request(self):
        assert utils_misc.cancel_request("отмена") is True
        assert utils_misc.cancel_request("ok") is False

    def test_create_cancel_keyboard(self):
        kb = utils_misc.create_cancel_keyboard()
        assert kb["keyboard"][0][0]["text"] == "❌ Отмена"

    def test_safe_execute(self):
        res, err = utils_misc.safe_execute(lambda x: x + 1, 1)
        assert res == 2
        assert err is None

    # --- utils_security ---
    def test_contains_profanity(self):
        assert (
            utils_security.contains_profanity("badword") is False
        )  # Assuming 'badword' is not in list
        assert utils_security.contains_profanity("хуй") is True

    def test_generate_strong_password(self):
        pwd = utils_security.generate_strong_password(10)
        assert len(pwd) == 10

    def test_generate_captcha(self):
        q, a = utils_security.generate_captcha()
        assert isinstance(q, str)
        assert isinstance(a, int)

    def test_sanitize_input(self):
        assert utils_security.sanitize_input("<script>") == "&lt;script&gt;"

    def test_calculate_age(self):
        birth = datetime.now() - timedelta(days=365 * 20 + 5)
        assert utils_security.calculate_age(birth) == 20

    # --- utils_validators ---
    def test_is_valid_uzbek_phone(self):
        assert utils_validators.is_valid_uzbek_phone("901234567") is True
        assert utils_validators.is_valid_uzbek_phone("123") is False

    def test_is_valid_email(self):
        assert utils_validators.is_valid_email("a@b.co") is True
        assert utils_validators.is_valid_email("abc") is False

    def test_validate_password(self):
        assert utils_validators.validate_password("Strong1!")[0] is True
        assert utils_validators.validate_password("weak")[0] is False

    def test_validate_login(self):
        assert utils_validators.validate_login("user")[0] is True
        assert utils_validators.validate_login("u")[0] is False

    def test_validate_name(self):
        assert utils_validators.validate_name("John")[0] is True
        assert utils_validators.validate_name("")[0] is False

    def test_validate_age(self):
        assert utils_validators.validate_age("25")[0] is True
        assert utils_validators.validate_age("10")[0] is False

    def test_validate_captcha(self):
        assert utils_validators.validate_captcha("4", 4) is True
