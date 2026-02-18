import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import formatters  # noqa: E402


class TestUtilsFormatters:
    def test_format_phone(self):
        assert formatters.format_phone("901234567") == "+998901234567"
        assert formatters.format_phone("+998901234567") == "+998901234567"
        assert formatters.format_phone("998901234567") == "+998901234567"
        assert formatters.format_phone("(90) 123-45-67") == "+998901234567"
        assert (
            formatters.format_phone("123") == "123"
        )  # Too short/invalid for regex but returns cleaned
        assert formatters.format_phone(None) == ""

    def test_extract_phone_operator(self):
        assert formatters.extract_phone_operator("+998901234567") == "90"
        assert formatters.extract_phone_operator("901234567") == "90"
        assert formatters.extract_phone_operator("123") is None

    def test_get_operator_name(self):
        assert formatters.get_operator_name("90") == "Beeline"
        assert formatters.get_operator_name("00") == "Неизвестный оператор"

    def test_show_phone_format_example(self):
        with patch("formatters.get_text_by_lang", return_value="text"):
            assert "text" in formatters.show_phone_format_example()

    def test_format_db_datetime_to_tashkent(self):
        # Test with ZoneInfo mock if needed, or rely on system
        dt_str = "2023-01-01 10:00:00"
        formatted = formatters.format_db_datetime_to_tashkent(dt_str)
        assert isinstance(formatted, str)
        assert formatters.format_db_datetime_to_tashkent(None) == "N/A"
        assert formatters.format_db_datetime_to_tashkent("invalid") == "invalid"

    def test_format_datetime(self):
        now = datetime.now()
        assert formatters.format_datetime(now) == "только что"
        assert "мин. назад" in formatters.format_datetime(now - timedelta(minutes=5))
        assert "ч. назад" in formatters.format_datetime(now - timedelta(hours=2))
        assert "вчера" in formatters.format_datetime(now - timedelta(days=1))
        assert "дн. назад" in formatters.format_datetime(now - timedelta(days=2))
        assert "." in formatters.format_datetime(now - timedelta(days=10))

    def test_truncate_text(self):
        assert formatters.truncate_text("hello", 10) == "hello"
        assert formatters.truncate_text("hello world", 5) == "he..."
        assert formatters.truncate_text(None) == ""

    def test_create_pagination(self):
        # 1 page
        assert formatters.create_pagination(1, 1) == []
        # Middle page
        buttons = formatters.create_pagination(5, 10)
        assert len(buttons) > 0
        assert any(b["text"] == "◀️ Назад" for b in buttons)
        assert any(b["text"] == "Вперед ▶️" for b in buttons)
        # First page
        buttons = formatters.create_pagination(1, 10)
        assert not any(b["text"] == "◀️ Назад" for b in buttons)
        # Last page
        buttons = formatters.create_pagination(10, 10)
        assert not any(b["text"] == "Вперед ▶️" for b in buttons)

    def test_mask_email(self):
        assert formatters.mask_email("test@example.com") == "t**t@example.com"
        assert formatters.mask_email("ab@c.com") == "ab***@c.com"
        assert formatters.mask_email("invalid") == "invalid"

    def test_mask_phone(self):
        assert formatters.mask_phone("+998901234567") == "+998901***567"
        assert formatters.mask_phone("123") == "123"

    def test_escape_markdown(self):
        assert formatters.escape_markdown("test_bold*") == "test\\_bold\\*"
        assert formatters.escape_markdown(None) == ""
