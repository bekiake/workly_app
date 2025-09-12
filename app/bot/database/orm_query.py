import math
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
import sys
import os
from datetime import datetime, date, time

# Bot modellarini import qilish
from database.models import User  # Bot uchun User modeli
from database.app_models import Employee, Attendance  # Asosiy app modellari

# Utils import - relative path bilan
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from app.utils.timezone import get_tashkent_time, get_tashkent_date, convert_to_tashkent, TASHKENT_TZ, get_tashkent_time_naive

# CheckTypeEnum va SourceEnum ni manual ravishda import qilish
try:
    from app.models.attendance import CheckTypeEnum
except ImportError:
    # Agar import bo'lmasa, enum ni manually yaratamiz
    import enum
    class CheckTypeEnum(enum.Enum):
        IN = "IN"
        OUT = "OUT"

# SourceEnum ni ham qo'shamiz
try:
    from app.models.attendance import SourceEnum
except ImportError:
    import enum
    class SourceEnum(enum.Enum):
        QR = "QR"
        FACE_ID = "FACE_ID"
        MANUAL = "MANUAL"

async def orm_add_user(
    session: AsyncSession,
    user_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
    phone: str | None = None,
):
    query = select(User).where(User.user_id == user_id)
    result = await session.execute(query)
    if result.first() is None:
        session.add(
            User(user_id=user_id, first_name=first_name, last_name=last_name, phone=phone)
        )
        await session.commit()


async def orm_get_all_employees(session: AsyncSession):
    """Получить всех активных сотрудников"""
    query = select(Employee).where(Employee.is_active == True)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_employee_by_telegram_id(session: AsyncSession, telegram_id: int):
    """Найти сотрудника по telegram_id"""
    query = select(Employee).where(Employee.telegram_id == telegram_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def orm_link_employee_telegram(session: AsyncSession, employee_id: int, telegram_id: int):
    """Привязать telegram_id к сотруднику"""
    # Проверяем, не привязан ли уже этот telegram_id к другому сотруднику
    existing = await orm_get_employee_by_telegram_id(session, telegram_id)
    if existing and existing.id != employee_id:
        return False, "Этот Telegram аккаунт уже привязан к другому сотруднику"
    
    # Обновляем сотрудника
    query = update(Employee).where(Employee.id == employee_id).values(telegram_id=telegram_id)
    await session.execute(query)
    await session.commit()
    return True, "Успешно привязано"


async def orm_create_attendance(
    session: AsyncSession,
    employee_id: int,
    check_type: CheckTypeEnum,
    location_lat: str = None,
    location_lon: str = None
):
    """Создать запись посещаемости через Telegram"""
    attendance = Attendance(
        employee_id=employee_id,
        check_type=check_type,
        source=SourceEnum.TELEGRAM,
        check_time=get_tashkent_time_naive(),  # Naive datetime с Ташkentским временем
        location_lat=location_lat,
        location_lon=location_lon
    )
    session.add(attendance)
    await session.commit()
    await session.refresh(attendance)
    return attendance


async def orm_get_daily_attendance_report(session: AsyncSession, report_date: date = None):
    """Получить ежедневный отчет по посещаемости"""
    if report_date is None:
        report_date = get_tashkent_date()  # Используем Ташкентскую дату
    
    # Получаем всех активных сотрудников
    employees_query = select(Employee).where(Employee.is_active == True)
    employees_result = await session.execute(employees_query)
    all_employees = employees_result.scalars().all()
    
    # Получаем записи посещаемости за день
    start_datetime = datetime.combine(report_date, time.min).replace(tzinfo=TASHKENT_TZ)
    end_datetime = datetime.combine(report_date, time.max).replace(tzinfo=TASHKENT_TZ)
    
    attendance_query = select(Attendance).where(
        and_(
            Attendance.check_time >= start_datetime,
            Attendance.check_time <= end_datetime,
            Attendance.check_type == CheckTypeEnum.IN
        )
    ).options(joinedload(Attendance.employee))
    
    attendance_result = await session.execute(attendance_query)
    attendance_records = attendance_result.scalars().all()
    
    # Определяем время начала работы (например, 9:00)
    work_start_time = time(9, 0)
    
    # Анализируем данные
    attended_employees = []
    late_employees = []
    
    for record in attendance_records:
        employee_info = {
            'employee': record.employee,
            'check_time': record.check_time,
            'source': record.source
        }
        
        attended_employees.append(employee_info)
        
        # Проверяем опоздание
        if record.check_time.time() > work_start_time:
            late_employees.append(employee_info)
    
    # Определяем отсутствующих
    attended_employee_ids = {record.employee_id for record in attendance_records}
    absent_employees = [emp for emp in all_employees if emp.id not in attended_employee_ids]
    
    # Сотрудники, пришедшие вовремя
    on_time_employees = [emp for emp in attended_employees if emp not in late_employees]
    
    return {
        'date': report_date,
        'total_employees': len(all_employees),
        'attended_count': len(attended_employees),
        'absent_count': len(absent_employees),
        'late_count': len(late_employees),
        'on_time_count': len(on_time_employees),
        'attended_employees': attended_employees,
        'absent_employees': absent_employees,
        'late_employees': late_employees,
        'on_time_employees': on_time_employees
    }


async def orm_get_employee_last_status(session: AsyncSession, employee_id: int):
    """Получить последний статус сотрудника (пришел или ушел)"""
    query = select(Attendance).where(
        Attendance.employee_id == employee_id
    ).order_by(Attendance.check_time.desc()).limit(1)
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def orm_check_if_already_checked_today(session: AsyncSession, employee_id: int, check_type: CheckTypeEnum):
    """Проверить, отметился ли сотрудник уже сегодня с данным типом"""
    today = get_tashkent_date()  # Используем Ташкентскую дату
    start_datetime = datetime.combine(today, time.min).replace(tzinfo=TASHKENT_TZ)
    end_datetime = datetime.combine(today, time.max).replace(tzinfo=TASHKENT_TZ)
    
    query = select(func.count(Attendance.id)).where(
        and_(
            Attendance.employee_id == employee_id,
            Attendance.check_time >= start_datetime,
            Attendance.check_time <= end_datetime,
            Attendance.check_type == check_type
        )
    )
    
    result = await session.execute(query)
    count = result.scalar()
    return count > 0


async def orm_get_today_attendance_status(session: AsyncSession, employee_id: int):
    """Получить статус отметок сотрудника на сегодня"""
    checked_in = await orm_check_if_already_checked_today(session, employee_id, CheckTypeEnum.IN)
    checked_out = await orm_check_if_already_checked_today(session, employee_id, CheckTypeEnum.OUT)
    return checked_in, checked_out


async def orm_get_attendance_status_today(session: AsyncSession, employee_id: int):
    """Получить время отметок сотрудника на сегодня (возвращает datetime или None)"""
    today = get_tashkent_date()
    
    # Проверяем отметку прихода
    query_in = select(Attendance.check_time).where(
        and_(
            Attendance.employee_id == employee_id,
            func.date(Attendance.check_time) == today,
            Attendance.check_type == CheckTypeEnum.IN
        )
    ).order_by(Attendance.check_time.desc()).limit(1)
    
    result_in = await session.execute(query_in)
    check_in_time = result_in.scalar_one_or_none()
    
    # Проверяем отметку ухода
    query_out = select(Attendance.check_time).where(
        and_(
            Attendance.employee_id == employee_id,
            func.date(Attendance.check_time) == today,
            Attendance.check_type == CheckTypeEnum.OUT
        )
    ).order_by(Attendance.check_time.desc()).limit(1)
    
    result_out = await session.execute(query_out)
    check_out_time = result_out.scalar_one_or_none()
    
    return check_in_time, check_out_time





