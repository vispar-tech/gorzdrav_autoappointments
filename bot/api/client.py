"""Асинхронный минималистичный API клиент для ГорЗдрав."""

from types import TracebackType
from typing import Any, Dict, Optional, Self, Type
from urllib.parse import urljoin

import aiohttp
from loguru import logger

from bot.api.constants import BASE_URL, DEFAULT_HEADERS, ENDPOINTS

from .models import (
    LPU,
    AppointmentCreateRequest,
    AppointmentCreateResponse,
    AppointmentsResponse,
    AttachmentsResponse,
    DistrictsResponse,
    DoctorsResponse,
    LPUsResponse,
    PatientAppointmentsResponse,
    PatientSearchResponse,
    PatientUpdateRequest,
    SpecialistsResponse,
)


class GorzdravAPIError(Exception):
    """Exception with fields of the error response."""

    def __init__(
        self,
        message: str,
        error_code: int,
        stack_trace: Optional[str],
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.stack_trace = stack_trace


class GorzdravAPIClient:
    """Asynchronous client for working with API."""

    def __init__(self, timeout: int = 30) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> Self:
        await self._ensure_session()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _headers(self) -> Dict[str, str]:
        return dict(DEFAULT_HEADERS)

    async def _ensure_session(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                headers=self._headers(),
            )

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Make HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            API response as dictionary

        Raises:
            GorzdravAPIError: When API returns error
            RuntimeError: If session is not initialized
        """
        await self._ensure_session()
        url = urljoin(BASE_URL, endpoint)

        if self._session is None:
            raise RuntimeError("Session not initialized")

        async with self._session.request(method, url, **kwargs) as resp:
            data = await resp.json()
            if not data.get("success", False):
                raise GorzdravAPIError(
                    message=data.get("message") or f"HTTP {resp.status}",
                    error_code=int(data.get("errorCode", 0)),
                    stack_trace=data.get("stackTrace"),
                )
            return data

    # Общие
    async def get_districts(self) -> DistrictsResponse:
        """Get all districts.

        Returns:
            Districts response containing list of available districts
        """
        logger.info("Fetching districts")
        data = await self._request("GET", ENDPOINTS["districts"])
        logger.debug(f"Retrieved {len(data.get('result', []))} districts")
        return DistrictsResponse(**data)

    async def get_all_lpus(self) -> LPUsResponse:
        """Get all medical institutions (LPUs).

        Returns:
            LPUs response containing list of all medical institutions
        """
        logger.info("Fetching all LPUs")
        data = await self._request("GET", ENDPOINTS["lpus"])
        logger.debug(f"Retrieved {len(data.get('result', []))} LPUs")
        return LPUsResponse(**data)

    async def get_lpus_by_district(self, district_id: int) -> LPUsResponse:
        """Get medical institutions by district.

        Args:
            district_id: District ID to filter LPUs

        Returns:
            LPUs response containing list of medical institutions in the district
        """
        logger.info(f"Fetching LPUs for district {district_id}")
        endpoint = ENDPOINTS["lpus_by_district"].format(district_id=district_id)
        data = await self._request("GET", endpoint)
        logger.debug(
            f"Retrieved {len(data.get('result', []))} LPUs for district {district_id}",
        )
        return LPUsResponse(**data)

    async def get_lpu_by_id(self, lpu_id: int) -> Optional[LPU]:
        """Get single medical institution by ID.

        Args:
            lpu_id: Medical institution ID

        Returns:
            LPU object if found, None otherwise
        """
        logger.info(f"Fetching LPU with ID {lpu_id}")
        lpus = (await self.get_all_lpus()).result
        for lpu in lpus:
            if lpu.id == lpu_id:
                logger.debug(f"Found LPU: {lpu.lpu_short_name or lpu.lpu_full_name}")
                return lpu
        logger.warning(f"LPU with ID {lpu_id} not found")
        return None

    # Расписание
    async def get_specialists(self, lpu_id: int) -> SpecialistsResponse:
        """Get specialists for medical institution.

        Args:
            lpu_id: Medical institution ID

        Returns:
            Specialists response containing list of available specialists
        """
        logger.info(f"Fetching specialists for LPU {lpu_id}")
        endpoint = ENDPOINTS["specialists"].format(lpu_id=lpu_id)
        data = await self._request("GET", endpoint)
        logger.debug(
            f"Retrieved {len(data.get('result', []))} specialists for LPU {lpu_id}",
        )
        return SpecialistsResponse(**data)

    async def get_doctors(self, lpu_id: int, specialist_id: str) -> DoctorsResponse:
        """Get doctors for specific specialist in medical institution.

        Args:
            lpu_id: Medical institution ID
            specialist_id: Specialist ID

        Returns:
            Doctors response containing list of available doctors
        """
        logger.info(f"Fetching doctors for LPU {lpu_id}, specialist {specialist_id}")
        endpoint = ENDPOINTS["doctors"].format(
            lpu_id=lpu_id,
            specialist_id=specialist_id,
        )
        data = await self._request("GET", endpoint)
        logger.debug(f"Retrieved {len(data.get('result', []))} doctors")
        return DoctorsResponse(**data)

    async def get_appointments(
        self,
        lpu_id: int,
        doctor_id: str,
    ) -> AppointmentsResponse:
        """Get available appointments for specific doctor.

        Args:
            lpu_id: Medical institution ID
            doctor_id: Doctor ID

        Returns:
            Appointments response containing list of available time slots
        """
        logger.info(f"Fetching appointments for LPU {lpu_id}, doctor {doctor_id}")
        endpoint = ENDPOINTS["appointments"].format(lpu_id=lpu_id, doctor_id=doctor_id)
        data = await self._request("GET", endpoint)
        logger.debug(f"Retrieved {len(data.get('result', []))} appointments")
        return AppointmentsResponse(**data)

    # Пациенты
    async def search_patient(
        self,
        lpu_id: int,
        last_name: str,
        first_name: str,
        middle_name: str,
        birthdate_iso: str,
        birthdate_value: Optional[str] = None,
    ) -> PatientSearchResponse:
        """Search for patient by personal information.

        Args:
            lpu_id: Medical institution ID
            last_name: Patient's last name
            first_name: Patient's first name
            middle_name: Patient's middle name
            birthdate_iso: Patient's birthdate in ISO format
            birthdate_value: Optional birthdate value

        Returns:
            Patient search response containing patient information if found
        """
        logger.info(f"Searching patient: {last_name} {first_name} {middle_name}")
        params = {
            "lpuId": lpu_id,
            "lastName": last_name,
            "firstName": first_name,
            "middleName": middle_name,
            "birthdate": birthdate_iso,
        }
        if birthdate_value:
            params["birthdateValue"] = birthdate_value
        data = await self._request("GET", ENDPOINTS["patient_search"], params=params)
        logger.debug(
            f"Patient search completed, found: {data.get('result') is not None}",
        )
        return PatientSearchResponse(**data)

    async def update_patient(self, payload: PatientUpdateRequest) -> None:
        """Update patient information.

        Args:
            payload: Patient update request data
        """
        logger.info("Updating patient information")
        await self._request(
            "POST",
            ENDPOINTS["patient_update"],
            json=payload.model_dump(exclude_none=True),
        )
        logger.debug("Patient information updated successfully")

    # Запись
    async def create_appointment(
        self,
        payload: AppointmentCreateRequest,
    ) -> AppointmentCreateResponse:
        """Create new appointment.

        Args:
            payload: Appointment creation request data

        Returns:
            Appointment creation response with booking details
        """
        logger.info("Creating new appointment")
        data = await self._request(
            "POST",
            ENDPOINTS["appointment_create"],
            json=payload.model_dump(exclude_none=True),
        )
        logger.debug("Appointment created successfully")
        return AppointmentCreateResponse(**data)

    # Записи пациента
    async def get_patient_appointments(
        self,
        lpu_id: int,
        patient_id: str,
    ) -> PatientAppointmentsResponse:
        """Get patient's existing appointments.

        Args:
            lpu_id: Medical institution ID
            patient_id: Patient ID

        Returns:
            Patient appointments response containing list of patient's appointments
        """
        logger.info(f"Fetching appointments for patient {patient_id} in LPU {lpu_id}")
        params = {"lpuId": str(lpu_id), "patientId": patient_id}
        data = await self._request(
            "GET",
            ENDPOINTS["patient_appointments"],
            params=params,
        )
        logger.debug(f"Retrieved {len(data.get('result', []))} patient appointments")
        return PatientAppointmentsResponse(**data)

    # Прикрепления
    async def get_attachments(
        self,
        polis_s: Optional[str] = None,
        polis_n: Optional[str] = None,
    ) -> AttachmentsResponse:
        """Get patient attachments by insurance policy.

        Args:
            polis_s: Insurance policy series
            polis_n: Insurance policy number

        Returns:
            Attachments response containing patient attachment information
        """
        logger.info(
            f"Fetching attachments for policy series={polis_s}, number={polis_n}",
        )
        params = {}
        if polis_s is not None:
            params["polisS"] = polis_s
        if polis_n is not None:
            params["polisN"] = polis_n
        data = await self._request(
            "GET",
            ENDPOINTS["attachments"],
            params=params,
        )
        logger.debug(f"Retrieved {len(data.get('result', []))} attachments")
        return AttachmentsResponse(**data)
