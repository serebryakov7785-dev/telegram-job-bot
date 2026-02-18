import hashlib
import io
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Добавляем корень проекта в путь, чтобы импорты работали
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database  # noqa: E402
import keyboards  # noqa: E402
from handlers.employer import EmployerHandlers  # noqa: E402
from handlers.seeker import SeekerHandlers  # noqa: E402
from pdf_generator import generate_resume_pdf  # noqa: E402


class TestNewFeatures:

    @pytest.fixture(autouse=True)
    def mock_md5(self, monkeypatch):
        """Mock hashlib.md5 to ignore usedforsecurity argument on older Python versions."""
        original_md5 = hashlib.md5

        def patched_md5(*args, **kwargs):
            kwargs.pop("usedforsecurity", None)
            return original_md5(*args, **kwargs)

        monkeypatch.setattr(hashlib, "md5", patched_md5)

    @pytest.fixture
    def mock_bot(self):
        return MagicMock()

    @pytest.fixture
    def seeker_handler(self, mock_bot):
        return SeekerHandlers(mock_bot)

    @pytest.fixture
    def employer_handler(self, mock_bot):
        return EmployerHandlers(mock_bot)

    def test_pdf_generation_structure(self):
        """Тест: Генерация PDF возвращает валидный объект BytesIO с PDF-заголовком"""
        from pdf_generator import generate_resume_pdf

        user_data = {
            "full_name": "Test Candidate",
            "phone": "+998901234567",
            "email": "test@example.com",
            "city": "Tashkent",
            "age": 25,
            "profession": "Python Developer",
            "experience": "3 years",
            "education": "Bachelor",
            "skills": "Django, Flask, SQL",
            "languages": "English, Russian",
        }

        # Запускаем генерацию
        # Patch reportlab's md5 if it has already imported the original one
        try:
            import reportlab.pdfbase.pdfdoc

            original_md5 = hashlib.md5

            def patched_md5(*args, **kwargs):
                kwargs.pop("usedforsecurity", None)
                return original_md5(*args, **kwargs)

            with patch("reportlab.pdfbase.pdfdoc.md5", side_effect=patched_md5):
                pdf_buffer = generate_resume_pdf(user_data, lang="ru")
        except ImportError:
            pdf_buffer = generate_resume_pdf(user_data, lang="ru")

        # Проверки
        assert isinstance(pdf_buffer, io.BytesIO)
        content = pdf_buffer.getvalue()
        assert len(content) > 0
        # PDF файлы всегда начинаются с %PDF
        assert content.startswith(b"%PDF"), "Сгенерированный файл не является PDF"

    def test_guest_mode_seeker_search(self, seeker_handler, mock_bot):
        """Тест: Поиск вакансий доступен для гостя (без регистрации)"""
        message = MagicMock()
        message.from_user.id = 99999
        message.chat.id = 99999

        # Мокаем БД: get_user_by_id возвращает None (пользователь не найден)
        with patch("database.get_user_by_id", return_value=None):
            # Мокаем выполнение запроса к БД (возвращаем пустой список вакансий)
            with patch("database.core.execute_query", return_value=[]):
                seeker_handler.handle_find_vacancies(message)

        # Проверяем, что бот НЕ отправил сообщение "Сначала зарегистрируйтесь"
        # А отправил сообщение с результатами поиска (в данном случае "нет вакансий")
        assert mock_bot.send_message.called
        args, kwargs = mock_bot.send_message.call_args
        text = args[1]

        assert "Сначала зарегистрируйтесь" not in text
        assert "Поиск вакансий" in text or "К сожалению" in text

        # Проверяем, что используется клавиатура для гостей (seeker_menu), а не main_menu
        # Мы не можем напрямую сравнить объекты клавиатур, но можем проверить логику в коде через patch keyboards
        # В данном тесте мы полагаемся на то, что handler отработал до конца без return

    def test_guest_mode_employer_search(self, employer_handler, mock_bot):
        """Тест: Поиск резюме доступен для гостя-работодателя"""
        message = MagicMock()
        message.from_user.id = 88888
        message.chat.id = 88888

        # Мокаем БД: пользователь не найден
        with patch("database.get_user_by_id", return_value=None):
            # Мокаем поиск соискателей
            with patch("database.get_all_seekers", return_value=[]):
                employer_handler.handle_find_candidates(message)

        # Проверяем, что бот показал экран поиска
        assert mock_bot.send_message.called
        args, _ = mock_bot.send_message.call_args
        text = args[1]

        assert "Сначала зарегистрируйтесь" not in text
        assert "Поиск сотрудников" in text or "К сожалению" in text

    def test_send_pdf_on_apply(self, seeker_handler, mock_bot):
        """Тест: Отправка PDF работодателю при успешном отклике"""
        vacancy_id = 100
        employer_tg_id = 777
        seeker_data = {"full_name": "John Doe", "phone": "123"}

        # Мокаем данные, которые возвращает SQL запрос о вакансии/работодателе
        employer_info = {
            "title": "Python Dev",
            "telegram_id": employer_tg_id,
            "language_code": "ru",
        }

        with patch("database.execute_query", return_value=employer_info):
            # Мокаем генератор PDF, чтобы не создавать реальный файл
            with patch("handlers.seeker_responses.generate_resume_pdf") as mock_gen:
                mock_pdf = io.BytesIO(b"%PDF-Mock")
                mock_gen.return_value = mock_pdf

                # Вызываем приватный метод отправки (или можно вызвать handle_application_callback с моками)
                seeker_handler._notify_employer_with_pdf(vacancy_id, seeker_data)

                # Проверяем, что бот отправил документ работодателю
                mock_bot.send_document.assert_called_once()
                call_args = mock_bot.send_document.call_args

                # Проверяем получателя (ID работодателя)
                assert call_args[0][0] == employer_tg_id
                # Проверяем, что отправлен именно наш мок PDF
                assert call_args[0][1] == mock_pdf
                # Проверяем подпись
                assert (
                    "Новый отклик" in call_args[1]["caption"]
                    or "Новый отклик" in call_args[0][2]
                )

    def test_download_resume_button(self, seeker_handler, mock_bot):
        """Тест: Кнопка 'Скачать PDF' генерирует и отправляет файл"""
        call = MagicMock()
        call.from_user.id = 123
        call.message.chat.id = 123
        call.data = "download_resume"

        user_data = {"full_name": "Test User", "id": 1}

        with patch("database.get_user_by_id", return_value=user_data):
            with patch("handlers.seeker_profile.generate_resume_pdf") as mock_gen:
                mock_pdf = io.BytesIO(b"%PDF-Mock")
                mock_gen.return_value = mock_pdf

                seeker_handler.handle_download_resume(call)

                # Проверяем уведомление "Генерирую..."
                mock_bot.answer_callback_query.assert_called_with(
                    call.id, "⏳ Генерирую PDF..."
                )

                # Проверяем отправку документа
                mock_bot.send_document.assert_called_once()
                assert mock_bot.send_document.call_args[0][0] == 123  # chat_id
