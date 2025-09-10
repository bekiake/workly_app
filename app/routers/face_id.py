from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.crud.employee import get_employee_by_id
from app.crud.attendance import create_attendance, check_if_already_checked_today
from app.services.simple_face_id import simple_face_service as face_service
# from app.services.face_id import face_service
from app.schemas.attendance import AttendanceCreate, CheckTypeEnum as CheckType
from datetime import datetime
from typing import Optional
from pydantic import Field
import base64

router = APIRouter(prefix="/face-id", tags=["Face ID"])

def get_error_suggestions(error_type: str) -> list:
    """Xatolik turiga qarab takliflar berish"""
    suggestions = {
        "duplicate_face": [
            "Bu yuz allaqachon ro'yxatga olingan",
            "Boshqa burchakdan rasm oling",
            "Yoki mavjud yuzlarni o'chirib, qaytadan urining"
        ],
        "face_belongs_to_other": [
            "Bu yuz boshqa xodimga tegishli",
            "To'g'ri xodimning rasmini yuklang",
            "Agar bu xato bo'lsa, admin bilan bog'laning"
        ],
        "max_faces_reached": [
            "Maksimal yuz soni chegarasiga yetildi",
            "Eski yuzlarni o'chiring",
            "Yoki admin bilan bog'lanib, limitni oshiring"
        ],
        "no_face_detected": [
            "Rasmda yuz aniqlanmadi",
            "Yaxshi yorug'likda rasm oling",
            "Yuzni to'g'ri yo'naltiring"
        ],
        "multiple_faces": [
            "Rasmda bir nechta yuz bor",
            "Faqat bitta yuz bo'lishi kerak",
            "Yakka rasm yuklang"
        ]
    }
    return suggestions.get(error_type, ["Yana bir bor urinib ko'ring"])

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
                        "face_count": result["face_count"],
                        "max_faces": result.get("max_faces", 3),
                        "can_add_more": result.get("can_add_more", False)
                    },
                    "registration_info": {
                        "image_saved": result.get("image_saved"),
                        "face_encoding_created": True,
                        "registration_time": datetime.now().isoformat(),
                        "method": result.get("method", "Simple Face Recognition")
                    },
                    "success": True,
                    "status": "registered"
                }
            )
        else:
            # Xatolik turini aniqlash
            error_type = "unknown"
            if "allaqachon ushbu xodim uchun ro'yxatga olingan" in result["message"]:
                error_type = "duplicate_face"
            elif "boshqa xodimga" in result["message"]:
                error_type = "face_belongs_to_other"
            elif "maksimal" in result["message"]:
                error_type = "max_faces_reached"
            elif "yuz topilmadi" in result["message"]:
                error_type = "no_face_detected"
            elif "bir nechta yuz" in result["message"]:
                error_type = "multiple_faces"
            
            return JSONResponse(
                status_code=400,
                content={
                    "message": result["message"],
                    "success": False,
                    "error_type": error_type,
                    "employee": {
                        "id": employee_id,
                        "name": employee.full_name
                    },
                    "details": result,
                    "suggestions": get_error_suggestions(error_type),
                    "method": "Simple Face Recognition"
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
        print(f"Recognized Employee ID: {employee_id}")
        # Helper funksiya orqali davomat yaratish
        try:
            attendance = await create_face_id_attendance(db, employee_id, check_type)
            print(f"Attendance created: {attendance}")
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
    can_add_info = face_service.can_add_more_faces(employee_id)
    
    return {
        "employee": {
            "id": employee_id,
            "name": employee.full_name,
            "position": employee.position.value
        },
        "face_data": {
            "registered_faces": face_count,
            "is_registered": face_count > 0,
            "status": "Ro'yxatga olingan" if face_count > 0 else "Ro'yxatga olinmagan",
            "can_add_more": can_add_info["can_add"],
            "max_faces": can_add_info["max_faces"],
            "remaining_slots": can_add_info["remaining_slots"]
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

@router.post("/check-duplicate")
async def check_face_duplicate(
    image: UploadFile = File(...),
    employee_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Yuz duplikatligi tekshiruvi (registratsiya qilishdan oldin)"""
    
    # Rasm formatini tekshirish
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Faqat rasm fayllari qabul qilinadi")
    
    try:
        # Rasm ma'lumotlarini o'qish va tayyorlash
        image_data = await image.read()
        image_b64 = base64.b64encode(image_data)
        
        # Yuz encoding olish
        import face_recognition
        from PIL import Image
        from io import BytesIO
        import numpy as np
        
        if image_b64.startswith(b'data:image'):
            image_b64 = image_b64.split(b',')[1]
        
        image_bytes = base64.b64decode(image_b64)
        image = Image.open(BytesIO(image_bytes))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        image_array = np.array(image)
        face_locations = face_recognition.face_locations(image_array)
        
        if not face_locations:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Rasmda yuz topilmadi",
                    "can_register": False
                }
            )
        
        if len(face_locations) > 1:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Rasmda bir nechta yuz topildi. Faqat bitta yuz bo'lishi kerak",
                    "can_register": False
                }
            )
        
        face_encodings = face_recognition.face_encodings(image_array, face_locations)
        if not face_encodings:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Yuz ma'lumotlarini olishda xatolik",
                    "can_register": False
                }
            )
        
        face_encoding = face_encodings[0]
        
        # Boshqa xodimlar orasida tekshirish
        duplicate_check = face_service.check_face_exists_for_other_employee(
            face_encoding, 
            exclude_employee_id=employee_id
        )
        
        if duplicate_check["exists"]:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": f"Bu yuz boshqa xodimga ({duplicate_check['employee_name']}) tegishli",
                    "can_register": False,
                    "duplicate_info": duplicate_check
                }
            )
        
        # Agar employee_id berilgan bo'lsa, shu xodimning yuzlari orasida tekshirish
        if employee_id:
            employee = await get_employee_by_id(db, employee_id)
            if not employee:
                raise HTTPException(status_code=404, detail="Xodim topilmadi")
            
            # Shu xodimning mavjud yuzlari orasida tekshirish
            if employee_id in face_service.known_faces:
                for existing_encoding in face_service.known_faces[employee_id]:
                    distance = face_recognition.face_distance([existing_encoding], face_encoding)[0]
                    if distance < face_service.tolerance:
                        return JSONResponse(
                            status_code=400,
                            content={
                                "success": False,
                                "message": "Bu yuz ushbu xodim uchun allaqachon ro'yxatga olingan",
                                "can_register": False,
                                "similarity": f"{(1-distance)*100:.1f}%"
                            }
                        )
            
            # Maksimal yuz soni tekshiruvi
            can_add_info = face_service.can_add_more_faces(employee_id)
            if not can_add_info["can_add"]:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": f"Maksimal {face_service.max_faces_per_employee} ta yuz ruxsat etiladi",
                        "can_register": False,
                        "face_limit_info": can_add_info
                    }
                )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Yuz ro'yxatga olish uchun mos",
                "can_register": True,
                "face_quality": "Yaxshi"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tekshirishda xatolik: {str(e)}")

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
