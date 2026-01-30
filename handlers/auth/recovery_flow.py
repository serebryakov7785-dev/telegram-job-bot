import database
import keyboards
import utils

class RecoveryFlowMixin:
    def handle_password_recovery(self, message):
        """Восстановление пароля"""
        user_id = message.from_user.id
        database.set_user_state(user_id, {'step': 'recovery'})
        
        self.bot.send_message(
            message.chat.id,
            "🔑 *Восстановление пароля*\n\n"
            "Введите ваш номер телефона или email для получения инструкций:",
            parse_mode='Markdown',
            reply_markup=keyboards.cancel_keyboard()
        )
    
    def process_recovery(self, message):
        """Обработка восстановления пароля"""
        if utils.cancel_request(message.text):
            self.bot.send_message(
                message.chat.id,
                "❌ Восстановление отменено",
                reply_markup=keyboards.main_menu()
            )
            database.clear_user_state(message.from_user.id)
            return
        
        identifier = message.text.strip()
        user_data, role = database.get_user_by_credentials(identifier)
        
        if user_data:
            email = user_data.get('email', 'не указан')
            phone = user_data.get('phone', 'не указан')
            
            # Маскируем email для безопасности
            masked_email = email[:3] + '***' + email[email.find('@'):] if '@' in email else email
            
            self.bot.send_message(
                message.chat.id,
                f"📧 *Инструкции отправлены!*\n\n"
                f"На email *{masked_email}* отправлена ссылка для сброса пароля.\n"
                f"Если не получили письмо, проверьте спам.\n\n"
                f"*Телефон для связи:* {phone}",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
        else:
            self.bot.send_message(
                message.chat.id,
                "❌ Пользователь не найден!\nПроверьте введенные данные.",
                parse_mode='Markdown',
                reply_markup=keyboards.main_menu()
            )
        
        database.clear_user_state(message.from_user.id)
    
    def handle_logout(self, message):
        """Выход из системы"""
        user_id = message.from_user.id
        database.clear_user_state(user_id)
        
        self.bot.send_message(
            message.chat.id,
            "✅ *Вы вышли из системы!*\n\n"
            "Будем рады видеть Вас снова!",
            parse_mode='Markdown',
            reply_markup=keyboards.main_menu()
        )