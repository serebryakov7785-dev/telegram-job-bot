# models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class JobSeeker:
    """Модель соискателя (БЕЗ ЛОГИНА)"""

    telegram_id: int
    phone: str
    email: str
    full_name: str
    gender: Optional[str] = None
    age: Optional[int] = None
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


def dict_to_job_seeker(data: Dict[str, Any]) -> JobSeeker:
    """Преобразование словаря в модель JobSeeker"""
    return JobSeeker(
        telegram_id=int(data.get("telegram_id", 0)),
        phone=str(data.get("phone", "")),
        email=str(data.get("email", "")),
        full_name=str(data.get("full_name", "")),
        gender=data.get("gender"),
        age=data.get("age") if isinstance(data.get("age"), int) else None,
        city=str(data.get("city", "Не указан")),
        profession=str(data.get("profession", "Не указана")),
        skills=str(data.get("skills", "Не указаны")),
        experience=str(data.get("experience", "Нет опыта")),
        education=str(data.get("education", "Не указано")),
        languages=str(data.get("languages", "Не указаны")),
        status=str(data.get("status", "active")),
        created_at=data.get("created_at"),
    )


def dict_to_employer(data: Dict[str, Any]) -> Employer:
    """Преобразование словаря в модель Employer"""
    return Employer(
        telegram_id=int(data.get("telegram_id", 0)),
        company_name=str(data.get("company_name", "")),
        contact_person=str(data.get("contact_person", "")),
        phone=str(data.get("phone", "")),
        email=str(data.get("email", "")),
        city=str(data.get("city", "Не указан")),
        description=str(data.get("description", "Описание не указано")),
        created_at=data.get("created_at"),
    )
