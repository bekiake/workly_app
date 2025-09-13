from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime, timedelta
from typing import Optional
from app.core.database import get_db
from app.crud import attendance as crud_attendance, employee as crud_employee

router = APIRouter(prefix="/statistics", tags=["Statistics"])

@router.get("/overview")
async def get_statistics_overview(db: AsyncSession = Depends(get_db)):
    """Umumiy statistika - yangilangan versiya"""
    
    # Umumiy xodimlar soni
    total_employees = len(await crud_employee.get_employees(db))
    active_employees = len(await crud_employee.get_employees(db, include_inactive=False))
    
    # Bugungi statistika
    today = date.today()
    today_attendances = await crud_attendance.get_daily_attendance(db, today)
    
    checked_in_today = len(set(
        att.employee_id for att in today_attendances 
        if att.check_type.value == "IN"
    ))
    
    late_today = len([
        att for att in today_attendances 
        if att.check_type.value == "IN" and att.is_late
    ])
    
    # Hozir ishda bo'lganlar
    currently_in_office = 0
    employee_last_status = {}
    
    for att in today_attendances:
        emp_id = att.employee_id
        if emp_id not in employee_last_status or att.check_time > employee_last_status[emp_id]["time"]:
            employee_last_status[emp_id] = {
                "type": att.check_type.value,
                "time": att.check_time
            }
    
    currently_in_office = sum(1 for status in employee_last_status.values() if status["type"] == "IN")
    
    # Oylik statistika (joriy oy)
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_data = await crud_attendance.get_monthly_attendance_report(db, current_month, current_year)
    
    # Ish vaqti ma'lumotlari
    from app.crud.attendance import WORK_START_TIME, WORK_END_TIME
    
    return {
        "employees": {
            "total": total_employees,
            "active": active_employees,
            "inactive": total_employees - active_employees
        },
        "today": {
            "date": today,
            "checked_in": checked_in_today,
            "late_arrivals": late_today,
            "currently_in_office": currently_in_office,
            "attendance_rate": round((checked_in_today / active_employees * 100) if active_employees > 0 else 0, 2)
        },
        "work_schedule": {
            "start_time": WORK_START_TIME.strftime("%H:%M"),
            "end_time": WORK_END_TIME.strftime("%H:%M"),
            "working_hours_per_day": 8.5
        },
        "current_month": {
            "month": current_month,
            "year": current_year,
            "total_reports": len(monthly_data),
            "avg_attendance_rate": round(
                sum(report["attendance_rate"] for report in monthly_data) / len(monthly_data) 
                if monthly_data else 0, 2
            ),
            "avg_punctuality_rate": round(
                sum(report["punctuality_rate"] for report in monthly_data) / len(monthly_data) 
                if monthly_data else 0, 2
            )
        }
    }
    
    return {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "today": {
            "date": today.isoformat(),
            "checked_in": checked_in_today,
            "late_arrivals": late_today,
            "currently_in_office": currently_in_office,
            "attendance_rate": round((checked_in_today / active_employees * 100), 1) if active_employees > 0 else 0
        },
        "monthly": {
            "month": current_month,
            "year": current_year,
            "total_working_days": len(monthly_data),
            "average_attendance": round(sum(row.present_days for row in monthly_data) / len(monthly_data), 1) if monthly_data else 0,
            "total_late_days": sum(row.late_days for row in monthly_data)
        }
    }

@router.get("/employee/{employee_id}/monthly")
async def get_employee_monthly_stats(
    employee_id: int, 
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Xodimning oylik statistikasi"""
    
    if not month:
        month = datetime.now().month
    if not year:
        year = datetime.now().year
    
    # Xodimni tekshirish
    employee = await crud_employee.get_employee_by_id(db, employee_id)
    if not employee:
        return {"error": "Xodim topilmadi"}
    
    # Oylik ma'lumotlar
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    attendances = await crud_attendance.get_attendance_by_employee(db, employee_id, start_date, end_date)
    
    # Statistika hisoblash
    check_ins = [att for att in attendances if att.check_type.value == "IN"]
    check_outs = [att for att in attendances if att.check_type.value == "IN"]
    late_days = [att for att in check_ins if att.is_late]
    
    unique_days = set(att.check_time.date() for att in check_ins)
    
    return {
        "employee": {
            "id": employee.id,
            "name": employee.full_name,
            "position": employee.position.value if employee.position else None
        },
        "period": {
            "month": month,
            "year": year,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        "statistics": {
            "total_check_ins": len(check_ins),
            "total_check_outs": len(check_outs),
            "unique_working_days": len(unique_days),
            "late_days": len(late_days),
            "late_percentage": round((len(late_days) / len(check_ins) * 100), 1) if check_ins else 0
        }
    }

@router.get("/department/{position}")
async def get_department_stats(
    position: str,
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Bo'lim bo'yicha statistika"""
    
    if not month:
        month = datetime.now().month
    if not year:
        year = datetime.now().year
    
    # Bo'lim xodimlari
    try:
        # No need to import PositionEnum as position is now a string
        position_filter = position.lower() if position else None
    except ValueError:
        return {"error": "Noto'g'ri lavozim"}
    
    employees = await crud_employee.get_employees(db)
    department_employees = [emp for emp in employees if emp.position and emp.position.lower() == position_filter]
    
    if not department_employees:
        return {"error": "Ushbu bo'limda xodimlar topilmadi"}
    
    # Har bir xodim uchun statistika
    stats = []
    total_late = 0
    total_present = 0
    
    for emp in department_employees:
        emp_stats = await get_employee_monthly_stats(emp.id, month, year, db)
        if "error" not in emp_stats:
            stats.append(emp_stats)
            total_late += emp_stats["statistics"]["late_days"]
            total_present += emp_stats["statistics"]["unique_working_days"]
    
    return {
        "department": position.upper(),
        "period": {"month": month, "year": year},
        "summary": {
            "total_employees": len(department_employees),
            "average_working_days": round(total_present / len(stats), 1) if stats else 0,
            "total_late_days": total_late,
            "average_late_days": round(total_late / len(stats), 1) if stats else 0
        },
        "employees": stats
    }

@router.get("/trends/weekly")
async def get_weekly_trends(
    weeks_back: int = Query(4, ge=1, le=12),
    db: AsyncSession = Depends(get_db)
):
    """Haftalik trend ma'lumotlari"""
    
    trends = []
    
    for week in range(weeks_back):
        # Hafta boshini hisoblash
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday() + (week * 7))
        end_of_week = start_of_week + timedelta(days=6)
        
        # Haftalik ma'lumotlar
        week_attendances = []
        current_date = start_of_week
        
        while current_date <= end_of_week:
            daily_att = await crud_attendance.get_daily_attendance(db, current_date)
            week_attendances.extend(daily_att)
            current_date += timedelta(days=1)
        
        # Statistika
        check_ins = [att for att in week_attendances if att.check_type.value == "IN"]
        late_count = len([att for att in check_ins if att.is_late])
        
        trends.append({
            "week_start": start_of_week.isoformat(),
            "week_end": end_of_week.isoformat(),
            "total_check_ins": len(check_ins),
            "late_arrivals": late_count,
            "late_percentage": round((late_count / len(check_ins) * 100), 1) if check_ins else 0
        })
    
    return {
        "weeks_analyzed": weeks_back,
        "trends": list(reversed(trends))  # Eng eski haftadan boshlab
    }
