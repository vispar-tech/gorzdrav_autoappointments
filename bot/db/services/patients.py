from typing import Any, Dict, List, Optional

from bot.db.models.patients import Patient
from bot.db.services.base import BaseService


class PatientsService(BaseService[Patient]):
    """Service for working with patients."""

    model = Patient

    async def get_patients_by_user_id(self, user_id: int) -> List[Patient]:
        """Get all patients for a specific user."""
        return list(await self.find_all(user_id=user_id))

    async def get_patient_by_id(self, patient_id: int) -> Optional[Patient]:
        """Get patient by ID."""
        return await self.find_one_or_none(id=patient_id)

    async def create_patient(self, patient_data: Dict[str, Any]) -> Patient:
        """Create a new patient."""
        patient = Patient(**patient_data)
        return await self.add_model(patient)

    async def delete_patient(self, patient_id: int) -> None:
        """Delete a patient."""
        return await self.delete(patient_id)
