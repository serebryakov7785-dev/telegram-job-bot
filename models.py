# models.py
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class JobSeeker:
    """Модель соискателя (БЕЗ ЛОГИНА)"""
    telegram_id: int
    phone: str
    email: str
    full_name: str
    age: Optional[int]
    city: str = "Не указан"
    profession: str = "Не указана"
    skills: str = "Не указаны"
    experience: str = "Нет опыта"
    education: str = "Не указано"
    languages: str = "Не указаны"
    status: str = "active"
    created_at: Optional[datetime] = None


@dataclass
class Employer:
    """Модель работодателя (БЕЗ ЛОГИНА)"""
    telegram_id: int
    company_name: str
    contact_person: str
    phone: str
    email: str
    city: str = "Не указан"
    description: str = "Описание не указано"
    created_at: Optional[datetime] = None


def dict_to_job_seeker(data: dict) -> JobSeeker:
    """Преобразование словаря в модель JobSeeker"""
    return JobSeeker(
        telegram_id=data.get('telegram_id'),
        phone=data.get('phone'),
        email=data.get('email'),
        full_name=data.get('full_name'),
        age=data.get('age'),
        city=data.get('city', 'Не указан'),
        profession=data.get('profession', 'Не указана'),
        skills=data.get('skills', 'Не указаны'),
        experience=data.get('experience', 'Нет опыта'),
        education=data.get('education', 'Не указано'),
        languages=data.get('languages', 'Не указаны'),
        status=data.get('status', 'active'),
        created_at=data.get('created_at')
    )


def dict_to_employer(data: dict) -> Employer:
    """Преобразование словаря в модель Employer"""
    return Employer(
        telegram_id=data.get('telegram_id'),
        company_name=data.get('company_name'),
        contact_person=data.get('contact_person'),
        phone=data.get('phone'),
        email=data.get('email'),
        city=data.get('city', 'Не указан'),
        description=data.get('description', 'Описание не указано'),
        created_at=data.get('created_at')
    )
