import os
import sys
from unittest.mock import MagicMock, patch

import requests

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Now import the bot module
import bot  # noqa: E402


def test_run_bot_keyboard_interrupt():
    """Тест остановки бота по Ctrl+C"""
    mock_bot_instance = MagicMock()
    mock_bot_instance.polling.side_effect = KeyboardInterrupt

    with patch("time.sleep"), patch("bot.logging"):
        bot.run_bot(bot=mock_bot_instance)

    mock_bot_instance.stop_bot.assert_called_once()


def test_run_bot_polling_exception():
    """Тест, что бот останавливается при критической ошибке в polling"""
    mock_bot_instance = MagicMock()
    # Simulate a critical error that stops the polling
    mock_bot_instance.polling.side_effect = Exception("Polling error")

    with patch("bot.close_all_connections") as mock_close_conn, patch("bot.logging"):
        bot.run_bot(bot=mock_bot_instance)

    # The bot should attempt to stop gracefully
    mock_close_conn.assert_called_once()
    mock_bot_instance.stop_bot.assert_called_once()


def test_run_bot_connection_error():
    """Тест, что бот останавливается при невосстановимой ошибке соединения"""
    mock_bot_instance = MagicMock()
    # non_stop=True should handle this, but if it fails and the exception propagates,
    # the bot should stop gracefully.
    mock_bot_instance.polling.side_effect = requests.exceptions.ConnectionError(
        "Connection lost"
    )

    with patch("bot.close_all_connections") as mock_close_conn, patch("bot.logging"):
        bot.run_bot(bot=mock_bot_instance)

    # The bot should attempt to stop gracefully
    mock_close_conn.assert_called_once()
    mock_bot_instance.stop_bot.assert_called_once()


def test_run_bot_read_timeout():
    """Тест, что бот останавливается при невосстановимом таймауте"""
    mock_bot_instance = MagicMock()
    # non_stop=True should handle this, but if it fails and the exception propagates,
    # the bot should stop gracefully.
    mock_bot_instance.polling.side_effect = requests.exceptions.ReadTimeout("Timeout")

    with patch("bot.close_all_connections") as mock_close_conn, patch("bot.logging"):
        bot.run_bot(bot=mock_bot_instance)

    # The bot should attempt to stop gracefully
    mock_close_conn.assert_called_once()
    mock_bot_instance.stop_bot.assert_called_once()


def test_main_block_success():
    """Тест успешного запуска из __main__"""
    import runpy

    mock_bot_instance = MagicMock()
    mock_bot_instance.polling.side_effect = KeyboardInterrupt

    with patch("bot_factory.create_bot", return_value=mock_bot_instance), patch(
        "bot.logging"
    ), patch("time.sleep"):

        # Запускаем bot.py как главный модуль
        runpy.run_module("bot", run_name="__main__")

        mock_bot_instance.polling.assert_called()


def test_run_bot_polling_critical_error():
    """Тест критической ошибки в polling"""
    mock_bot_instance = MagicMock()
    mock_bot_instance.polling.side_effect = Exception("Critical")

    with patch("bot.logging.critical") as mock_log, patch(
        "bot.close_all_connections"
    ), patch("bot.logging.info"), patch("bot.logging.warning"):
        bot.run_bot(bot=mock_bot_instance)
        mock_log.assert_called()
        mock_bot_instance.stop_bot.assert_called_once()


def test_run_bot_polling_normal_exit():
    """Тест нормального завершения polling (без перезапуска)"""
    mock_bot_instance = MagicMock()
    # polling() returns None when stopped, e.g. by bot.stop_polling()
    mock_bot_instance.polling.return_value = None

    with patch("bot.close_all_connections") as mock_close_conn, patch("bot.logging"):
        bot.run_bot(bot=mock_bot_instance)

    # Polling should be called once
    mock_bot_instance.polling.assert_called_once()
    # The bot should stop gracefully
    mock_close_conn.assert_called_once()
    mock_bot_instance.stop_bot.assert_called_once()


def test_run_bot_health_check_registration():
    """Тест проверки БД при запуске"""
    mock_bot_instance = MagicMock()
    mock_bot_instance.polling.return_value = None

    with patch("bot.create_bot", return_value=mock_bot_instance), patch(
        "bot.check_connection_health", return_value=True
    ) as mock_health, patch("bot.get_pool_stats", return_value={"used": 1}), patch(
        "bot.logging"
    ), patch(
        "bot.close_all_connections"
    ):

        bot.run_bot(bot=mock_bot_instance)

        # 1. Проверка вызова health check при старте
        mock_health.assert_called()


def test_run_bot_db_failure():
    """Тест остановки бота, если БД не отвечает при запуске"""
    mock_bot_instance = MagicMock()

    with patch("bot.create_bot", return_value=mock_bot_instance), patch(
        "bot.check_connection_health", return_value=False
    ), patch("bot.logging.critical") as mock_log, patch("sys.exit") as mock_exit:

        bot.run_bot(bot=mock_bot_instance)

        mock_log.assert_called_with("❌ БД не отвечает! Запуск отменен.")
        mock_exit.assert_called_with(1)
