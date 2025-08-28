from enum import Enum
from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from datetime import datetime as _dt
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Dict, List

from bot.database.repositories import PatientRepository, ScheduleRepository
from bot.database.models import Schedule
from bot.api.client import GorzdravAPIClient

router = Router(name="schedule")


class ScheduleStates(StatesGroup):
    choosing_specialist = State()
    choosing_doctors = State()
    choosing_time = State()


class ScheduleActions(Enum):
    CREATE = "sched:create"
    LIST = "sched:list"
    DELETE = "sched:delete"
    CANCEL = "sched:cancel"


@router.message(Command("schedule"))
async def schedule_menu(message: Message):
    if not message.from_user:
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Создать",
                    callback_data=ScheduleActions.CREATE.value,
                ),
                InlineKeyboardButton(
                    text="📋 Мои расписания", callback_data=ScheduleActions.LIST.value
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Удалить", callback_data=ScheduleActions.DELETE.value
                ),
            ],
        ]
    )
    await message.answer("Выберите действие:", reply_markup=kb)


@router.callback_query(F.data == ScheduleActions.CANCEL.value)
async def cancel_schedule_action(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not call.message:
        return
    await state.clear()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Создать",
                    callback_data=ScheduleActions.CREATE.value,
                ),
                InlineKeyboardButton(
                    text="📋 Мои расписания", callback_data=ScheduleActions.LIST.value
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Удалить", callback_data=ScheduleActions.DELETE.value
                ),
            ],
        ]
    )

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Выберите действие:",
    )
    await bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=kb,
    )
    await call.answer("Отменено")


@router.callback_query(F.data == ScheduleActions.LIST.value)
async def list_schedules(call: CallbackQuery, bot: Bot):
    if not call.from_user or not call.message:
        return
    patient = await PatientRepository().get_patient_by_user(call.from_user.id)
    if not patient:
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Сначала пройдите регистрацию: /register",
        )
        await bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
        return
    schedules = await ScheduleRepository().get_patient_schedules(patient.id)
    if not schedules:
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Расписаний пока нет.",
        )
        await bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
        return

    # Подгружаем справочники из API для удобного отображения
    lines: List[str] = []
    async with GorzdravAPIClient() as client:
        specs = (
            (await client.get_specialists(int(patient.prefer_lpu_id))).result
            if patient.prefer_lpu_id
            else []
        )
        spec_name_by_id: Dict[str, str] = {sp.id: sp.name for sp in specs}

        for s in schedules:
            time_range = ""
            if s.preferred_time_start:
                time_range += s.preferred_time_start.strftime("%H:%M")
            if s.preferred_time_end:
                time_range += f"–{s.preferred_time_end.strftime('%H:%M')}"

            spec_name = spec_name_by_id.get(s.specialist_id, s.specialist_id)
            doctor_names: List[str] = []
            try:
                if patient.prefer_lpu_id:
                    docs = (
                        await client.get_doctors(
                            int(patient.prefer_lpu_id), s.specialist_id
                        )
                    ).result
                    id_to_name = {d.id: d.name for d in docs}
                    if s.preferred_doctors:
                        doctor_names = [
                            id_to_name.get(did, did) for did in s.preferred_doctors
                        ]
                    else:
                        doctor_names = []
            except Exception:
                doctor_names = s.preferred_doctors or []

            lines.append(
                "\n".join(
                    [
                        f"#{s.id}",
                        f"• Специализация: {spec_name}",
                        f"• Врачи: {', '.join(doctor_names) if doctor_names else 'любой'}",
                        f"• Время: {time_range or 'весь день'}",
                    ]
                )
            )

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Ваши расписания:\n\n" + "\n\n".join(lines),
    )
    await bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=None,
    )


@router.callback_query(F.data == ScheduleActions.CREATE.value)
async def create_schedule_start(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not call.from_user or not call.message:
        return
    patient = await PatientRepository().get_patient_by_user(call.from_user.id)
    if not patient or not patient.prefer_lpu_id:
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Сначала завершите регистрацию и закрепите ЛПУ: /register",
        )
        await bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
        return

    async with GorzdravAPIClient() as client:
        specs = (await client.get_specialists(int(patient.prefer_lpu_id))).result
    spec_map: Dict[str, str] = {s.id: s.name for s in specs}
    inline_rows: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=name, callback_data=f"spec:{sid}")]
        for sid, name in spec_map.items()
    ]
    # Добавляем кнопку отмены
    inline_rows.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена", callback_data=ScheduleActions.CANCEL.value
            )
        ]
    )
    kb_inline = InlineKeyboardMarkup(inline_keyboard=inline_rows)
    await state.set_state(ScheduleStates.choosing_specialist)
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Выберите направление (специализацию):",
    )
    await bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=kb_inline,
    )
    await state.update_data(spec_map=spec_map, lpu_id=int(patient.prefer_lpu_id))


@router.callback_query(ScheduleStates.choosing_specialist, F.data.startswith("spec:"))
async def choose_specialist_cb(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not call.from_user or not call.message:
        return
    data = await state.get_data()
    spec_map: Dict[str, str] = data.get("spec_map", {})
    specialist_id = (call.data or "").split(":", 1)[1]
    if specialist_id not in spec_map:
        await call.answer("Неизвестная специализация")
        return
    lpu_id_val = data.get("lpu_id")
    if lpu_id_val is None:
        patient = await PatientRepository().get_patient_by_user(call.from_user.id)
        if not patient or not patient.prefer_lpu_id:
            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="Сначала завершите регистрацию и закрепите ЛПУ: /register",
            )
            await bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None,
            )
            return
        lpu_id = int(patient.prefer_lpu_id)
    else:
        lpu_id = int(lpu_id_val)

    async with GorzdravAPIClient() as client:
        doctors = (await client.get_doctors(lpu_id, specialist_id)).result
    doc_map: Dict[str, str] = {d.id: d.name for d in doctors}

    selected: List[str] = []
    rows: List[List[InlineKeyboardButton]] = []
    for did, name in doc_map.items():
        label = ("✅ " if did in selected else "") + name
        rows.append([InlineKeyboardButton(text=label, callback_data=f"doc:{did}")])
    rows.append([InlineKeyboardButton(text="Готово", callback_data="doc_done")])
    # Добавляем кнопку назад
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=ScheduleActions.CREATE.value
            )
        ]
    )
    kb_inline = InlineKeyboardMarkup(inline_keyboard=rows)

    await state.update_data(
        specialist_id=specialist_id, doctors_map=doc_map, selected_doctors=selected
    )
    await state.set_state(ScheduleStates.choosing_doctors)
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Выберите одного или нескольких врачей кнопками ниже. Когда закончите — нажмите 'Готово'",
    )
    await bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=kb_inline,
    )


@router.callback_query(
    ScheduleStates.choosing_doctors, F.data == ScheduleActions.CREATE.value
)
async def back_to_specialists(call: CallbackQuery, state: FSMContext, bot: Bot):
    """Возврат к выбору специализации"""
    if not call.message:
        return

    data = await state.get_data()
    spec_map: Dict[str, str] = data.get("spec_map", {})

    inline_rows: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=name, callback_data=f"spec:{sid}")]
        for sid, name in spec_map.items()
    ]
    # Добавляем кнопку отмены
    inline_rows.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена", callback_data=ScheduleActions.CANCEL.value
            )
        ]
    )
    kb_inline = InlineKeyboardMarkup(inline_keyboard=inline_rows)

    await state.set_state(ScheduleStates.choosing_specialist)
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Выберите направление (специализацию):",
    )
    await bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=kb_inline,
    )


@router.callback_query(ScheduleStates.choosing_doctors, F.data == "doc_done")
async def done_doctors_cb(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(ScheduleStates.choosing_time)

    # Создаем клавиатуру с кнопкой назад
    kb_back = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_doctors")]
        ]
    )

    if call.message:
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Укажите интервал времени в формате HH:MM-HH:MM (например, 09:00-14:00). Если любое время подходит — отправьте 'Весь день'",
        )
        await bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=kb_back,
        )
    await call.answer("Врачи выбраны")


@router.callback_query(ScheduleStates.choosing_time, F.data == "back_to_doctors")
async def back_to_doctors(call: CallbackQuery, state: FSMContext, bot: Bot):
    """Возврат к выбору врачей"""
    if not call.message:
        return

    data = await state.get_data()
    doc_map: Dict[str, str] = data.get("doctors_map", {})
    selected: List[str] = data.get("selected_doctors", []) or []

    rows: List[List[InlineKeyboardButton]] = []
    for did, name in doc_map.items():
        label = ("✅ " if did in selected else "") + name
        rows.append([InlineKeyboardButton(text=label, callback_data=f"doc:{did}")])
    rows.append([InlineKeyboardButton(text="Готово", callback_data="doc_done")])
    # Добавляем кнопку назад
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=ScheduleActions.CREATE.value
            )
        ]
    )
    kb_inline = InlineKeyboardMarkup(inline_keyboard=rows)

    await state.set_state(ScheduleStates.choosing_doctors)
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Выберите одного или нескольких врачей кнопками ниже. Когда закончите — нажмите 'Готово'",
    )
    await bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=kb_inline,
    )


@router.callback_query(ScheduleStates.choosing_doctors, F.data.startswith("doc:"))
async def collect_doctors_cb(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    doc_map: Dict[str, str] = data.get("doctors_map", {})
    doc_id = (call.data or "").split(":", 1)[1]
    if doc_id not in doc_map:
        await call.answer("Неизвестный врач")
        return
    selected: List[str] = data.get("selected_doctors", []) or []
    if doc_id in selected:
        selected.remove(doc_id)
        await call.answer("Убран")
    else:
        selected.append(doc_id)
        await call.answer("Добавлен")
    await state.update_data(selected_doctors=selected)

    # Перестроим клавиатуру с галочками
    rows: List[List[InlineKeyboardButton]] = []
    for did, name in doc_map.items():
        label = ("✅ " if did in selected else "") + name
        rows.append([InlineKeyboardButton(text=label, callback_data=f"doc:{did}")])
    rows.append([InlineKeyboardButton(text="Готово", callback_data="doc_done")])
    # Добавляем кнопку назад
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=ScheduleActions.CREATE.value
            )
        ]
    )
    kb_inline = InlineKeyboardMarkup(inline_keyboard=rows)
    if call.message:
        await bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=kb_inline,
        )


@router.message(ScheduleStates.choosing_time)
async def choose_time(message: Message, state: FSMContext):
    if not message.from_user:
        return
    text = (message.text or "").strip()
    start_str = end_str = None
    if text.lower() != "весь день":
        if "-" not in text:
            await message.answer("Формат времени: HH:MM-HH:MM или 'Весь день'")
            return
        start_str, end_str = [p.strip() for p in text.split("-", 1)]

    data = await state.get_data()
    patient = await PatientRepository().get_patient_by_user(message.from_user.id)
    if not patient:
        await message.answer("Сначала /register")
        await state.clear()
        return

    sched = Schedule(
        patient_id=patient.id,
        specialist_id=str(data.get("specialist_id")),
        preferred_time_start=None,
        preferred_time_end=None,
        preferred_doctors=data.get("selected_doctors", []),
        notes=None,
    )
    # Парсим время, если указано

    try:
        if start_str and end_str:
            sched.preferred_time_start = _dt.strptime(start_str, "%H:%M").time()
            sched.preferred_time_end = _dt.strptime(end_str, "%H:%M").time()
    except ValueError:
        await message.answer("Неверный формат времени. Используйте HH:MM-HH:MM")
        return

    created = await ScheduleRepository().create_schedule(sched)

    # Красивое резюме с названиями
    spec_map: Dict[str, str] = data.get("spec_map", {})
    spec_name = spec_map.get(sched.specialist_id, sched.specialist_id)
    doctors_map: Dict[str, str] = data.get("doctors_map", {})
    selected: List[str] = data.get("selected_doctors", []) or []
    doctor_names = [doctors_map.get(did, did) for did in selected]

    summary = "\n".join(
        [
            f"✅ Расписание #{created.id} создано",
            f"• Специализация: {spec_name}",
            f"• Врачи: {', '.join(doctor_names) if doctor_names else 'любой'}",
            f"• Время: {(start_str or '00:00')}-{(end_str or '23:59')}",
        ]
    )

    await state.clear()
    await message.answer(summary, reply_markup=ReplyKeyboardRemove())


@router.callback_query(F.data == ScheduleActions.DELETE.value)
async def delete_schedule_prompt(call: CallbackQuery, state: FSMContext):
    if not call.from_user or not call.message:
        return
    patient = await PatientRepository().get_patient_by_user(call.from_user.id)
    if not patient:
        await call.message.answer("Сначала /register")
        return
    schedules = await ScheduleRepository().get_patient_schedules(patient.id)
    if not schedules:
        await call.message.answer("Нечего удалять")
        return

    kb_buttons = [[KeyboardButton(text=f"#{s.id}")] for s in schedules]
    # Добавляем кнопку отмены
    kb_buttons.append([KeyboardButton(text="❌ Отмена")])

    kb = ReplyKeyboardMarkup(
        keyboard=kb_buttons,
        resize_keyboard=True,
    )
    await state.update_data(delete_mode=True)
    await call.message.answer("Выберите расписание для удаления:", reply_markup=kb)


@router.message(F.text == "❌ Отмена")
async def cancel_delete_mode(message: Message, state: FSMContext):
    """Отмена режима удаления"""
    data = await state.get_data()
    if data.get("delete_mode"):
        await state.clear()
        await message.answer("Отменено.", reply_markup=ReplyKeyboardRemove())


@router.message(F.text.regexp(r"^#\d+$"))
async def schedule_id_actions(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("delete_mode"):
        schedule_id = int((message.text or "").lstrip("#"))
        await ScheduleRepository().delete_schedule(schedule_id)
        await state.clear()
        await message.answer("Удалено.", reply_markup=ReplyKeyboardRemove())
        return
