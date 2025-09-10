from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime
from typing import List
from app.core.database import get_db
from app.crud import attendance as crud_attendance
from app.crud import employee as crud_employee
from app.schemas.attendance import QRScanRequest
from app.models.attendance import CheckTypeEnum

router = APIRouter(prefix="/mobile", tags=["Mobile App"])

@router.post("/scan")
async def mobile_qr_scan(qr_request: QRScanRequest, db: AsyncSession = Depends(get_db)):
    """
    Mobil ilova uchun QR kod skanerlash
    Planshet ilovasida foydalanish uchun
    """
    
    # Employee ni topish
    employee = await crud_employee.get_employee_by_uuid(db, qr_request.qr_code)
    if not employee:
        return {
            "success": False,
            "message": "QR kod yaroqsiz! Iltimos, to'g'ri QR kodni skanerlang.",
            "error_code": "INVALID_QR"
        }
    
    if not employee.is_active:
        return {
            "success": False,
            "message": "Sizning hisobingiz faol emas. HR bo'limiga murojaat qiling.",
            "error_code": "INACTIVE_EMPLOYEE"
        }
    
    # Bugun allaqachon shu turdagi belgi qo'yilgan yoki yo'qligini tekshirish
    already_checked = await crud_attendance.check_if_already_checked_today(
        db, employee.id, qr_request.check_type.value
    )
    
    if already_checked:
        action = "kelganingizni" if qr_request.check_type.value == "IN" else "ketganingizni"
        return {
            "success": False,
            "message": f"Siz bugun allaqachon {action} belgilab qo'ygansiz!",
            "error_code": "ALREADY_CHECKED",
            "employee_name": employee.full_name
        }
    
    # Davomat yaratish
    attendance = await crud_attendance.create_attendance_by_qr(db, qr_request)
    if not attendance:
        return {
            "success": False,
            "message": "Texnik xatolik yuz berdi. Qaytadan urinib ko'ring.",
            "error_code": "SYSTEM_ERROR"
        }
    
    # Agar error qaytarilgan bo'lsa
    if isinstance(attendance, dict) and "error" in attendance:
        return {
            "success": False,
            "message": attendance["error"],
            "error_code": "VALIDATION_ERROR",
            "employee_name": employee.full_name
        }
    
    # Agar success dict qaytarilgan bo'lsa
    if isinstance(attendance, dict) and "success" in attendance:
        actual_attendance = attendance["attendance"]
    else:
        actual_attendance = attendance
    
    # Muvaffaqiyatli javob
    action = "Ishga keldingiz" if qr_request.check_type.value == "IN" else "Ishdan ketdingiz"
    
    response = {
        "success": True,
        "message": f"✅ {action}!",
        "employee_photo": employee.photo if employee.photo else None,
        "employee_name": employee.full_name,
        "employee_position": employee.position.value if employee.position else "Belgilanmagan",
        "check_time": actual_attendance.check_time.strftime("%Y-%m-%d %H:%M:%S"),
        "check_type": actual_attendance.check_type.value,
        "is_late": actual_attendance.is_late
    }
    
    # Kechikish haqida ogohlantirish
    if actual_attendance.is_late and qr_request.check_type.value == "IN":
        response["warning"] = "⚠️ Siz kechikdingiz! (9:00 dan keyin)"
    
    return response

@router.get("/status/{employee_uuid}")
async def get_mobile_employee_status(employee_uuid: str, db: AsyncSession = Depends(get_db)):
    """
    Mobil ilova uchun xodim holatini tekshirish
    """
    employee = await crud_employee.get_employee_by_uuid(db, employee_uuid)
    if not employee:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    
    # Oxirgi davomat holatini olish
    last_attendance = await crud_attendance.get_employee_last_status(db, employee.id)
    
    today = date.today()
    
    if not last_attendance or last_attendance.check_time.date() != today:
        return {
            "employee_name": employee.full_name,
            "status": "not_checked_in",
            "message": "Bugun hali ishga kelmagan",
            "can_check_in": True,
            "can_check_out": False
        }
    
    # Oxirgi holat bo'yicha qaror qabul qilish
    if last_attendance.check_type.value == "IN":
        return {
            "employee_name": employee.full_name,
            "status": "checked_in",
            "message": f"Ishga kelgan: {last_attendance.check_time.strftime('%H:%M')}",
            "check_time": last_attendance.check_time.strftime("%Y-%m-%d %H:%M:%S"),
            "is_late": last_attendance.is_late,
            "can_check_in": False,
            "can_check_out": True
        }
    else:  # check_type == "OUT"
        return {
            "employee_name": employee.full_name,
            "status": "checked_out", 
            "message": f"Ishdan ketgan: {last_attendance.check_time.strftime('%H:%M')}",
            "check_time": last_attendance.check_time.strftime("%Y-%m-%d %H:%M:%S"),
            "can_check_in": False,
            "can_check_out": False
        }

@router.get("/employee/{employee_uuid}")
async def get_mobile_employee_info(employee_uuid: str, db: AsyncSession = Depends(get_db)):
    """
    UUID bo'yicha xodim ma'lumotlarini olish (Mobil ilova uchun)
    """
    employee = await crud_employee.get_employee_by_uuid(db, employee_uuid)
    if not employee:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    
    return {
        "id": employee.id,
        "uuid": employee.uuid,
        "full_name": employee.full_name,
        "position": employee.position.value if employee.position else None,
        "phone": employee.phone,
        "photo": employee.photo,
        "is_active": employee.is_active
    }

@router.get("/today-attendance/{employee_id}")
async def get_today_attendance(employee_id: int, db: AsyncSession = Depends(get_db)):
    """
    Xodimning bugungi davomat ma'lumotlari
    """
    today = date.today()
    attendance_list = await crud_attendance.get_attendance_by_employee(
        db, employee_id, start_date=today, end_date=today
    )
    
    result = []
    for attendance in attendance_list:
        result.append({
            "id": attendance.id,
            "check_type": attendance.check_type.value,
            "check_time": attendance.check_time.strftime("%Y-%m-%d %H:%M:%S"),
            "is_late": attendance.is_late,
            "is_early_departure": attendance.is_early_departure
        })
    
    return {
        "employee_id": employee_id,
        "date": today.strftime("%Y-%m-%d"),
        "attendance": result,
        "total_records": len(result)
    }

@router.post("/check-status")
async def check_mobile_status(qr_request: QRScanRequest, db: AsyncSession = Depends(get_db)):
    """
    QR kod skanerlashdan oldin holatni tekshirish
    (Actual scan qilmasdan, faqat holat ko'rish uchun)
    """
    employee = await crud_employee.get_employee_by_uuid(db, qr_request.qr_code)
    if not employee:
        return {
            "valid": False,
            "message": "QR kod yaroqsiz",
            "error_code": "INVALID_QR"
        }
    
    if not employee.is_active:
        return {
            "valid": False,
            "message": "Xodim hisobi faol emas",
            "error_code": "INACTIVE_EMPLOYEE"
        }
    
    # Bugun shu turdagi check mavjudligini tekshirish
    already_checked = await crud_attendance.check_if_already_checked_today(
        db, employee.id, qr_request.check_type.value
    )
    
    if already_checked:
        action = "kelgan" if qr_request.check_type.value == "IN" else "ketgan"
        return {
            "valid": False,
            "message": f"Bugun allaqachon {action} deb belgilangan",
            "error_code": "ALREADY_CHECKED",
            "employee": {
                "name": employee.full_name,
                "position": employee.position.value if employee.position else None
            }
        }
    
    return {
        "valid": True,
        "message": "Scan qilish mumkin",
        "employee": {
            "name": employee.full_name,
            "position": employee.position.value if employee.position else None,
            "photo": employee.photo
        },
        "check_type": qr_request.check_type.value
    }
