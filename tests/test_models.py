from models import dict_to_employer, dict_to_job_seeker


def test_job_seeker_model():
    data = {
        "telegram_id": 1,
        "phone": "123",
        "email": "a@b.c",
        "full_name": "Name",
        "age": 20,
    }
    js = dict_to_job_seeker(data)
    assert js.telegram_id == 1
    assert js.city == "Не указан"  # default
    assert js.status == "active"


def test_employer_model():
    data = {
        "telegram_id": 1,
        "company_name": "Comp",
        "contact_person": "Person",
        "phone": "123",
        "email": "a@b.c",
    }
    emp = dict_to_employer(data)
    assert emp.telegram_id == 1
    assert emp.description == "Описание не указано"
