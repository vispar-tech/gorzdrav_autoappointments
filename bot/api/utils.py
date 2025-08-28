"""
Утилиты для работы с API Горздрав
"""

import re
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from loguru import logger


def parse_date(date_str: str) -> Optional[date]:
    """
    Парсит дату из строки в формате Горздрав

    Args:
        date_str: Строка с датой (например, "1990-05-15")

    Returns:
        Объект date или None при ошибке
    """
    if not date_str:
        return None

    try:
        # Пробуем разные форматы дат
        formats = [
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                return parsed.date()
            except ValueError:
                continue

        logger.warning(f"Не удалось распарсить дату: {date_str}")
        return None

    except Exception as e:
        logger.error(f"Ошибка парсинга даты {date_str}: {e}")
        return None


def parse_datetime(datetime_str: str) -> Optional[datetime]:
    """
    Парсит дату и время из строки в формате Горздрав

    Args:
        datetime_str: Строка с датой и временем

    Returns:
        Объект datetime или None при ошибке
    """
    if not datetime_str:
        return None

    try:
        # Убираем Z и заменяем на +00:00 для корректного парсинга
        if datetime_str.endswith("Z"):
            datetime_str = datetime_str[:-1] + "+00:00"

        # Пробуем ISO формат
        try:
            return datetime.fromisoformat(datetime_str)
        except ValueError:
            pass

        # Пробуем другие форматы
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%d.%m.%Y %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Не удалось распарсить дату и время: {datetime_str}")
        return None

    except Exception as e:
        logger.error(f"Ошибка парсинга даты и времени {datetime_str}: {e}")
        return None


def format_date_for_api(date_obj: date) -> str:
    """
    Форматирует дату для отправки в API

    Args:
        date_obj: Объект date

    Returns:
        Строка в формате YYYY-MM-DD
    """
    return date_obj.strftime("%Y-%m-%d")


def format_datetime_for_api(datetime_obj: datetime) -> str:
    """
    Форматирует дату и время для отправки в API

    Args:
        datetime_obj: Объект datetime

    Returns:
        Строка в формате YYYY-MM-DDTHH:MM:SS
    """
    return datetime_obj.strftime("%Y-%m-%dT%H:%M:%S")


def validate_policy_number(policy: str) -> bool:
    """
    Валидирует номер полиса ОМС

    Args:
        policy: Номер полиса

    Returns:
        True если номер корректен
    """
    if not policy:
        return False

    # Убираем пробелы и дефисы
    policy = re.sub(r"[\s\-]", "", policy)

    # Проверяем длину (16 цифр для полиса ОМС)
    if len(policy) != 16:
        return False

    # Проверяем, что все символы - цифры
    if not policy.isdigit():
        return False

    return True


def validate_snils(snils: str) -> bool:
    """
    Валидирует СНИЛС

    Args:
        snils: СНИЛС

    Returns:
        True если СНИЛС корректен
    """
    if not snils:
        return False

    # Убираем пробелы, дефисы и точки
    snils = re.sub(r"[\s\-\.]", "", snils)

    # Проверяем длину (11 цифр для СНИЛС)
    if len(snils) != 11:
        return False

    # Проверяем, что все символы - цифры
    if not snils.isdigit():
        return False

    # Проверяем контрольную сумму
    try:
        numbers = [int(d) for d in snils[:-2]]
        control_sum = int(snils[-2:])

        # Вычисляем контрольную сумму
        calculated_sum = 0
        for i, num in enumerate(numbers):
            calculated_sum += num * (9 - i)

        if calculated_sum < 100:
            calculated_sum = calculated_sum
        elif calculated_sum < 200:
            calculated_sum = calculated_sum - 101
        else:
            calculated_sum = calculated_sum - 201

        return calculated_sum == control_sum

    except (ValueError, IndexError):
        return False


def validate_phone(phone: str) -> bool:
    """
    Валидирует номер телефона

    Args:
        phone: Номер телефона

    Returns:
        True если номер корректен
    """
    if not phone:
        return False

    # Убираем пробелы, скобки и дефисы
    phone = re.sub(r"[\s\(\)\-]", "", phone)

    # Проверяем формат +7XXXXXXXXXX
    if phone.startswith("+7") and len(phone) == 12 and phone[1:].isdigit():
        return True

    # Проверяем формат 8XXXXXXXXXX
    if phone.startswith("8") and len(phone) == 11 and phone.isdigit():
        return True

    return False


def format_phone(phone: str) -> str:
    """
    Форматирует номер телефона в стандартный вид

    Args:
        phone: Номер телефона

    Returns:
        Отформатированный номер в виде +7XXXXXXXXXX
    """
    if not phone:
        return phone

    # Убираем все нецифровые символы
    digits = re.sub(r"[^\d]", "", phone)

    if len(digits) == 11 and digits.startswith("8"):
        # Заменяем 8 на +7
        return "+7" + digits[1:]
    elif len(digits) == 11 and digits.startswith("7"):
        # Добавляем +
        return "+" + digits
    elif len(digits) == 10:
        # Добавляем +7
        return "+7" + digits
    else:
        return phone


def filter_available_slots(
    slots: List[Dict[str, Any]],
    preferred_time_start: Optional[str] = None,
    preferred_time_end: Optional[str] = None,
    preferred_doctors: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Фильтрует доступные слоты по предпочтениям

    Args:
        slots: Список доступных слотов
        preferred_time_start: Предпочитаемое время начала (HH:MM)
        preferred_time_end: Предпочитаемое время окончания (HH:MM)
        preferred_doctors: Список предпочитаемых ID врачей

    Returns:
        Отфильтрованный список слотов
    """
    filtered_slots = []

    for slot in slots:
        # Фильтр по врачам
        if preferred_doctors and slot["doctor"].id not in preferred_doctors:
            continue

        # Фильтр по времени
        if preferred_time_start or preferred_time_end:
            appointment = slot["appointment"]
            visit_start = appointment.visitStart.time()

            if preferred_time_start:
                start_time = datetime.strptime(preferred_time_start, "%H:%M").time()
                if visit_start < start_time:
                    continue

            if preferred_time_end:
                end_time = datetime.strptime(preferred_time_end, "%H:%M").time()
                if visit_start > end_time:
                    continue

        filtered_slots.append(slot)

    return filtered_slots


def sort_slots_by_priority(
    slots: List[Dict[str, Any]], preferred_doctors: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Сортирует слоты по приоритету

    Args:
        slots: Список слотов
        preferred_doctors: Список предпочитаемых ID врачей

    Returns:
        Отсортированный список слотов
    """

    def get_priority(slot):
        priority = 0

        # Приоритет предпочитаемым врачам
        if preferred_doctors and slot["doctor"].id in preferred_doctors:
            priority += 100

        # Приоритет по времени (раньше = выше приоритет)
        appointment = slot["appointment"]
        priority += (24 - appointment.visitStart.hour) * 10

        # Приоритет по количеству свободных мест
        priority += slot["doctor"].freeTicketCount

        return priority

    return sorted(slots, key=get_priority, reverse=True)
