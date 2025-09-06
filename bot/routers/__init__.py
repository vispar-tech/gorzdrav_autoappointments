from .appointments import router as appointments_router
from .patients import router as patients_router
from .payments import router as payments_router
from .schedules import router as schedules_router
from .start import router as start_router

__all__ = [
    "appointments_router",
    "patients_router",
    "payments_router",
    "schedules_router",
    "start_router",
]
