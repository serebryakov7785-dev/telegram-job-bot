import importlib
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock telebot before importing flask_app
sys.modules["telebot"] = MagicMock()
sys.modules["telebot.types"] = MagicMock()
# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Patch config.Config.TOKEN and bot_factory.create_bot before importing flask_app
# This ensures that flask_app.WEBHOOK_PATH and flask_app.bot are correctly mocked.
with patch("config.Config.TOKEN", "test_token"), patch(
    "bot_factory.create_bot"
) as mock_create_bot:
    _mock_bot_instance = MagicMock()
    mock_create_bot.return_value = _mock_bot_instance
    from flask_app import app as flask_app  # Import the app


@pytest.fixture
def mock_bot():
    return _mock_bot_instance
