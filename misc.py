import logging
import re
import time
from typing import Any, Callable, Dict, Optional, Tuple

CANCEL_WORDS = {
    "отмена",
    "отменить",
    "назад",
    "вернуться",
    "отбой",
    "стоп",
    "stop",
    "cancel",
    "выход",
    "меню",
    "/start",
    "/cancel",
    "/menu",
    "/выход",
    "🏠",
    "❌",
    "🚫",
}
_WORD_BOUNDED_CANCEL_WORDS = [w for w in CANCEL_WORDS if w.isalpha()]
_CANCEL_REGEX = re.compile(
    r"\b(" + "|".join(_WORD_BOUNDED_CANCEL_WORDS) + r")\b", re.IGNORECASE
)


def cancel_request(text: str) -> bool:
    """Проверка, хочет ли пользователь отменить"""
    if not text or not isinstance(text, str):
        return False
    text_lower = text.lower().strip()
    if text_lower in CANCEL_WORDS:
        return True
    if _CANCEL_REGEX.search(text_lower):
        return True
    return False


def create_cancel_keyboard() -> Dict[str, Any]:
    """Создание клавиатуры отмены (для JSON ответов)"""
    return {
        "keyboard": [[{"text": "❌ Отмена"}]],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def safe_execute(
    func: Callable[..., Any], *args: Any, **kwargs: Any
) -> Tuple[Any, Optional[str]]:
    """Безопасное выполнение функции"""
    try:
        result = func(*args, **kwargs)
        return result, None
    except Exception as e:
        error_msg = f"❌ Ошибка в {func.__name__}: {type(e).__name__}: {str(e)}"
        logging.error(error_msg, exc_info=True)
        return None, error_msg


def retry_on_error(
    func: Callable, max_retries: int = 3, delay: float = 1.0
) -> Callable:
    """Обертка для повтора выполнения при ошибке"""

    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt >= max_retries - 1:
                    raise e
                logging.warning(
                    f"Попытка {attempt + 1} из {max_retries} не удалась: {e}",
                    exc_info=True,
                )
                time.sleep(delay * (attempt + 1))

    return wrapper
