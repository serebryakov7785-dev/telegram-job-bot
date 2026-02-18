import time
from typing import Any, Dict, List, Tuple, cast

from .core import execute_query

# ================= КЭШИРОВАНИЕ =================
_vacancies_cache: Dict[Tuple[int, int], Tuple[float, List[Dict[str, Any]]]] = {}
VACANCY_CACHE_TTL = 60  # Время жизни кэша в секундах


def invalidate_vacancies_cache():
    """Сброс кэша списка вакансий"""
    _vacancies_cache.clear()


def create_vacancy(data: Dict[str, Any]) -> bool:
    """Создание новой вакансии"""
    try:
        execute_query(
            """
            INSERT INTO vacancies (employer_id, title, description, salary, job_type, languages)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                data["employer_id"],
                data["title"],
                data["description"],
                data.get("salary", "Не указана"),
                data.get("job_type", "Полный день"),
                data.get("languages", "Не указаны"),
            ),
        )
        invalidate_vacancies_cache()
        return True
    except Exception as e:
        print(f"❌ Ошибка создания вакансии: {e}")
        return False


def update_vacancy(vacancy_id: int, **kwargs: Any) -> bool:
    """Обновление вакансии"""
    allowed_keys = {"title", "description", "salary", "job_type", "status", "languages"}
    updates = {k: v for k, v in kwargs.items() if k in allowed_keys}

    if not updates:
        return False

    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values())
    values.append(vacancy_id)

    try:
        # fmt: off
        query = f"UPDATE vacancies SET {set_clause} WHERE id = ?"  # nosec B608
        # fmt: on
        result = execute_query(query, tuple(values))
        if result > 0:
            invalidate_vacancies_cache()
            return True
        return False
    except Exception as e:
        print(f"❌ Ошибка обновления вакансии: {e}")
        return False


def delete_vacancy(vacancy_id: int) -> bool:
    """Удаление вакансии"""
    try:
        # Удаляем вакансию (отклики удалятся каскадно или можно явно удалить)
        execute_query("DELETE FROM applications WHERE vacancy_id = ?", (vacancy_id,))
        result = execute_query("DELETE FROM vacancies WHERE id = ?", (vacancy_id,))
        if result > 0:
            invalidate_vacancies_cache()
            return True
        return False
    except Exception as e:
        print(f"❌ Ошибка удаления вакансии: {e}")
        return False


def get_employer_vacancies(employer_id: int) -> List[Dict[str, Any]]:
    """Получение вакансий работодателя"""
    try:
        return cast(
            List[Dict[str, Any]],
            execute_query(
                """
            SELECT * FROM vacancies
            WHERE employer_id = ?
            ORDER BY created_at DESC, id DESC
        """,
                (employer_id,),
                fetchall=True,
            ),
        )
    except Exception as e:
        print(f"❌ Ошибка получения вакансий: {e}")
        return []


def get_all_vacancies(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """Получение всех активных вакансий"""
    # Проверка кэша
    cache_key = (limit, offset)
    if cache_key in _vacancies_cache:
        timestamp, vacancies = _vacancies_cache[cache_key]
        if time.time() - timestamp < VACANCY_CACHE_TTL:
            return [v.copy() for v in vacancies]

    try:
        result = execute_query(
            """
            SELECT v.*, e.company_name, e.phone, e.email, e.city
            FROM vacancies v
            JOIN employers e ON v.employer_id = e.id
            WHERE v.status = 'active'
            ORDER BY v.created_at DESC, v.id DESC
            LIMIT ? OFFSET ?
        """,
            (limit, offset),
            fetchall=True,
        )

        _vacancies_cache[cache_key] = (time.time(), result)
        typed_result = cast(List[Dict[str, Any]], [v.copy() for v in result])
        return typed_result
    except Exception as e:
        print(f"❌ Ошибка получения всех вакансий: {e}")
        return []


def get_seeker_applications(seeker_id: int) -> List[Dict[str, Any]]:
    """Получение откликов соискателя"""
    try:
        return cast(
            List[Dict[str, Any]],
            execute_query(
                """
            SELECT a.*, v.title, v.salary, e.company_name
            FROM applications a
            JOIN vacancies v ON a.vacancy_id = v.id
            JOIN employers e ON v.employer_id = e.id
            WHERE a.seeker_id = ?
            ORDER BY a.created_at DESC, a.id DESC
        """,
                (seeker_id,),
                fetchall=True,
            ),
        )
    except Exception as e:
        print(f"❌ Ошибка получения откликов: {e}")
        return []


def create_application(vacancy_id: int, seeker_id: int, message: str = "") -> bool:
    """Создание отклика на вакансию"""
    try:
        execute_query(
            """
            INSERT INTO applications (vacancy_id, seeker_id, message)
            VALUES (?, ?, ?)
        """,
            (vacancy_id, seeker_id, message),
        )
        return True
    except Exception as e:
        print(f"❌ Ошибка создания отклика: {e}")
        return False


def check_application_exists(vacancy_id: int, seeker_id: int) -> bool:
    """Проверка существования отклика"""
    try:
        result = execute_query(
            """
            SELECT id FROM applications
            WHERE vacancy_id = ? AND seeker_id = ?
        """,
            (vacancy_id, seeker_id),
            fetchone=True,
        )
        return result is not None
    except Exception as e:
        print(f"❌ Ошибка проверки отклика: {e}")
        return False


def get_employer_statistics(employer_id: int) -> Dict[str, int]:
    """Получение статистики работодателя"""
    try:
        # Количество вакансий
        res_total = execute_query(
            """
            SELECT COUNT(*) as count FROM vacancies WHERE employer_id = ?
        """,
            (employer_id,),
            fetchone=True,
        )
        total_vacancies = res_total["count"] if res_total else 0

        # Количество активных вакансий
        res_active = execute_query(
            """
            SELECT COUNT(*) as count FROM vacancies WHERE employer_id = ? AND status = 'active'
        """,
            (employer_id,),
            fetchone=True,
        )
        active_vacancies = res_active["count"] if res_active else 0

        # Количество откликов
        res_apps = execute_query(
            """
            SELECT COUNT(*) as count
            FROM applications a
            JOIN vacancies v ON a.vacancy_id = v.id
            WHERE v.employer_id = ?
        """,
            (employer_id,),
            fetchone=True,
        )
        total_applications = res_apps["count"] if res_apps else 0

        return {
            "total_vacancies": total_vacancies,
            "active_vacancies": active_vacancies,
            "total_applications": total_applications,
        }
    except Exception as e:
        print(f"❌ Ошибка получения статистики работодателя: {e}")
        return {"total_vacancies": 0, "active_vacancies": 0, "total_applications": 0}
