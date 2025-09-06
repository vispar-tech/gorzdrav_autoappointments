"""Pydantic модели для API Горздрав."""

from datetime import datetime
from typing import Any, Callable, ClassVar, List, Optional

from pydantic import BaseModel, Field, field_validator


class APIResponse(BaseModel):
    """Base model for API response."""

    success: bool = Field(..., description="Success of the request")
    error_code: int = Field(0, description="Error code", alias="errorCode")
    message: Optional[str] = Field(None, description="Message", alias="message")
    stack_trace: Optional[str] = Field(
        None,
        description="Stack of calls",
        alias="stackTrace",
    )


class District(BaseModel):
    """Model of the district of the city."""

    id: str = Field(..., description="ID of the district")
    name: str = Field(..., description="Name of the district")
    okato: Optional[int] = Field(None, description="OKATO code")

    class Config:
        json_encoders: ClassVar[dict[type, Callable[[Any], Any]]] = {
            int: str,  # ID can be a string in API
        }


class DistrictsResponse(APIResponse):
    """Response with a list of districts."""

    result: List[District] = Field(..., description="List of districts")


class LPU(BaseModel):
    """Model of the medical institution."""

    id: int = Field(..., description="ID of the LPU")
    description: Optional[str] = Field(None, description="Description of the LPU")
    district: int = Field(..., description="ID of the district")
    district_id: int = Field(
        ...,
        description="ID of the district (duplicates district)",
        alias="districtId",
    )
    district_name: Optional[str] = Field(
        None,
        description="Name of the district",
        alias="districtName",
    )
    is_active: bool = Field(..., description="Is the LPU active", alias="isActive")
    lpu_full_name: Optional[str] = Field(
        None,
        description="Full name of the LPU",
        alias="lpuFullName",
    )
    lpu_short_name: Optional[str] = Field(
        None,
        description="Short name of the LPU",
        alias="lpuShortName",
    )
    lpu_type: Optional[str] = Field(
        None,
        description="Type of the LPU",
        alias="lpuType",
    )
    oid: Optional[str] = Field(None, description="OID")
    part_of: Optional[str] = Field(
        None,
        description="Part of the organization",
        alias="partOf",
    )
    head_organization: Optional[str] = Field(
        None,
        description="ID of the main organization",
        alias="headOrganization",
    )
    organization: Optional[str] = Field(None, description="ID of the organization")
    address: Optional[str] = Field(None, description="Address")
    phone: Optional[str] = Field(None, description="Phone")
    email: Optional[str] = Field(None, description="Email")
    longitude: Optional[str] = Field(None, description="Longitude")
    latitude: Optional[str] = Field(None, description="Latitude")
    covid_vaccination: bool = Field(
        ...,
        description="COVID vaccination",
        alias="covidVaccination",
    )
    in_depth_examination: bool = Field(
        ...,
        description="In-depth examination",
        alias="inDepthExamination",
    )
    subdivision: Optional[str] = Field(None, description="Subdivision")
    covid_vaccination_ticket_count: Optional[int] = Field(
        None,
        description="Number of tickets for COVID vaccination",
        alias="covidVaccinationTicketCount",
    )
    covid_vaccination_ticket_receive_time: Optional[str] = Field(
        None,
        description="Time of receiving the ticket for COVID vaccination",
        alias="covidVaccinationTicketReceiveTime",
    )


class LPUsResponse(APIResponse):
    """Response with a list of LPUs."""

    result: List[LPU] = Field(..., description="List of LPUs")


class Specialist(BaseModel):
    """Model of the specialist of the doctor."""

    id: str = Field(..., description="ID of the specialist")
    fer_id: Optional[str] = Field(
        None,
        description="Federal code of the specialty",
        alias="ferId",
    )
    name: Optional[str] = Field(None, description="Name of the specialty")
    count_free_participant: int = Field(
        ...,
        description="Number of free participants",
        alias="countFreeParticipant",
    )
    count_free_ticket: int = Field(
        ...,
        description="Number of free tickets",
        alias="countFreeTicket",
    )
    last_date: Optional[datetime] = Field(
        None,
        description="Last available date",
        alias="lastDate",
    )
    nearest_date: Optional[datetime] = Field(
        None,
        description="Nearest available date",
        alias="nearestDate",
    )

    @field_validator("last_date", "nearest_date", mode="before")
    @classmethod
    def parse_dates(cls, v: str | None) -> datetime | None:
        """Parse dates from string."""
        if v is None:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None


class SpecialistsResponse(APIResponse):
    """Response with a list of specialists."""

    result: List[Specialist] = Field(..., description="List of specialists")


class Doctor(BaseModel):
    """Model of the doctor."""

    id: str = Field(..., description="ID of the doctor")
    name: str = Field(..., description="FIO of the doctor")
    aria_number: Optional[str] = Field(
        None,
        description="Number of the cabinet",
        alias="ariaNumber",
    )
    aria_type: Optional[str] = Field(
        None,
        description="Type of the cabinet",
        alias="ariaType",
    )
    comment: Optional[str] = Field(None, description="Comment")
    free_participant_count: int = Field(
        ...,
        description="Number of free participants",
        alias="freeParticipantCount",
    )
    free_ticket_count: int = Field(
        ...,
        description="Number of free tickets",
        alias="freeTicketCount",
    )
    last_date: Optional[datetime] = Field(
        None,
        description="Last available date",
        alias="lastDate",
    )
    nearest_date: Optional[datetime] = Field(
        None,
        description="Nearest available date",
        alias="nearestDate",
    )
    last_name: Optional[str] = Field(None, description="Last name", alias="lastName")
    first_name: Optional[str] = Field(None, description="First name", alias="firstName")
    middle_name: Optional[str] = Field(
        None,
        description="Middle name",
        alias="middleName",
    )

    @field_validator("last_date", "nearest_date", mode="before")
    @classmethod
    def parse_dates(cls, v: str | None) -> datetime | None:
        """Parse dates from string."""
        if v is None:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None


class DoctorsResponse(APIResponse):
    """Response with a list of doctors."""

    result: List[Doctor] = Field(..., description="List of doctors")


class Appointment(BaseModel):
    """Model of the appointment."""

    id: str = Field(..., description="ID of the appointment")
    visit_start: datetime = Field(
        ...,
        description="Time of the appointment start",
        alias="visitStart",
    )
    visit_end: datetime = Field(
        ...,
        description="Time of the appointment end",
        alias="visitEnd",
    )
    address: Optional[str] = Field(None, description="Address")
    number: Optional[str] = Field(None, description="Number")
    room: Optional[str] = Field(..., description="Cabinet")

    @field_validator("visit_start", "visit_end", mode="before")
    @classmethod
    def parse_dates(cls, v: str) -> datetime:
        """Parse dates from string."""
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid date format: {v}") from e


class AppointmentsResponse(APIResponse):
    """Response with a list of appointments."""

    result: List[Appointment] = Field(..., description="List of appointments")


class PatientSearchResponse(APIResponse):
    """Response with a list of patients."""

    result: Optional[str] = Field(None, description="ID of the found patient")


class PatientUpdateRequest(BaseModel):
    """Request to update the patient data (minimal)."""

    lpu_id: int = Field(..., description="ID of the LPU", serialization_alias="lpuId")
    patient_id: str = Field(
        ...,
        description="ID of the patient",
        serialization_alias="patientId",
    )
    mobile_phone_number: Optional[str] = Field(
        ...,
        description="Mobile phone without +7",
        serialization_alias="mobilePhoneNumber",
    )


class AppointmentCreateRequest(BaseModel):
    """Request to create an appointment (by examples from requests)."""

    esia_id: Optional[str] = Field(
        default=None,
        description="ESIA ID",
        serialization_alias="esiaId",
    )
    lpu_id: int = Field(..., description="ID of the LPU", serialization_alias="lpuId")
    patient_id: str = Field(
        ...,
        description="ID of the patient",
        serialization_alias="patientId",
    )
    appointment_id: str = Field(
        ...,
        description="ID of the appointment slot",
        serialization_alias="appointmentId",
    )
    referral_id: Optional[str] = Field(
        None,
        description="ID of the referral",
        serialization_alias="referralId",
    )
    ipmpi_card_id: Optional[str] = Field(
        None,
        description="ID карты IPMPI",
        serialization_alias="ipmpiCardId",
    )
    recipient_email: Optional[str] = Field(
        None,
        description="Email of the recipient",
        serialization_alias="recipientEmail",
    )
    patient_last_name: str = Field(
        ...,
        description="Last name of the patient",
        serialization_alias="patientLastName",
    )
    patient_first_name: str = Field(
        ...,
        description="First name of the patient",
        serialization_alias="patientFirstName",
    )
    patient_middle_name: Optional[str] = Field(
        default=None,
        description="Middle name of the patient",
        serialization_alias="patientMiddleName",
    )
    patient_birthdate: str = Field(
        ...,
        description="Birthdate in ISO",
        serialization_alias="patientBirthdate",
    )
    room: Optional[str] = Field(None, description="Cabinet")
    address: Optional[str] = Field(None, description="Address of the appointment")
    visit_date: str = Field(
        ...,
        description="Date/time of the appointment in ISO",
        serialization_alias="visitDate",
    )


class AppointmentCreateResponse(APIResponse):
    """Response with a list of appointments."""


class DoctorBrief(BaseModel):
    """Model of the doctor brief."""

    id: Optional[str] = Field(None, description="ID of the doctor")
    name: Optional[str] = Field(None, description="Name of the doctor")
    aria_number: Optional[str] = Field(
        None,
        description="Number of the cabinet",
        alias="ariaNumber",
    )
    aria_type: Optional[str] = Field(
        None,
        description="Type of the cabinet",
        alias="ariaType",
    )
    comment: Optional[str] = Field(None, description="Comment")
    free_participant_count: Optional[int] = Field(
        None,
        description="Number of free participants",
        alias="freeParticipantCount",
    )
    free_ticket_count: Optional[int] = Field(
        None,
        description="Number of free tickets",
        alias="freeTicketCount",
    )
    last_date: Optional[datetime] = Field(
        None,
        description="Last available date",
        alias="lastDate",
    )
    nearest_date: Optional[datetime] = Field(
        None,
        description="Nearest available date",
        alias="nearestDate",
    )
    last_name: Optional[str] = Field(None, description="Last name", alias="lastName")
    first_name: Optional[str] = Field(None, description="First name", alias="firstName")
    middle_name: Optional[str] = Field(
        None,
        description="Middle name",
        alias="middleName",
    )

    @field_validator("last_date", "nearest_date", mode="before")
    @classmethod
    def _parse_dates(cls, v: str | None) -> datetime | None:
        """Parse dates from string."""
        if v is None:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None


class SpecialistBrief(BaseModel):
    """Model of the specialist brief."""

    id: Optional[str] = Field(None, description="ID of the specialist")
    fer_id: Optional[str] = Field(
        None,
        description="Federal code of the specialty",
        alias="ferId",
    )
    name: Optional[str] = Field(None, description="Name of the specialist")
    count_free_participant: Optional[int] = Field(
        None,
        description="Number of free participants",
        alias="countFreeParticipant",
    )
    count_free_ticket: Optional[int] = Field(
        None,
        description="Number of free tickets",
        alias="countFreeTicket",
    )
    last_date: Optional[datetime] = Field(
        None,
        description="Last available date",
        alias="lastDate",
    )
    nearest_date: Optional[datetime] = Field(
        None,
        description="Nearest available date",
        alias="nearestDate",
    )

    @field_validator("last_date", "nearest_date", mode="before")
    @classmethod
    def _parse_dates(cls, v: str | None) -> datetime | None:
        if v is None:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None


class PositionBrief(BaseModel):
    """Model of the position brief."""

    id: Optional[str] = Field(None, description="ID of the position")
    fer_id: Optional[str] = Field(
        None,
        description="Federal code of the position",
        alias="ferId",
    )
    name: Optional[str] = Field(None, description="Name of the position")
    count_free_participant: Optional[int] = Field(
        None,
        description="Number of free participants",
        alias="countFreeParticipant",
    )
    count_free_ticket: Optional[int] = Field(
        None,
        description="Number of free tickets",
        alias="countFreeTicket",
    )
    last_date: Optional[datetime] = Field(
        None,
        description="Last available date",
        alias="lastDate",
    )
    nearest_date: Optional[datetime] = Field(
        None,
        description="Nearest available date",
        alias="nearestDate",
    )

    @field_validator("last_date", "nearest_date", mode="before")
    @classmethod
    def _parse_dates(cls, v: str | None) -> datetime | None:
        if v is None:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None


class PatientAppointmentItem(BaseModel):
    """Model of the patient appointment item."""

    appointment_id: str = Field(
        ...,
        description="ID of the appointment",
        alias="appointmentId",
    )
    date_created_appointment: Optional[datetime] = Field(
        None,
        description="Date of the appointment",
        alias="dateCreatedAppointment",
    )
    doctor_bring_referal: Optional[DoctorBrief] = Field(
        None,
        description="Doctor brief for the bring referal",
        alias="doctorBringReferal",
    )
    doctor_rending_consultation: Optional[DoctorBrief] = Field(
        None,
        description="Doctor brief for the rending consultation",
        alias="doctorRendingConsultation",
    )
    is_appointment_by_referral: bool = Field(
        ...,
        description="Is the appointment by referral",
        alias="isAppointmentByReferral",
    )
    lpu_address: Optional[str] = Field(
        None,
        description="Address of the LPU",
        alias="lpuAddress",
    )
    lpu_full_name: Optional[str] = Field(
        None,
        description="Full name of the LPU",
        alias="lpuFullName",
    )
    lpu_id: str = Field(..., description="ID of the LPU", alias="lpuId")
    lpu_phone: Optional[str] = Field(
        None,
        description="Phone of the LPU",
        alias="lpuPhone",
    )
    lpu_short_name: Optional[str] = Field(
        None,
        description="Short name of the LPU",
        alias="lpuShortName",
    )
    patient_id: str = Field(..., description="ID of the patient", alias="patientId")
    referral_id: Optional[str] = Field(
        None,
        description="ID of the referral",
        alias="referralId",
    )
    speciality_bring_referal: Optional[SpecialistBrief] = Field(
        None,
        description="Specialist brief for the bring referal",
        alias="specialityBringReferal",
    )
    speciality_rending_consultation: Optional[SpecialistBrief] = Field(
        None,
        description="Specialist brief for the rending consultation",
        alias="specialityRendingConsultation",
    )
    visit_start: datetime = Field(
        ...,
        description="Time of the appointment start",
        alias="visitStart",
    )
    status: Optional[str] = Field(
        None,
        description="Status of the appointment",
        alias="status",
    )
    visit_type: Optional[str] = Field(
        None,
        description="Type of the appointment",
        alias="type",
    )
    position_bring_referal: Optional[PositionBrief] = Field(
        None,
        description="Position brief for the bring referal",
        alias="positionBringReferal",
    )
    position_rending_consultation: Optional[PositionBrief] = Field(
        None,
        description="Position brief for the rending consultation",
        alias="positionRendingConsultation",
    )
    infections: Optional[str] = Field(None, description="Infections")
    patient_full_name: Optional[str] = Field(
        None,
        description="Full name of the patient",
        alias="patientFullName",
    )
    patient_birth_date: Optional[str] = Field(
        None,
        description="Birth date of the patient",
        alias="patientBirthDate",
    )

    @field_validator("visit_start", "date_created_appointment", mode="before")
    @classmethod
    def _parse_dt(cls, v: str | None) -> datetime | None:
        if v is None:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None


class PatientAppointmentsResponse(APIResponse):
    """Response with a list of patient appointments."""

    result: List[PatientAppointmentItem] = Field(default_factory=list)


class Attachment(BaseModel):
    """Model of the attachment LPU."""

    id: int = Field(..., description="ID of the attachment")
    description: Optional[str] = Field(
        None,
        description="Description of the attachment",
    )
    district: int = Field(..., description="ID of the district")
    district_id: int = Field(
        ...,
        description="ID of the district (duplicates district)",
        alias="districtId",
    )
    district_name: Optional[str] = Field(
        None,
        description="Name of the district",
        alias="districtName",
    )
    is_active: bool = Field(
        ...,
        description="Is the attachment active",
        alias="isActive",
    )
    lpu_full_name: Optional[str] = Field(
        None,
        description="Full name of the LPU",
        alias="lpuFullName",
    )
    lpu_short_name: Optional[str] = Field(
        None,
        description="Short name of the LPU",
        alias="lpuShortName",
    )
    lpu_type: Optional[str] = Field(
        None,
        description="Type of the LPU",
        alias="lpuType",
    )
    oid: Optional[str] = Field(None, description="OID")
    part_of: Optional[str] = Field(
        None,
        description="Part of the organization",
        alias="partOf",
    )
    head_organization: Optional[str] = Field(
        None,
        description="ID of the main organization",
        alias="headOrganization",
    )
    organization: Optional[str] = Field(None, description="ID of the organization")
    address: Optional[str] = Field(None, description="Address")
    phone: Optional[str] = Field(None, description="Phone")
    email: Optional[str] = Field(None, description="Email")
    longitude: Optional[str] = Field(None, description="Longitude")
    latitude: Optional[str] = Field(None, description="Latitude")
    covid_vaccination: bool = Field(
        ...,
        description="COVID vaccination",
        alias="covidVaccination",
    )
    in_depth_examination: bool = Field(
        ...,
        description="In-depth examination",
        alias="inDepthExamination",
    )
    subdivision: Optional[str] = Field(None, description="Subdivision")


class AttachmentsResponse(APIResponse):
    """Response with a list of attachments."""

    result: List[Attachment] = Field(..., description="List of attachments")
