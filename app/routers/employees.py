from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.crud import employee as crud_employee
from app.schemas import employee as schema_employee
from app.services.file_service import save_employee_photo, delete_employee_photo, get_photo_full_path
from app.core.database import get_db

router = APIRouter(prefix="/employees", tags=["Employees"])

@router.post("/", response_model=schema_employee.Employee)
async def create_employee(employee: schema_employee.EmployeeCreate, db: AsyncSession = Depends(get_db)):
    """Yangi xodim yaratish"""
    return await crud_employee.create_employee(db, employee)

@router.post("/with-photo", response_model=schema_employee.Employee)
async def create_employee_with_photo(
    full_name: str = Form(...),
    position: str = Form(...),
    phone: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """Yangi xodim yaratish (rasm bilan)"""
    
    # Xodim ma'lumotlarini yaratish
    employee_data = schema_employee.EmployeeCreate(
        full_name=full_name,
        position=position,
        phone=phone
    )
    
    # Xodimni yaratish
    new_employee = await crud_employee.create_employee(db, employee_data)
    
    # Agar rasm berilgan bo'lsa, uni yuklash
    if file and file.filename:
        try:
            photo_url = await save_employee_photo(file, new_employee.id)
            
            # Xodim ma'lumotlarini rasm URL bilan yangilash
            from app.schemas.employee import EmployeeUpdate
            update_data = EmployeeUpdate(photo=photo_url)
            updated_employee = await crud_employee.update_employee(db, new_employee.id, update_data)
            
            return updated_employee
        except Exception as e:
            # Agar rasm yuklashda xatolik bo'lsa, xodimni o'chirish
            await crud_employee.delete_employee(db, new_employee.id)
            raise HTTPException(status_code=400, detail=f"Rasm yuklashda xatolik: {str(e)}")
    
    return new_employee

@router.get("/", response_model=List[schema_employee.Employee])
async def get_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """Barcha xodimlarni olish"""
    return await crud_employee.get_employees(db, skip=skip, limit=limit, include_inactive=include_inactive)

@router.get("/{employee_id}", response_model=schema_employee.Employee)
async def get_employee(employee_id: int, db: AsyncSession = Depends(get_db)):
    """ID bo'yicha xodimni olish"""
    employee = await crud_employee.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    return employee

@router.get("/uuid/{employee_uuid}", response_model=schema_employee.Employee)
async def get_employee_by_uuid(employee_uuid: str, db: AsyncSession = Depends(get_db)):
    """UUID bo'yicha xodimni olish"""
    employee = await crud_employee.get_employee_by_uuid(db, employee_uuid)
    if not employee:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    return employee

@router.put("/{employee_id}", response_model=schema_employee.Employee)
async def update_employee(
    employee_id: int, 
    employee_update: schema_employee.EmployeeUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """Xodim ma'lumotlarini yangilash"""
    employee = await crud_employee.update_employee(db, employee_id, employee_update)
    if not employee:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    return employee

@router.delete("/{employee_id}", response_model=schema_employee.Employee)
async def delete_employee(employee_id: int, db: AsyncSession = Depends(get_db)):
    """Xodimni o'chirish (soft delete)"""
    employee = await crud_employee.delete_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    return employee

@router.post("/{employee_id}/photo")
async def upload_employee_photo(
    employee_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Xodim rasmini yuklash"""
    
    # Xodimni tekshirish
    employee = await crud_employee.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    
    # Eski rasmni o'chirish
    if employee.photo:
        await delete_employee_photo(employee.photo)
    
    # Yangi rasmni saqlash
    photo_url = await save_employee_photo(file, employee_id)
    
    # DB da yangilash
    from app.schemas.employee import EmployeeUpdate
    update_data = EmployeeUpdate(photo=photo_url)
    updated_employee = await crud_employee.update_employee(db, employee_id, update_data)
    
    return {
        "message": "Rasm muvaffaqiyatli yuklandi",
        "photo_url": photo_url,
        "employee": updated_employee
    }

@router.get("/{employee_id}/photo")
async def get_employee_photo(employee_id: int, db: AsyncSession = Depends(get_db)):
    """Xodim rasmini olish"""
    
    employee = await crud_employee.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    
    if not employee.photo:
        raise HTTPException(status_code=404, detail="Xodim rasmi mavjud emas")
    
    file_path = get_photo_full_path(employee.photo)
    if not file_path:
        raise HTTPException(status_code=404, detail="Rasm fayli topilmadi")
    
    return FileResponse(
        file_path,
        media_type="image/jpeg",
        filename=f"employee_{employee_id}_photo.jpg"
    )

@router.delete("/{employee_id}/photo")
async def delete_employee_photo_endpoint(employee_id: int, db: AsyncSession = Depends(get_db)):
    """Xodim rasmini o'chirish"""
    
    employee = await crud_employee.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    
    if not employee.photo:
        raise HTTPException(status_code=404, detail="Xodim rasmi mavjud emas")
    
    # Rasmni o'chirish
    deleted = await delete_employee_photo(employee.photo)
    
    # DB dan URL ni o'chirish
    from app.schemas.employee import EmployeeUpdate
    update_data = EmployeeUpdate(photo=None)
    updated_employee = await crud_employee.update_employee(db, employee_id, update_data)
    
    return {
        "message": "Rasm muvaffaqiyatli o'chirildi",
        "deleted": deleted,
        "employee": updated_employee
    }
