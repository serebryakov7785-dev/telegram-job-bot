import os
import sys

# Устанавливаем рабочую директорию в папку проекта, чтобы находились .env, БД и логи
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Загружаем переменные окружения ЯВНО перед импортом конфига
from dotenv import load_dotenv

load_dotenv()

# Автоматическая настройка для PythonAnywhere
if "PYTHONANYWHERE_DOMAIN" in os.environ:
    # Отключаем мониторинг (нет лишних портов)
    os.environ["ENABLE_MONITORING"] = "false"
    # Отключаем многопоточность (ограничения WSGI)
    os.environ["BOT_THREADED"] = "false"

import telebot
from flask import Flask, abort, request

from bot_factory import create_bot
from config import Config

# Инициализируем бота (подключаем БД, роуты и т.д.)
bot = create_bot()
app = Flask(__name__)

# Секретный путь для вебхука
WEBHOOK_PATH = f"/{Config.TOKEN}"


@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    """Принимает обновления от Telegram"""
    if request.headers.get("content-type") == "application/json":
        print("DEBUG: Получено обновление от Telegram", file=sys.stderr)
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "", 200
    else:
        abort(403)


@app.route("/set_webhook")
def set_webhook():
    """Устанавливает вебхук (запустите один раз в браузере)"""
    host = request.host
    webhook_url = f"https://{host}{WEBHOOK_PATH}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f"Webhook set to {webhook_url}", 200


@app.route("/")
def index():
    return "Bot is running!", 200
