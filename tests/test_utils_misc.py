import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import misc  # noqa: E402


class TestUtilsMisc:
    def test_cancel_request(self):
        assert misc.cancel_request("отмена") is True
        assert misc.cancel_request("cancel") is True
        assert misc.cancel_request("/start") is True
        assert misc.cancel_request("hello") is False
        assert misc.cancel_request(None) is False
        assert misc.cancel_request(123) is False

    def test_create_cancel_keyboard(self):
        kb = misc.create_cancel_keyboard()
        assert "keyboard" in kb
        assert kb["keyboard"][0][0]["text"] == "❌ Отмена"

    def test_safe_execute(self):
        def success_func(a, b):
            return a + b

        def fail_func():
            raise ValueError("Error")

        res, err = misc.safe_execute(success_func, 1, 2)
        assert res == 3
        assert err is None

        res, err = misc.safe_execute(fail_func)
        assert res is None
        assert "ValueError" in err

    def test_retry_on_error(self):
        mock_func = MagicMock()
        mock_func.side_effect = [Exception("Fail"), "Success"]

        decorated = misc.retry_on_error(mock_func, max_retries=3, delay=0.01)
        assert decorated() == "Success"
        assert mock_func.call_count == 2

        mock_func.reset_mock()
        mock_func.side_effect = Exception("Fail")
        with pytest.raises(Exception):
            decorated()
        assert mock_func.call_count == 3
