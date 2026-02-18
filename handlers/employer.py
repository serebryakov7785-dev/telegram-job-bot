import keyboards
from handlers.employer_responses import EmployerResponseMixin
from handlers.employer_search import EmployerSearchMixin
from handlers.employer_vacancy import EmployerVacancyMixin
from localization import get_all_translations


class EmployerHandlers(
    EmployerVacancyMixin, EmployerSearchMixin, EmployerResponseMixin
):
    def __init__(self, bot):
        self.bot = bot

    def register(self, bot):
        bot.register_message_handler(
            self.handle_create_vacancy,
            func=lambda m: m.text in get_all_translations("menu_create_vacancy"),
        )
        bot.register_message_handler(
            self.handle_find_candidates,
            func=lambda m: m.text in get_all_translations("menu_find_candidates"),
        )
        bot.register_message_handler(
            self.handle_my_vacancies,
            func=lambda m: m.text in get_all_translations("menu_my_vacancies"),
        )

        bot.register_callback_query_handler(
            self.handle_invitation_callback, func=lambda c: c.data.startswith("invite_")
        )
        bot.register_callback_query_handler(
            self.handle_my_vacancy_actions,
            func=lambda c: c.data.startswith(
                ("edit_vac_", "delete_vac_", "responses_vac_")
            ),
        )
        bot.register_callback_query_handler(
            self.handle_confirm_delete, func=lambda c: c.data.startswith("confirm_del_")
        )
        bot.register_callback_query_handler(
            self.handle_cancel_delete, func=lambda c: c.data.startswith("cancel_del_")
        )

    def handle_cancel_delete(self, call):
        self.bot.delete_message(call.message.chat.id, call.message.message_id)
        self.bot.send_message(
            call.message.chat.id,
            "🏠 Возврат в меню",
            reply_markup=keyboards.employer_main_menu(),
        )
