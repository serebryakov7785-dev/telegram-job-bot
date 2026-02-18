import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import security  # noqa: E402


class TestUtilsSecurity:
    def test_contains_profanity(self):
        assert security.contains_profanity("это простое предложение") is False
        assert security.contains_profanity("а вот тут хуй") is True
        assert security.contains_profanity("fuck this") is True
        assert security.contains_profanity("qotoq so'z") is True
        assert security.contains_profanity(None) is False
        assert security.contains_profanity("") is False

    def test_generate_strong_password(self):
        pwd = security.generate_strong_password(12)
        assert len(pwd) == 12
        assert any(c.islower() for c in pwd)
        assert any(c.isupper() for c in pwd)
        assert any(c.isdigit() for c in pwd)
        assert any(not c.isalnum() for c in pwd)

        # Test minimum length
        pwd_short = security.generate_strong_password(6)
        assert len(pwd_short) == 8

    def test_generate_captcha(self):
        for _ in range(10):
            q, a = security.generate_captcha()
            assert isinstance(q, str)
            assert isinstance(a, int)
            # eval is generally unsafe, but here it's fine as we control the input
            assert eval(q.replace("×", "*")) == a

    def test_generate_text_captcha(self):
        q, a = security.generate_text_captcha()
        assert isinstance(q, str)
        assert isinstance(a, str)
        assert len(q) > 0
        assert len(a) > 0

    def test_sanitize_input(self):
        assert (
            security.sanitize_input("<script>alert('xss')</script>")
            == "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;"
        )
        assert security.sanitize_input("line1\nline2") == "line1<br>line2"
        assert security.sanitize_input("  padded  ") == "padded"
        assert security.sanitize_input("a" * 600) == "a" * 500
        assert security.sanitize_input(None) == ""

    def test_generate_token(self):
        token1 = security.generate_token()
        token2 = security.generate_token()
        assert isinstance(token1, str)
        assert len(token1) == 32
        assert token1 != token2

    def test_generate_random_string(self):
        s_with_digits = security.generate_random_string(10, include_digits=True)
        assert len(s_with_digits) == 10
        assert s_with_digits.isalnum()

        s_no_digits = security.generate_random_string(10, include_digits=False)
        assert len(s_no_digits) == 10
        assert s_no_digits.isalpha()
        assert not any(c.isdigit() for c in s_no_digits)

    def test_calculate_age(self):
        # Birthday has passed this year
        birth_date_passed = datetime.now() - timedelta(days=365 * 25 + 10)
        assert security.calculate_age(birth_date_passed) == 25

        # Birthday has not passed this year
        birth_date_future = datetime.now() - timedelta(days=365 * 30 - 10)
        assert security.calculate_age(birth_date_future) == 29
