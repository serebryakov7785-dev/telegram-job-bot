from datetime import datetime, timedelta
from typing import Optional

from config import Config
from localization import get_text_by_lang
from validators import is_valid_email

try:
    from zoneinfo import ZoneInfo
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        ZoneInfo = None


def format_phone(phone: str) -> str:
    """Форматирование телефона в стандартный формат +998XXXXXXXXX"""
    if not phone:
        return ""
    clean_phone = "".join(filter(str.isdigit, phone))
    if len(clean_phone) == 9:
        operator = clean_phone[0:2]
        if operator in Config.UZBEK_OPERATORS:
            return f"+998{clean_phone}"
    elif len(clean_phone) == 12 and clean_phone.startswith("998"):
        return f"+{clean_phone}"
    if clean_phone.startswith("8") and len(clean_phone) == 10:
        return phone
    return clean_phone if clean_phone else phone


def extract_phone_operator(phone: str) -> Optional[str]:
    """Извлечение кода оператора из номера"""
    formatted = format_phone(phone)
    if formatted.startswith("+998") and len(formatted) == 13:
        return formatted[4:6]
    return None


def get_operator_name(operator_code: str) -> str:
    """Получение названия оператора по коду"""
    operator_names = {
        "90": "Beeline",
        "91": "Beeline",
        "93": "Ucell",
        "94": "Ucell",
        "95": "Uzmobile",
        "97": "Uzmobile",
        "98": "Perfectum Mobile",
        "99": "Uzmobile",
        "88": "Uzmobile",
        "77": "Uzmobile",
        "33": "Humans",
        "50": "Uzmobile",
        "55": "Ucell",
    }
    return operator_names.get(operator_code, "Неизвестный оператор")


def show_phone_format_example(lang: str = "ru") -> str:
    """Примеры номеров Узбекистана"""
    operators_str = ", ".join(Config.UZBEK_OPERATORS[:5]) + "..."
    examples = [
        "+998901234567",
        "998901234567",
        "901234567",
        "90 123 45 67",
        "(90) 123-45-67",
    ]
    examples_text = "\n".join([f"• `{example}`" for example in examples])
    return (
        f"{get_text_by_lang('phone_format_header', lang)}\n\n"
        f"{get_text_by_lang('phone_format_examples_header', lang)}\n{examples_text}\n\n"
        f"{get_text_by_lang('phone_format_operators_header', lang)} {operators_str}\n\n"
        f"{get_text_by_lang('phone_format_conversion_note', lang)}"
    )


def format_db_datetime_to_tashkent(
    date_str: str, format_str: str = "%d.%m.%Y %H:%M:%S"
) -> str:
    """Formats a UTC datetime string from the DB to Tashkent time."""
    if not date_str:
        return "N/A"
    try:
        utc_dt = datetime.strptime(str(date_str).split(".")[0], "%Y-%m-%d %H:%M:%S")
        if ZoneInfo:
            tashkent_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(
                ZoneInfo("Asia/Tashkent")
            )
        else:
            tashkent_dt = utc_dt + timedelta(hours=5)
        return tashkent_dt.strftime(format_str)
    except (ValueError, TypeError):
        return str(date_str)


def format_datetime(dt: datetime) -> str:
    """Форматирование даты и времени для пользователя"""
    now = datetime.now()
    diff = now - dt
    if diff.days == 0:
        if diff.seconds < 60:
            return "только что"
        elif diff.seconds < 3600:
            return f"{diff.seconds // 60} мин. назад"
        else:
            return f"{diff.seconds // 3600} ч. назад"
    elif diff.days == 1:
        return "вчера"
    elif diff.days < 7:
        return f"{diff.days} дн. назад"
    else:
        return dt.strftime("%d.%m.%Y")


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Обрезка текста с добавлением суффикса"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)].rstrip() + suffix


def create_pagination(
    current_page: int, total_pages: int, max_buttons: int = 5
) -> list:
    """Создание пагинации"""
    if total_pages <= 1:
        return []
    half = max_buttons // 2
    start = max(1, current_page - half)
    end = min(total_pages, start + max_buttons - 1)
    if end - start + 1 < max_buttons:
        start = max(1, end - max_buttons + 1)
    buttons = []
    if current_page > 1:
        buttons.append({"text": "◀️ Назад", "callback_data": f"page_{current_page - 1}"})
    for page in range(start, end + 1):
        if page == current_page:
            buttons.append({"text": f"• {page} •", "callback_data": f"page_{page}"})
        else:
            buttons.append({"text": str(page), "callback_data": f"page_{page}"})
    if current_page < total_pages:
        buttons.append(
            {"text": "Вперед ▶️", "callback_data": f"page_{current_page + 1}"}
        )
    return buttons


def mask_email(email: str) -> str:
    """Маскирование email для безопасности"""
    if not is_valid_email(email):
        return email
    local, domain = email.split("@")
    if len(local) <= 2:
        return f"{local}***@{domain}"
    return f"{local[0]}{'*' * (len(local)-2)}{local[-1]}@{domain}"


def mask_phone(phone: str) -> str:
    """Маскирование телефона для безопасности"""
    formatted = format_phone(phone)
    if not formatted.startswith("+998") or len(formatted) != 13:
        return phone
    return f"{formatted[:7]}***{formatted[10:]}"


def escape_markdown(text: str) -> str:
    if not text:
        return ""
    return (
        str(text)
        .replace("_", "\\_")
        .replace("*", "\\*")
        .replace("`", "\\`")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )
