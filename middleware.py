import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from database.core import execute_query
from localization import get_text_by_lang, get_user_language

RATE_LIMIT = 5
TIME_WINDOW = 10
MUTE_DURATION = 30

user_requests: Dict[int, List[float]] = defaultdict(list)
muted_users: Dict[int, float] = {}


def check_user_blocked(user_id):
    try:
        res = execute_query(
            "SELECT blocked_until FROM blocked_users WHERE telegram_id = ?",
            (user_id,),
            fetchone=True,
        )
        if not res:
            return None
        blocked_until = res["blocked_until"]
        if blocked_until == "forever":
            return "forever"
        until_dt = datetime.strptime(blocked_until, "%Y-%m-%d %H:%M:%S")
        if datetime.now() < until_dt:
            return until_dt
        return None
    except Exception as e:
        logging.error(f"Error checking block status: {e}")
        return None


def check_rate_limit(bot, obj):
    user_id = obj.from_user.id
    current_time = time.time()

    if user_id in muted_users:
        if current_time < muted_users[user_id]:
            return False
        else:
            del muted_users[user_id]

    user_requests[user_id] = [
        t for t in user_requests[user_id] if current_time - t < TIME_WINDOW
    ]
    if len(user_requests[user_id]) >= RATE_LIMIT:
        muted_users[user_id] = current_time + MUTE_DURATION
        try:
            lang = get_user_language(user_id)
            if hasattr(obj, "chat"):  # Message
                text = get_text_by_lang("rate_limit_message", lang).format(
                    duration=MUTE_DURATION
                )
                bot.send_message(user_id, text)
            else:  # Callback
                bot.answer_callback_query(
                    obj.id, get_text_by_lang("rate_limit_alert", lang), show_alert=True
                )
        except Exception:
            pass
        return False

    user_requests[user_id].append(current_time)
    return True


def setup_middleware(bot, monitoring=False, metrics=None):
    original_process_new_messages = bot.process_new_messages
    original_process_new_callback_query = bot.process_new_callback_query

    def custom_process_new_messages(messages):
        valid = []
        for msg in messages:
            blocked = check_user_blocked(msg.from_user.id)
            if blocked:
                if blocked == "forever":
                    txt = "🚫 *Вы заблокированы навсегда.*"
                else:
                    txt = f"🚫 *Вы заблокированы.*\n⏳ До: {blocked}"
                try:
                    bot.send_message(msg.chat.id, txt, parse_mode="Markdown")
                except Exception:
                    pass
                continue
            if check_rate_limit(bot, msg):
                valid.append(msg)
        if valid:
            original_process_new_messages(valid)

    def custom_process_new_callback_query(queries):
        valid = []
        for call in queries:
            if check_user_blocked(call.from_user.id):
                try:
                    bot.answer_callback_query(
                        call.id, "🚫 Вы заблокированы.", show_alert=True
                    )
                except Exception:
                    pass
                continue
            if check_rate_limit(bot, call):
                valid.append(call)
        if valid:
            original_process_new_callback_query(valid)

    bot.process_new_messages = custom_process_new_messages
    bot.process_new_callback_query = custom_process_new_callback_query
