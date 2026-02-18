import re
from typing import Any, Tuple

from config import Config


# ================= ВАЛИДАЦИЯ ТЕЛЕФОНА =================
def is_valid_uzbek_phone(phone: str) -> bool:
    """Проверка номера Узбекистана с улучшенной валидацией"""
    if not phone or not isinstance(phone, str):
        return False

    # Очищаем от всех нецифровых символов, кроме +
    clean_phone = "".join(c for c in phone if c.isdigit() or c == "+")

    # Убираем плюс для единообразной обработки
    if clean_phone.startswith("+"):
        clean_phone = clean_phone[1:]

    # Проверяем длину
    if len(clean_phone) == 9:
        # Формат: 901234567
        operator = clean_phone[0:2]
        return operator in Config.UZBEK_OPERATORS and clean_phone.isdigit()

    elif len(clean_phone) == 12 and clean_phone.startswith("998"):
        # Формат: 998901234567
        operator = clean_phone[3:5]
        return operator in Config.UZBEK_OPERATORS and clean_phone.isdigit()

    return False


# ================= ВАЛИДАЦИЯ EMAIL =================
def is_valid_email(email: str) -> bool:
    """Проверка валидности email с улучшенной валидацией"""
    if not email or not isinstance(email, str):
        return False

    email = email.strip().lower()

    # Базовый паттерн
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(pattern, email):
        return False

    # Дополнительные проверки
    if len(email) > 254:
        return False
    local_part = email.split("@")[0]
    if len(local_part) > 64:
        return False
    if ".." in email:
        return False
    domain = email.split("@")[1]
    if domain.startswith(".") or domain.endswith("."):
        return False

    return True


# ================= ВАЛИДАЦИЯ ПАРОЛЯ =================

_COMMON_PASSWORDS = {  # noqa: E302
    "password",
    "123456",
    "12345678",
    "123456789",
    "qwerty",
    "admin",
    "password123",
    "uzbekistan",
    "tashkent",
}


def validate_password(password: str) -> Tuple[bool, str]:
    """Валидация пароля с улучшенными проверками"""
    if not password or not isinstance(password, str):
        return False, "❌ Пароль не может быть пустым"

    password = password.strip()

    if len(password) < 8:
        return False, "❌ Пароль должен содержать минимум 8 символов"
    if len(password) > 100:
        return False, "❌ Пароль слишком длинный (максимум 100 символов)"
    if not any(char.isdigit() for char in password):
        return False, "❌ Пароль должен содержать хотя бы одну цифру"
    if not any(char.isalpha() for char in password):
        return False, "❌ Пароль должен содержать хотя бы одну букву"
    if not any(char.isupper() for char in password):
        return False, "❌ Пароль должен содержать хотя бы одну заглавную букву"
    if not any(char.islower() for char in password):
        return False, "❌ Пароль должен содержать хотя бы одну строчную букву"

    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(char in special_chars for char in password):
        return (
            False,
            "❌ Пароль должен содержать хотя бы один специальный символ (!@#$%^&* и т.д.)",
        )

    if is_sequential(password):
        return False, "❌ Пароль содержит простую последовательность символов"
    if password.lower() in _COMMON_PASSWORDS:
        return False, "❌ Пароль слишком простой и распространенный"

    return True, "✅ Пароль принят"


def is_sequential(text: str) -> bool:
    """Проверка на последовательности (123, abc, qwerty)"""
    text_lower = text.lower()
    sequential_patterns = [
        "123456",
        "234567",
        "345678",
        "456789",
        "abcdef",
        "bcdefg",
        "cdefgh",
        "defghi",
        "efghij",
        "fghijk",
        "qwerty",
        "asdfgh",
        "zxcvbn",
    ]
    for pattern in sequential_patterns:
        if pattern in text_lower:
            return True
    if len(set(text)) < len(text) / 2:
        return True
    return False


# ================= ВАЛИДАЦИЯ ЛОГИНА =================
def validate_login(login: str) -> Tuple[bool, str]:
    """Валидация логина"""
    if not login or not isinstance(login, str):
        return False, "❌ Логин не может быть пустым"
    login = login.strip()
    if len(login) < 3:
        return False, "❌ Логин должен содержать минимум 3 символа"
    if len(login) > 50:
        return False, "❌ Логин слишком длинный (максимум 50 символов)"
    if not re.match(r"^[a-zA-Z0-9_.-]+$", login):
        return False, "❌ Используйте только буквы, цифры, точку, дефис и подчеркивание"
    if (
        login.startswith(".")
        or login.startswith("-")
        or login.endswith(".")
        or login.endswith("-")
    ):
        return (
            False,
            "❌ Логин не может начинаться или заканчиваться точкой или дефисом",
        )
    if ".." in login:
        return False, "❌ Логин не может содержать две точки подряд"
    return True, "✅ Логин принят"


# ================= ВАЛИДАЦИЯ ДАННЫХ =================
def validate_name(name: str) -> Tuple[bool, str]:
    """Валидация имени/названия"""
    if not name or not isinstance(name, str):
        return False, "❌ Имя не может быть пустым"
    name = name.strip()
    if len(name) < 2:
        return False, "❌ Имя слишком короткое (минимум 2 символа)"
    if len(name) > 100:
        return False, "❌ Имя слишком длинное (максимум 100 символов)"
    if not re.match(r"^[a-zA-Zа-яА-ЯёЁўқғҳЎҚҒҲ\s\-\']+$", name):
        return False, "❌ Имя содержит недопустимые символы"
    if "  " in name:
        return False, "❌ Уберите лишние пробелы в имени"
    return True, "✅ Имя принято"


def validate_age(age_str: str) -> Tuple[bool, int, str]:
    """Валидация возраста"""
    try:
        age = int(age_str.strip())
        if age < 16:
            return False, age, "❌ Минимальный возраст - 16 лет"
        if age > 100:
            return False, age, "❌ Возраст не может превышать 100 лет"
        return True, age, "✅ Возраст принят"
    except ValueError:
        return False, 0, "❌ Введите число для возраста"


def validate_captcha(user_answer: str, correct_answer: Any) -> bool:
    """Проверка ответа капчи"""
    if not user_answer:
        return False
    user_answer = user_answer.strip().lower()
    if isinstance(correct_answer, (int, float)):
        try:
            return int(user_answer) == correct_answer and int(user_answer) > 0
        except ValueError:
            return False
    elif isinstance(correct_answer, str):
        return user_answer == correct_answer.lower()
    return False
