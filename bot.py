import logging
import sys
from datetime import datetime
from typing import Any, Optional

from bot_factory import create_bot
from database.core import check_connection_health, close_all_connections, get_pool_stats

# Загрузка конфигурации
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def start_polling(bot: Any) -> None:
    """Запуск цикла polling"""
    try:
        # Параметр non_stop=True в bot.polling() уже обеспечивает автоматический перезапуск
        # при большинстве ошибок. Внешний цикл while True не нужен и мешает
        # корректной обработке остановки бота по Ctrl+C.
        bot.polling(non_stop=True, timeout=60, long_polling_timeout=60)
    except (KeyboardInterrupt, SystemExit):
        # Корректно обрабатываем прерывание работы пользователем
        logging.info("\n🛑 Бот остановлен пользователем (Ctrl+C).")
    except Exception as e:
        # Ловим любые другие критические ошибки, которые могли остановить polling
        logging.critical(
            f"❌ Критическая ошибка остановила polling: {e}", exc_info=True
        )
    finally:
        # Этот блок гарантирует, что ресурсы будут освобождены при любом исходе.
        close_all_connections()
        bot.stop_bot()


def run_bot(bot: Optional[Any] = None) -> None:
    """Запускает бота. Принимает опциональный параметр bot для тестирования."""
    if bot is None:
        bot = create_bot()

    # Проверка БД перед запуском
    if not check_connection_health():
        logging.critical("❌ БД не отвечает! Запуск отменен.")
        sys.exit(1)

    stats = get_pool_stats()
    if stats:
        logging.info(f"📊 Статистика пула PostgreSQL: {stats}")

    logging.info("=" * 60)
    logging.info("🤖 БОТ ДЛЯ ПОИСКА РАБОТЫ - УЗБЕКИСТАН 🇺🇿")
    logging.info("=" * 60)
    logging.info("🚀 Запуск: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logging.info("📱 Только номера: +998")
    logging.info("=" * 60)

    logging.info("✅ Бот запущен! Откройте Telegram и найдите своего бота")
    logging.info("=" * 60)

    try:
        bot.remove_webhook()
    except Exception:
        pass

    start_polling(bot)  # Этот вызов блокирует выполнение до остановки бота

    logging.info("Бот полностью остановлен.")


if __name__ == "__main__":
    run_bot()
