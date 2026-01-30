import pytest
from telebot import types
import keyboards

def test_main_menu():
    """Проверка главного меню"""
    markup = keyboards.main_menu()
    assert hasattr(markup, 'keyboard')
    assert len(markup.keyboard) == 2
    assert markup.keyboard[0][0]['text'] == '👤 Я ищу работу'

def test_seeker_main_menu():
    """Проверка меню соискателя"""
    markup = keyboards.seeker_main_menu()
    assert hasattr(markup, 'keyboard')
    assert len(markup.keyboard) == 3
    assert markup.keyboard[0][1]['text'] == '📄 Мое резюме'

def test_vacancy_actions():
    """Проверка инлайн-кнопки отклика"""
    markup = keyboards.vacancy_actions(123)
    assert hasattr(markup, 'keyboard')
    assert len(markup.keyboard[0]) == 1
    button = markup.keyboard[0][0]
    assert button.text == "📝 Откликнуться"
    assert button.callback_data == "apply_123"

def test_my_vacancy_actions():
    """Проверка инлайн-кнопок управления вакансией"""
    markup = keyboards.my_vacancy_actions(456)
    assert hasattr(markup, 'keyboard')
    assert len(markup.keyboard[0]) == 3
    assert markup.keyboard[0][0].callback_data == "edit_vac_456"
    assert markup.keyboard[0][1].callback_data == "delete_vac_456"
    assert markup.keyboard[0][2].callback_data == "responses_vac_456"

def test_delete_confirmation_keyboard():
    """Проверка инлайн-кнопок подтверждения удаления"""
    markup = keyboards.delete_confirmation_keyboard(789)
    assert hasattr(markup, 'keyboard')
    assert len(markup.keyboard[0]) == 2
    assert markup.keyboard[0][0].callback_data == "confirm_del_789"
    assert markup.keyboard[0][1].callback_data == "cancel_del_789"

def test_employer_main_menu():
    """Проверка меню работодателя"""
    markup = keyboards.employer_main_menu()
    assert hasattr(markup, 'keyboard')
    # Проверяем наличие кнопок
    texts = [btn['text'] for row in markup.keyboard for btn in row]
    assert any("Создать вакансию" in t for t in texts)