import re
import random
import string
import hashlib
import logging
import time
from typing import Tuple, Optional, Dict, Any, Callable
from datetime import datetime
from config import UZBEK_OPERATORS


# ================= ВАЛИДАЦИЯ ТЕЛЕФОНА =================
def is_valid_uzbek_phone(phone: str) -> bool:
    """Проверка номера Узбекистана с улучшенной валидацией"""
    if not phone or not isinstance(phone, str):
        return False

    # Очищаем от всех нецифровых символов, кроме +
    clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')

    # Убираем плюс для единообразной обработки
    if clean_phone.startswith('+'):
        clean_phone = clean_phone[1:]

    # Проверяем длину
    if len(clean_phone) == 9:
        # Формат: 901234567
        operator = clean_phone[0:2]
        return operator in UZBEK_OPERATORS and clean_phone.isdigit()

    elif len(clean_phone) == 12 and clean_phone.startswith('998'):
        # Формат: 998901234567
        operator = clean_phone[3:5]
        return operator in UZBEK_OPERATORS and clean_phone.isdigit()

    return False


def format_phone(phone: str) -> str:
    """Форматирование телефона в стандартный формат +998XXXXXXXXX"""
    if not phone:
        return ""

    # Очищаем от всех нецифровых символов
    clean_phone = ''.join(filter(str.isdigit, phone))

    if len(clean_phone) == 9:
        # 901234567 -> +998901234567
        operator = clean_phone[0:2]
        if operator in UZBEK_OPERATORS:
            return f"+998{clean_phone}"

    elif len(clean_phone) == 12 and clean_phone.startswith('998'):
        # 998901234567 -> +998901234567
        return f"+{clean_phone}"

    # Пытаемся исправить другие форматы
    if clean_phone.startswith('8') and len(clean_phone) == 10:
        # 8901234567 -> +7901234567 (но это Россия, не Узбекистан)
        # Лучше вернуть как есть или обработать как ошибку
        return phone

    # Если не удалось отформатировать, возвращаем очищенную версию
    return clean_phone if clean_phone else phone


def extract_phone_operator(phone: str) -> Optional[str]:
    """Извлечение кода оператора из номера"""
    formatted = format_phone(phone)
    if formatted.startswith('+998') and len(formatted) == 13:
        return formatted[4:6]  # +998 90 1234567 -> 90
    return None


def get_operator_name(operator_code: str) -> str:
    """Получение названия оператора по коду"""
    operator_names = {
        '90': 'Beeline',
        '91': 'Beeline',
        '93': 'Ucell',
        '94': 'Ucell',
        '95': 'Uzmobile',
        '97': 'Uzmobile',
        '98': 'Perfectum Mobile',
        '99': 'Uzmobile',
        '88': 'Uzmobile',
        '77': 'Uzmobile',
        '33': 'Humans',
        '50': 'Uzmobile',
        '55': 'Ucell'
    }
    return operator_names.get(operator_code, 'Неизвестный оператор')


# ================= ЦЕНЗУРА =================
def contains_profanity(text: str) -> bool:
    """Проверка текста на наличие нецензурной лексики (RU, EN, UZ)"""
    if not text:
        return False

    text_lower = text.lower()

    # Паттерны с границами слов для уменьшения ложных срабатываний
    patterns = [
        # Русские маты (кириллица) - Расширенный список
        r'\bхуй\w*', r'\bхуе\w*', r'\bхуё\w*', r'\bхуя\w*',
        r'\bпизд\w*',
        r'\bеб(а|у|л)\w*', r'\bеб(а|у|л)н\w*',  # ебать, ебучий, ебло, еблан
        r'\bбля(д|т)\w*',
        r'\bмуд(а|о)(к|ч)\w*',
        r'\bпид(о|а|е)р\w*',
        r'\bг(а|о)ндон\w*',
        r'\bшлюх\w*',
        r'\bсук(а|и)\b', r'\bсукин\w*', r'\bсуч(к|а)\w*',
        r'\bзалуп\w*',
        r'\bманд(а|ы|у)\b',
        r'\bдолбо(е|ё)б\w*',
        r'\bхер\w*', r'\bпохер\w*', r'\bнахер\w*',
        r'\bчмо\w*', r'\bлох\w*', r'\bдроч\w*',
        r'\bдурак\w*', r'\bдебил\w*', r'\bидиот\w*',

        # Русские маты (латиница/транслит)
        r'\b(x|h)u(y|i)\w*', r'\bpizd\w*',
        r'\beb(a|l|u)(?!y)\w*',  # ebat, ebal, ebu (исключая ebay)
        r'\bblya(d|t)\w*', r'\bmud(a|o)k\w*',
        r'\bpid(o|a|e)r\w*', r'\bgandon\w*',
        r'\bsuk(a|i)\b', r'\bzalup\w*',
        r'\bdolbo(e|y)b\w*', r'\bxer\w*', r'\bpoher\w*',

        # Английские маты (латиница)
        r'\bfuck\w*', r'\bshit\b', r'\bbitch\w*',
        r'\bdick\w*', r'\bcock\w*', r'\bpussy\w*', r'\basshole\w*', r'\bcunt\w*', r'\bbastard\w*',
        r'\bnigger\w*', r'\bwhore\w*', r'\bslut\w*',

        # Английские маты (кириллица)
        r'\bфак\b', r'\bфак(и|е|о)\w*', r'\bмазафак\w*',  # фак, факинг, факер
        r'\bшит\b', r'\bбулшит\w*',
        r'\bбич\b', r'\bпусси\w*',
        r'\bдикх(е|э)д\w*', r'\b(а|э)схол\w*', r'\bка(н|м)шот\w*',
        r'\bниггер\w*',

        # Узбекские маты (латиница и кириллица)
        r'\b(jalab|жала б)\w*',
        r'\b(qotoq|qo\'toq|коток|қотақ)\w*',
        r'\b(siktir|сиктир)\w*',
        r'\b(sikay|сикай)\w*',
        r'\b(onangni|онангни)\w*',
        r'\b(haromi|хароми)\w*',
        r'\b(dalbayob|далбаёб)\w*',
        r'\b(gandon|гандон)\w*',
        r'\b(chumo|чумо)\w*'
    ]

    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True

    return False


# ================= ВАЛИДАЦИЯ EMAIL =================
def is_valid_email(email: str) -> bool:
    """Проверка валидности email с улучшенной валидацией"""
    if not email or not isinstance(email, str):
        return False

    email = email.strip().lower()

    # Базовый паттерн
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(pattern, email):
        return False

    # Дополнительные проверки
    # 1. Проверка длины
    if len(email) > 254:  # RFC 5321 ограничение
        return False

    # 2. Проверка локальной части (до @)
    local_part = email.split('@')[0]
    if len(local_part) > 64:  # RFC 5321 ограничение
        return False

    # 3. Проверка на последовательные точки
    if '..' in email:
        return False

    # 4. Проверка домена
    domain = email.split('@')[1]
    if domain.startswith('.') or domain.endswith('.'):
        return False

    return True


def extract_email_domain(email: str) -> Optional[str]:
    """Извлечение домена из email"""
    if not is_valid_email(email):
        return None
    return email.split('@')[1].lower()


# ================= ВАЛИДАЦИЯ ПАРОЛЯ =================
def validate_password(password: str) -> Tuple[bool, str]:  # noqa: C901
    """Валидация пароля с улучшенными проверками"""
    if not password or not isinstance(password, str):
        return False, "❌ Пароль не может быть пустым"

    password = password.strip()

    # 1. Проверка длины
    if len(password) < 8:
        return False, "❌ Пароль должен содержать минимум 8 символов"

    if len(password) > 100:
        return False, "❌ Пароль слишком длинный (максимум 100 символов)"

    # 2. Проверка на наличие цифр
    if not any(char.isdigit() for char in password):
        return False, "❌ Пароль должен содержать хотя бы одну цифру"

    # 3. Проверка на наличие букв
    if not any(char.isalpha() for char in password):
        return False, "❌ Пароль должен содержать хотя бы одну букву"

    # 4. Проверка на наличие заглавных букв
    if not any(char.isupper() for char in password):
        return False, "❌ Пароль должен содержать хотя бы одну заглавную букву"

    # 5. Проверка на наличие строчных букв
    if not any(char.islower() for char in password):
        return False, "❌ Пароль должен содержать хотя бы одну строчную букву"

    # 6. Проверка на спецсимволы (опционально)
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(char in special_chars for char in password):
        return False, "❌ Пароль должен содержать хотя бы один специальный символ (!@#$%^&* и т.д.)"
    # 8. Проверка на последовательности
    if is_sequential(password):
        return False, "❌ Пароль содержит простую последовательность символов"

    # 7. Проверка на распространенные пароли (в конце, после всех проверок на сложность)
    if password.lower() in _COMMON_PASSWORDS:
        return False, "❌ Пароль слишком простой и распространенный"

    return True, "✅ Пароль принят"


def is_sequential(text: str) -> bool:
    """Проверка на последовательности (123, abc, qwerty)"""
    text_lower = text.lower()

    sequential_patterns = [
        '123456', '234567', '345678', '456789',
        'abcdef', 'bcdefg', 'cdefgh', 'defghi', 'efghij', 'fghijk',
        'qwerty', 'asdfgh', 'zxcvbn'
    ]

    for pattern in sequential_patterns:
        if pattern in text_lower:
            return True

    # Проверка на повторяющиеся символы
    if len(set(text)) < len(text) / 2:  # Больше половины символов повторяются
        return True

    return False


def generate_strong_password(length: int = 12) -> str:
    """Генерация сильного пароля"""
    if length < 8:
        length = 8

    # Наборы символов
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # Гарантируем наличие всех типов символов
    password_chars = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special)
    ]

    # Дополняем случайными символами
    all_chars = lowercase + uppercase + digits + special
    password_chars.extend(random.choice(all_chars) for _ in range(length - 4))

    # Перемешиваем
    random.shuffle(password_chars)

    return ''.join(password_chars)


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

    # Разрешенные символы: буквы, цифры, подчеркивание, точка, дефис
    if not re.match(r'^[a-zA-Z0-9_.-]+$', login):
        return False, "❌ Используйте только буквы, цифры, точку, дефис и подчеркивание"

    # Не может начинаться или заканчиваться точкой или дефисом
    if login.startswith('.') or login.startswith('-') or login.endswith('.') or login.endswith('-'):
        return False, "❌ Логин не может начинаться или заканчиваться точкой или дефисом"

    # Не может содержать две точки подряд
    if '..' in login:
        return False, "❌ Логин не может содержать две точки подряд"

    return True, "✅ Логин принят"


# ================= ВАЛИДАЦИЯ ПАРОЛЯ (КОНСТАНТЫ) =================
_COMMON_PASSWORDS = {
    'password', '123456', '12345678', '123456789', 'qwerty',
    'admin', 'password123', 'uzbekistan', 'tashkent'
}


# ================= КАПЧА =================
def generate_captcha() -> Tuple[str, int]:
    """Генерация капчи с положительными ответами"""
    operation = random.choice(['+', '-', '*'])

    if operation == '+':
        # Сложение: a + b
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        answer = a + b
        question = f"{a} + {b}"

    elif operation == '-':
        # Вычитание: гарантируем положительный результат
        a = random.randint(5, 25)
        b = random.randint(1, a - 1)  # b всегда меньше a
        answer = a - b
        question = f"{a} - {b}"

    else:  # '*'
        # Умножение: небольшие числа для простоты
        a = random.randint(2, 5)
        b = random.randint(2, 5)
        answer = a * b
        question = f"{a} × {b}"

    return question, answer


def generate_text_captcha() -> Tuple[str, str]:
    """Генерация текстовой капчи (альтернатива математической)"""
    # Простые математические вопросы на русском
    captchas = [
        ("Сколько будет 2 + 2?", "4"),
        ("Сколько дней в неделе?", "7"),
        ("Сколько букв в слове 'привет'?", "6"),
        ("Напишите число после 9", "10"),
        ("Сколько углов у квадрата?", "4"),
        ("Сколько месяцев в году?", "12"),
        ("Сколько пальцев на одной руке?", "5"),
    ]

    question, answer = random.choice(captchas)
    return question, answer


def validate_captcha(user_answer: str, correct_answer: Any) -> bool:
    """Проверка ответа капчи"""
    if not user_answer:
        return False

    user_answer = user_answer.strip().lower()

    # Если правильный ответ - число
    if isinstance(correct_answer, (int, float)):
        try:
            user_num = int(user_answer)
            return user_num == correct_answer and user_num > 0
        except ValueError:
            # Пробуем распознать текстовые числа
            number_words = {
                'один': 1, 'два': 2, 'три': 3, 'четыре': 4, 'пять': 5,
                'шесть': 6, 'семь': 7, 'восемь': 8, 'девять': 9, 'десять': 10
            }
            if user_answer in number_words:
                return number_words[user_answer] == correct_answer
            return False

    # Если правильный ответ - строка
    elif isinstance(correct_answer, str):
        return user_answer == correct_answer.lower()

    return False


# ================= УТИЛИТЫ ОТМЕНЫ =================
CANCEL_WORDS = {
    'отмена', 'отменить', 'назад', 'вернуться', 'отбой',
    'стоп', 'stop', 'cancel', 'выход', 'меню',
    '/start', '/cancel', '/menu', '/выход',
    '🏠', '❌', '🚫'
}
# Компилируем регулярное выражение для поиска слов отмены как целых слов
_WORD_BOUNDED_CANCEL_WORDS = [w for w in CANCEL_WORDS if w.isalpha()]
_CANCEL_REGEX = re.compile(r'\b(' + '|'.join(_WORD_BOUNDED_CANCEL_WORDS) + r')\b', re.IGNORECASE)


def cancel_request(text: str) -> bool:
    """Проверка, хочет ли пользователь отменить, с использованием границ слов."""
    if not text or not isinstance(text, str):
        return False

    text_lower = text.lower().strip()

    # 1. Проверка на точное совпадение (самый быстрый и надежный способ)
    if text_lower in CANCEL_WORDS:
        return True

    # 2. Используем регулярное выражение для поиска целых слов внутри фразы
    if _CANCEL_REGEX.search(text_lower):
        return True

    return False


def create_cancel_keyboard() -> Dict[str, Any]:
    """Создание клавиатуры отмены (для JSON ответов)"""
    return {
        'keyboard': [[{'text': '❌ Отмена'}]],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }


# ================= ФОРМАТИРОВАНИЕ =================
def show_phone_format_example() -> str:
    """Примеры номеров Узбекистана"""
    operators_str = ', '.join(UZBEK_OPERATORS[:5]) + "..."

    examples = [
        "+998901234567",
        "998901234567",
        "901234567",
        "90 123 45 67",
        "(90) 123-45-67"
    ]

    examples_text = "\n".join([f"• `{example}`" for example in examples])

    return (
        "📱 *Формат номера Узбекистана:*\n\n"
        f"*✅ Примеры:*\n{examples_text}\n\n"
        f"*📞 Коды операторов:* {operators_str}\n\n"
        "*💡 Все форматы будут преобразованы в:* +998XXXXXXXXX"
    )


def format_datetime(dt: datetime) -> str:
    """Форматирование даты и времени для пользователя"""
    now = datetime.now()
    diff = now - dt

    if diff.days == 0:
        if diff.seconds < 60:
            return "только что"
        elif diff.seconds < 3600:
            minutes = diff.seconds // 60
            return f"{minutes} мин. назад"
        else:
            hours = diff.seconds // 3600
            return f"{hours} ч. назад"
    elif diff.days == 1:
        return "вчера"
    elif diff.days < 7:
        return f"{diff.days} дн. назад"
    else:
        return dt.strftime("%d.%m.%Y")


# ================= БЕЗОПАСНОСТЬ =================
def sanitize_input(text: str, max_length: int = 500) -> str:
    """Очистка пользовательского ввода от потенциально опасных символов"""
    if not text:
        return ""

    # Убираем лишние пробелы
    text = text.strip()

    # Ограничиваем длину
    if len(text) > max_length:
        text = text[:max_length]

    # Убираем опасные HTML/JS символы (базовая защита)
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
        '\n': '<br>'
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def generate_token(length: int = 32) -> str:
    """Генерация токена для восстановления пароля и т.д."""
    return hashlib.sha256(f"{random.random()}{time.time()}".encode()).hexdigest()[:length]


# ================= УТИЛИТЫ РАБОТЫ С ТЕКСТОМ =================
def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Обрезка текста с добавлением суффикса"""
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)].rstrip() + suffix


def create_pagination(current_page: int, total_pages: int, max_buttons: int = 5) -> list:
    """Создание пагинации"""
    if total_pages <= 1:
        return []

    # Вычисляем диапазон кнопок
    half = max_buttons // 2
    start = max(1, current_page - half)
    end = min(total_pages, start + max_buttons - 1)

    # Корректируем начало, если достигли конца
    if end - start + 1 < max_buttons:
        start = max(1, end - max_buttons + 1)

    buttons = []

    # Кнопка "Назад"
    if current_page > 1:
        buttons.append({"text": "◀️ Назад", "callback_data": f"page_{current_page - 1}"})

    # Номера страниц
    for page in range(start, end + 1):
        if page == current_page:
            buttons.append({"text": f"• {page} •", "callback_data": f"page_{page}"})
        else:
            buttons.append({"text": str(page), "callback_data": f"page_{page}"})

    # Кнопка "Вперед"
    if current_page < total_pages:
        buttons.append({"text": "Вперед ▶️", "callback_data": f"page_{current_page + 1}"})

    return buttons


# ================= ОБРАБОТКА ОШИБОК =================
def safe_execute(func: Callable, *args, **kwargs) -> Tuple[Any, Optional[str]]:
    """
    Безопасное выполнение функции с обработкой ошибок
    Возвращает (результат, ошибка)
    """
    try:
        result = func(*args, **kwargs)
        return result, None
    except Exception as e:
        error_msg = f"❌ Ошибка в {func.__name__}: {type(e).__name__}: {str(e)}"
        logging.error(error_msg, exc_info=True)
        return None, error_msg


def retry_on_error(func: Callable, max_retries: int = 3, delay: float = 1.0) -> Callable:
    """Создает обертку, которая повторяет выполнение функции при ошибке."""
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt >= max_retries - 1:
                    raise last_exception
                logging.warning(f"Попытка {attempt + 1} из {max_retries} не удалась: {e}", exc_info=True)
                time.sleep(delay * (attempt + 1))
    return wrapper


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

    # Проверка на допустимые символы (буквы, пробелы, дефисы, апострофы)
    if not re.match(r'^[a-zA-Zа-яА-ЯёЁўқғҳЎҚҒҲ\s\-\']+$', name):
        return False, "❌ Имя содержит недопустимые символы"

    # Проверка на множественные пробелы
    if '  ' in name:
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


# ================= ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ =================
def generate_random_string(length: int = 8, include_digits: bool = True) -> str:
    """Генерация случайной строки"""
    chars = string.ascii_letters
    if include_digits:
        chars += string.digits

    return ''.join(random.choice(chars) for _ in range(length))


def calculate_age(birth_date: datetime) -> int:
    """Вычисление возраста по дате рождения"""
    today = datetime.now()

    # Вычисляем разницу в годах
    age = today.year - birth_date.year

    # Корректируем, если день рождения еще не наступил в этом году
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1

    return age


def mask_email(email: str) -> str:
    """Маскирование email для безопасности"""
    if not is_valid_email(email):
        return email

    local, domain = email.split('@')

    if len(local) <= 2:
        return f"{local}***@{domain}"

    # Оставляем первую и последнюю букву локальной части
    masked_local = local[0] + '*' * (len(local) - 2) + local[-1]

    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """Маскирование телефона для безопасности"""
    formatted = format_phone(phone)

    if not formatted.startswith('+998') or len(formatted) != 13:
        return phone

    # Маскируем: +998 90 *** ** 67
    return f"{formatted[:7]}***{formatted[10:]}"


def escape_markdown(text: str) -> str:
    """
    Escapes characters for legacy Telegram Markdown.
    In legacy mode, we need to escape `*`, `_`, '`' and '['.
    """
    if not text:
        return ""
    text = str(text)
    text = text.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[').replace(']', '\\]')
    return text
