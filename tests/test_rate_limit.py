import sys
from unittest.mock import MagicMock

# Мокаем библиотеку telebot ПЕРЕД импортом bot, чтобы тесты работали без неё
sys.modules['telebot'] = MagicMock()
sys.modules['telebot.types'] = MagicMock()

import time  # noqa: E402
import bot  # noqa: E402


class TestRateLimit:
    def setup_method(self):
        """Очистка состояния перед каждым тестом"""
        bot.user_requests.clear()
        bot.muted_users.clear()

    def test_rate_limit_allow(self):
        """Проверка, что одиночные сообщения проходят"""
        message = MagicMock()
        message.from_user.id = 12345

        # Первое сообщение должно пройти
        assert bot.check_rate_limit(message) is True
        # Пользователь не должен быть в списке заглушенных
        assert 12345 not in bot.muted_users

    def test_rate_limit_exceeded(self):
        """Проверка блокировки при превышении лимита"""
        message = MagicMock()
        message.from_user.id = 67890

        # Отправляем максимально разрешенное количество сообщений
        # bot.RATE_LIMIT = 5
        for _ in range(bot.RATE_LIMIT):
            assert bot.check_rate_limit(message) is True

        # Следующее сообщение (6-е) должно быть заблокировано
        assert bot.check_rate_limit(message) is False

        # Проверяем, что пользователь попал в бан
        assert 67890 in bot.muted_users
        # Проверяем, что время разбана установлено в будущем
        assert bot.muted_users[67890] > time.time()

    def test_mute_expiration(self):
        """Проверка автоматического разбана по истечении времени"""
        message = MagicMock()
        message.from_user.id = 11111

        # Имитируем, что пользователь был забанен, но время бана истекло (1 секунду назад)
        bot.muted_users[11111] = time.time() - 1

        # Сообщение должно пройти, а пользователь удален из списка забаненных
        assert bot.check_rate_limit(message) is True
        assert 11111 not in bot.muted_users
