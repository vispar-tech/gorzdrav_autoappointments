"""Utilities for working with Gorzdrav API."""

import re
from datetime import date, datetime
from typing import Optional

from loguru import logger


def parse_date(date_str: str) -> Optional[date]:
    """
    Parse date from string in Gorzdrav format.

    Args:
        date_str: Date string (e.g., "1990-05-15")

    Returns:
        date object or None on error
    """
    if not date_str:
        return None

    try:
        # Try different date formats
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


def validate_phone(phone: str) -> bool:
    """
    Validate phone number.

    Args:
        phone: Phone number

    Returns:
        True if number is valid
    """
    if not phone:
        return False

    # Remove spaces, brackets and dashes
    phone = re.sub(r"[\s\(\)\-]", "", phone)

    # Check format +7XXXXXXXXXX
    if phone.startswith("+7") and len(phone) == 12 and phone[1:].isdigit():
        return True

    # Check format 8XXXXXXXXXX
    return bool(phone.startswith("8") and len(phone) == 11 and phone.isdigit())


def format_phone(phone: str) -> str:
    """
    Format phone number to standard format.

    Args:
        phone: Phone number

    Returns:
        Formatted number as +7XXXXXXXXXX
    """
    if not phone:
        return phone

    # Remove all non-digit characters
    digits = re.sub(r"[^\d]", "", phone)

    if len(digits) == 11 and digits.startswith("8"):
        # Replace 8 with +7
        return "+7" + digits[1:]
    if len(digits) == 11 and digits.startswith("7"):
        # Add +
        return "+" + digits
    if len(digits) == 10:
        # Add +7
        return "+7" + digits
    return phone
