"""
Pydantic модели для API Горздрав
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class APIResponse(BaseModel):
    """Базовая модель ответа API"""

    success: bool = Field(..., description="Успешность запроса")
    errorCode: int = Field(0, description="Код ошибки")
    message: Optional[str] = Field(None, description="Сообщение")
    stackTrace: Optional[str] = Field(None, description="Стек вызовов")


class District(BaseModel):
    """Модель района города"""

    id: str = Field(..., description="ID района")
    name: str = Field(..., description="Название района")
    okato: Optional[int] = Field(None, description="ОКАТО код")

    class Config:
        json_encoders = {
            int: str  # ID может быть строкой в API
        }


class DistrictsResponse(APIResponse):
    """Ответ с списком районов"""

    result: List[District] = Field(..., description="Список районов")


class LPU(BaseModel):
    """Модель лечебно-профилактического учреждения"""

    id: int = Field(..., description="ID ЛПУ")
    description: str = Field(..., description="Описание ЛПУ")
    district: int = Field(..., description="ID района")
    districtId: int = Field(..., description="ID района (дублирует district)")
    districtName: str = Field(..., description="Название района")
    isActive: bool = Field(..., description="Активно ли ЛПУ")
    lpuFullName: str = Field(..., description="Полное название ЛПУ")
    lpuShortName: str = Field(..., description="Краткое название ЛПУ")
    lpuType: Optional[str] = Field(None, description="Тип ЛПУ")
    oid: Optional[str] = Field(None, description="OID")
    partOf: Optional[str] = Field(None, description="Часть организации")
    headOrganization: Optional[str] = Field(None, description="ID головной организации")
    organization: str = Field(..., description="ID организации")
    address: Optional[str] = Field(None, description="Адрес")
    phone: Optional[str] = Field(None, description="Телефон")
    email: Optional[str] = Field(None, description="Email")
    longitude: Optional[str] = Field(None, description="Долгота")
    latitude: Optional[str] = Field(None, description="Широта")
    covidVaccination: bool = Field(..., description="COVID вакцинация")
    inDepthExamination: bool = Field(..., description="Углубленный осмотр")
    subdivision: Optional[str] = Field(None, description="Подразделение")
    covidVaccinationTicketCount: Optional[int] = Field(
        None, description="Количество талонов на COVID вакцинацию"
    )
    covidVaccinationTicketReceiveTime: Optional[str] = Field(
        None, description="Время получения талона на COVID вакцинацию"
    )


class LPUsResponse(APIResponse):
    """Ответ с списком ЛПУ"""

    result: List[LPU] = Field(..., description="Список ЛПУ")


class Specialist(BaseModel):
    """Модель специализации врача"""

    id: str = Field(..., description="ID специализации")
    ferId: str = Field(..., description="Федеральный код специальности")
    name: str = Field(..., description="Название специальности")
    countFreeParticipant: int = Field(
        ..., description="Количество свободных участников"
    )
    countFreeTicket: int = Field(..., description="Количество свободных талонов")
    lastDate: Optional[datetime] = Field(None, description="Последняя доступная дата")
    nearestDate: Optional[datetime] = Field(
        None, description="Ближайшая доступная дата"
    )

    @field_validator("lastDate", "nearestDate", mode="before")
    def parse_dates(cls, v: str | None) -> datetime | None:
        """Парсит даты из строки"""
        if v is None:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None


class SpecialistsResponse(APIResponse):
    """Ответ с списком специализаций"""

    result: List[Specialist] = Field(..., description="Список специализаций")


class Doctor(BaseModel):
    """Модель врача"""

    id: str = Field(..., description="ID врача")
    name: str = Field(..., description="ФИО врача")
    ariaNumber: str = Field(..., description="Номер кабинета")
    ariaType: Optional[str] = Field(None, description="Тип кабинета")
    comment: Optional[str] = Field(None, description="Комментарий")
    freeParticipantCount: int = Field(
        ..., description="Количество свободных участников"
    )
    freeTicketCount: int = Field(..., description="Количество свободных талонов")
    lastDate: Optional[datetime] = Field(None, description="Последняя доступная дата")
    nearestDate: Optional[datetime] = Field(
        None, description="Ближайшая доступная дата"
    )
    lastName: Optional[str] = Field(None, description="Фамилия")
    firstName: Optional[str] = Field(None, description="Имя")
    middleName: Optional[str] = Field(None, description="Отчество")

    @field_validator("lastDate", "nearestDate", mode="before")
    def parse_dates(cls, v: str | None) -> datetime | None:
        """Парсит даты из строки"""
        if v is None:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None


class DoctorsResponse(APIResponse):
    """Ответ с списком врачей"""

    result: List[Doctor] = Field(..., description="Список врачей")


class Appointment(BaseModel):
    """Модель записи на прием"""

    id: str = Field(..., description="ID записи")
    visitStart: datetime = Field(..., description="Время начала приема")
    visitEnd: datetime = Field(..., description="Время окончания приема")
    address: Optional[str] = Field(None, description="Адрес")
    number: Optional[str] = Field(None, description="Номер")
    room: str = Field(..., description="Кабинет")

    @field_validator("visitStart", "visitEnd", mode="before")
    def parse_dates(cls, v: str) -> datetime:
        """Парсит даты из строки"""
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"Неверный формат даты: {v}")


class AppointmentsResponse(APIResponse):
    """Ответ с списком записей на прием"""

    result: List[Appointment] = Field(..., description="Список записей на прием")


class PatientSearchResponse(APIResponse):
    """Ответ поиска пациента"""

    result: Optional[str] = Field(None, description="ID найденного пациента")


class PatientUpdateRequest(BaseModel):
    """Запрос на обновление данных пациента (минимальный)"""

    lpuId: int = Field(..., description="ID ЛПУ")
    patientId: str = Field(..., description="ID пациента")
    mobilePhoneNumber: str = Field(..., description="Мобильный телефон без +7")


class AppointmentCreateRequest(BaseModel):
    """Запрос на создание записи на прием (по примерам из requests)"""

    esiaId: Optional[str] = Field(None, description="ESIA ID")
    lpuId: int = Field(..., description="ID ЛПУ")
    patientId: str = Field(..., description="ID пациента")
    appointmentId: str = Field(..., description="ID слота записи")
    referralId: Optional[str] = Field(None, description="ID направления")
    ipmpiCardId: Optional[str] = Field(None, description="ID карты IPMPI")
    recipientEmail: Optional[str] = Field(None, description="Email получателя")
    patientLastName: str = Field(..., description="Фамилия пациента")
    patientFirstName: str = Field(..., description="Имя пациента")
    patientMiddleName: str = Field(..., description="Отчество пациента")
    patientBirthdate: str = Field(..., description="Дата рождения в ISO")
    room: Optional[str] = Field(None, description="Кабинет")
    address: Optional[str] = Field(None, description="Адрес приема")
    visitDate: str = Field(..., description="Дата/время приема в ISO")


class AppointmentCreateResponse(APIResponse):
    """Ответ создания записи на прием (без result)"""


class DoctorBrief(BaseModel):
    id: Optional[str] = Field(None)
    name: Optional[str] = Field(None)
    ariaNumber: Optional[str] = Field(None)
    ariaType: Optional[str] = Field(None)
    comment: Optional[str] = Field(None)
    freeParticipantCount: Optional[int] = Field(None)
    freeTicketCount: Optional[int] = Field(None)
    lastDate: Optional[datetime] = Field(None)
    nearestDate: Optional[datetime] = Field(None)
    lastName: Optional[str] = Field(None)
    firstName: Optional[str] = Field(None)
    middleName: Optional[str] = Field(None)

    @field_validator("lastDate", "nearestDate", mode="before")
    def _parse_dates(cls, v: str | None) -> datetime | None:
        if v is None:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None


class SpecialistBrief(BaseModel):
    id: Optional[str] = Field(None)
    ferId: Optional[str] = Field(None)
    name: Optional[str] = Field(None)
    countFreeParticipant: Optional[int] = Field(None)
    countFreeTicket: Optional[int] = Field(None)
    lastDate: Optional[datetime] = Field(None)
    nearestDate: Optional[datetime] = Field(None)

    @field_validator("lastDate", "nearestDate", mode="before")
    def _parse_dates(cls, v: str | None) -> datetime | None:
        if v is None:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None


class PositionBrief(BaseModel):
    id: Optional[str] = Field(None)
    ferId: Optional[str] = Field(None)
    name: Optional[str] = Field(None)
    countFreeParticipant: Optional[int] = Field(None)
    countFreeTicket: Optional[int] = Field(None)
    lastDate: Optional[datetime] = Field(None)
    nearestDate: Optional[datetime] = Field(None)

    @field_validator("lastDate", "nearestDate", mode="before")
    def _parse_dates(cls, v: str | None) -> datetime | None:
        if v is None:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None


class PatientAppointmentItem(BaseModel):
    appointmentId: str
    dateCreatedAppointment: Optional[datetime] = None
    doctorBringReferal: Optional[DoctorBrief] = None
    doctorRendingConsultation: Optional[DoctorBrief] = None
    isAppointmentByReferral: bool
    lpuAddress: Optional[str] = None
    lpuFullName: Optional[str] = None
    lpuId: str
    lpuPhone: Optional[str] = None
    lpuShortName: Optional[str] = None
    patientId: str
    referralId: Optional[str] = None
    specialityBringReferal: Optional[SpecialistBrief] = None
    specialityRendingConsultation: Optional[SpecialistBrief] = None
    visitStart: datetime
    status: Optional[str] = None
    type: Optional[str] = None
    positionBringReferal: Optional[PositionBrief] = None
    positionRendingConsultation: Optional[PositionBrief] = None
    infections: Optional[str] = None
    patientFullName: Optional[str] = None
    patientBirthDate: Optional[str] = None

    @field_validator("visitStart", "dateCreatedAppointment", mode="before")
    def _parse_dt(cls, v: str | None) -> datetime | None:
        if v is None:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None


class PatientAppointmentsResponse(APIResponse):
    result: List[PatientAppointmentItem] = Field(default_factory=list)
