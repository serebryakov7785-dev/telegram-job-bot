from handlers.seeker_profile import SeekerProfileMixin
from handlers.seeker_responses import SeekerResponseMixin
from handlers.seeker_search import SeekerSearchMixin
from localization import get_all_translations


class SeekerHandlers(SeekerSearchMixin, SeekerProfileMixin, SeekerResponseMixin):
    def __init__(self, bot):
        self.bot = bot

    def register(self, bot):
        bot.register_message_handler(
            self.handle_find_vacancies,
            func=lambda m: m.text in get_all_translations("menu_find_vacancies"),
        )
        bot.register_message_handler(
            self.handle_my_resume,
            func=lambda m: m.text in get_all_translations("menu_my_resume"),
        )
        bot.register_message_handler(
            self.handle_my_responses,
            func=lambda m: m.text in get_all_translations("menu_my_responses"),
        )
        bot.register_callback_query_handler(
            self.handle_application_callback, func=lambda c: c.data.startswith("apply_")
        )
        bot.register_callback_query_handler(
            self.handle_download_resume, func=lambda c: c.data == "download_resume"
        )
