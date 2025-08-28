"""
Асинхронный минималистичный API клиент для ГорЗдрав
"""

from types import TracebackType
from typing import Optional, Dict, Any, Type
from urllib.parse import urljoin
import aiohttp
from loguru import logger

from bot.api.constants import BASE_URL, DEFAULT_HEADERS, ENDPOINTS
from .models import (
    DistrictsResponse,
    LPUsResponse,
    LPU,
    SpecialistsResponse,
    DoctorsResponse,
    AppointmentsResponse,
    PatientSearchResponse,
    PatientUpdateRequest,
    AppointmentCreateRequest,
    AppointmentCreateResponse,
    PatientAppointmentsResponse,
)


class GorzdravAPIException(Exception):
    """Исключение с полями ответа об ошибке"""

    def __init__(self, message: str, error_code: int, stack_trace: Optional[str]):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.stack_trace = stack_trace


class GorzdravAPIClient:
    """Асинхронный клиент для работы с API"""

    def __init__(self, token: Optional[str] = None, timeout: int = 30):
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._token = token

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.close()

    def _headers(self) -> Dict[str, str]:
        headers = dict(DEFAULT_HEADERS)
        if self._token:
            headers["token"] = self._token
        return headers

    async def _ensure_session(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout, headers=self._headers()
            )

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> Dict[str, Any]:
        await self._ensure_session()
        url = urljoin(BASE_URL, endpoint)
        assert self._session is not None
        async with self._session.request(method, url, **kwargs) as resp:
            data = await resp.json()
            if not data.get("success", False):
                raise GorzdravAPIException(
                    message=data.get("message") or f"HTTP {resp.status}",
                    error_code=int(data.get("errorCode", 0)),
                    stack_trace=data.get("stackTrace"),
                )
            return data

    # Общие
    async def get_districts(self) -> DistrictsResponse:
        logger.info("GET districts")
        data = await self._request("GET", ENDPOINTS["districts"])
        return DistrictsResponse(**data)

    async def get_all_lpus(self) -> LPUsResponse:
        logger.info("GET lpus")
        data = await self._request("GET", ENDPOINTS["lpus"])
        return LPUsResponse(**data)

    async def get_lpus_by_district(self, district_id: int) -> LPUsResponse:
        logger.info(f"GET lpus by district {district_id}")
        endpoint = ENDPOINTS["lpus_by_district"].format(district_id=district_id)
        data = await self._request("GET", endpoint)
        return LPUsResponse(**data)

    async def get_lpu_by_id(self, lpu_id: int) -> Optional[LPU]:
        """Возвращает информацию об одном ЛПУ (через полный список)."""
        lpus = (await self.get_all_lpus()).result
        for lpu in lpus:
            if lpu.id == lpu_id:
                return lpu
        return None

    # Расписание
    async def get_specialists(self, lpu_id: int) -> SpecialistsResponse:
        logger.info(f"GET specialists for lpu {lpu_id}")
        endpoint = ENDPOINTS["specialists"].format(lpu_id=lpu_id)
        data = await self._request("GET", endpoint)
        return SpecialistsResponse(**data)

    async def get_doctors(self, lpu_id: int, specialist_id: str) -> DoctorsResponse:
        logger.info(f"GET doctors for lpu {lpu_id} speciality {specialist_id}")
        endpoint = ENDPOINTS["doctors"].format(
            lpu_id=lpu_id, specialist_id=specialist_id
        )
        data = await self._request("GET", endpoint)
        return DoctorsResponse(**data)

    async def get_appointments(
        self, lpu_id: int, doctor_id: str
    ) -> AppointmentsResponse:
        logger.info(f"GET appointments for lpu {lpu_id} doctor {doctor_id}")
        endpoint = ENDPOINTS["appointments"].format(lpu_id=lpu_id, doctor_id=doctor_id)
        data = await self._request("GET", endpoint)
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
        logger.info("GET patient search")
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
        return PatientSearchResponse(**data)

    async def update_patient(self, payload: PatientUpdateRequest) -> None:
        logger.info("POST patient update")
        await self._request(
            "POST",
            ENDPOINTS["patient_update"],
            json=payload.model_dump(exclude_none=True),
        )

    # Запись
    async def create_appointment(
        self, payload: AppointmentCreateRequest
    ) -> AppointmentCreateResponse:
        logger.info("POST appointment create")
        data = await self._request(
            "POST",
            ENDPOINTS["appointment_create"],
            json=payload.model_dump(exclude_none=True),
        )
        return AppointmentCreateResponse(**data)

    # Записи пациента
    async def get_patient_appointments(
        self, lpu_id: int, patient_id: str
    ) -> PatientAppointmentsResponse:
        logger.info(f"GET patient appointments lpu={lpu_id} patient={patient_id}")
        params = {"lpuId": str(lpu_id), "patientId": patient_id}
        data = await self._request(
            "GET", ENDPOINTS["patient_appointments"], params=params
        )
        return PatientAppointmentsResponse(**data)

    async def health_check(self) -> bool:
        try:
            await self.get_districts()
            return True
        except Exception:
            return False
