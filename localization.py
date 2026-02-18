import json
import logging
import os

TRANSLATIONS = {}
LOCALES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")


def load_translations():
    """Loads all translation files from the locales directory."""
    if not os.path.exists(LOCALES_DIR):
        logging.error(f"Locales directory not found at: {os.path.abspath(LOCALES_DIR)}")
        return

    for filename in os.listdir(LOCALES_DIR):
        if filename.endswith(".json"):
            lang_code = filename.split(".")[0]
            file_path = os.path.join(LOCALES_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    TRANSLATIONS[lang_code] = json.load(f)
                logging.info(f"Successfully loaded translation: {lang_code}")
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Failed to load or parse {file_path}: {e}")


load_translations()

# Сопоставление текста кнопки с кодом языка
LANGUAGE_MAP = {"🇺🇿 O'zbekcha": "uz", "🇷🇺 Русский": "ru", "🇬🇧 English": "en"}

REGIONS = {
    "ru": {
        "Ташкентская обл.": [
            "Ташкент",
            "Нурафшон",
            "Алмалык",
            "Ангрен",
            "Ахангаран",
            "Бекабад",
            "Бука",
            "Газалкент",
            "Келес",
            "Паркент",
            "Пскент",
            "Тойтепа",
            "Чиназ",
            "Чирчик",
            "Янгиабад",
            "Янгиюль",
        ],
        "Андижанская обл.": [
            "Андижан",
            "Асака",
            "Карасу",
            "Кургантепа",
            "Мархамат",
            "Пайтуг",
            "Пахтаабад",
            "Ханабад",
            "Ходжаабад",
            "Шахрихан",
        ],
        "Бухарская обл.": [
            "Бухара",
            "Алат",
            "Вабкент",
            "Газли",
            "Гиждуван",
            "Каган",
            "Каракуль",
            "Караулбазар",
            "Ромитан",
            "Шафиркан",
        ],
        "Джизакская обл.": [
            "Джизак",
            "Гагарин",
            "Галляарал",
            "Даштабад",
            "Дустлик",
            "Заамин",
            "Пахтакор",
        ],
        "Кашкадарьинская обл.": [
            "Карши",
            "Бешкент",
            "Гузар",
            "Камаши",
            "Касан",
            "Китаб",
            "Мубарек",
            "Талимарджан",
            "Чиракчи",
            "Шахрисабз",
            "Яккабаг",
        ],
        "Навоийская обл.": [
            "Навои",
            "Зарафшан",
            "Кызылтепа",
            "Нурата",
            "Учкудук",
            "Янгирабат",
        ],
        "Наманганская обл.": [
            "Наманган",
            "Касансай",
            "Пап",
            "Туракурган",
            "Учкурган",
            "Хаккулабад",
            "Чуст",
            "Чартак",
        ],
        "Самаркандская обл.": [
            "Самарканд",
            "Акташ",
            "Булунгур",
            "Джамбай",
            "Джума",
            "Иштыхан",
            "Каттакурган",
            "Нурабад",
            "Пайарык",
            "Ургут",
            "Челек",
        ],
        "Сурхандарьинская обл.": [
            "Термез",
            "Байсун",
            "Денау",
            "Джаркурган",
            "Кумкурган",
            "Шаргунь",
            "Шерабад",
            "Шурчи",
        ],
        "Сырдарьинская обл.": ["Гулистан", "Бахт", "Сырдарья", "Ширин", "Янгиер"],
        "Ферганская обл.": [
            "Фергана",
            "Бешарык",
            "Коканд",
            "Кува",
            "Кувасай",
            "Маргилан",
            "Риштан",
            "Хамза",
            "Яйпан",
        ],
        "Хорезмская обл.": ["Ургенч", "Гурлен", "Питнак", "Хива", "Ханка", "Шават"],
        "Респ. Каракалпакстан": [
            "Нукус",
            "Беруни",
            "Бустон",
            "Кунград",
            "Мангит",
            "Муйнак",
            "Тахиаташ",
            "Турткуль",
            "Ходжейли",
            "Чимбай",
            "Шуманай",
        ],
    },
    "uz": {
        "Toshkent viloyati": [
            "Toshkent",
            "Nurafshon",
            "Olmaliq",
            "Angren",
            "Ohangaron",
            "Bekobod",
            "Bo'ka",
            "G'azalkent",
            "Keles",
            "Parkent",
            "Piskent",
            "To'ytepa",
            "Chinoz",
            "Chirchiq",
            "Yangiobod",
            "Yangiyo'l",
        ],
        "Andijon viloyati": [
            "Andijon",
            "Asaka",
            "Qorasuv",
            "Qo'rg'ontepa",
            "Marhamat",
            "Poytug'",
            "Paxtaobod",
            "Xonobod",
            "Xo'jaobod",
            "Shahrixon",
        ],
        "Buxoro viloyati": [
            "Buxoro",
            "Olot",
            "Vobkent",
            "Gazli",
            "G'ijduvon",
            "Kogon",
            "Qorako'l",
            "Qorovulbozor",
            "Romitan",
            "Shofirkon",
        ],
        "Jizzax viloyati": [
            "Jizzax",
            "Gagarin",
            "G'allaorol",
            "Dashtobod",
            "Do'stlik",
            "Zomin",
            "Paxtakor",
        ],
        "Qashqadaryo viloyati": [
            "Qarshi",
            "Beshkent",
            "G'uzor",
            "Qamashi",
            "Koson",
            "Kitob",
            "Muborak",
            "Tolimarjon",
            "Chiroqchi",
            "Shahrisabz",
            "Yakkabog'",
        ],
        "Navoiy viloyati": [
            "Navoiy",
            "Zarafshon",
            "Qiziltepa",
            "Nurota",
            "Uchquduq",
            "Yangirabot",
        ],
        "Namangan viloyati": [
            "Namangan",
            "Kosonsoy",
            "Pop",
            "To'raqo'rg'on",
            "Uchqo'rg'on",
            "Haqqulobod",
            "Chust",
            "Chortoq",
        ],
        "Samarqand viloyati": [
            "Samarqand",
            "Oqtosh",
            "Bulung'ur",
            "Jomboy",
            "Juma",
            "Ishtixon",
            "Kattaqo'rg'on",
            "Nurobod",
            "Payariq",
            "Urgut",
            "Chelak",
        ],
        "Surxondaryo viloyati": [
            "Termiz",
            "Boysun",
            "Denov",
            "Jarqo'rg'on",
            "Qumqo'rg'on",
            "Sharg'un",
            "Sherobod",
            "Sho'rchi",
        ],
        "Sirdaryo viloyati": ["Guliston", "Baxt", "Sirdaryo", "Shirin", "Yangiyer"],
        "Farg'ona viloyati": [
            "Farg'ona",
            "Beshariq",
            "Qo'qon",
            "Quva",
            "Quvasoy",
            "Marg'ilon",
            "Rishton",
            "Hamza",
            "Yaypan",
        ],
        "Xorazm viloyati": ["Urganch", "Gurlan", "Pitonak", "Xiva", "Xonqa", "Shovot"],
        "Qoraqalpog'iston Resp.": [
            "Nukus",
            "Beruniy",
            "Bo'ston",
            "Qo'ng'irot",
            "Mang'it",
            "Mo'ynoq",
            "Taxiatosh",
            "To'rtko'l",
            "Xo'jayli",
            "Chimboy",
            "Shumanay",
        ],
    },
    "en": {
        "Tashkent Region": [
            "Tashkent",
            "Nurafshon",
            "Olmaliq",
            "Angren",
            "Ohangaron",
            "Bekobod",
            "Bo'ka",
            "G'azalkent",
            "Keles",
            "Parkent",
            "Piskent",
            "To'ytepa",
            "Chinoz",
            "Chirchiq",
            "Yangiobod",
            "Yangiyo'l",
        ],
        "Andijan Region": [
            "Andijan",
            "Asaka",
            "Qorasuv",
            "Qo'rg'ontepa",
            "Marhamat",
            "Poytug'",
            "Paxtaobod",
            "Xonobod",
            "Xo'jaobod",
            "Shahrixon",
        ],
        "Bukhara Region": [
            "Bukhara",
            "Olot",
            "Vobkent",
            "Gazli",
            "G'ijduvon",
            "Kogon",
            "Qorako'l",
            "Qorovulbozor",
            "Romitan",
            "Shofirkon",
        ],
        "Jizzakh Region": [
            "Jizzakh",
            "Gagarin",
            "G'allaorol",
            "Dashtobod",
            "Do'stlik",
            "Zomin",
            "Paxtakor",
        ],
        "Qashqadaryo Region": [
            "Qarshi",
            "Beshkent",
            "G'uzor",
            "Qamashi",
            "Koson",
            "Kitob",
            "Muborak",
            "Tolimarjon",
            "Chiroqchi",
            "Shahrisabz",
            "Yakkabog'",
        ],
        "Navoiy Region": [
            "Navoiy",
            "Zarafshon",
            "Qiziltepa",
            "Nurota",
            "Uchquduq",
            "Yangirabot",
        ],
        "Namangan Region": [
            "Namangan",
            "Kosonsoy",
            "Pop",
            "To'raqo'rg'on",
            "Uchqo'rg'on",
            "Haqqulobod",
            "Chust",
            "Chortoq",
        ],
        "Samarqand Region": [
            "Samarqand",
            "Oqtosh",
            "Bulung'ur",
            "Jomboy",
            "Juma",
            "Ishtixon",
            "Kattaqo'rg'on",
            "Nurobod",
            "Payariq",
            "Urgut",
            "Chelak",
        ],
        "Surxondaryo Region": [
            "Termiz",
            "Boysun",
            "Denov",
            "Jarqo'rg'on",
            "Qumqo'rg'on",
            "Sharg'un",
            "Sherobod",
            "Sho'rchi",
        ],
        "Sirdaryo Region": ["Guliston", "Baxt", "Sirdaryo", "Shirin", "Yangiyer"],
        "Fergana Region": [
            "Fergana",
            "Beshariq",
            "Qo'qon",
            "Quva",
            "Quvasoy",
            "Marg'ilon",
            "Rishton",
            "Hamza",
            "Yaypan",
        ],
        "Khorezm Region": ["Urganch", "Gurlan", "Pitonak", "Xiva", "Xonqa", "Shovot"],
        "Karakalpakstan Rep.": [
            "Nukus",
            "Beruniy",
            "Bo'ston",
            "Qo'ng'irot",
            "Mang'it",
            "Mo'ynoq",
            "Taxiatosh",
            "To'rtko'l",
            "Ходжейли",
            "Чимбай",
            "Шуманай",
        ],
    },
}

PROFESSION_SPHERES_KEYS = {
    "sphere_it": [
        "prof_backend",
        "prof_frontend",
        "prof_fullstack",
        "prof_qa",
        "prof_designer",
        "prof_product",
    ],
    "sphere_sales": [
        "prof_sales_manager",
        "prof_sales_consultant",
        "prof_sales_rep",
        "prof_cashier",
        "prof_supervisor",
    ],
    "sphere_med": [
        "prof_doctor",
        "prof_nurse",
        "prof_pharmacist",
        "prof_lab",
        "prof_med_rep",
    ],
    "sphere_edu": ["prof_teacher", "prof_professor", "prof_educator", "prof_tutor"],
    "sphere_construct": [
        "prof_engineer",
        "prof_architect",
        "prof_foreman",
        "prof_worker",
        "prof_electrician",
        "prof_welder",
    ],
    "sphere_transport": [
        "prof_driver",
        "prof_logist",
        "prof_forwarder",
        "prof_mechanic",
        "prof_courier",
    ],
    "sphere_finance": [
        "prof_accountant",
        "prof_economist",
        "prof_analyst",
        "prof_auditor",
    ],
    "sphere_service": [
        "prof_waiter",
        "prof_cook",
        "prof_hairdresser",
        "prof_admin",
        "prof_guard",
    ],
    "sphere_admin": [
        "prof_secretary",
        "prof_office_mgr",
        "prof_assistant",
        "prof_operator",
    ],
}

LANGUAGES_I18N = {
    "ru": {
        "🇺🇿 Узбекский": "lang_name_uz",
        "🇷🇺 Русский": "lang_name_ru",
        "🇬🇧 Английский": "lang_name_en",
    },
    "uz": {
        "🇺🇿 O'zbek": "lang_name_uz",
        "🇷🇺 Rus": "lang_name_ru",
        "🇬🇧 Ingliz": "lang_name_en",
    },
    "en": {
        "🇺🇿 Uzbek": "lang_name_uz",
        "🇷🇺 Russian": "lang_name_ru",
        "🇬🇧 English": "lang_name_en",
    },
}

LEVELS_I18N = {
    "ru": {
        "Базовый": "level_basic",
        "Практический": "level_practical",
        "Свободный": "level_fluent",
        "В совершенстве": "level_proficient",
    },
    "uz": {
        "Boshlang'ich": "level_basic",
        "Amaliy": "level_practical",
        "Erkin": "level_fluent",
        "Mukammal": "level_proficient",
    },
    "en": {
        "Basic": "level_basic",
        "Practical": "level_practical",
        "Fluent": "level_fluent",
        "Proficient": "level_proficient",
    },
}


def get_user_language(user_id):
    """Получает код языка пользователя из БД, по умолчанию 'ru'."""
    from database.core import execute_query, get_user_state

    # Прямой запрос в БД для обхода кэша
    try:
        # 1. Проверяем соискателей
        res = execute_query(
            "SELECT language_code FROM job_seekers WHERE telegram_id = ?",
            (user_id,),
            fetchone=True,
        )
        if res and res.get("language_code"):
            return res["language_code"]

        # 2. Проверяем работодателей
        res = execute_query(
            "SELECT language_code FROM employers WHERE telegram_id = ?",
            (user_id,),
            fetchone=True,
        )
        if res and res.get("language_code"):
            return res["language_code"]
    except Exception as e:
        logging.error(f"Error fetching user language: {e}")

    state = get_user_state(user_id)
    if state and state.get("language_code"):
        return state["language_code"]

    return "ru"


def get_text_by_lang(key, lang="ru"):
    """Получает переведенную строку по коду языка."""
    lang_dict = TRANSLATIONS.get(lang, {})
    default_dict = TRANSLATIONS.get("ru", {})
    return lang_dict.get(key, default_dict.get(key, key))


def get_all_translations(key):
    """Возвращает список переводов для ключа на всех языках"""
    return [d.get(key, "") for d in TRANSLATIONS.values() if d.get(key)]
