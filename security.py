import hashlib
import random
import re
import string
import time
from datetime import datetime
from typing import Tuple


def contains_profanity(text: str) -> bool:
    """Проверка текста на наличие нецензурной лексики (RU, EN, UZ)"""
    if not text:
        return False
    text_lower = text.lower()
    patterns = [
        r"\bхуй\w*",
        r"\bхуе\w*",
        r"\bхуё\w*",
        r"\bхуя\w*",
        r"\bпизд\w*",
        r"\bеб(а|у|л)\w*",
        r"\bеб(а|у|л)н\w*",
        r"\bбля(д|т)\w*",
        r"\bмуд(а|о)(к|ч)\w*",
        r"\bпид(о|а|е)р\w*",
        r"\bг(а|о)ндон\w*",
        r"\bшлюх\w*",
        r"\bсук(а|и)\b",
        r"\bсукин\w*",
        r"\bсуч(к|а)\w*",
        r"\bзалуп\w*",
        r"\bманд(а|ы|у)\b",
        r"\bдолбо(е|ё)б\w*",
        r"\bхер\w*",
        r"\bпохер\w*",
        r"\bнахер\w*",
        r"\bчмо\w*",
        r"\bлох\w*",
        r"\bдроч\w*",
        r"\bдурак\w*",
        r"\bдебил\w*",
        r"\bидиот\w*",
        r"\b(x|h)u(y|i)\w*",
        r"\bpizd\w*",
        r"\beb(a|l|u)(?!y)\w*",
        r"\bblya(d|t)\w*",
        r"\bmud(a|o)k\w*",
        r"\bpid(o|a|e)r\w*",
        r"\bgandon\w*",
        r"\bsuk(a|i)\b",
        r"\bzalup\w*",
        r"\bdolbo(e|y)b\w*",
        r"\bxer\w*",
        r"\bpoher\w*",
        r"\bfuck\w*",
        r"\bshit\b",
        r"\bbitch\w*",
        r"\bdick\w*",
        r"\bcock\w*",
        r"\bpussy\w*",
        r"\basshole\w*",
        r"\bcunt\w*",
        r"\bbastard\w*",
        r"\bnigger\w*",
        r"\bwhore\w*",
        r"\bslut\w*",
        r"\bфак\b",
        r"\bфак(и|е|о)\w*",
        r"\bмазафак\w*",
        r"\bшит\b",
        r"\bбулшит\w*",
        r"\bбич\b",
        r"\bпусси\w*",
        r"\bдикх(е|э)д\w*",
        r"\b(а|э)схол\w*",
        r"\bка(н|м)шот\w*",
        r"\bниггер\w*",
        r"\b(jalab|жала б)\w*",
        r"\b(qotoq|qo\'toq|коток|қотақ)\w*",
        r"\b(siktir|сиктир)\w*",
        r"\b(sikay|сикай)\w*",
        r"\b(onangni|онангни)\w*",
        r"\b(haromi|хароми)\w*",
        r"\b(dalbayob|далбаёб)\w*",
        r"\b(gandon|гандон)\w*",
        r"\b(chumo|чумо)\w*",
    ]
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def generate_strong_password(length: int = 12) -> str:
    """Генерация сильного пароля"""
    if length < 8:
        length = 8
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    password_chars = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special),
    ]
    all_chars = lowercase + uppercase + digits + special
    password_chars.extend(random.choice(all_chars) for _ in range(length - 4))
    random.shuffle(password_chars)
    return "".join(password_chars)


def generate_captcha() -> Tuple[str, int]:
    """Генерация капчи с положительными ответами"""
    operation = random.choice(["+", "-", "*"])
    if operation == "+":
        a, b = random.randint(1, 20), random.randint(1, 20)
        return f"{a} + {b}", a + b
    elif operation == "-":
        a = random.randint(5, 25)
        b = random.randint(1, a - 1)
        return f"{a} - {b}", a - b
    else:
        a, b = random.randint(2, 5), random.randint(2, 5)
        return f"{a} × {b}", a * b


def generate_text_captcha() -> Tuple[str, str]:
    """Генерация текстовой капчи"""
    captchas = [
        ("Сколько будет 2 + 2?", "4"),
        ("Сколько дней в неделе?", "7"),
        ("Сколько букв в слове 'привет'?", "6"),
        ("Напишите число после 9", "10"),
        ("Сколько углов у квадрата?", "4"),
        ("Сколько месяцев в году?", "12"),
        ("Сколько пальцев на одной руке?", "5"),
    ]
    return random.choice(captchas)


def sanitize_input(text: str, max_length: int = 500) -> str:
    """Очистка пользовательского ввода"""
    if not text:
        return ""
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length]
    replacements = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
        "\n": "<br>",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def generate_token(length: int = 32) -> str:
    """Генерация токена"""
    return hashlib.sha256(f"{random.random()}{time.time()}".encode()).hexdigest()[
        :length
    ]


def generate_random_string(length: int = 8, include_digits: bool = True) -> str:
    """Генерация случайной строки"""
    chars = string.ascii_letters
    if include_digits:
        chars += string.digits
    return "".join(random.choice(chars) for _ in range(length))


def calculate_age(birth_date: datetime) -> int:
    today = datetime.now()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age
