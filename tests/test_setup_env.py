import os
import runpy
import sys
from unittest.mock import mock_open, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestSetupEnv:
    def test_run_setup_env(self):
        """Test execution of setup_env.py script"""
        script_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "setup_env.py")
        )
        if not os.path.exists(script_path):
            pytest.skip("setup_env.py not found")

        # Mock inputs: Token, Admin ID, Enable Monitoring (n), Sentry (n)
        # Adjust inputs based on what the script actually asks
        inputs = ["123:TEST_TOKEN", "123456", "8000"]

        with patch("builtins.input", side_effect=inputs), patch(
            "builtins.open", mock_open()
        ) as mock_file, patch(
            "os.path.exists", return_value=False
        ):  # .env does not exist

            try:
                # Run the script
                runpy.run_path(script_path, run_name="__main__")
            except SystemExit:
                pass
            except StopIteration:
                pass  # Ran out of inputs

            # Verify writing to .env
            handle = mock_file()
            handle.write.assert_called()
            # We can check if content was written
            args = handle.write.call_args_list
            content = "".join([call[0][0] for call in args])
            assert "TELEGRAM_BOT_TOKEN" in content
