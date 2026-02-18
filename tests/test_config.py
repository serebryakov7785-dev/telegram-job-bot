from unittest.mock import patch

import pytest

import config


def test_init_config_success():
    """Проверка успешной инициализации конфигурации"""
    # Патчим TOKEN и ADMIN_IDS значениями
    with patch("config.Config.TOKEN", "123:test_token"), patch(
        "config.Config.ADMIN_IDS", [123456]
    ):
        assert config.init_config() is True


def test_init_config_no_token():
    """Проверка выхода при отсутствии токена"""
    # Патчим TOKEN как None
    with patch("config.Config.TOKEN", None):
        with pytest.raises(SystemExit) as excinfo:
            config.init_config()
        assert excinfo.value.code == 1


def test_init_config_no_admins(caplog):
    """Проверка предупреждения при отсутствии админов"""
    with patch("config.Config.TOKEN", "123:test_token"), patch(
        "config.Config.ADMIN_IDS", []
    ):
        config.init_config()
        # Проверяем, что в логах появилось предупреждение
        assert "Внимание: ADMIN_IDS не установлен" in caplog.text
