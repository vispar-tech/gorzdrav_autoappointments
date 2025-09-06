from aiogram.fsm.state import State, StatesGroup


class PatientFormStates(StatesGroup):
    """States for patient form."""

    waiting_for_last_name = State()
    waiting_for_first_name = State()
    waiting_for_middle_name = State()
    waiting_for_birth_date = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_oms = State()
    waiting_for_district = State()
    waiting_for_lpu = State()
    waiting_for_confirmation = State()


class ScheduleFormStates(StatesGroup):
    """States for schedule form."""

    waiting_for_patient = State()
    waiting_for_lpu = State()
    waiting_for_specialist = State()
    waiting_for_doctors = State()
    waiting_for_time = State()
    waiting_for_confirmation = State()
