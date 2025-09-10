from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, func, desc, text
from datetime import datetime, date, time, timedelta
from typing import Optional, List
from app.models import attendance as attendance_model
from app.models import employee as employee_model
from app.schemas import attendance as attendance_schema
from app.crud.employee import get_employee_by_uuid

# Ish vaqti sozlamalari
WORK_START_TIME = time(9, 30)  # 9:30
WORK_END_TIME = time(18, 0)    # 18:00

def is_working_hours(check_time: datetime, check_type: str) -> tuple[bool, str]:
    """Ish vaqtida ekanligini tekshirish"""
    current_time = check_time.time()
    
    if check_type == "IN":
        # Kelish vaqti 7:00 dan 11:00 gacha bo'lishi mumkin
        if time(7, 0) <= current_time <= time(11, 0):
            return True, ""
        else:
            return False, "Kelish vaqti 7:00 dan 11:00 gacha bo'lishi kerak"
    
    elif check_type == "OUT":
        # Ketish vaqti 16:00 dan 20:00 gacha bo'lishi mumkin
        if time(16, 0) <= current_time <= time(20, 0):
            return True, ""
        else:
            return False, "Ketish vaqti 16:00 dan 20:00 gacha bo'lishi kerak"
    
    return True, ""

def calculate_attendance_status(check_time: datetime, check_type: str) -> tuple[bool, bool]:
    """Kechikish va erta ketishni hisoblash"""
    current_time = check_time.time()
    is_late = False
    is_early_departure = False
    
    if check_type == "IN":
        # 9:30 dan keyin kelgan bo'lsa kech
        is_late = current_time > WORK_START_TIME
    
    elif check_type == "OUT":
        # 18:00 dan oldin ketgan bo'lsa erta
        is_early_departure = current_time < WORK_END_TIME
    
    return is_late, is_early_departure

def calculate_time_difference_minutes(actual_time: time, expected_time: time) -> int:
    """Vaqtlar orasidagi farqni daqiqalarda hisoblash"""
    actual_minutes = actual_time.hour * 60 + actual_time.minute
    expected_minutes = expected_time.hour * 60 + expected_time.minute
    return actual_minutes - expected_minutes

async def create_attendance_by_qr(db: AsyncSession, qr_request: attendance_schema.QRScanRequest):
    """QR kod orqali davomat yaratish"""
    # Employee ni UUID bo'yicha topish
    employee = await get_employee_by_uuid(db, qr_request.qr_code)
    if not employee:
        return {"error": "Xodim topilmadi"}

    # Ish vaqtini tekshirish
    check_time = datetime.now()
    is_valid_time, time_error = is_working_hours(check_time, qr_request.check_type.value)
    
    if not is_valid_time:
        return {"error": time_error}

    # Bugun allaqachon shu turdagi belgi qo'yilgan yoki yo'qligini tekshirish
    already_checked = await check_if_already_checked_today(
        db, employee.id, qr_request.check_type.value
    )
    
    if already_checked:
        action = "kelgan" if qr_request.check_type.value == "IN" else "ketgan"
        return {"error": f"Siz bugun allaqachon {action} deb belgilangansiz"}

    # Kechikish va erta ketishni hisoblash
    is_late, is_early_departure = calculate_attendance_status(check_time, qr_request.check_type.value)
    
    db_attendance = attendance_model.Attendance(
        employee_id=employee.id,
        check_type=qr_request.check_type,
        is_late=is_late,
        is_early_departure=is_early_departure
    )
    db.add(db_attendance)
    await db.commit()
    await db.refresh(db_attendance)
    
    # Muvaffaqiyatli natija
    action = "keldi" if qr_request.check_type.value == "IN" else "ketdi"
    status_msg = ""
    if is_late:
        diff_minutes = calculate_time_difference_minutes(check_time.time(), WORK_START_TIME)
        status_msg = f" ({diff_minutes} daqiqa kech)"
    elif is_early_departure:
        diff_minutes = abs(calculate_time_difference_minutes(check_time.time(), WORK_END_TIME))
        status_msg = f" ({diff_minutes} daqiqa erta)"
        
    return {
        "success": True,
        "message": f"{employee.full_name} {action}{status_msg}",
        "attendance": db_attendance
    }

async def create_attendance(db: AsyncSession, attendance: attendance_schema.AttendanceCreate):
    """Oddiy davomat yaratish"""
    employee = await get_employee_by_uuid(db, attendance.employee_uuid)
    if not employee:
        return None
    
    # Ish vaqtini tekshirish
    check_time = datetime.now()
    is_valid_time, time_error = is_working_hours(check_time, attendance.check_type.value)
    
    if not is_valid_time:
        return {"error": time_error}

    # Kechikish va erta ketishni hisoblash
    is_late, is_early_departure = calculate_attendance_status(check_time, attendance.check_type.value)
    
    db_attendance = attendance_model.Attendance(
        employee_id=employee.id,
        check_type=attendance.check_type,
        is_late=is_late,
        is_early_departure=is_early_departure
    )
    db.add(db_attendance)
    await db.commit()
    await db.refresh(db_attendance)
    return db_attendance

async def get_attendance_by_employee(db: AsyncSession, employee_id: int, 
                                   start_date: Optional[date] = None, 
                                   end_date: Optional[date] = None):
    query = select(attendance_model.Attendance).where(
        attendance_model.Attendance.employee_id == employee_id
    )
    
    if start_date:
        query = query.where(func.date(attendance_model.Attendance.check_time) >= start_date)
    if end_date:
        query = query.where(func.date(attendance_model.Attendance.check_time) <= end_date)
    
    query = query.order_by(desc(attendance_model.Attendance.check_time))
    result = await db.execute(query)
    return result.scalars().all()

async def get_daily_attendance(db: AsyncSession, target_date: date):
    """Kunlik davomat ma'lumotlari"""
    query = select(attendance_model.Attendance).options(
        selectinload(attendance_model.Attendance.employee)
    ).where(
        func.date(attendance_model.Attendance.check_time) == target_date
    ).order_by(attendance_model.Attendance.check_time)
    
    result = await db.execute(query)
    return result.scalars().all()

async def get_monthly_attendance_report(db: AsyncSession, month: int, year: int):
    """Oylik hisobot uchun ma'lumotlar - yangilangan versiya"""
    start_date = date(year, month, 1)
    
    # Oyning oxirgi kunini aniqlash
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # Ish kunlarini hisoblash (6 kun/hafta - faqat yakshanba dam)
    working_days = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() != 6:  # Faqat yakshanba (Sunday=6) dam, qolgan kunlar ish
            working_days += 1
        current_date += timedelta(days=1)
    
    # Har bir xodim uchun batafsil statistika
    query = select(employee_model.Employee).where(employee_model.Employee.is_active == True)
    result = await db.execute(query)
    employees = result.scalars().all()
    
    reports = []
    for employee in employees:
        stats = await get_employee_monthly_statistics(db, employee.id, month, year)
        
        reports.append({
            "employee_id": employee.id,
            "employee_name": employee.full_name,
            "position": employee.position.value,
            "working_days": working_days,
            "present_days": stats["present_days"],
            "absent_days": stats["absent_days"],
            "late_days": stats["late_days"],
            "early_departure_days": stats["early_departure_days"],
            "total_worked_hours": stats["total_worked_hours"],
            "expected_hours": stats["expected_hours"],
            "attendance_rate": stats["attendance_rate"],
            "punctuality_rate": stats["punctuality_rate"],
            "salary_info": stats.get("salary_info", {})
        })
    
    return reports

async def get_employee_last_status(db: AsyncSession, employee_id: int):
    """Xodimning oxirgi holatini olish (keldi yoki ketdi)"""
    result = await db.execute(
        select(attendance_model.Attendance)
        .where(attendance_model.Attendance.employee_id == employee_id)
        .order_by(desc(attendance_model.Attendance.check_time))
        .limit(1)
    )
    return result.scalar_one_or_none()

async def check_if_already_checked_today(db: AsyncSession, employee_id: int, check_type: str):
    """Bugun allaqachon keldi/ketdi deb belgilangan yoki yo'qligini tekshirish"""
    today = date.today()
    
    # API dan "in"/"out" keladi, lekin DB da "IN"/"OUT" saqlanadi
    db_check_type = check_type.upper()
    
    # Faqat COUNT qilish, obyekt qaytarmaslik
    result = await db.execute(
        select(func.count(attendance_model.Attendance.id))
        .where(
            and_(
                attendance_model.Attendance.employee_id == employee_id,
                func.date(attendance_model.Attendance.check_time) == today,
                attendance_model.Attendance.check_type == db_check_type
            )
        )
    )
    count = result.scalar()
    return count > 0

async def calculate_daily_work_hours(db: AsyncSession, employee_id: int, target_date: date) -> dict:
    """Kunlik ish soatlarini hisoblash - yangilangan versiya"""
    
    # Kunda kelish va ketish vaqtlarini olish
    result = await db.execute(
        select(attendance_model.Attendance)
        .where(
            and_(
                attendance_model.Attendance.employee_id == employee_id,
                func.date(attendance_model.Attendance.check_time) == target_date
            )
        )
        .order_by(attendance_model.Attendance.check_time)
    )
    
    attendances = result.scalars().all()
    
    if not attendances:
        return {
            "date": target_date,
            "worked_hours": 0,
            "status": "absent",
            "check_in": None,
            "check_out": None,
            "is_late": False,
            "is_early_departure": False,
            "late_minutes": 0,
            "early_departure_minutes": 0
        }
    
    check_in = None
    check_out = None
    is_late = False
    is_early_departure = False
    late_minutes = 0
    early_departure_minutes = 0
    
    for attendance in attendances:
        if attendance.check_type.value == "IN":
            check_in = attendance.check_time
            is_late = attendance.is_late
            if is_late:
                late_minutes = calculate_time_difference_minutes(
                    attendance.check_time.time(), WORK_START_TIME
                )
        elif attendance.check_type.value == "OUT":
            check_out = attendance.check_time
            is_early_departure = attendance.is_early_departure
            if is_early_departure:
                early_departure_minutes = abs(calculate_time_difference_minutes(
                    attendance.check_time.time(), WORK_END_TIME
                ))
    
    # Ish soatlarini hisoblash
    worked_hours = 0
    status = "incomplete"
    
    if check_in and check_out:
        # To'liq ish kuni
        worked_time = check_out - check_in
        worked_hours = worked_time.total_seconds() / 3600
        
        status = "complete"
        
        # Normal ish vaqti 8.5 soat (9:30-18:00)
        if worked_hours >= 8.5:
            status = "full_day"
        elif worked_hours >= 4:
            status = "half_day"
        else:
            status = "short_day"
    
    elif check_in and not check_out:
        status = "not_checked_out"
    
    return {
        "date": target_date,
        "worked_hours": round(worked_hours, 2),
        "status": status,
        "check_in": check_in,
        "check_out": check_out,
        "is_late": is_late,
        "is_early_departure": is_early_departure,
        "late_minutes": late_minutes,
        "early_departure_minutes": early_departure_minutes
    }

async def get_employee_monthly_statistics(db: AsyncSession, employee_id: int, month: int, year: int) -> dict:
    """Xodimning oylik statistikasi - yangilangan versiya"""
    
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # Xodim ma'lumotlarini olish
    result = await db.execute(
        select(employee_model.Employee).where(employee_model.Employee.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    
    if not employee:
        return {"error": "Xodim topilmadi"}
    
    # Har bir kun uchun statistika
    daily_stats = []
    total_worked_hours = 0
    present_days = 0
    late_days = 0
    early_departure_days = 0
    working_days = 0
    total_late_minutes = 0
    total_early_departure_minutes = 0
    
    current_date = start_date
    while current_date <= end_date:
        # Faqat ish kunlarini hisobga olish (6 kun/hafta - faqat yakshanba dam)
        if current_date.weekday() != 6:  # Faqat yakshanba (Sunday=6) dam
            working_days += 1
            day_stats = await calculate_daily_work_hours(db, employee_id, current_date)
            daily_stats.append(day_stats)
            
            # Faqat check_in mavjud bo'lgan kunlarni hisoblash
            if day_stats["check_in"] is not None:
                present_days += 1
                total_worked_hours += day_stats["worked_hours"]
                
                if day_stats["is_late"]:
                    late_days += 1
                    total_late_minutes += day_stats["late_minutes"]
                
                if day_stats["is_early_departure"]:
                    early_departure_days += 1
                    total_early_departure_minutes += day_stats["early_departure_minutes"]
        
        current_date += timedelta(days=1)
    
    # Foizlarni hisoblash
    attendance_rate = (present_days / working_days * 100) if working_days > 0 else 0
    punctuality_rate = ((present_days - late_days) / present_days * 100) if present_days > 0 else 0
    
    # Maosh hisoblash
    base_salary = float(employee.base_salary) if employee.base_salary else 0
    expected_hours = working_days * 8.5  # 8.5 soat kuniga
    
    # Udjelishlar hisoblash
    salary_calculations = calculate_salary_deductions(
        base_salary=base_salary,
        worked_hours=total_worked_hours,
        expected_hours=expected_hours,
        late_days=late_days,
        early_departure_days=early_departure_days,
        absent_days=working_days - present_days
    )
    
    return {
        "employee_id": employee_id,
        "employee_name": employee.full_name,
        "position": employee.position.value if employee.position else "Unknown",
        "month": month,
        "year": year,
        "working_days": working_days,
        "present_days": present_days,
        "absent_days": working_days - present_days,
        "late_days": late_days,
        "early_departure_days": early_departure_days,
        "total_worked_hours": round(total_worked_hours, 2),
        "expected_hours": expected_hours,
        "total_late_minutes": total_late_minutes,
        "total_early_departure_minutes": total_early_departure_minutes,
        "attendance_rate": round(attendance_rate, 2),
        "punctuality_rate": round(punctuality_rate, 2),
        "salary_info": salary_calculations,
        "daily_stats": daily_stats
    }

def calculate_salary_deductions(base_salary: float, worked_hours: float, expected_hours: float, 
                              late_days: int, early_departure_days: int, absent_days: int) -> dict:
    """Maosh va uderzhaniyalarni hisoblash"""
    
    if base_salary <= 0:
        return {
            "base_salary": 0,
            "final_salary": 0,
            "total_deductions": 0,
            "deduction_breakdown": {}
        }
    
    # Kunlik maosh (6 kun/hafta - 26 kun/oy)
    daily_salary = base_salary / 26  # Oyda 26 ish kuni (6 kun/hafta)
    hourly_salary = daily_salary / 8.5  # Kuniga 8.5 soat
    
    # Uderjhanilar
    deductions = {}
    
    # Yo'qolgan kunlar uchun to'liq uderjhanie
    if absent_days > 0:
        absent_deduction = absent_days * daily_salary
        deductions["absent_days"] = {
            "days": absent_days,
            "amount": round(absent_deduction, 2)
        }
    
    # Kechikkanlar uchun uderjhanie (har kechikish uchun kichik jarim)
    if late_days > 0:
        late_penalty = late_days * (daily_salary * 0.02)  # Har kechikish uchun kunlik maoshning 2%
        deductions["late_arrivals"] = {
            "days": late_days,
            "amount": round(late_penalty, 2)
        }
    
    # Erta ketishlar uchun uderjhanie (har erta ketish uchun kichik jarim)
    if early_departure_days > 0:
        early_penalty = early_departure_days * (daily_salary * 0.03)  # Har erta ketish uchun kunlik maoshning 3%
        deductions["early_departures"] = {
            "days": early_departure_days,
            "amount": round(early_penalty, 2)
        }
    
    # Kam ishlanhan soatlar uchun
    if worked_hours < expected_hours:
        shortage_hours = expected_hours - worked_hours
        if shortage_hours > 2:  # 2 soatdan ko'p kamchlik bo'lsa
            shortage_deduction = shortage_hours * hourly_salary
            deductions["hour_shortage"] = {
                "hours": round(shortage_hours, 2),
                "amount": round(shortage_deduction, 2)
            }
    
    # Umumiy uderzhaniya
    total_deductions = sum(item["amount"] for item in deductions.values())
    final_salary = base_salary - total_deductions
    
    return {
        "base_salary": round(base_salary, 2),
        "daily_salary": round(daily_salary, 2),
        "hourly_salary": round(hourly_salary, 2),
        "total_deductions": round(total_deductions, 2),
        "final_salary": round(final_salary, 2),
        "deduction_breakdown": deductions,
        "worked_hours": round(worked_hours, 2),
        "expected_hours": round(expected_hours, 2)
    }
