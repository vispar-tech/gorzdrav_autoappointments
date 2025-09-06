from functools import partial
from typing import TYPE_CHECKING

from bot.utils.files import PRIVACY_POLICY_PATH, USER_AGREEMENT_PATH, read_txt_file

if TYPE_CHECKING:
    from bot.api.models import Attachment, PatientAppointmentItem
    from bot.db.models.patients import Patient

WELCOME_TEXT = """
🎉 <b>Добро пожаловать в МедБот СПб!</b> 🏥

Привет, {first_name}! 👋

Я ваш персональный помощник для автоматической записи к врачам в системе ГорЗдрав! 📅

<b>✨ Что я умею:</b>
• 🔍 Автоматически искать свободные записи к нужным специалистам
• ⏰ Записывать вас на удобное время (в платной версии)
• 📋 Показывать все ваши текущие записи
• 👥 Добавлять несколько пациентов для записи
• 🏥 Работать с любой поликлиникой в системе ГорЗдрав

<b>💰 Тарифы:</b>
• <b>Бесплатно:</b> {max_unsubscribed_patients} пациент, {max_unsubscribed_schedules} разовые записи без выбора времени 🆓
• <b>Платно:</b> 500₽/месяц за до {max_subscribed_patients} пациентов, до {max_subscribed_schedules} активных расписаний, безлимитное исполнение расписаний 💳

<b>🚀 Как начать работу:</b>
1️⃣ Добавьте данные пациентов для записи
2️⃣ Создайте расписание для записи
3️⃣ Бот автоматически ищет свободные записи и записывает вас!

<b>📱 Основные команды:</b>
/patients - Пациенты пользователя
/schedules - Все расписания всех пациентов
/appointments - Все записи всех пациентов
/help - Помощь и поддержка

<b>💡 Важно:</b> Для начала работы добавьте данные пациентов

<b>⚠️ Согласие:</b> Продолжение использования бота означает автоматическое согласие с пользовательским соглашением и политикой конфиденциальности.

Удачи! 🌟
"""  # noqa: E501

HELP_TEXT = """
🆘 <b>Частые вопросы и помощь</b>

<b>💰 Тарифная система:</b>
• <b>Бесплатно:</b> {max_unsubscribed_patients} пациент, {max_unsubscribed_schedules} единоразовые записи без выбора времени 🆓
• <b>Платно:</b> 500₽/месяц за до {max_subscribed_patients} пациентов, до {max_subscribed_schedules} активных расписаний, безлимитное исполнение расписаний 💳

<b>🔧 Как работает бот:</b>
1️⃣ <b>Добавление пациентов:</b> Добавьте данные пациентов для записи
2️⃣ <b>Создание расписания:</b> Создайте расписание для записи
3️⃣ <b>Автопоиск:</b> Бот автоматически ищет свободные записи и записывает вас!

<b>❓ Часто задаваемые вопросы:</b>
• <b>Сколько бесплатных записей?</b> {max_unsubscribed_patients} пациент, {max_unsubscribed_schedules} единоразовые записи, затем только платно 💰
• <b>Сколько пациентов можно добавить?</b> В бесплатной версии - {max_unsubscribed_patients}, в платной - до {max_subscribed_patients} 👥
• <b>Сколько расписаний в платной версии?</b> До {max_subscribed_schedules} активных расписаний, безлимитное исполнение расписаний 📅
• <b>Безопасно ли это?</b> Да, все данные надежно защищены 🔒
• <b>Какие поликлиники доступны?</b> Все в системе ГорЗдрав 🏥
• <b>Как часто проверяются записи?</b> Каждые несколько минут ⏰
• <b>Можно ли выбрать удобное время?</b> Только в платной версии ⏰

<b>📋 Основные команды:</b>
/start - Главное меню
/patients - Пациенты пользователя
/schedules - Все расписания всех пациентов
/appointments - Все записи всех пациентов
/help - Помощь и поддержка

<b>🆘 Техническая поддержка:</b> @vispar_work
"""  # noqa: E501

FULL_HELP_TEXT = """
🆘 <b>Полная справка по боту ГорЗдрав</b> 🏥

<b>💰 Тарифная система:</b>
• <b>Бесплатно:</b> {max_unsubscribed_patients} пациент, {max_unsubscribed_schedules} единоразовые записи без выбора времени 🆓
• <b>Платно:</b> 500₽/месяц за до {max_subscribed_patients} пациентов, до {max_subscribed_schedules} активных расписаний, безлимитное исполнение расписаний 💳

<b>📋 Основные команды:</b>
/start - Главное меню и приветствие
/patients - Пациенты пользователя
/schedules - Все расписания всех пациентов
/appointments - Все записи всех пациентов
/help - Эта справка

<b>🔧 Как работает бот:</b>
1️⃣ <b>Добавление пациентов:</b> Добавьте данные пациентов для записи
2️⃣ <b>Выбор поликлиники:</b> Выберите предпочитаемую поликлинику
3️⃣ <b>Автопоиск:</b> Бот автоматически ищет свободные записи и записывает вас!

<b>❓ Часто задаваемые вопросы:</b>
• <b>Сколько бесплатных записей?</b> {max_unsubscribed_patients} пациент, {max_unsubscribed_schedules} единоразовые записи, затем только платно 💰
• <b>Сколько пациентов можно добавить?</b> В бесплатной версии - {max_unsubscribed_patients}, в платной - до {max_subscribed_patients} 👥
• <b>Сколько расписаний в платной версии?</b> До {max_subscribed_schedules} активных расписаний, безлимитное исполнение расписаний 📅
• <b>Безопасно ли это?</b> Да, все данные надежно защищены 🔒
• <b>Какие поликлиники доступны?</b> Все в системе ГорЗдрав 🏥
• <b>Как часто проверяются записи?</b> Каждые несколько минут ⏰
• <b>Можно ли выбрать удобное время?</b> Только в платной версии ⏰

<b>🚀 Быстрый старт:</b>
1. Добавьте данные пациентов для записи
2. Создайте расписание для записи
3. Бот автоматически ищет свободные записи и записывает вас!

<b>🆘 Техническая поддержка:</b> @vispar_work или используйте /start для возврата в главное меню
"""  # noqa: E501


def get_appointments_text(
    appointments_data: "list[tuple[Patient, Attachment, PatientAppointmentItem]]",
) -> str:
    """Format appointments data into a readable text."""
    if not appointments_data:
        return "<b>📋 Записи</b>\n\n❌ У вас нет активных записей к врачам."

    text = "<b>📋 Ваши записи к врачам</b>\n\n"

    for i, (patient, attachment, appointment) in enumerate(appointments_data, 1):
        # Форматируем дату и время
        visit_start = appointment.visit_start.strftime("%d.%m.%Y %H:%M")

        # Форматируем имя пациента
        patient_name = f"{patient.last_name} {patient.first_name}"
        if patient.middle_name:
            patient_name += f" {patient.middle_name}"

        # Форматируем информацию о враче
        doctor_info = ""
        if appointment.doctor_rending_consultation:
            doctor = appointment.doctor_rending_consultation
            doctor_name = doctor.name or "Не указано"
            doctor_info = f"👨‍⚕️ <b>Врач:</b> {doctor_name}\n"
            if doctor.aria_number:
                doctor_info += f"🏥 <b>Кабинет:</b> {doctor.aria_number}\n"

        # Форматируем специализацию
        specialty_info = ""
        if appointment.speciality_rending_consultation:
            specialty = appointment.speciality_rending_consultation
            specialty_name = specialty.name or "Не указано"
            specialty_info = f"🩺 <b>Специализация:</b> {specialty_name}\n"

        text += f"{i}. <b>{patient_name}</b>\n"
        text += f"📅 <b>Дата:</b> {visit_start}\n"
        lpu_name = attachment.lpu_short_name or attachment.lpu_full_name
        text += f"🏥 <b>Поликлиника:</b> {lpu_name}\n"
        if doctor_info:
            text += doctor_info
        if specialty_info:
            text += specialty_info
        text += f"📞 <b>Телефон:</b> {attachment.phone or 'Не указан'}\n"

        if appointment.lpu_address:
            text += f"📍 <b>Адрес приема:</b> {appointment.lpu_address}\n"

        text += "\n\n"

    return text


get_user_aggrement_text = partial(read_txt_file, USER_AGREEMENT_PATH)
get_privacy_policy_text = partial(read_txt_file, PRIVACY_POLICY_PATH)

SUBSCRIPTION_TEXT = """
⏰ Срок действия: {days} дней

✨ Что дает подписка:
• До 10 пациентов для записи
• До 10 активных расписаний
• Безлимитное исполнение расписаний
• Приоритетная исполнение расписаний
• Приоритетная поддержка


Для оплаты нажмите кнопку ниже ⬇️
"""
