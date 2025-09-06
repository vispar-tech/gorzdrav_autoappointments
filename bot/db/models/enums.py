from enum import Enum


class ScheduleStatus(Enum):
    """Schedule appointment statuses."""

    PENDING = "pending"  # Waiting for slot search
    FOUND = "found"  # Slot found
    CANCELLED = "cancelled"  # Appointment cancelled
