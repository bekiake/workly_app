from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import FileResponse
from datetime import date, datetime
from typing import List, Optional
from app.crud import attendance as crud_attendance
from app.schemas import attendance as schema_attendance
from app.core.database import get_db
from app.services.reports import generate_monthly_report
from app.crud.employee import get_employee_by_uuid

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.post("/qr-scan")
async def scan_qr_code(qr_request: schema_attendance.QRScanRequest, db: AsyncSession = Depends(get_db)):
    """QR kod skanerlash va davomat belgilash"""
    
    result = await crud_attendance.create_attendance_by_qr(db, qr_request)
    
    # Yangilangan create_attendance_by_qr error qaytarishi mumkin
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Muvaffaqiyatli natija
    if isinstance(result, dict) and "success" in result:
        return {
            "success": True,
            "message": result["message"],
            "attendance": result["attendance"]
        }
    
    # Eski format uchun fallback
    return result

@router.get("/employee/{employee_id}", response_model=List[schema_attendance.Attendance])
async def get_employee_attendance(
    employee_id: int, 
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Xodimning davomat tarixini olish"""
    return await crud_attendance.get_attendance_by_employee(db, employee_id, start_date, end_date)

@router.get("/daily/{target_date}")
async def get_daily_attendance(target_date: date, db: AsyncSession = Depends(get_db)):
    """Kunlik davomat ma'lumotlari"""
    attendances = await crud_attendance.get_daily_attendance(db, target_date)
    
    result = []
    for attendance in attendances:
        result.append({
            "id": attendance.id,
            "employee_name": attendance.employee.full_name,
            "employee_position": attendance.employee.position if attendance.employee.position else "N/A",
            "check_type": attendance.check_type.value,
            "check_time": attendance.check_time,
            "is_late": attendance.is_late
        })
    
    return result

@router.get("/status/{employee_id}")
async def get_employee_current_status(employee_id: int, db: AsyncSession = Depends(get_db)):
    """Xodimning hozirgi holatini olish (ishda yoki uyda)"""
    last_attendance = await crud_attendance.get_employee_last_status(db, employee_id)
    
    if not last_attendance:
        return {"status": "unknown", "message": "Hech qanday davomat ma'lumoti yo'q"}
    
    # Bugungi sanada oxirgi davomat
    today = date.today()
    if last_attendance.check_time.date() != today:
        return {"status": "out", "message": "Bugun hali kelmagan"}
    
    if last_attendance.check_type.value == "in":
        return {
            "status": "in", 
            "message": "Ishda", 
            "check_time": last_attendance.check_time,
            "is_late": last_attendance.is_late
        }
    else:
        return {
            "status": "out", 
            "message": "Ketgan", 
            "check_time": last_attendance.check_time
        }

@router.get("/report/monthly/{year}/{month}")
async def get_monthly_report(year: int, month: int, db: AsyncSession = Depends(get_db)):
    """Oylik hisobot ma'lumotlarini olish - yangilangan versiya"""
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Oy 1-12 orasida bo'lishi kerak")
    
    report_data = await crud_attendance.get_monthly_attendance_report(db, month, year)
    
    # report_data endi list[dict] formatida keladi
    return {
        "month": month,
        "year": year,
        "reports": report_data
    }

@router.get("/report/download/daily/{target_date}")
async def download_daily_report(target_date: date, db: AsyncSession = Depends(get_db)):
    """Kunlik hisobotni Excel fayl sifatida yuklab olish"""
    from app.services.reports import generate_daily_report, delete_file_after_delay
    
    file_path = await generate_daily_report(db, target_date)
    
    # Faylni yuklab olingandan keyin 5 daqiqada o'chirish
    import asyncio
    asyncio.create_task(delete_file_after_delay(file_path, 300))
    
    return FileResponse(
        file_path, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        filename=f"kunlik_davomat_{target_date}.xlsx"
    )

@router.get("/report/download/{year}/{month}")
async def download_monthly_report(year: int, month: int, db: AsyncSession = Depends(get_db)):
    """Oylik hisobotni Excel fayl sifatida yuklab olish"""
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Oy 1-12 orasida bo'lishi kerak")
    
    file_path = await generate_monthly_report(db, year, month)
    
    # Faylni yuklab olingandan keyin 5 daqiqada o'chirish uchun background task
    import asyncio
    from app.services.reports import delete_file_after_delay
    asyncio.create_task(delete_file_after_delay(file_path, 300))  # 5 daqiqa
    
    return FileResponse(
        file_path, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        filename=f"davomat_hisoboti_{year}_{month:02d}.xlsx"
    )

@router.get("/report/daily/{target_date}")
async def download_daily_report(target_date: str, db: AsyncSession = Depends(get_db)):
    """Kunlik batafsil hisobotni Excel fayl sifatida yuklab olish"""
    try:
        from datetime import datetime
        date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Sana formati noto'g'ri. YYYY-MM-DD formatida kiriting")
    
    from app.services.reports import generate_daily_report
    file_path = await generate_daily_report(db, date_obj)
    
    # Faylni yuklab olingandan keyin 5 daqiqada o'chirish uchun background task
    import asyncio
    from app.services.reports import delete_file_after_delay
    asyncio.create_task(delete_file_after_delay(file_path, 300))  # 5 daqiqa
    
    return FileResponse(
        file_path, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        filename=f"kunlik_batafsil_{target_date}.xlsx"
    )

@router.get("/report/detailed/{year}/{month}")
async def download_detailed_monthly_report(year: int, month: int, db: AsyncSession = Depends(get_db)):
    """Batafsil oylik hisobotni Excel fayl sifatida yuklab olish"""
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Oy 1-12 orasida bo'lishi kerak")
    
    from app.services.reports import generate_detailed_monthly_report
    file_path = await generate_detailed_monthly_report(db, year, month)
    
    # Faylni yuklab olingandan keyin 5 daqiqada o'chirish uchun background task
    import asyncio
    from app.services.reports import delete_file_after_delay
    asyncio.create_task(delete_file_after_delay(file_path, 300))  # 5 daqiqa
    
    return FileResponse(
        file_path, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        filename=f"batafsil_hisoboti_{year}_{month:02d}.xlsx"
    )

@router.get("/statistics/employee/{employee_id}")
async def get_employee_statistics(
    employee_id: int,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020),
    db: AsyncSession = Depends(get_db)
):
    """Xodimning oylik statistikasi"""
    stats = await crud_attendance.get_employee_monthly_statistics(db, employee_id, month, year)
    return stats

@router.get("/statistics/daily/{employee_id}/{target_date}")
async def get_daily_work_hours(
    employee_id: int,
    target_date: date,
    db: AsyncSession = Depends(get_db)
):
    """Xodimning kunlik ish soatlari"""
    stats = await crud_attendance.calculate_daily_work_hours(db, employee_id, target_date)
    return stats

@router.get("/report/detailed/{year}/{month}")
async def get_detailed_monthly_report(
    year: int, 
    month: int, 
    db: AsyncSession = Depends(get_db)
):
    """Batafsil oylik hisobot - maosh hisob-kitoblari bilan"""
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Oy 1-12 orasida bo'lishi kerak")
    
    # Barcha faol xodimlar uchun batafsil statistika
    from app.crud.employee import get_employees
    employees = await get_employees(db, include_inactive=False)
    
    detailed_reports = []
    for employee in employees:
        stats = await crud_attendance.get_employee_monthly_statistics(db, employee.id, month, year)
        if not isinstance(stats, dict) or "error" in stats:
            continue
        detailed_reports.append(stats)
    
    # Umumiy statistika
    total_base_salary = sum(report["salary_info"]["base_salary"] for report in detailed_reports)
    total_final_salary = sum(report["salary_info"]["final_salary"] for report in detailed_reports)
    total_deductions = sum(report["salary_info"]["total_deductions"] for report in detailed_reports)
    
    return {
        "month": month,
        "year": year,
        "summary": {
            "total_employees": len(detailed_reports),
            "total_base_salary": round(total_base_salary, 2),
            "total_final_salary": round(total_final_salary, 2),
            "total_deductions": round(total_deductions, 2),
            "average_attendance_rate": round(
                sum(report["attendance_rate"] for report in detailed_reports) / len(detailed_reports)
                if detailed_reports else 0, 2
            ),
            "average_punctuality_rate": round(
                sum(report["punctuality_rate"] for report in detailed_reports) / len(detailed_reports)
                if detailed_reports else 0, 2
            )
        },
        "employee_reports": detailed_reports
    }

@router.get("/work-time/config")
async def get_work_time_config():
    """Ish vaqti sozlamalarini olish"""
    from app.crud.attendance import WORK_START_TIME, WORK_END_TIME
    
    return {
        "work_start": WORK_START_TIME.strftime("%H:%M"),
        "work_end": WORK_END_TIME.strftime("%H:%M"),
        "working_hours_per_day": 8.5,
        "check_in_window": "07:00 - 11:00",
        "check_out_window": "16:00 - 20:00",
        "lunch_time": "Yo'q",
        "salary_calculation": {
            "working_days_per_month": 22,
            "late_penalty": "0.5 soat har kechikish uchun",
            "absence_penalty": "To'liq kunlik maosh"
        }
    }
