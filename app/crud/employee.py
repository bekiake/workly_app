import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_
from typing import Optional, List
from app.schemas import employee as employee_schema
from app.models import employee as employee_model

async def create_employee(db: AsyncSession, employee: employee_schema.EmployeeCreate):
    employee_uuid = str(uuid.uuid4())
    
    db_employee = employee_model.Employee(
        uuid=employee_uuid,
        full_name=employee.full_name,
        position=employee.position,
        phone=employee.phone,
        photo=employee.photo
    )
    db.add(db_employee)
    await db.commit()
    await db.refresh(db_employee)
    return db_employee

async def get_employee_by_id(db: AsyncSession, employee_id: int):
    result = await db.execute(
        select(employee_model.Employee).where(employee_model.Employee.id == employee_id)
    )
    return result.scalar_one_or_none()

async def get_employee_by_uuid(db: AsyncSession, employee_uuid: str):
    result = await db.execute(
        select(employee_model.Employee).where(employee_model.Employee.uuid == employee_uuid)
    )
    return result.scalar_one_or_none()

async def get_employee_by_qr_code(db: AsyncSession, qr_code: str):
    """QR code UUID bilan bir xil"""
    return await get_employee_by_uuid(db, qr_code)

async def get_employees(db: AsyncSession, skip: int = 0, limit: int = 100, include_inactive: bool = False):
    query = select(employee_model.Employee)
    
    if not include_inactive:
        query = query.where(employee_model.Employee.is_active == True)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def update_employee(db: AsyncSession, employee_id: int, employee_update: employee_schema.EmployeeUpdate):
    db_employee = await get_employee_by_id(db, employee_id)
    if not db_employee:
        return None
    
    update_data = employee_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_employee, field, value)
    
    await db.commit()
    await db.refresh(db_employee)
    return db_employee

async def delete_employee(db: AsyncSession, employee_id: int):
    db_employee = await get_employee_by_id(db, employee_id)
    if not db_employee:
        return None
    
    # Soft delete
    db_employee.is_active = False
    await db.commit()
    return db_employee

async def get_employees_with_attendance_count(db: AsyncSession):
    result = await db.execute(select(employee_model.Employee))
    return result.scalars().all()


async def get_employee_by_telegram_id(db: AsyncSession, telegram_id: int):
    """Найти сотрудника по Telegram ID"""
    result = await db.execute(
        select(employee_model.Employee).where(employee_model.Employee.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def link_telegram_to_employee(db: AsyncSession, employee_id: int, telegram_id: int):
    """Привязать Telegram ID к сотруднику"""
    # Проверяем, что telegram_id не привязан к другому сотруднику
    existing = await get_employee_by_telegram_id(db, telegram_id)
    if existing and existing.id != employee_id:
        return None, "Telegram ID уже привязан к другому сотруднику"
    
    # Обновляем сотрудника
    db_employee = await get_employee_by_id(db, employee_id)
    if not db_employee:
        return None, "Сотрудник не найден"
    
    db_employee.telegram_id = telegram_id
    await db.commit()
    await db.refresh(db_employee)
    return db_employee, "Успешно привязано"
