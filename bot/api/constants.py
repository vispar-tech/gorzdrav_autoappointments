"""
Константы для API Горздрав
"""

# Базовые URL
BASE_URL = "https://gorzdrav.spb.ru"


# Endpoints
ENDPOINTS = {
    # Общие
    "districts": "_api/api/v2/shared/districts",
    "lpus": "_api/api/v2/shared/lpus",
    "lpus_by_district": "_api/api/v2/shared/district/{district_id}/lpus",
    # Расписание
    "specialists": "_api/api/v2/schedule/lpu/{lpu_id}/specialties",
    "doctors": "_api/api/v2/schedule/lpu/{lpu_id}/speciality/{specialist_id}/doctors",
    "appointments": "_api/api/v2/schedule/lpu/{lpu_id}/doctor/{doctor_id}/appointments",
    # Пациенты
    "patient_search": "_api/api/v2/patient/search",
    "patient_update": "_api/api/v2/patient/update",
    # Запись
    "appointment_create": "_api/api/v2/appointment/create",
    # Записи пациента
    "patient_appointments": "_api/api/v2/appointments",
}

# HTTP заголовки
DEFAULT_HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "Referer": "https://gorzdrav.spb.ru/service-free-schedule",
}
