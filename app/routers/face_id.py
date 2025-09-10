from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud.employee import get_employee_by_id
from app.crud.attendance import create_attendance, check_if_already_checked_today
from app.services.simple_face_id import simple_face_service as face_service
from app.schemas.attendance import AttendanceCreate, CheckTypeEnum as CheckType
from datetime import datetime
from typing import Optional
from pydantic import Field
import base64

router = APIRouter(prefix="/face-id", tags=["Face ID"])

async def create_face_id_attendance(db: AsyncSession, employee_id: int, check_type: CheckType):
    """Face ID orqali davomat yaratish uchun helper funksiya"""
    
    # Employee ma'lumotlarini olish
    employee = await get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    
    # Bugun allaqachon shu turdagi belgi qo'yilgan yoki yo'qligini tekshirish
    already_checked = await check_if_already_checked_today(
        db, employee_id, check_type.value
    )
    
    if already_checked:
        action = "kelgansiz" if check_type.value == "IN" else "ketgansiz"
        raise HTTPException(
            status_code=400, 
            detail=f"Siz bugun allaqachon {action} deb belgilangansiz"
        )
    
    # Attendance yaratish - UUID kerak
    attendance_data = AttendanceCreate(
        employee_uuid=employee.uuid,
        check_type=check_type
    )
    
    return await create_attendance(db, attendance_data)

@router.post("/register")
async def register_employee_face(
    employee_id: int = Form(...),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Xodimning yuzini ro'yxatga olish"""
    
    # Xodim mavjudligini tekshirish
    employee = await get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    
    # Rasm formatini tekshirish
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Faqat rasm fayllari qabul qilinadi")
    
    try:
        # Rasm ma'lumotlarini o'qish
        image_data = await image.read()
        
        # Base64 ga kodlash
        image_b64 = base64.b64encode(image_data)
        
        # Face ID servisiga yuborish
        result = face_service.register_employee_face(
            employee_id=employee_id,
            employee_name=employee.full_name,
            image_data=image_b64
        )
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "message": result["message"],
                    "employee": {
                        "id": employee_id,
                        "name": employee.full_name,
                        "face_count": result["face_count"]
                    },
                    "success": True
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "message": result["message"],
                    "success": False,
                    "details": result
                }
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Serverda xatolik: {str(e)}")

@router.post("/recognize")
async def recognize_face_attendance(
    image: UploadFile = File(...),
    check_type: CheckType = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Yuz tanish orqali davomat belgilash"""
    
    # Rasm formatini tekshirish
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Faqat rasm fayllari qabul qilinadi")
    
    try:
        # Rasm ma'lumotlarini o'qish
        image_data = await image.read()
        
        # Base64 ga kodlash
        image_b64 = base64.b64encode(image_data)
        
        # Yuzni tanish
        recognition_result = face_service.recognize_face(image_b64)
        
        if not recognition_result["success"]:
            return JSONResponse(
                status_code=400,
                content={
                    "message": recognition_result["message"],
                    "success": False,
                    "recognized": False
                }
            )
        
        employee_id = recognition_result["employee_id"]
        
        # Helper funksiya orqali davomat yaratish
        try:
            attendance = await create_face_id_attendance(db, employee_id, check_type)
            employee = await get_employee_by_id(db, employee_id)  # Employee ma'lumotlarini olish
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "message": e.detail,
                    "success": False,
                    "recognized": True,
                    "employee_id": employee_id
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Davomat muvaffaqiyatli belgilandi: {recognition_result['employee_name']}",
                "success": True,
                "recognized": True,
                "employee": {
                    "id": employee_id,
                    "name": employee.full_name,
                    "position": employee.position.value
                },
                "attendance": {
                    "id": attendance.id,
                    "check_type": check_type.value,
                    "check_time": attendance.check_time.isoformat(),
                    "is_late": attendance.is_late,
                    "is_early_departure": attendance.is_early_departure
                },
                "recognition": {
                    "confidence": recognition_result["confidence"],
                    "distance": recognition_result.get("distance", 0)
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Serverda xatolik: {str(e)}")

@router.get("/employee/{employee_id}/faces")
async def get_employee_face_info(
    employee_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Xodimning yuz ma'lumotlari haqida ma'lumot"""
    
    # Xodim mavjudligini tekshirish
    employee = await get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    
    face_count = face_service.get_employee_faces_count(employee_id)
    
    return {
        "employee": {
            "id": employee_id,
            "name": employee.full_name,
            "position": employee.position.value
        },
        "face_data": {
            "registered_faces": face_count,
            "is_registered": face_count > 0,
            "status": "Ro'yxatga olingan" if face_count > 0 else "Ro'yxatga olinmagan"
        }
    }

@router.delete("/employee/{employee_id}/faces")
async def delete_employee_faces(
    employee_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Xodimning barcha yuz ma'lumotlarini o'chirish"""
    
    # Xodim mavjudligini tekshirish
    employee = await get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    
    result = face_service.delete_employee_faces(employee_id)
    
    if result["success"]:
        return JSONResponse(
            status_code=200,
            content={
                "message": result["message"],
                "employee": {
                    "id": employee_id,
                    "name": employee.full_name
                },
                "deleted_faces": result["deleted_faces"],
                "success": True
            }
        )
    else:
        return JSONResponse(
            status_code=400,
            content={
                "message": result["message"],
                "success": False
            }
        )

@router.get("/statistics")
async def get_face_id_statistics():
    """Face ID tizimi statistikalari"""
    
    stats = face_service.get_statistics()
    
    return {
        "face_id_statistics": stats,
        "system_info": {
            "tolerance": stats["tolerance"],
            "description": "Face tanish tizimi statistikalari"
        }
    }

@router.post("/test-recognition")
async def test_face_recognition(
    image: UploadFile = File(...),
):
    """Yuzni tanish testini amalga oshirish (davomat belgilamasdan)"""
    
    # Rasm formatini tekshirish
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Faqat rasm fayllari qabul qilinadi")
    
    try:
        # Rasm ma'lumotlarini o'qish
        image_data = await image.read()
        
        # Base64 ga kodlash
        image_b64 = base64.b64encode(image_data)
        
        # Yuzni tanish
        result = face_service.recognize_face(image_b64)
        
        return {
            "test_result": result,
            "description": "Bu faqat test. Davomat belgilanmadi."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test paytida xatolik: {str(e)}")

@router.get("/health")
async def face_id_health_check():
    """Face ID tizimi ishlash holatini tekshirish"""
    
    try:
        stats = face_service.get_statistics()
        
        return {
            "status": "healthy",
            "message": "Face ID tizimi normal ishlayapti",
            "registered_employees": stats["total_employees"],
            "total_faces": stats["total_faces"],
            "system_ready": True
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Face ID tizimida muammo: {str(e)}",
            "system_ready": False
        }
